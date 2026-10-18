/* P07-A2 autonomous Cortex-A53 FPGA execution candidate.
 *
 * This is NOT the accepted P05G/P05R runner. Only use with a separately
 * versioned P07A2B01 batch and the EXACT frozen trained context staged in
 * the reserved non-Linux DDR region. On real board execute and verify via
 * P07-specific XSDB/ELF gate before any physical MNIST accuracy claim.
 */
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "p03_hw_xilinx_io.h"
#include "p03_hw_runtime_bridge.h"
#include "p03_mmio.h"
#include "p07_a1_ingress.h"
#include "p07_a2_runtime.h"
#include "p07_a2_batch.h"
#include "p07_a2_sha256.h"

#define P07_A2_BACKING_BASE UINT32_C(0x40000000)
#define P07_A2_CONTEXT_BYTES 524288u
#define P07_A2_POLL_LIMIT UINT32_C(100000000)
#define P07_A2_TRACE_BANK 7u
#define P07_A2_MAILBOX_MAGIC UINT32_C(0x52373050) /* "P07R" */
#define P07_A2_MAILBOX_OK UINT32_C(0x600D600D)
#define P07_A2_MAILBOX_FAIL UINT32_C(0xDEAD0000)
#define P07_A2_BUILD_ID "P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX"

_Static_assert(P03_HW_EVENT_DEPTH == P07_A1_AXON_CAPACITY,
               "P07/P03 event bank capacity mismatch");
_Static_assert(P07_A2_TRACE_OFFSET + P07_A2_TRACE_BYTES <= P07_A2_RESULT_BYTES,
               "P07 full 26x42 compartment traces overflow result region");

static const volatile char firmware_identity[] = P07_A2_BUILD_ID;
/* Exact USER-ATTESTED P06-A4.2 static DDR and P07-A1 compiled deployment. */
static const uint8_t expected_ddr_sha[32] = {0x96u,0x17u,0xa8u,0x22u,0xf7u,0x4fu,0xaau,0x87u,0x23u,0x86u,0x9bu,0xb5u,0x76u,0xcfu,0x57u,0xb3u,0x8au,0xf1u,0xa1u,0xa9u,0x1au,0xc8u,0x1cu,0x47u,0xc2u,0x46u,0xa9u,0x42u,0x5du,0x0du,0xd9u,0x55u};
static const uint8_t expected_compiled_sha[32] = {0xe6u,0x12u,0xa9u,0x71u,0xcdu,0xa1u,0x1fu,0xaeu,0x3fu,0x1bu,0xe2u,0x15u,0xc0u,0xcau,0x3eu,0xd7u,0xdeu,0x7bu,0x2au,0xf7u,0x33u,0x94u,0x46u,0xe9u,0x26u,0xceu,0x55u,0x96u,0x58u,0xdbu,0x2fu,0x7fu};

/* The scheduler owns its runtime on its own stack. Never read a second
 * static p03_rt here: that object remains at timestep zero forever.
 * Bound once in prepare(), invalidated at each frame boundary. */
static const p03_rt *active_runtime;
static p03_hw_adapter hw;
static p03_hw_runtime_bridge bridge;
static p03_rt_ops bridge_ops;
static p07_a2_batch_info batch;
static uint8_t ingress[P07_A1_RECORD_BYTES];
static uint32_t trace_cache[P07_A2_OUTPUTS][8];
static uint8_t master_verified;
static uint32_t current_frame;
static uint32_t fault_detail;
static volatile uint32_t *const result_area =
    (volatile uint32_t *)(uintptr_t)P07_A2_RESULT_BASE;

