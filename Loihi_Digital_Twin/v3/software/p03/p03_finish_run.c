/*
 * P03 combined autonomous PS launch and 5-over-3 P02-golden acceptance runner.
 *
 * One ELF, frozen DDR manifest determines 7 or 100 algorithmic timesteps.
 * All 5 logical cores and 3 resident slots are scheduled on Cortex-A53 #0;
 * no XSDB/VIO assistance is used during the timestep loop.
 *
 * PC duties: provision five P02 DDR records, one 256-byte immutable
 * manifest, and clear a 256-byte result mailbox before the single launch.
 * All DDR inputs/outputs lie in the explicitly reserved P02 backing region.
 */
#include <stddef.h>
#include <stdint.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "p03_hw_xilinx_io.h"
#include "p03_hw_runtime_bridge.h"
#include "p03_mmio.h"

#define RUN_CONFIG_ADDR UINTPTR_C(0x43FE0000) /* set below via uintptr_t */
#define RUN_MAILBOX_ADDR ((uintptr_t)0x43FF0000u)
#define RUN_BACKING_ADDR ((uintptr_t)0x40000000u)
#define RUN_MAGIC UINT32_C(0x50334346)
#define RUN_RESULT_MAGIC UINT32_C(0x50335253)
#define RUN_VERSION 1u
#define RUN_PASS UINT32_C(0x600D600D)
#define RUN_FAIL UINT32_C(0xDEAD0000)
#define RUN_POLL UINT32_C(100000000)
#define RUN_WORDS 64u
#define RUN_CORE_COUNT 5u
#define RUN_SLOTS 3u
#define RUN_RECORD_BYTES 0x80000u

/* Do not allow accidental launch of earlier zero-packet b3 probes. */
static const volatile char run_build_id[] =
    "P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V1";

enum {
    FAIL_WIDTH=1, FAIL_MANIFEST=2, FAIL_DDR=3, FAIL_ADAPTER=4,
    FAIL_REGISTER=5, FAIL_RUNTIME_INIT=6, FAIL_BIND=7,
    FAIL_INPUT=8, FAIL_FINAL_FLUSH=9, FAIL_RESULT=10,
    FAIL_RUNTIME=11
};

enum {
    M_MAGIC=0, M_SCHEMA=1, M_RESULT=2, M_ERROR=3,
    M_REQUESTED_STEPS=4, M_LAST_STEP=5, M_EVENT_BANK=6,
    M_FAULT=7, M_FAULT_PHASE=8, M_RT_PHASE=9,
    M_MMIO_ID=10, M_CAPS=11, M_CORES=12, M_SLOTS=13,
    M_DISPATCHES=14, M_PACKETS=15, M_BARRIERS=16, M_COMPLETED_STEPS=17,
    M_INITIAL_INS=18, M_INS=19, M_OUTS=20, M_FLUSH_OUTS=21,
    M_EVICTIONS=22, M_HITS=23,
    M_PL_DISPATCH_LO=24, M_PL_DISPATCH_HI=25,
    M_PL_PAGE_LO=26, M_PL_PAGE_HI=27,
    M_ROUTE_TICKS_LO=28, M_ROUTE_TICKS_HI=29,
    M_BARRIER_TICKS_LO=30, M_BARRIER_TICKS_HI=31,
    M_INFER_TICKS_LO=32, M_INFER_TICKS_HI=33,
    M_CONTROL_TICKS_LO=34, M_CONTROL_TICKS_HI=35,
    M_CNTFRQ_HZ=36, M_RESIDENT_ROUTES=37,
    M_PAGE_COMPLETED=38, M_DISPATCH_COMPLETED=39, M_LAST_PAGE_BYTES=40,
    M_GLOBAL_STATUS=41, M_PAGE_PENDING=42, M_READ_BURSTS=43,
    M_WRITE_BURSTS=44, M_STATES_BEGIN=45,
    M_NEXT_COUNTS_BEGIN=55, M_MANIFEST_CRC=60,
    M_LAST_PACKET_LO=61, M_LAST_PACKET_HI=62,
    M_EXPECTED_PACKETS=63
};

static volatile uint32_t *const result = (volatile uint32_t *)RUN_MAILBOX_ADDR;
static volatile const uint32_t *const config =
    (volatile const uint32_t *)(uintptr_t)0x43FE0000u;
