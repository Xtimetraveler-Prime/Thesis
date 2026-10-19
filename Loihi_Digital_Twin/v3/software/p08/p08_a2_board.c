/* P08-A2.1 latency-only derivative of frozen P07-A4.2b.
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
#include "p07_a4_stream.h"
#include "p07_a4_supervisor.h"
#include "p08_a2_timing.h"

#define P07_A2_BACKING_BASE UINT32_C(0x40000000)
#define P07_A2_CONTEXT_BYTES 524288u
#define P07_A2_POLL_LIMIT UINT32_C(100000000)
#define P07_A2_TRACE_BANK 7u
#define P07_A2_MAILBOX_MAGIC UINT32_C(0x52373050) /* "P07R" */
#define P07_A2_MAILBOX_OK UINT32_C(0x600D600D)
#define P07_A2_MAILBOX_FAIL UINT32_C(0xDEAD0000)
#define P07_A4_BUILD_ID "P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1"

_Static_assert(P03_HW_EVENT_DEPTH == P07_A1_AXON_CAPACITY,
               "P07/P03 event bank capacity mismatch");
_Static_assert(P07_A2_TRACE_BYTES <= 65536u,"A4 trace overflow");

static const volatile char firmware_identity[] = P07_A4_BUILD_ID;
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
static p07_a4_descriptor dataset;
static uint8_t desc_bytes[P07_A4_HEADER_BYTES],map_bytes[P07_A4_MAP_BYTES];
static uint8_t dataset_verified;
static uint8_t ingress[P07_A1_RECORD_BYTES];
static uint32_t trace_cache[P07_A2_OUTPUTS][8];
static uint8_t master_verified;
static uint32_t current_frame;
static uint32_t fault_detail;
static p03_rt_counters p08_saved_counters;
static uint8_t p08_counters_valid;
static uint64_t p08_run_start,p08_counter_hz;
static volatile uint8_t *const p08_area=(volatile uint8_t *)(uintptr_t)P08_A2_BASE;
static volatile uint8_t *const journal_area=(volatile uint8_t *)(uintptr_t)P07_A4_JOURNAL_BASE;
static volatile uint32_t *const trace_area=(volatile uint32_t *)(uintptr_t)P07_A4_TRACE_BASE;