static void fence(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static void flush_result(void)
{
    fence();
    Xil_DCacheFlushRange((INTPTR)P07_A2_RESULT_BASE, P07_A2_RESULT_BYTES);
    fence();
}
static void halt_forever(void) {
    for (;;) __asm__ volatile("wfe");
}
static uint32_t le32(const volatile uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static uint64_t le64(const volatile uint8_t *p)
{
    return (uint64_t)le32(p) | ((uint64_t)le32(p+4u)<<32);
}
static void record_failed(uint32_t code, uint32_t detail)
{
    result_area[2u]=P07_A2_MAILBOX_FAIL | code;
    result_area[3u]=code;
    result_area[4u]=current_frame;
    result_area[5u]=detail;
    flush_result();
}
static void reset_result(void)
{
    uint32_t index;
    for(index=0;index<P07_A2_RESULT_BYTES/4u;++index)
        result_area[index]=0;
    result_area[0]=P07_A2_MAILBOX_MAGIC;
    result_area[1]=1u;
    flush_result();
}
static int load_batch(void)
{
    static uint8_t header[P07_A2_BATCH_HEADER_BYTES];
    const volatile uint8_t *src =
        (const volatile uint8_t *)(uintptr_t)P07_A2_BATCH_BASE;
    uint32_t i;
    Xil_DCacheInvalidateRange((INTPTR)P07_A2_BATCH_BASE,
                              P07_A2_BATCH_HEADER_BYTES);
    fence();
    for(i=0;i<P07_A2_BATCH_HEADER_BYTES;++i)header[i]=src[i];
    if(p07_a2_batch_validate(header,sizeof(header),&batch)!=0)
        return -1;
    result_area[6u]=batch.frame_count;
    result_area[7u]=batch.trace_frame;
    flush_result();
    return 0;
}
static int verify_immutable_master(void)
{
    static uint8_t digest[32];
    const volatile uint8_t *src =
        (const volatile uint8_t *)(uintptr_t)P07_A2_MASTER_BASE;
    uint32_t i;
    Xil_DCacheInvalidateRange((INTPTR)P07_A2_MASTER_BASE,
                              P07_A2_CONTEXT_BYTES);
    fence();
    /* The reserved master staging memory is *not* owned by PL. */
    p07_a2_sha256((const uint8_t *)(uintptr_t)P07_A2_MASTER_BASE,
                  P07_A2_CONTEXT_BYTES,digest);
    if(memcmp(digest,expected_ddr_sha,sizeof(digest))!=0)
        return -1;
    if(memcmp((const void *)(uintptr_t)P07_A2_MASTER_BASE,
              "LTV3CTX1",8)!=0 ||
       le32(src+8u)!=1u || le32(src+16u)!=P07_A2_CONTEXT_BYTES ||
       le32(src+20u)!=0u || le32(src+28u)!=0u ||
       le32(src+32u)!=42u || le32(src+36u)!=25408u ||
       le32(src+40u)!=32u || le32(src+44u)!=0u ||
       le32(src+48u)!=0u || le32(src+52u)!=0u)
        return -1;
    for(i=0;i<32u;++i)
        if(expected_ddr_sha[i]!=digest[i])return -1;
    master_verified=1u;
    return 0;
}
static int load_image_record(uint32_t frame)
{
    const uintptr_t addr=(uintptr_t)P07_A2_INPUT_BASE+
                         (uintptr_t)frame*P07_A1_RECORD_BYTES;
    const volatile uint8_t *src=(const volatile uint8_t *)addr;
    uint32_t i;
    p07_a1_info info;
    if(frame>=batch.frame_count ||
       addr+P07_A1_RECORD_BYTES>P07_A2_BATCH_BASE)
        return -1;
    Xil_DCacheInvalidateRange((INTPTR)addr, P07_A1_RECORD_BYTES);
    fence();
    for(i=0;i<P07_A1_RECORD_BYTES;++i)ingress[i]=src[i];
    if(p07_a1_validate(ingress,sizeof(ingress),&info)!=P07_A1_OK ||
       memcmp(info.ddr_sha256,expected_ddr_sha,32u)!=0 ||
       memcmp(info.deployment_fingerprint,expected_compiled_sha,32u)!=0)
        return -1;
    return 0;
}
static int reset_core0_from_master(void)
{
    const volatile uint32_t *src =
        (const volatile uint32_t *)(uintptr_t)P07_A2_MASTER_BASE;
    volatile uint32_t *dest =
        (volatile uint32_t *)(uintptr_t)P07_A2_BACKING_BASE;
    uint32_t index;
    if(!master_verified) return -1;
    /* Previous PL page-outs may own stale cachelines; invalidate DDR target
     * then overwrite with the immutable original P02 record, every frame.
     * Master staging and ingress regions are never overwritten by PL.
     */
    Xil_DCacheInvalidateRange((INTPTR)P07_A2_BACKING_BASE,
                              P07_A2_CONTEXT_BYTES);
    fence();
    for(index=0;index<P07_A2_CONTEXT_BYTES/4u;++index)
        dest[index]=src[index];
    fence();
    Xil_DCacheFlushRange((INTPTR)P07_A2_BACKING_BASE,
                         P07_A2_CONTEXT_BYTES);
    fence();
    return 0;
}
static int validate_deployment(void *cookie)
{
    p07_a1_info info;
    (void)cookie;
    if(!master_verified ||
       p07_a1_validate(ingress,sizeof(ingress),&info)!=P07_A1_OK ||
       memcmp(info.ddr_sha256,expected_ddr_sha,32u)!=0 ||
       memcmp(info.deployment_fingerprint,expected_compiled_sha,32u)!=0)
        return -1;
    return 0;
}
static int validate_backing(void *cookie)
{
    const volatile uint8_t *p=(const volatile uint8_t *)
                                  (uintptr_t)P07_A2_BACKING_BASE;
    (void)cookie;
    Xil_DCacheInvalidateRange((INTPTR)P07_A2_BACKING_BASE,64u);
    fence();
    return memcmp((const void *)p,"LTV3CTX1",8)==0 &&
           le32(p+32u)==42u && le32(p+36u)==25408u &&
           le32(p+40u)==32u ? 0 : -1;
}
static int load_input(void *cookie)
{
    (void)cookie;
    /* Ingress events are NOT preloaded. A53 generates one current
     * timestep at dispatch using the accepted P07-A1 encoder.
     */
    return (hw.event_counts[0][0]==0 && hw.event_counts[0][1]==0)?0:-1;
}
static int write_result_callback(void *cookie,const p03_rt *runtime)
{
    (void)cookie;
    if(!runtime || runtime->counters.timesteps_completed!=26u ||
       runtime->counters.logical_dispatches!=26u ||
       runtime->counters.barriers!=26u ||
       runtime->first_fault!=P03_RT_FAULT_NONE)
        return -1;
    /* Final result is written only after p07_a2_run_frame returned DONE. */
    return p03_hw_quiescent(&hw)==P03_HW_OK ? 0:-1;
}
static uint64_t read_ticks(void *cookie)
{
    uint64_t ticks;
    (void)cookie;
    __asm__ volatile("isb; mrs %0, cntvct_el0":"=r"(ticks));
    return ticks;
}
static void on_error(void *cookie,const p03_rt *runtime)
{
    (void)cookie;
    if(runtime)
        fault_detail=(uint32_t)runtime->first_fault;
}
static int prepare(void *cookie,const uint8_t *record,size_t bytes,
                   p03_rt *runtime,p03_rt_ops *ops,void **ops_ctx)
{
    const volatile uint8_t *page=(const volatile uint8_t *)
                                    (uintptr_t)P07_A2_MASTER_BASE;
    uint32_t comp,syn,route,axons=0u,index;
    uint64_t metadata;
    p03_hw_io io=p03_hw_xilinx_io();
    (void)cookie;
    active_runtime=NULL;
    if(!master_verified || record!=ingress || bytes!=sizeof(ingress) ||
       !runtime || !ops || !ops_ctx || validate_deployment(NULL)!=0)
        return -1;
    if(reset_core0_from_master()!=0 ||
       p03_hw_init(&hw,&io,NULL,P03_HW_BACKING_BASE,
                   P07_A2_POLL_LIMIT)!=P03_HW_OK)
        return -1;
    comp=le32(page+32u);syn=le32(page+36u);route=le32(page+40u);
    if(comp!=42u || syn!=25408u || route!=32u) return -1;
    metadata=((uint64_t)comp<<7u)|((uint64_t)syn<<18u)|
             ((uint64_t)route<<34u);
    if(p03_hw_register_core(&hw,0u,metadata,0u,0u)!=P03_HW_OK)
        return -1;
    /* Read the real sparse axon bank of the SHA-pinned static context.
     * All 816 valid IDs are registered, including the 32 internal routes.
     * Never treat pixel index as destination axon.
     */
    for(index=0;index<4096u;++index) {
        uint64_t word=le64(page+0x7000u+(uintptr_t)index*8u);
        if((word>>42u)!=0u)return -1;
        if(word & (UINT64_C(1)<<41u)) {
            if(p03_hw_register_axon(&hw,0u,(uint16_t)index)!=P03_HW_OK)
                return -1;
            ++axons;
        } else if(word!=0u) return -1;
    }
    if(axons!=816u) return -1;
    for(index=0;index<784u;++index) {
        uint32_t axon=(uint32_t)ingress[128u+2u*index] |
                     ((uint32_t)ingress[128u+2u*index+1u]<<8u);
        if(axon>=4096u || !(hw.valid_axons[0][axon>>3u] &
                            (uint8_t)(1u<<(axon&7u))))
            return -1;
    }
    memset(&bridge,0,sizeof(bridge));
    bridge.hw=&hw;
    bridge.runtime=runtime;
    bridge.app_cookie=&hw;
    bridge.validate_deployment=validate_deployment;
    bridge.validate_backing=validate_backing;
    bridge.load_input=load_input;
    bridge.write_result=write_result_callback;
    bridge.read_ticks=read_ticks;
    bridge.on_error=on_error;
    if(p03_hw_bind_runtime(&bridge,&bridge_ops)!=0)
        return -1;
    *ops=bridge_ops;
    *ops_ctx=&bridge;
    active_runtime=runtime;
    return 0;
}
static int append_current(void *cookie,uint8_t slot,uint8_t bank,
                          const uint16_t *axons,size_t count)
{
    uint32_t words[8]={0};
    uint32_t existing,i;
    (void)cookie;
    if(slot!=0u || bank>1u || count>784u || (count && !axons))
        return -1;
    existing=hw.event_counts[0][bank];
    if(existing>4096u || count>4096u-existing) return -1;
    /* Preflight all IDs/registrations before writing a single event. */
    for(i=0;i<count;++i)
        if(axons[i]>=4096u ||
           !(hw.valid_axons[0][axons[i]>>3u] &
             (uint8_t)(1u<<(axons[i]&7u))))
            return -1;
    for(i=0;i<count;++i) {
        words[0]=axons[i];
        if(p03_hw_debug_word(&hw,slot,bank?
                             P03_HW_EVENT1_DEBUG_BANK:
                             P03_HW_EVENT0_DEBUG_BANK,
                             (uint16_t)(existing+i),1,words)!=P03_HW_OK)
            return -1;
        hw.event_counts[0][bank]=(uint16_t)(existing+i+1u);
    }
    return 0;
}
static int read_trace(void *cookie,uint8_t slot,uint16_t compartment,
                      uint32_t words[8])
{
    uint32_t i,k,tick;
    (void)cookie;
    if(!active_runtime) return -1;
    tick=active_runtime->current_timestep;
    if(!words || slot!=0u || compartment<32u || compartment>=42u ||
       tick>=26u)
        return -1;
    if(current_frame==batch.trace_frame) {
        if(compartment==32u) {
            for(i=0;i<42u;++i) {
                uint32_t raw[8]={0};
                if(p03_hw_debug_word(&hw,slot,P07_A2_TRACE_BANK,
                                      (uint16_t)i,0,raw)!=P03_HW_OK)
                    return -1;
                for(k=0;k<8u;++k) {
                    uint32_t idx=(P07_A2_TRACE_OFFSET/4u)+
                                  (tick*42u+i)*8u+k;
                    result_area[idx]=raw[k];
                    if(i>=32u)trace_cache[i-32u][k]=raw[k];
                }
            }
        }
        memcpy(words,trace_cache[compartment-32u],8u*sizeof(uint32_t));
        return 0;
    }
    return p03_hw_debug_word(&hw,slot,P07_A2_TRACE_BANK,
                             compartment,0,words)==P03_HW_OK?0:-1;
}
static void write_frame_result(uint32_t frame,int rc,
                               const p07_a2_result *r)
{
    uint32_t i,base=(P07_A2_FRAME_RESULT_OFFSET/4u)+
                      frame*(P07_A2_FRAME_RESULT_BYTES/4u);
    uint32_t input_total=0u;
    for(i=0;i<32u;++i)result_area[base+i]=0u;
    result_area[base+0u]=(rc==0)?P07_A2_MAILBOX_OK:P07_A2_MAILBOX_FAIL;
    result_area[base+1u]=r->predicted_class;
    result_area[base+2u]=r->all_silent;
    result_area[base+3u]=r->timesteps;
    result_area[base+4u]=r->dispatches;
    result_area[base+5u]=r->barriers;
    result_area[base+6u]=r->committed_routes;
    result_area[base+7u]=r->dropped_final_packets;
    for(i=0;i<10u;++i)result_area[base+8u+i]=r->counts[i];
    for(i=0;i<26u;++i) input_total+=r->external_events[i];
    result_area[base+18u]=input_total;
    result_area[base+19u]=(uint32_t)r->first_fault;
    result_area[base+20u]=(uint32_t)r->fault_phase;
    result_area[base+21u]=(uint32_t)ingress[56]|
                             ((uint32_t)ingress[57]<<8u)|
                             ((uint32_t)ingress[58]<<16u)|
                             ((uint32_t)ingress[59]<<24u);
    for(i=0;i<26u;++i) {
        uint32_t cls,bits=0u,word,offset;
        for(cls=0;cls<10u;++cls)
            bits|=(uint32_t)r->output_spikes[i][cls]<<cls;
        word=i*10u/32u;offset=(i*10u)%32u;
        result_area[base+23u+word]|=bits<<offset;
        if(offset>22u)
            result_area[base+24u+word]|=bits>>(32u-offset);
    }
    flush_result();
}
int main(void)
{
    p07_a2_driver driver;
    p07_a2_result frame_result;
    uint32_t frame;
    int rc;
    (void)firmware_identity[0];
    reset_result();
    master_verified=0u;
    current_frame=0u;
    fault_detail=0u;
    if(load_batch()!=0) {record_failed(1u,0u);halt_forever();}
    if(verify_immutable_master()!=0) {
        record_failed(2u,0u);halt_forever();
    }
    if(p03_hw_xilinx_fpd128_ready()!=0) {
        record_failed(3u,0u);halt_forever();
    }
    driver.prepare=prepare;
    driver.append_current=append_current;
    driver.read_trace=read_trace;
    driver.cookie=&hw;
    for(frame=0;frame<batch.frame_count;++frame) {
        current_frame=frame;
        if(load_image_record(frame)!=0) {
            record_failed(4u,frame);halt_forever();
        }
        rc=p07_a2_run_frame(ingress,sizeof(ingress),&driver,&frame_result);
        write_frame_result(frame,rc,&frame_result);
        if(rc!=P07_A2_OK) {
            record_failed(5u,
              ((uint32_t)frame_result.fault_phase<<16u)|
               (uint32_t)frame_result.first_fault);
            halt_forever();
        }
        result_area[8u]=frame+1u; /* frames completed */
        flush_result();
    }
    result_area[2u]=P07_A2_MAILBOX_OK;
    result_area[3u]=0u;
    flush_result();
    halt_forever();
    return 0;
}
