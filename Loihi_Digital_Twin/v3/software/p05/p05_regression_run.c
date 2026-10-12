/*
 * P05.1 standalone Cortex-A53 deployment-driven regression application.
 *
 * Distinct from accepted P03 fixed-run ELF, but links the SAME untouched
 * portable P03 scheduler and physical FPD128/DDR adapter/bridge. No PC
 * algorithmic control after the single XSDB con.
 *
 * P05G v1 header: physical 0x43FE0000, 256B.
 * P05G payload: physical 0x43F00000, <= 0xE0000.
 * P05R v1 result: physical 0x43FF0000, 256B.
 * Logical core k backing: 0x40000000 + k*0x80000.
 */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "p03_hw_xilinx_io.h"
#include "p03_hw_runtime_bridge.h"
#include "p03_mmio.h"
#include "p05_deployment.h"

#define P05_RESULT_MAGIC UINT32_C(0x52353050) /* bytes "P05R" */
#define P05_RESULT_OK UINT32_C(0x600D600D)
#define P05_RESULT_FAIL UINT32_C(0xDEAD0000)
#define P05_POLL_LIMIT UINT32_C(100000000)
#define P05_CORE_COUNT_LIMIT P05_DEPLOY_MAX_CORES

/* Retained in binary and validated by build/physical runner. */
static const volatile char p05_build_id[] =
    "P05_CONFIGURABLE_A53_REGRESSION_V1";

enum {
    E_WIDTH = 1, E_CONFIG = 2, E_RECORD = 3, E_ADAPTER = 4,
    E_REGISTER = 5, E_RUNTIME_INIT = 6, E_BIND = 7,
    E_RUNTIME = 8, E_RESULT = 9, E_CHECKPOINT = 10,
};

enum {
    R_MAGIC=0, R_VERSION=1, R_RESULT=2, R_ERROR=3,
    R_STEPS=4, R_COMPLETED_STEPS=5, R_CORES=6, R_SLOTS=7,
    R_RUNTIME_PHASE=8, R_FIRST_FAULT=9, R_FAULT_PHASE=10,
    R_DISPATCHES=11, R_PACKETS=12, R_BARRIERS=13,
    R_INITIAL_INS=14, R_REPLACEMENT_INS=15, R_RUNTIME_OUTS=16,
    R_FINAL_OUTS=17, R_EVICTIONS=18, R_HITS=19,
    R_PL_DISPATCH_LO=20, R_PL_DISPATCH_HI=21,
    R_PL_PAGE_LO=22, R_PL_PAGE_HI=23,
    R_PS_INFER_LO=24, R_PS_INFER_HI=25,
    R_PS_ROUTE_LO=26, R_PS_ROUTE_HI=27,
    R_PS_BARRIER_LO=28, R_PS_BARRIER_HI=29,
    R_PS_CONTROL_LO=30, R_PS_CONTROL_HI=31,
    R_CNTFRQ_HZ=32, R_HW_ID=33, R_HW_CAPS=34,
    R_HW_DISPATCHES=35, R_HW_PAGES=36, R_HW_LAST_PAGE_BYTES=37,
    R_HW_STATUS=38, R_HW_PAGE_PENDING=39,
    R_HW_READ_BURSTS=40, R_HW_WRITE_BURSTS=41,
    R_RESIDENT_DELIVERIES=42, R_INPUTS_CONSUMED=43,
    R_CHECKPOINTS_PASSED=44, R_FAILED_STEP=45,
    R_FAILED_CORE=46, R_FAILED_CLASS=47,
    R_EXPECTED_CRC=48, R_OBSERVED_CRC=49,
    R_HEADER_CRC=50, R_PAYLOAD_CRC=51,
    R_LAST_PACKET_LO=52, R_LAST_PACKET_HI=53,
    R_OBSERVATION_MODE=54, R_EXPECTED_EVENTS=55,
    R_EXPECTED_CHECKS=56, R_EXPECTED_DISPATCHES=57,
    R_DIAG_FLAGS=58, R_LAST_PAGE_ERROR=59,
    R_RESERVED_BASE=60
};