static void fence(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static void flush_region(uintptr_t addr,uint32_t len)
{
    fence();Xil_DCacheFlushRange((INTPTR)addr,len);fence();
}
static void halt_forever(void) {for(;;)__asm__ volatile("wfe");}
static uint64_t p08_clock_rate(void)
{
    uint64_t freq;
    __asm__ volatile("isb; mrs %0, cntfrq_el0":"=r"(freq));
    return freq;
}
static void p08_clear_sidecar(void)
{
    uint32_t i;
    volatile uint32_t *dst=(volatile uint32_t *)(uintptr_t)P08_A2_BASE;
    for(i=0;i<P08_A2_CAPACITY/4u;++i)dst[i]=0u;
    flush_region(P08_A2_BASE,P08_A2_CAPACITY);
}
static int p08_header(uint32_t status,uint32_t completed,uint64_t stop)
{
    uint8_t buf[P08_A2_HEADER_BYTES];
    uint32_t i;
    if(p08_a2_pack_header(buf,sizeof(buf),dataset.frame_count,
          dataset.trace_frame,completed,status,p08_counter_hz,
          p08_run_start,stop)!=0)return -1;
    for(i=0;i<sizeof(buf);++i)p08_area[i]=buf[i];
    flush_region(P08_A2_BASE,P08_A2_HEADER_BYTES);
    return 0;
}
static int p08_write_record(const p08_a2_record *record)
{
    uint8_t buf[P08_A2_RECORD_BYTES];
    uint32_t i;
    uintptr_t addr;
    if(record->image_index>=dataset.frame_count ||
       p08_a2_pack_record(buf,sizeof(buf),record)!=0)return -1;
    addr=(uintptr_t)P08_A2_BASE+P08_A2_HEADER_BYTES+
         (uintptr_t)record->image_index*P08_A2_RECORD_BYTES;
    if(addr+sizeof(buf)>(uintptr_t)P08_A2_BASE+P08_A2_CAPACITY)return -1;
    for(i=0;i<sizeof(buf);++i)
        ((volatile uint8_t *)(uintptr_t)addr)[i]=buf[i];
    flush_region(addr,sizeof(buf));
    return 0;
}
static uint32_t le32(const volatile uint8_t *p)
{
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint64_t le64(const volatile uint8_t *p)
{
    return (uint64_t)le32(p)|((uint64_t)le32(p+4u)<<32);
}
static int commit_progress(void *unused,uint32_t status,uint32_t done,uint32_t fault)
{
    uint8_t raw[P07_A4_JOURNAL_HEADER_BYTES];
    uint32_t k,n=dataset_verified?dataset.frame_count:1u;
    uint32_t tr=dataset_verified?dataset.trace_frame:0u;
    uint32_t id=dataset_verified?dataset.descriptor_crc32:0u;
    (void)unused;
    if(p07_a4_make_journal_header(raw,sizeof(raw),n,tr,id,status,done,fault)!=0)return -1;
    for(k=0;k<sizeof(raw);++k)journal_area[k]=raw[k];
    flush_region(P07_A4_JOURNAL_BASE,P07_A4_JOURNAL_HEADER_BYTES);
    return 0;
}
static void record_failed(uint32_t code)
{
    (void)commit_progress(NULL,UINT32_C(0xDEAD0000)|code,0u,UINT32_MAX);
}
static void clear_output(void)
{
    uint32_t k;
    volatile uint32_t *dst=(volatile uint32_t *)(uintptr_t)P07_A4_JOURNAL_BASE;
    for(k=0;k<P07_A4_JOURNAL_CAPACITY/4u;++k)dst[k]=0u;
    for(k=0;k<65536u/4u;++k)trace_area[k]=0u;
    flush_region(P07_A4_JOURNAL_BASE,P07_A4_JOURNAL_CAPACITY);
    flush_region(P07_A4_TRACE_BASE,65536u);
}
static int load_dataset(void)
{
    const volatile uint8_t *a=(const volatile uint8_t *)(uintptr_t)P07_A4_DESCRIPTOR_BASE;
    const volatile uint8_t *b=(const volatile uint8_t *)(uintptr_t)P07_A4_MAPPING_BASE;
    uint32_t k,n;
    dataset_verified=0u;
    Xil_DCacheInvalidateRange((INTPTR)P07_A4_DESCRIPTOR_BASE,P07_A4_HEADER_BYTES+P07_A4_MAP_BYTES);
    fence();
    for(k=0;k<P07_A4_HEADER_BYTES;++k)desc_bytes[k]=a[k];
    for(k=0;k<P07_A4_MAP_BYTES;++k)map_bytes[k]=b[k];
    n=le32(a+16u);
    if(!n||n>P07_A4_MAX_FRAMES)return -1;
    Xil_DCacheInvalidateRange((INTPTR)P07_A4_INPUT_BASE,n*P07_A4_IMAGE_BYTES);
    fence();
    if(p07_a4_validate_staging(desc_bytes,sizeof(desc_bytes),map_bytes,sizeof(map_bytes),
       (const uint8_t *)(uintptr_t)P07_A4_INPUT_BASE,
       (size_t)n*P07_A4_IMAGE_BYTES,&dataset)!=0)return -1;
    dataset_verified=1u;
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
    uintptr_t loc=(uintptr_t)P07_A4_INPUT_BASE+(uintptr_t)frame*P07_A4_IMAGE_BYTES;
    p07_a1_info info;
    if(!dataset_verified||frame>=dataset.frame_count||
       loc+P07_A4_IMAGE_BYTES>(uintptr_t)P07_A4_INPUT_BASE+P07_A4_INPUT_CAPACITY)return -1;
    Xil_DCacheInvalidateRange((INTPTR)loc,P07_A4_IMAGE_BYTES);fence();
    if(p07_a4_make_ingress(&dataset,map_bytes,sizeof(map_bytes),
      (const uint8_t *)loc,P07_A4_IMAGE_BYTES,frame,ingress,sizeof(ingress))!=0)return -1;
    if(p07_a1_validate(ingress,sizeof(ingress),&info)!=P07_A1_OK ||
       memcmp(info.ddr_sha256,expected_ddr_sha,32u)!=0 ||
       memcmp(info.deployment_fingerprint,expected_compiled_sha,32u)!=0)return -1;
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
    if(p03_hw_quiescent(&hw)!=P03_HW_OK)return -1;
    p08_saved_counters=runtime->counters;
    p08_counters_valid=1u;
    return 0;
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
    if(current_frame==dataset.trace_frame) {
        if(compartment==32u) {
            for(i=0;i<42u;++i) {
                uint32_t raw[8]={0};
                if(p03_hw_debug_word(&hw,slot,P07_A2_TRACE_BANK,
                                      (uint16_t)i,0,raw)!=P03_HW_OK)
                    return -1;
                for(k=0;k<8u;++k) {
                    uint32_t idx=(tick*42u+i)*8u+k;
                    trace_area[idx]=raw[k];
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
static int commit_frame_result(uint32_t frame,const p07_a2_result *r)
{
    p07_a4_compact_result obj;
    uint8_t buf[P07_A4_FRAME_RESULT_BYTES];
    uintptr_t loc=(uintptr_t)P07_A4_JOURNAL_BASE+P07_A4_JOURNAL_HEADER_BYTES+
       (uintptr_t)frame*P07_A4_FRAME_RESULT_BYTES;
    uint32_t t,cls,k;
    if(!r||frame>=dataset.frame_count||
       loc+P07_A4_FRAME_RESULT_BYTES>(uintptr_t)P07_A4_JOURNAL_BASE+P07_A4_JOURNAL_CAPACITY||
       r->timesteps!=26u||r->dispatches!=26u||r->barriers!=26u||
       r->first_fault!=P03_RT_FAULT_NONE)return -1;
    memset(&obj,0,sizeof(obj));
    obj.image_index=frame;
    obj.pixel_crc32=p07_a4_crc32(ingress+128u+1568u,784u);
    obj.committed_routes=r->committed_routes;
    obj.dropped_final_packets=r->dropped_final_packets;
    for(t=0;t<26u;++t) {
        obj.external_event_total+=r->external_events[t];
        for(cls=0;cls<10u;++cls)obj.output_spikes[t][cls]=r->output_spikes[t][cls];
    }
    if(p07_a4_pack_result(&obj,buf,sizeof(buf))!=0)return -1;
    for(cls=0;cls<10u;++cls)
        if((uint32_t)buf[32u+2u*cls]+((uint32_t)buf[33u+2u*cls]<<8u)!=r->counts[cls])return -1;
    if((uint32_t)buf[12u]!=r->predicted_class ||
       (uint32_t)buf[16u]!=r->all_silent)return -1;
    for(k=0;k<sizeof(buf);++k)((volatile uint8_t *)(uintptr_t)loc)[k]=buf[k];
    flush_region(loc,sizeof(buf));
    return 0;
}
static int execute_image(void *ctx,uint32_t frame)
{
    p07_a2_driver *driver=(p07_a2_driver *)ctx;
    p07_a2_result res;
    p08_a2_record t;
    memset(&t,0,sizeof(t));
    t.image_index=frame;
    t.flags=frame==dataset.trace_frame?1u:0u;
    p08_counters_valid=0u;
    t.service_start=read_ticks(NULL);
    current_frame=frame;
    if(load_image_record(frame)!=0)return -1;
    t.after_ingress=read_ticks(NULL);
    if(p07_a2_run_frame(ingress,sizeof(ingress),driver,&res)!=P07_A2_OK)return -1;
    t.after_neural=read_ticks(NULL);
    if(!p08_counters_valid)return -1;
    if(commit_frame_result(frame,&res)!=0)return -1;
    if(frame==dataset.trace_frame)flush_region(P07_A4_TRACE_BASE,65536u);
    t.after_commit=read_ticks(NULL);
    t.pl_dispatch_cycles=p08_saved_counters.pl_dispatch_cycles;
    t.pl_page_cycles=p08_saved_counters.pl_page_cycles;
    t.ps_inference_ticks=p08_saved_counters.ps_inference_ticks;
    t.ps_control_ticks=p08_saved_counters.ps_control_ticks;
    t.ps_route_ticks=p08_saved_counters.ps_route_ticks;
    t.ps_barrier_ticks=p08_saved_counters.ps_barrier_ticks;
    if(p08_write_record(&t)!=0 || p08_header(0u,frame+1u,0u)!=0)
        return -1;
    return 0;
}
int main(void)
{
    p07_a2_driver driver;
    p07_a4_callbacks ops;
    uint32_t done=0u,fault=UINT32_MAX;
    int rc;
    (void)firmware_identity[0];
    master_verified=0u;dataset_verified=0u;current_frame=0u;fault_detail=0u;
    memset(&dataset,0,sizeof(dataset));
    clear_output();
    /* Scrub candidate evidence even if descriptor/immutable master rejects. */
    p08_clear_sidecar();
    if(load_dataset()!=0){record_failed(1u);halt_forever();}
    if(verify_immutable_master()!=0){record_failed(2u);halt_forever();}
    if(p03_hw_xilinx_fpd128_ready()!=0){record_failed(3u);halt_forever();}
    p08_counter_hz=p08_clock_rate();
    if(!p08_counter_hz){record_failed(4u);halt_forever();}
    p08_run_start=read_ticks(NULL);
    if(p08_header(0u,0u,0u)!=0){record_failed(5u);halt_forever();}
    driver.prepare=prepare;driver.append_current=append_current;
    driver.read_trace=read_trace;driver.cookie=&hw;
    ops.cookie=&driver;ops.execute_and_commit_image=execute_image;
    ops.commit_progress=commit_progress;
    rc=p07_a4_run_images(dataset.frame_count,&ops,&done,&fault);
    if(p08_header(rc==P07_A4_RUN_OK?P08_A2_OK_STATUS:
                  P08_A2_FAIL_STATUS,done,read_ticks(NULL))!=0)
        halt_forever();
    if(rc!=P07_A4_RUN_OK)halt_forever();
    halt_forever();
    return 0;
}