static p03_rt runtime;
static p03_hw_adapter hw;
static p03_hw_runtime_bridge bridge;
static p03_rt_ops ops;
static int (*base_dispatch)(void *,uint8_t,uint8_t,uint32_t,uint8_t,
                            uint32_t *,uint64_t *);
static int (*base_drain)(void *,uint8_t,uint32_t,uint32_t,uint8_t,uint32_t *);
static uint32_t initial_crc[RUN_CORE_COUNT];
static uint32_t flush_outs;
static uint64_t last_packet;
static uint32_t resident_routes;
static uint32_t first_error;

static void fence(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static void flush_result(void)
{
    fence();
    Xil_DCacheFlushRange((INTPTR)RUN_MAILBOX_ADDR, 256);
    fence();
}
static void halt_forever(void)
{
    for (;;) __asm__ volatile("wfe");
}
static uint32_t crc_update(uint32_t crc, uint8_t v)
{
    unsigned b;
    crc ^= v;
    for (b=0;b<8;++b)
        crc=(crc>>1) ^ ((crc & 1u) ? UINT32_C(0xEDB88320) : 0u);
    return crc;
}
static uint32_t crc_physical(uintptr_t base, uint32_t bytes)
{
    const volatile uint8_t *buf = (const volatile uint8_t *)base;
    uint32_t crc = UINT32_C(0xFFFFFFFF), i;
    Xil_DCacheInvalidateRange((INTPTR)base,bytes);
    fence();
    for (i=0;i<bytes;++i) crc=crc_update(crc,buf[i]);
    return crc ^ UINT32_C(0xFFFFFFFF);
}
static uint32_t config_crc(void)
{
    const volatile uint8_t *p = (const volatile uint8_t *)(uintptr_t)0x43FE0000u;
    uint32_t crc=UINT32_C(0xFFFFFFFF), i;
    Xil_DCacheInvalidateRange((INTPTR)0x43FE0000u,256);
    fence();
    for (i=0;i<252;++i) crc=crc_update(crc,p[i]);
    return crc ^ UINT32_C(0xFFFFFFFF);
}
static void put64(unsigned low, uint64_t value)
{
    result[low]=(uint32_t)value;
    result[low+1]=(uint32_t)(value>>32);
}
static void snapshot(const p03_rt *rt)
{
    result[M_REQUESTED_STEPS]=rt->requested_timesteps;
    result[M_LAST_STEP]=rt->current_timestep;
    result[M_EVENT_BANK]=rt->current_event_bank;
    result[M_FAULT]=(uint32_t)rt->first_fault;
    result[M_FAULT_PHASE]=(uint32_t)rt->fault_phase;
    result[M_RT_PHASE]=(uint32_t)rt->phase;
    result[M_DISPATCHES]=rt->counters.logical_dispatches;
    result[M_PACKETS]=rt->counters.routed_packets;
    result[M_BARRIERS]=rt->counters.barriers;
    result[M_COMPLETED_STEPS]=rt->counters.timesteps_completed;
    result[M_INITIAL_INS]=rt->counters.initial_page_ins;
    result[M_INS]=rt->counters.page_ins;
    result[M_OUTS]=rt->counters.page_outs;
    result[M_FLUSH_OUTS]=flush_outs;
    result[M_EVICTIONS]=rt->counters.evictions;
    result[M_HITS]=rt->counters.page_hits;
    put64(M_PL_DISPATCH_LO,rt->counters.pl_dispatch_cycles);
    put64(M_PL_PAGE_LO,rt->counters.pl_page_cycles);
    put64(M_ROUTE_TICKS_LO,rt->counters.ps_route_ticks);
    put64(M_BARRIER_TICKS_LO,rt->counters.ps_barrier_ticks);
    put64(M_INFER_TICKS_LO,rt->counters.ps_inference_ticks);
    put64(M_CONTROL_TICKS_LO,rt->counters.ps_control_ticks);
    result[M_MANIFEST_CRC]=config[63];
    put64(M_LAST_PACKET_LO,last_packet);
    result[M_EXPECTED_PACKETS]=config[45];
}
static void report_error(uint32_t code)
{
    if (!first_error) first_error=code;
    snapshot(&runtime);
    result[M_RESULT]=RUN_FAIL | first_error;
    result[M_ERROR]=first_error;
    flush_result();
}
static uint64_t read_clock(void *ctx)
{
    uint64_t counter;
    (void)ctx;
    __asm__ volatile("isb; mrs %0, cntvct_el0" : "=r"(counter));
    return counter;
}
static uint32_t read_frequency(void)
{
    uint64_t hz;
    __asm__ volatile("mrs %0, cntfrq_el0" : "=r"(hz));
    return (uint32_t)hz;
}
static int validate_manifest(void)
{
    uint32_t i;
    if (config_crc()!=config[63]) return -1;
    if (config[0]!=RUN_MAGIC || config[1]!=RUN_VERSION ||
        (config[2]!=7u && config[2]!=100u) ||
        config[3]!=RUN_CORE_COUNT || config[4]!=RUN_SLOTS ||
        config[5]!=10u || config[6]!=RUN_BACKING_ADDR ||
        config[7]!=RUN_RECORD_BYTES ||
        config[8]!=RUN_MAILBOX_ADDR || config[9]!=1u ||
        config[46]!=RUN_CORE_COUNT*config[2] ||
        config[47]!=config[2] ||
        config[48]!=(config[2]&1u))
        return -1;
    for (i=0;i<RUN_CORE_COUNT;++i) {
        uint64_t meta=(uint64_t)config[10+2*i] |
                      ((uint64_t)config[11+2*i]<<32);
        if ((meta & 0x7fu)!=i ||
            ((meta>>7)&0x7ffu)!=1u ||
            config[25+i]!=0 ||
            config[30+i]!=10u+i || config[35+i]!=i ||
            config[40+i]==0)
            return -1;
        initial_crc[i]=config[40+i];
    }
    for(i=49;i<63;++i)
        if (config[i] != 0u) return -1;
    return 0;
}
static int check_records(void *ctx)
{
    unsigned i;
    (void)ctx;
    /* Immutable initial 512 KiB records, verified before any writes by PL.
     * CRC32 is an integrity check, not a cryptographic authenticity proof.
     */
    for(i=0;i<RUN_CORE_COUNT;++i) {
        uintptr_t base=RUN_BACKING_ADDR+(uintptr_t)i*RUN_RECORD_BYTES;
        if (crc_physical(base,RUN_RECORD_BYTES)!=initial_crc[i] ||
            Xil_In32(base)!=UINT32_C(0x3356544C) ||
            Xil_In32(base+4)!=UINT32_C(0x31585443) ||
            Xil_In32(base+8)!=1u ||
            Xil_In32(base+0x10)!=RUN_RECORD_BYTES ||
            Xil_In32(base+0x14)!=i ||
            Xil_In32(base+0x2c)!=0u ||
            Xil_In32(base+0x30)!=0u ||
            Xil_In32(base+0x1000)!=config[20+i])
            return -1;
    }
    return 0;
}
static int validate_deployment(void *ctx)
{
    (void)ctx;
    return validate_manifest();
}
static int verify_initial_residency(void *ctx)
{
    p03_hw_adapter *adapter=ctx;
    uint32_t data[8]={0};
    unsigned s;
    for(s=0;s<RUN_SLOTS;++s) {
        if (runtime.resident[s]!=(int16_t)s ||
            p03_hw_debug_word(adapter,(uint8_t)s,
                              P03_HW_CONFIG_DEBUG_BANK,0,0,data) ||
            data[0]!=config[20+s])
            return -1;
    }
    return 0;
}
static int inject_external_and_dispatch(
    void *ctx,uint8_t id,uint8_t slot,uint32_t step,uint8_t bank,
    uint32_t *emitted,uint64_t *cycles)
{
    p03_hw_runtime_bridge *b=ctx;
    uint16_t count;
    uint32_t words[8]={0};
    (void)step;
    if (!base_dispatch || id>=RUN_CORE_COUNT ||
        b->hw!=&hw || b->runtime!=&runtime ||
        bank>1) return -1;
    count=hw.event_counts[id][bank];
    if (count>=P03_HW_EVENT_DEPTH) return -1;
    words[0]=config[30+id]; /* external axon 10+core */
    if (p03_hw_debug_word(&hw,slot,
        bank ? P03_HW_EVENT1_DEBUG_BANK : P03_HW_EVENT0_DEBUG_BANK,
        count,1,words)!=P03_HW_OK)
        return -1;
    hw.event_counts[id][bank]=(uint16_t)(count+1u);
    return base_dispatch(ctx,id,slot,step,bank,emitted,cycles);
}
static int observe_and_drain(void *ctx,uint8_t id,uint32_t emitted,
                             uint32_t timestep,uint8_t next_bank,
                             uint32_t *committed)
{
    uint8_t slot;
    uint32_t k;
    uint64_t packet;
    if (!base_drain || emitted>P03_RT_MAX_PACKETS) return -1;
    for(slot=0;slot<runtime.slot_count;++slot)
        if(runtime.resident[slot]==(int16_t)id)break;
    if(slot>=runtime.slot_count)return -1;
    for(k=0;k<emitted;++k) {
        if(p03_hw_read_packet(&hw,slot,(uint16_t)k,&packet)!=P03_HW_OK)
            return -1;
        last_packet=packet; /* evidence only; normal router re-reads and commits */
        {
            uint8_t dest=(uint8_t)(packet & UINT64_C(0x7F));
            uint8_t s;
            for(s=0;s<runtime.slot_count;++s) {
                if(runtime.resident[s]==(int16_t)dest) {
                    ++resident_routes;
                    break;
                }
            }
        }
    }
    return base_drain(ctx,id,emitted,timestep,next_bank,committed);
}
static int write_result(void *ctx,const p03_rt *rt)
{
    p03_hw_adapter *adapter=ctx;
    uint32_t i, id,cap;
    uint32_t addr;
    uint32_t readbacks[7]={0};
    if (adapter!=&hw) return -1;
    /* Complete the authoritative DDR backing state: eviction policy does
     * not normally save the still-resident final three contexts.
     * Explicit finalization is mandatory for byte-exact P02/v2 comparison.
     */
    for(i=0;i<rt->slot_count;++i) {
        if(rt->resident[i]!=P03_RT_EMPTY_SLOT && rt->dirty[i]) {
            uint64_t cycles=0;
            if(p03_hw_page(adapter,(uint8_t)rt->resident[i],
                           (uint8_t)i,1,1,&cycles)!=P03_HW_OK)
                return -1;
            ++flush_outs;
        }
    }
    if(adapter->io.read32(adapter->cookie,P03_REG_ID,&id) ||
       adapter->io.read32(adapter->cookie,P03_REG_CAPABILITIES,&cap) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_COMPLETED,&readbacks[0]) ||
       adapter->io.read32(adapter->cookie,P03_REG_DISPATCH_COMPLETED,&readbacks[1]) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_BYTES,&readbacks[2]) ||
       adapter->io.read32(adapter->cookie,P03_REG_GLOBAL_STATUS,&readbacks[3]) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_PENDING_BYTES,&readbacks[4]) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_READ_BURSTS,&readbacks[5]) ||
       adapter->io.read32(adapter->cookie,P03_REG_PAGE_WRITE_BURSTS,&readbacks[6]))
        return -1;
    result[M_MMIO_ID]=id;
    result[M_CAPS]=cap;
    result[M_PAGE_COMPLETED]=readbacks[0];
    result[M_DISPATCH_COMPLETED]=readbacks[1];
    result[M_LAST_PAGE_BYTES]=readbacks[2];
    result[M_GLOBAL_STATUS]=readbacks[3];
    result[M_PAGE_PENDING]=readbacks[4];
    result[M_READ_BURSTS]=readbacks[5];
    result[M_WRITE_BURSTS]=readbacks[6];

    /* DDR-committed normalized state words (1 compartment per ring core).
     * Full physical record comparison is independently done on the PC
     * AFTER the firmware has stopped, with no loop-level control.
     */
    for(i=0;i<RUN_CORE_COUNT;++i) {
        addr=(uint32_t)RUN_BACKING_ADDR+i*RUN_RECORD_BYTES+0x5000u;
        Xil_DCacheInvalidateRange((INTPTR)(uintptr_t)(addr & ~63u),64);
        fence();
        result[M_STATES_BEGIN+2*i]=Xil_In32(addr);
        result[M_STATES_BEGIN+2*i+1]=Xil_In32(addr+4u);
        result[M_NEXT_COUNTS_BEGIN+i]=
            adapter->event_counts[i][rt->requested_timesteps&1u];
    }
    snapshot(rt);
    result[M_CORES]=RUN_CORE_COUNT;
    result[M_SLOTS]=RUN_SLOTS;
    result[M_CNTFRQ_HZ]=read_frequency();
    result[M_RESIDENT_ROUTES]=resident_routes;

    if(id!=P03_MMIO_ID_VALUE || cap!=UINT32_C(0x0001031F) ||
       rt->first_fault!=P03_RT_FAULT_NONE ||
       rt->counters.logical_dispatches!=config[46] ||
       rt->counters.routed_packets!=config[45] ||
       resident_routes==0u ||
       rt->counters.barriers!=config[47] ||
       rt->counters.timesteps_completed!=config[2] ||
       rt->current_event_bank!=(config[2]&1u) ||
       rt->counters.initial_page_ins!=3u ||
       flush_outs!=3u ||
       readbacks[1]!=config[46] ||
       readbacks[0]!=(rt->counters.initial_page_ins +
                      rt->counters.page_ins +
                      rt->counters.page_outs + flush_outs) ||
       readbacks[2]!=P03_HW_MUTABLE_BYTES ||
       readbacks[3]!=0 || readbacks[4]!=0 ||
       p03_hw_quiescent(adapter)!=P03_HW_OK)
        return -1;
    result[M_RESULT]=RUN_PASS;
    result[M_ERROR]=0;
    flush_result();
    return 0;
}
static void on_error(void *ctx,const p03_rt *rt)
{
    (void)ctx;
    (void)rt;
    report_error(FAIL_RUNTIME);
}
int main(void)
{
    p03_hw_io io=p03_hw_xilinx_io();
    const uint8_t ids[RUN_CORE_COUNT]={0,1,2,3,4};
    uint32_t i;
    for(i=0;i<RUN_WORDS;++i) result[i]=0;
    result[M_MAGIC]=RUN_RESULT_MAGIC;
    result[M_SCHEMA]=RUN_VERSION;
    flush_result();
    if(run_build_id[0]!='P') {
        report_error(FAIL_MANIFEST); halt_forever();
    }
    if(p03_hw_xilinx_fpd128_ready()!=0) {
        report_error(FAIL_WIDTH); halt_forever();
    }
    if(validate_manifest()!=0) {
        report_error(FAIL_MANIFEST); halt_forever();
    }
    if(check_records(NULL)!=0) {
        report_error(FAIL_DDR); halt_forever();
    }
    if(p03_hw_init(&hw,&io,NULL,P03_HW_BACKING_BASE,RUN_POLL)!=P03_HW_OK) {
        report_error(FAIL_ADAPTER); halt_forever();
    }
    for(i=0;i<RUN_CORE_COUNT;++i) {
        uint64_t meta=(uint64_t)config[10+2*i] |
                      ((uint64_t)config[11+2*i]<<32);
        if(p03_hw_register_core(&hw,(uint8_t)i,meta,0,0)!=P03_HW_OK ||
           p03_hw_register_axon(&hw,(uint8_t)i,(uint16_t)config[30+i])!=P03_HW_OK) {
            report_error(FAIL_REGISTER); halt_forever();
        }
    }
    if(p03_rt_init(&runtime,ids,RUN_CORE_COUNT,RUN_SLOTS,config[2])!=0) {
        report_error(FAIL_RUNTIME_INIT); halt_forever();
    }
    bridge.hw=&hw;
    bridge.runtime=&runtime;
    bridge.app_cookie=&hw;
    bridge.validate_deployment=validate_deployment;
    bridge.validate_backing=check_records;
    bridge.load_input=verify_initial_residency;
    bridge.write_result=write_result;
    bridge.read_ticks=read_clock;
    bridge.on_error=on_error;
    if(p03_hw_bind_runtime(&bridge,&ops)!=0) {
        report_error(FAIL_BIND); halt_forever();
    }
    base_dispatch=ops.dispatch;
    base_drain=ops.drain_route;
    ops.dispatch=inject_external_and_dispatch;
    ops.drain_route=observe_and_drain;
    if(p03_rt_execute(&runtime,&ops,&bridge)!=0) {
        report_error(FAIL_RUNTIME); halt_forever();
    }
    if(result[M_RESULT]!=RUN_PASS) {
        report_error(FAIL_RESULT); halt_forever();
    }
    result[M_RT_PHASE]=(uint32_t)runtime.phase;
    flush_result();
    halt_forever();
    return 0;
}