static volatile uint32_t *const result =
    (volatile uint32_t *)(uintptr_t)P05_DEPLOY_MAILBOX_BASE;
static const volatile uint8_t *const input_header =
    (const volatile uint8_t *)(uintptr_t)P05_DEPLOY_HEADER_BASE;
static const volatile uint8_t *const input_payload =
    (const volatile uint8_t *)(uintptr_t)P05_DEPLOY_PAYLOAD_BASE;
static p05_deployment_info deployment;
static p03_rt runtime;
static p03_hw_adapter hw;
static p03_hw_runtime_bridge bridge;
static p03_rt_ops ops;
static uint8_t service_order[P05_CORE_COUNT_LIMIT];
static uint32_t rank_of[P05_CORE_COUNT_LIMIT];
static uint32_t initial_crc[P05_CORE_COUNT_LIMIT];
static uint32_t first_error;
static volatile uint32_t final_outs;
static uint32_t event_cursor;
static uint32_t checkpoint_cursor;
static uint32_t resident_deliveries;
static uint32_t diag_flags;
static uint32_t failed_step, failed_core, failed_class;
static uint32_t expected_crc, observed_crc;
static uint64_t last_packet;
static int (*hardware_dispatch)(void *,uint8_t,uint8_t,uint32_t,uint8_t,
                                 uint32_t *,uint64_t *);
static int (*hardware_route)(void *,uint8_t,uint32_t,uint32_t,uint8_t,
                              uint32_t *);
static int (*hardware_barrier)(void *,uint32_t,uint8_t);

static void fence(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static void flush_result(void)
{
    fence();
    Xil_DCacheFlushRange((INTPTR)P05_DEPLOY_MAILBOX_BASE,256u);
    fence();
}
static void halt_forever(void)
{
    for (;;) __asm__ volatile("wfe");
}
static uint32_t little32(const volatile uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint32_t crc_update(uint32_t crc, uint8_t value)
{
    uint32_t b;
    crc ^= value;
    for (b=0;b<8u;++b)
        crc=(crc>>1)^((crc & 1u) ? UINT32_C(0xEDB88320) : 0u);
    return crc;
}
static uint32_t crc_physical(uintptr_t addr, uint32_t bytes)
{
    const volatile uint8_t *p=(const volatile uint8_t *)addr;
    uint32_t i,crc=UINT32_C(0xFFFFFFFF);
    Xil_DCacheInvalidateRange((INTPTR)addr,bytes);
    fence();
    for(i=0;i<bytes;++i) crc=crc_update(crc,p[i]);
    return crc ^ UINT32_C(0xFFFFFFFF);
}
static uint32_t crc_word(uint32_t lo, uint32_t hi, uint8_t length)
{
    uint32_t crc=UINT32_C(0xFFFFFFFF),i;
    for(i=0;i<length;++i) {
        uint8_t b=(uint8_t)((i<4u ? lo>>(8u*i) :
                                   hi>>(8u*(i-4u))) & 0xFFu);
        crc=crc_update(crc,b);
    }
    return crc ^ UINT32_C(0xFFFFFFFF);
}
static void put64(uint32_t word,uint64_t value)
{
    result[word]=(uint32_t)value;
    result[word+1]=(uint32_t)(value>>32);
}
static void snapshot(const p03_rt *rt)
{
    result[R_STEPS]=deployment.timesteps;
    result[R_COMPLETED_STEPS]=rt->counters.timesteps_completed;
    result[R_CORES]=deployment.core_count;
    result[R_SLOTS]=deployment.slot_count;
    result[R_RUNTIME_PHASE]=(uint32_t)rt->phase;
    result[R_FIRST_FAULT]=(uint32_t)rt->first_fault;
    result[R_FAULT_PHASE]=(uint32_t)rt->fault_phase;
    result[R_DISPATCHES]=rt->counters.logical_dispatches;
    result[R_PACKETS]=rt->counters.routed_packets;
    result[R_BARRIERS]=rt->counters.barriers;
    result[R_INITIAL_INS]=rt->counters.initial_page_ins;
    result[R_REPLACEMENT_INS]=rt->counters.page_ins;
    result[R_RUNTIME_OUTS]=rt->counters.page_outs;
    result[R_FINAL_OUTS]=final_outs;
    result[R_EVICTIONS]=rt->counters.evictions;
    result[R_HITS]=rt->counters.page_hits;
    put64(R_PL_DISPATCH_LO,rt->counters.pl_dispatch_cycles);
    put64(R_PL_PAGE_LO,rt->counters.pl_page_cycles);
    put64(R_PS_INFER_LO,rt->counters.ps_inference_ticks);
    put64(R_PS_ROUTE_LO,rt->counters.ps_route_ticks);
    put64(R_PS_BARRIER_LO,rt->counters.ps_barrier_ticks);
    put64(R_PS_CONTROL_LO,rt->counters.ps_control_ticks);
    result[R_HEADER_CRC]=deployment.header_crc32;
    result[R_PAYLOAD_CRC]=deployment.payload_crc32;
    result[R_INPUTS_CONSUMED]=event_cursor;
    result[R_CHECKPOINTS_PASSED]=checkpoint_cursor;
    result[R_RESIDENT_DELIVERIES]=resident_deliveries;
    result[R_FAILED_STEP]=failed_step;
    result[R_FAILED_CORE]=failed_core;
    result[R_FAILED_CLASS]=failed_class;
    result[R_EXPECTED_CRC]=expected_crc;
    result[R_OBSERVED_CRC]=observed_crc;
    put64(R_LAST_PACKET_LO,last_packet);
    result[R_OBSERVATION_MODE]=deployment.diagnostic_mode;
    result[R_EXPECTED_EVENTS]=deployment.event_count;
    result[R_EXPECTED_CHECKS]=deployment.checkpoint_count;
    result[R_EXPECTED_DISPATCHES]=deployment.dispatch_count;
    result[R_DIAG_FLAGS]=diag_flags;
    result[R_LAST_PAGE_ERROR]=(uint32_t)hw.last_error;
}
static void report_failure(uint32_t code)
{
    if (first_error==0u) first_error=code;
    snapshot(&runtime);
    result[R_RESULT]=P05_RESULT_FAIL | first_error;
    result[R_ERROR]=first_error;
    flush_result();
}
static uint64_t ticks(void *ctx)
{
    uint64_t value;
    (void)ctx;
    __asm__ volatile("isb; mrs %0, cntvct_el0":"=r"(value));
    return value;
}
static uint32_t frequency(void)
{
    uint64_t value;
    __asm__ volatile("mrs %0, cntfrq_el0":"=r"(value));
    return (uint32_t)value;
}
static const volatile uint8_t *core_row(uint32_t rank)
{
    return input_payload + (uintptr_t)rank*P05_DEPLOY_CORE_BYTES;
}
static const volatile uint8_t *event_row(uint32_t index)
{
    return input_payload + (uintptr_t)deployment.core_count*
           P05_DEPLOY_CORE_BYTES + (uintptr_t)index*
           P05_DEPLOY_EVENT_BYTES;
}
static const volatile uint8_t *check_row(uint32_t index)
{
    return input_payload + (uintptr_t)deployment.core_count*
           P05_DEPLOY_CORE_BYTES + (uintptr_t)deployment.event_count*
           P05_DEPLOY_EVENT_BYTES + (uintptr_t)index*
           P05_DEPLOY_CHECKPOINT_BYTES;
}
static int load_descriptor(void)
{
    uint8_t header[P05_DEPLOY_HEADER_BYTES];
    uint32_t payload_bytes,i;
    /* The first size word must be bounded BEFORE invalidating/reading
     * any caller-controlled payload address.
     */
    Xil_DCacheInvalidateRange((INTPTR)P05_DEPLOY_HEADER_BASE,
                              P05_DEPLOY_HEADER_BYTES);
    fence();
    for(i=0;i<P05_DEPLOY_HEADER_BYTES;++i)
        header[i]=input_header[i];
    payload_bytes=little32(input_header+12u*4u);
    if(payload_bytes == 0u ||
       payload_bytes > P05_DEPLOY_PAYLOAD_CAPACITY)
        return -1;
    Xil_DCacheInvalidateRange((INTPTR)P05_DEPLOY_PAYLOAD_BASE,
                              payload_bytes);
    fence();
    if(p05_deployment_validate(
        header,sizeof(header),
        (const uint8_t *)(uintptr_t)P05_DEPLOY_PAYLOAD_BASE,
        (size_t)payload_bytes,&deployment)!=P05_VALID)
        return -1;
    for(i=0;i<P05_CORE_COUNT_LIMIT;++i) rank_of[i]=UINT32_MAX;
    for(i=0;i<deployment.core_count;++i) {
        uint32_t id=little32(core_row(i));
        if(id>=P05_CORE_COUNT_LIMIT) return -1;
        service_order[i]=(uint8_t)id;
        rank_of[id]=i;
        initial_crc[id]=little32(core_row(i)+4u*4u);
    }
    return 0;
}
static int check_records(void *ctx)
{
    uint32_t i;
    (void)ctx;
    for(i=0;i<deployment.core_count;++i) {
        const volatile uint8_t *desc=core_row(i);
        uint32_t id=little32(desc);
        uint64_t meta=(uint64_t)little32(desc+4u) |
                       ((uint64_t)little32(desc+8u)<<32);
        uintptr_t addr=P05_DEPLOY_BACKING_BASE+
                       (uintptr_t)id*P05_DEPLOY_RECORD_BYTES;
        if(crc_physical(addr,P05_DEPLOY_RECORD_BYTES)!=initial_crc[id] ||
           Xil_In32(addr)!=UINT32_C(0x3356544C) ||
           Xil_In32(addr+4u)!=UINT32_C(0x31585443) ||
           Xil_In32(addr+8u)!=1u ||
           Xil_In32(addr+12u)!=0x1000u ||
           Xil_In32(addr+0x10u)!=P05_DEPLOY_RECORD_BYTES ||
           Xil_In32(addr+0x14u)!=id ||
           Xil_In32(addr+0x1cu)!=0u ||
           Xil_In32(addr+0x20u)!=((meta>>7)&0x7FFu) ||
           Xil_In32(addr+0x24u)!=((meta>>18)&0xFFFFu) ||
           Xil_In32(addr+0x28u)!=((meta>>34)&0x1FFFu) ||
           Xil_In32(addr+0x2cu)!=0u ||
           Xil_In32(addr+0x30u)!=0u ||
           Xil_In32(addr+0x1000u)!=little32(desc+12u))
            return -1;
    }
    return 0;
}
static int check_deployment(void *ctx)
{
    (void)ctx;
    return deployment.core_count!=0u ? 0 : -1;
}
static int check_initial_resident(void *ctx)
{
    p03_hw_adapter *adapter=ctx;
    uint32_t s,data[8]={0};
    for(s=0;s<deployment.slot_count;++s) {
        if(runtime.resident[s]!=(int16_t)service_order[s] ||
           p03_hw_debug_word(adapter,(uint8_t)s,
                             P03_HW_CONFIG_DEBUG_BANK,0,0,data) ||
           data[0]!=little32(core_row(s)+12u))
            return -1;
    }
    return 0;
}
static int inject_and_dispatch(void *ctx,uint8_t id,uint8_t slot,
                               uint32_t step,uint8_t bank,
                               uint32_t *emitted,uint64_t *cycles)
{
    p03_hw_runtime_bridge *b=ctx;
    uint16_t count;
    uint32_t words[8]={0};
    if(!hardware_dispatch || b->hw!=&hw || b->runtime!=&runtime ||
       bank>1u || id>=P05_CORE_COUNT_LIMIT ||
       rank_of[id]==UINT32_MAX)
        return -1;
    count=hw.event_counts[id][bank];
    while(event_cursor<deployment.event_count) {
        const volatile uint8_t *row=event_row(event_cursor);
        uint32_t t=little32(row), target=little32(row+4u);
        if(t!=step || target!=id) break;
        if(count>=P03_HW_EVENT_DEPTH) return -1;
        words[0]=little32(row+8u);
        if(p03_hw_debug_word(&hw,slot,
            bank?P03_HW_EVENT1_DEBUG_BANK:P03_HW_EVENT0_DEBUG_BANK,
            count,1,words)!=P03_HW_OK)
            return -1;
        ++count;
        hw.event_counts[id][bank]=count;
        ++event_cursor;
    }
    /* Reject a stale/misordered row before issuing any FPGA dispatch. */
    if(event_cursor<deployment.event_count) {
        const volatile uint8_t *row=event_row(event_cursor);
        uint32_t t=little32(row), target=little32(row+4u);
        if(t<step ||
           (t==step &&
            (target>=P05_CORE_COUNT_LIMIT ||
             rank_of[target]<=rank_of[id])))
            return -1;
    }
    return hardware_dispatch(ctx,id,slot,step,bank,emitted,cycles);
}
static int observe_and_route(void *ctx,uint8_t id,uint32_t emitted,
                             uint32_t step,uint8_t next_bank,
                             uint32_t *committed)
{
    uint32_t k,s;
    uint64_t packet;
    if(!hardware_route || emitted>P03_RT_MAX_PACKETS)return -1;
    for(s=0;s<runtime.slot_count;++s)
        if(runtime.resident[s]==(int16_t)id)break;
    if(s>=runtime.slot_count)return -1;
    for(k=0;k<emitted;++k) {
        if(p03_hw_read_packet(&hw,(uint8_t)s,(uint16_t)k,
                              &packet)!=P03_HW_OK)
            return -1;
        last_packet=packet;
        {
            uint32_t r;
            uint8_t dest=(uint8_t)(packet & UINT64_C(0x7F));
            for(r=0;r<runtime.slot_count;++r)
                if(runtime.resident[r]==(int16_t)dest) {
                    ++resident_deliveries;
                    break;
                }
        }
    }
    return hardware_route(ctx,id,emitted,step,next_bank,committed);
}
static int core_resident(uint32_t id)
{
    uint32_t s;
    for(s=0;s<runtime.slot_count;++s)
        if(runtime.resident[s]==(int16_t)id)
            return (int)s;
    return P03_RT_EMPTY_SLOT;
}
static int checkpoint_crc(uint32_t id,uint32_t cls,uint32_t *crc)
{
    uint32_t offset,bank,size,words[8]={0};
    int slot;
    uint32_t lo,hi=0u;
    if(!crc)return -1;
    switch(cls) {
        case P05_OBS_STATE0:
            offset=0x5000u;bank=5u;size=8u;break;
        case P05_OBS_EVENT0:
            offset=P03_HW_EVENT0_OFFSET;
            bank=P03_HW_EVENT0_DEBUG_BANK;size=4u;break;
        case P05_OBS_EVENT1:
            offset=P03_HW_EVENT1_OFFSET;
            bank=P03_HW_EVENT1_DEBUG_BANK;size=4u;break;
        case P05_OBS_PACKET0:
            offset=0x64000u;bank=P03_HW_PACKET_DEBUG_BANK;
            size=8u;break;
        default:return -1;
    }
    slot=core_resident(id);
    if(slot!=P03_RT_EMPTY_SLOT) {
        if(p03_hw_debug_word(&hw,(uint8_t)slot,(uint8_t)bank,
                             0u,0,words)!=P03_HW_OK)
            return -1;
        lo=words[0];
        if(size==8u)hi=words[1];
    } else {
        uintptr_t addr=P05_DEPLOY_BACKING_BASE+
                       (uintptr_t)id*P05_DEPLOY_RECORD_BYTES+offset;
        uintptr_t aligned=addr & ~(uintptr_t)63u;
        Xil_DCacheInvalidateRange((INTPTR)aligned,64u);
        fence();
        lo=Xil_In32(addr);
        if(size==8u)hi=Xil_In32(addr+4u);
    }
    *crc=crc_word(lo,hi,(uint8_t)size);
    return 0;
}
static int barrier_with_checkpoints(void *ctx,uint32_t step,uint8_t next)
{
    if(!hardware_barrier ||
       hardware_barrier(ctx,step,next)!=0)return -1;
    while(checkpoint_cursor<deployment.checkpoint_count) {
        const volatile uint8_t *row=check_row(checkpoint_cursor);
        uint32_t t=little32(row),id=little32(row+4u),
                 cls=little32(row+8u),expected=little32(row+12u);
        uint32_t measured;
        if(t!=step) {
            if(t<step)return -1;
            break;
        }
        if(checkpoint_crc(id,cls,&measured)!=0) {
            failed_step=step;failed_core=id;failed_class=cls;
            expected_crc=expected;
            diag_flags=2u; /* unable to read at stable barrier */
            return -1;
        }
        if(measured!=expected) {
            failed_step=step;failed_core=id;failed_class=cls;
            expected_crc=expected;observed_crc=measured;
            diag_flags=1u; /* first observed mismatching state */
            return -1;
        }
        ++checkpoint_cursor;
    }
    return 0;
}
static int finalize_result(void *ctx,const p03_rt *rt)
{
    p03_hw_adapter *adapter=ctx;
    uint32_t id,cap,pages,dispatches,bytes,status,pending;
    uint32_t read_bursts,write_bursts,i;
    if(adapter!=&hw)return -1;
    for(i=0;i<rt->slot_count;++i) {
        if(rt->resident[i]!=P03_RT_EMPTY_SLOT && rt->dirty[i]) {
            uint64_t cycles=0;
            if(p03_hw_page(adapter,(uint8_t)rt->resident[i],
                           (uint8_t)i,1,1,&cycles)!=P03_HW_OK)
                return -1;
            ++final_outs;
        }
    }
    if(adapter->io.read32(adapter->cookie,P03_REG_ID,&id) ||
       adapter->io.read32(adapter->cookie,P03_REG_CAPABILITIES,&cap) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_COMPLETED,&pages) ||
       adapter->io.read32(adapter->cookie,P03_REG_DISPATCH_COMPLETED,&dispatches) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_BYTES,&bytes) ||
       adapter->io.read32(adapter->cookie,P03_REG_GLOBAL_STATUS,&status) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_PENDING_BYTES,&pending) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_READ_BURSTS,&read_bursts) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_WRITE_BURSTS,&write_bursts))
        return -1;
    result[R_HW_ID]=id;result[R_HW_CAPS]=cap;
    result[R_HW_PAGES]=pages;result[R_HW_DISPATCHES]=dispatches;
    result[R_HW_LAST_PAGE_BYTES]=bytes;
    result[R_HW_STATUS]=status;result[R_HW_PAGE_PENDING]=pending;
    result[R_HW_READ_BURSTS]=read_bursts;
    result[R_HW_WRITE_BURSTS]=write_bursts;
    result[R_CNTFRQ_HZ]=frequency();
    snapshot(rt);
    if(id!=P03_MMIO_ID_VALUE || cap!=UINT32_C(0x0001031F) ||
       rt->first_fault!=P03_RT_FAULT_NONE ||
       rt->counters.logical_dispatches!=deployment.dispatch_count ||
       rt->counters.timesteps_completed!=deployment.timesteps ||
       rt->counters.barriers!=deployment.timesteps ||
       rt->counters.initial_page_ins!=deployment.slot_count ||
       event_cursor!=deployment.event_count ||
       checkpoint_cursor!=deployment.checkpoint_count ||
       final_outs!=deployment.slot_count ||
       dispatches!=deployment.dispatch_count ||
       pages!=(rt->counters.initial_page_ins+rt->counters.page_ins+
               rt->counters.page_outs+final_outs) ||
       bytes!=P03_HW_MUTABLE_BYTES ||
       status!=0u || pending!=0u ||
       p03_hw_quiescent(adapter)!=P03_HW_OK)
        return -1;
    /* Never publish terminal success here: scheduler must enter DONE. */
    result[R_ERROR]=0u;
    flush_result();
    return 0;
}
static void on_error(void *ctx,const p03_rt *rt)
{
    (void)ctx;(void)rt;
    report_failure(diag_flags?E_CHECKPOINT:E_RUNTIME);
}
int main(void)
{
    uint32_t i;
    p03_hw_io io=p03_hw_xilinx_io();
    first_error=0u; final_outs=0u;event_cursor=0u;
    checkpoint_cursor=0u;resident_deliveries=0u;
    diag_flags=0u;last_packet=0u;
    failed_step=failed_core=failed_class=0u;
    expected_crc=observed_crc=0u;
    memset(&deployment,0,sizeof(deployment));
    fence();
    for(i=0;i<64u;++i)result[i]=0u;
    result[R_MAGIC]=P05_RESULT_MAGIC;
    result[R_VERSION]=P05_DEPLOY_VERSION;
    flush_result();
    if(p05_build_id[0]!='P' || load_descriptor()!=0) {
        report_failure(E_CONFIG);halt_forever();
    }
    if(p03_hw_xilinx_fpd128_ready()!=0) {
        report_failure(E_WIDTH);halt_forever();
    }
    if(check_records(NULL)!=0) {
        report_failure(E_RECORD);halt_forever();
    }
    if(p03_hw_init(&hw,&io,NULL,P03_HW_BACKING_BASE,
                   P05_POLL_LIMIT)!=P03_HW_OK) {
        report_failure(E_ADAPTER);halt_forever();
    }
    for(i=0;i<deployment.core_count;++i) {
        const volatile uint8_t *row=core_row(i);
        uint8_t id=service_order[i];
        uint64_t meta=(uint64_t)little32(row+4u) |
                       ((uint64_t)little32(row+8u)<<32);
        if(p03_hw_register_core(&hw,id,meta,0u,0u)!=P03_HW_OK ||
           p03_hw_register_axon(&hw,id,
                                (uint16_t)little32(row+20u))!=P03_HW_OK) {
            report_failure(E_REGISTER);halt_forever();
        }
    }
    if(p03_rt_init(&runtime,service_order,(uint16_t)deployment.core_count,
                   (uint8_t)deployment.slot_count,
                   deployment.timesteps)!=0) {
        report_failure(E_RUNTIME_INIT);halt_forever();
    }
    bridge.hw=&hw;bridge.runtime=&runtime;bridge.app_cookie=&hw;
    bridge.validate_deployment=check_deployment;
    bridge.validate_backing=check_records;
    bridge.load_input=check_initial_resident;
    bridge.write_result=finalize_result;
    bridge.read_ticks=ticks;
    bridge.on_error=on_error;
    if(p03_hw_bind_runtime(&bridge,&ops)!=0) {
        report_failure(E_BIND);halt_forever();
    }
    hardware_dispatch=ops.dispatch;
    hardware_route=ops.drain_route;
    hardware_barrier=ops.barrier_ready;
    ops.dispatch=inject_and_dispatch;
    ops.drain_route=observe_and_route;
    ops.barrier_ready=barrier_with_checkpoints;
    if(p03_rt_execute(&runtime,&ops,&bridge)!=0) {
        report_failure(diag_flags?E_CHECKPOINT:E_RUNTIME);
        halt_forever();
    }
    if(runtime.phase!=P03_RT_DONE || result[R_ERROR]!=0u) {
        report_failure(E_RESULT);halt_forever();
    }
    result[R_RUNTIME_PHASE]=(uint32_t)runtime.phase;
    result[R_RESULT]=P05_RESULT_OK;
    flush_result();
    halt_forever();
    return 0;
}
