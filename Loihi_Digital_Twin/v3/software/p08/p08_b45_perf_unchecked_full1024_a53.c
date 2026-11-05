/* P08-B4.5 unchecked: DISTINCT offline-build A53 application.
 * Original P07/P03 neural logic, frozen model and 1024 image service
 * boundaries are unchanged. Only context-reset integrity policy differs.
 * Separate, explicitly UNPROTECTED performance-only 16-image pilot.
 * No XMPU or read-only DDR security guarantee is claimed.
 * Requires operator-approved guarded JTAG, original staging and a
 * post-run backup readback before any evidence is accepted.
 * Input, journal and A53 timing integrity remain for external proof.
 */
#include <stdint.h>
#include <stddef.h>
#include <string.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "p03_mmio.h"
#include "p03_hw_xilinx_io.h"
#include "p07_a2_sha256.h"
#include "p07_b4l_b3_bindings.h"
#include "p07_b4m_frozen_routes.h"
#include "p07_b4m_dispatch_metadata.h"
#include "p07_b4m_full_inference.h"
#include "p08_b2_ingress.h"
#include "p08_b2_context_reset.h"
#include "p08_b45_reset_variants.h"
#include "p08_b45_perf_reset.h"
#include "p08_b2_service_meter.h"
/* Generated ONLY from original frozen B2.4 33-file source at build staging. */
#include "p08_b2_2_original_context_sha256.h"

#define B23_ID "P08_B45_PERF_UNCHECKED_ORIGINAL_27CORE_1024_A53_V1"
#define B45_MODE P08_B45_UNCHECKED_CONTENT
#define B23_FRAMES 1024u
#define B23_RAW_POOL 0x42100000u
#define B23_RAW_POOL_BYTES (1024u*784u)
#define B23_BACKUP 0x43000000u
#define B23_JOURNAL 0x42200000u
#define B23_TIMING 0x42300000u
/* NEW experimental PC-readable 1024x256B reset-only profiling records.
 * CANNOT be interpreted as original production timer or other output. */
#define B45_PROFILE_BASE UINT32_C(0x42400000)
#define B45_PROFILE_BYTES (B23_FRAMES*B23_ROW_BYTES)
#define B45_PROFILE_END (B45_PROFILE_BASE+B45_PROFILE_BYTES)
#define B45_PROFILE_ROW_MAGIC UINT32_C(0x50384532)
#define B23_MAILBOX 0x43FF0200u
#define B23_MAGIC UINT32_C(0x50384232)
#define B23_ROW_MAGIC UINT32_C(0x4A423832)
#define B23_TIMER_MAGIC UINT32_C(0x54423832)
#define B23_FAIL UINT32_C(0xDEAD0823)
#define B23_PASS UINT32_C(0x600D0823)
#define B23_DONE UINT32_C(0xC0DEF00D)
#define B23_WORDS 64u
#define B23_ROW_BYTES (B23_WORDS*4u)
#define B23_TICK_READY 26u
#define B23_DISPATCHES 702u
#define B23_SELECT_TRACE 1023u
#define B23_FIRST_FAULT_FRAME UINT32_C(0xFFFFFFFF)

_Static_assert(B23_RAW_POOL_BYTES==802816u,"original matched raw pool geometry");
_Static_assert(B45_PROFILE_BYTES==262144u,"one 256B profile row per 1024 frames");
_Static_assert(B45_PROFILE_BASE>=B23_TIMING+0x100000u,
               "profile sidecar must not overlap accepted original timing");
_Static_assert(B45_PROFILE_END<=B23_BACKUP,
               "profile must not overwrite original immutable backup");
_Static_assert(B45_PROFILE_END<=B4L_BIND_BASE,
               "profile must not overwrite original B4l bindings");
_Static_assert(B45_PROFILE_BASE>=P07_B4M_FRAME_BASE+P07_B4M_FRAME_MAX_BYTES,
               "profile must not overwrite original input frame workspace");
_Static_assert(P08_B2_WIRE_BYTES==123216u,"original B1.3 packed input changed");
_Static_assert(B23_FRAMES*B23_ROW_BYTES<=0x100000u,
               "1024 result journals exceed reserved 1MiB");
_Static_assert(P07_B2_MAX_ROUTE_BINDINGS==10000u,
               "separate B4m 10K output-route build macro required");
_Static_assert(sizeof(p08_b2_original_context_sha256)==27u*32u,
               "genuine 27xSHA256 frozen pins incomplete");

static const volatile char app_identity[]=B23_ID;
static const uint8_t accepted_raw_pool_sha[32]={
    0x73,0x90,0x06,0xf0,0x3b,0x37,0xc3,0x6d,
    0x7a,0xa1,0x1b,0x6b,0x68,0x61,0x23,0x38,
    0xfc,0x52,0x49,0xc7,0xf4,0x8b,0x9d,0x85,
    0x45,0x20,0xee,0x7e,0x3e,0xa9,0xc0,0x6e
};
/* Original P07 PS/PL C data paths are called UNMODIFIED. */
static p03_hw_adapter hw;
static p07_b3_pager pager;
static p07_b3c2_hw_scheduler scheduler;
static b4l_binding_receipt binding_receipt;
static p07_b4m_frozen_binding frozen;
static p07_b4m_full_workspace buffers;
static p07_b4m_full_receipt receipt;
static p08_b45_reset_state reset_state;
static p08_b2_route_binding b23_input_routes;
static p08_b2_meter meter;
static uint32_t cookie;
static uint64_t packet_words[P07_B3C_MAX_RAW_WORDS];
static uint64_t p03_scratch[P03_RT_MAX_PACKETS];
static p07_b2_route route_buffer[P07_B2_MAX_ROUTE_BINDINGS];
static uint16_t compartment_buffer[P07_B3_CORES];
static uint16_t verified_spikes[P07_B4M_TRACE_SPIKE_CAP][2];
static uint32_t current_words[P07_B4A_WORD_CAPACITY];
static uint8_t packet_scratch[P07_B3C_MAX_FRAME_BYTES];
static uint8_t packet_frame[P07_B3C_MAX_FRAME_BYTES];

static void fence(void){__asm__ volatile("dsb sy" ::: "memory");}
static void halt(void){for(;;)__asm__ volatile("wfe");}
static uint64_t observed_frequency(void){
    uint64_t result;__asm__ volatile("mrs %0, cntfrq_el0":"=r"(result));
    return result;
}
static uint64_t observed_counter(void){
    uint64_t result;
    __asm__ volatile("isb; mrs %0, cntvct_el0":"=r"(result)::"memory");
    return result;
}
static void invalidate(uintptr_t addr,uint32_t size){
    fence();Xil_DCacheInvalidateRange((INTPTR)addr,size);fence();
}
static void flush(uintptr_t addr,uint32_t size){
    fence();Xil_DCacheFlushRange((INTPTR)addr,size);fence();
}
static int reset_invalidate(void *ctx,uintptr_t address,size_t len){
    (void)ctx;
    if(address>UINT32_MAX || len>UINT32_MAX || len==0u)return -1;
    invalidate(address,(uint32_t)len);return 0;
}
static int reset_clean(void *ctx,uintptr_t address,size_t len){
    (void)ctx;
    if(address>UINT32_MAX || len>UINT32_MAX || len==0u)return -1;
    flush(address,(uint32_t)len);return 0;
}
static int reset_idle(void *ctx){
    p03_hw_adapter *target=(p03_hw_adapter *)ctx;
    return p03_hw_quiescent(target)==P03_HW_OK?0:-1;
}
static void reset_barrier(void *ctx){(void)ctx;fence();}
static int read_ddr32(void *ctx,uint64_t physical,uint32_t *value){
    uint64_t rel,offset;
    (void)ctx;
    if(!value||physical<P03_HW_BACKING_BASE||
       physical>=P03_HW_BACKING_BASE+27u*P03_HW_RECORD_BYTES||
       (physical&3u))return -1;
    rel=physical-P03_HW_BACKING_BASE;
    offset=rel%P03_HW_RECORD_BYTES;
    if(!((offset>=P03_HW_EVENT0_OFFSET&&offset<P03_HW_EVENT0_OFFSET+16384u)||
         (offset>=P03_HW_EVENT1_OFFSET&&offset<P03_HW_EVENT1_OFFSET+16384u)))
        return -1;
    *value=Xil_In32((UINTPTR)physical);
    return 0;
}
static uint32_t crc32(const uint8_t *data,size_t length){
    uint32_t result=UINT32_C(0xFFFFFFFF),j;
    size_t i;
    for(i=0u;i<length;i++){
        result^=data[i];
        for(j=0u;j<8u;j++)
            result=(result>>1u)^((result&1u)?UINT32_C(0xEDB88320):0u);
    }
    return ~result;
}
static void mailbox(uint32_t status,uint32_t frame,uint32_t fault,
                    uint32_t completed,uint64_t cntfrq){
    volatile uint32_t *m=(volatile uint32_t *)(uintptr_t)B23_MAILBOX;
    uint32_t i;
    for(i=0u;i<B23_WORDS;i++)m[i]=0u;
    m[0]=B23_MAGIC;m[1]=1u;m[2]=status;m[3]=frame;
    m[4]=fault;m[5]=completed;m[6]=(uint32_t)cntfrq;
    m[7]=(uint32_t)(cntfrq>>32u);
    m[8]=reset_state.generation;
    m[9]=pager.counters.dispatches;
    m[10]=pager.counters.barriers;
    m[11]=scheduler.poisoned;
    m[12]=reset_state.poisoned;
    m[13]=(uint32_t)hw.last_error;
    m[63]=B23_DONE;
    flush(B23_MAILBOX,B23_ROW_BYTES);
}
static int sha_ok(const uint8_t *p,size_t n,const uint8_t pinned[32]){
    uint8_t actual[32];
    p07_a2_sha256(p,n,actual);
    return memcmp(actual,pinned,32u)==0;
}
static int begin_frozen_runtime(void){
    const uint8_t *descriptor=(const uint8_t *)(uintptr_t)B4L_BIND_BASE;
    const uint8_t *outroutes=(const uint8_t *)(uintptr_t)P07_B4M_ROUTE_OUT_BASE;
    const uint8_t *inroutes=(const uint8_t *)(uintptr_t)P07_B4M_ROUTE_IN_BASE;
    const uint8_t *headers[P07_B4M_METADATA_CORES];
    p03_hw_io io=p03_hw_xilinx_io();
    uint32_t i;
    if(p03_hw_init(&hw,&io,&cookie,P03_HW_BACKING_BASE,1000000u)!=P03_HW_OK ||
       p03_hw_identify(&hw)!=P03_HW_OK)
        return -1;
    invalidate(B4L_BIND_BASE,B4L_BIND_SIZE);
    invalidate(P07_B4M_ROUTE_OUT_BASE,P07_B4M_ROUTE_OUT_BYTES);
    invalidate(P07_B4M_ROUTE_IN_BASE,P07_B4M_ROUTE_IN_BYTES);
    if(b4l_bind_frozen(&hw,descriptor,B4L_BIND_SIZE,
                        &binding_receipt)!=B4L_BIND_OK)
        return -2;
    for(i=0u;i<P07_B4M_METADATA_CORES;i++){
        uintptr_t p=P03_HW_BACKING_BASE+
                     (uintptr_t)i*P03_HW_RECORD_BYTES;
        invalidate(p,0x1000u);
        headers[i]=(const uint8_t *)p;
    }
    if(p07_b4m_apply_p02_counts(&hw,headers)!=P07_B4M_METADATA_OK)
        return -3;
    if(p07_b4m_mount_frozen_routes(&frozen,outroutes,
            P07_B4M_ROUTE_OUT_BYTES,inroutes,
            P07_B4M_ROUTE_IN_BYTES,&hw,route_buffer,
            P07_B2_MAX_ROUTE_BINDINGS,compartment_buffer,
            P07_B3_CORES)!=P07_B4M_ROUTE_OK)
        return -4;
    return 0;
}
static int prepare_new_scheduler(void){
    if(p07_b3_init(&pager,P07_B3_ORDER_ASCENDING)!=P07_B3_OK)
        return -1;
    if(p07_b3c2_init(&scheduler,&pager,&hw,packet_words,
        P07_B3C_MAX_RAW_WORDS,p03_scratch,P03_RT_MAX_PACKETS)
        !=P07_B3C2_OK)return -2;
    memset(&buffers,0,sizeof(buffers));
    buffers.merged_current_words=current_words;
    buffers.merged_capacity=P07_B4A_WORD_CAPACITY;
    buffers.source_spikes=verified_spikes;
    buffers.source_capacity=P07_B4M_TRACE_SPIKE_CAP;
    buffers.frame_scratch=packet_scratch;
    buffers.scratch_capacity=sizeof(packet_scratch);
    buffers.packet_frame=packet_frame;
    buffers.frame_capacity=sizeof(packet_frame);
    return 0;
}
static int commit_journal(uint32_t index,const uint8_t *raw,size_t wire_bytes,
                          const p08_b45_reset_receipt *reset){
    volatile uint32_t *where=(volatile uint32_t *)(uintptr_t)
                            (B23_JOURNAL+(uintptr_t)index*B23_ROW_BYTES);
    uint32_t words[B23_WORDS]={0};
    uint8_t raw_sha[32],wire_sha[32];
    uint32_t i;
    p07_a2_sha256(raw,784u,raw_sha);
    p07_a2_sha256((const uint8_t *)(uintptr_t)P07_B4M_FRAME_BASE,
                  wire_bytes,wire_sha);
    words[0]=B23_ROW_MAGIC;words[1]=1u;
    words[2]=index;words[3]=B23_PASS;
    words[4]=reset->generation;
    words[5]=receipt.magic;
    words[6]=receipt.classification;
    words[7]=receipt.dispatches;
    words[8]=receipt.barriers;
    words[9]=receipt.trace_compartment_count;
    words[10]=receipt.external_current;
    words[11]=receipt.source_spikes;
    words[12]=receipt.captured_packets;
    words[13]=receipt.inserted_next;
    words[14]=receipt.page_ins;
    words[15]=receipt.page_outs;
    words[16]=receipt.final_outs;
    words[17]=(uint32_t)receipt.cumulative_trace_fnv64;
    words[18]=(uint32_t)(receipt.cumulative_trace_fnv64>>32u);
    words[19]=(uint32_t)receipt.read_bytes;
    words[20]=(uint32_t)(receipt.read_bytes>>32u);
    words[21]=(uint32_t)receipt.write_bytes;
    words[22]=(uint32_t)(receipt.write_bytes>>32u);
    words[23]=(uint32_t)wire_bytes;
    for(i=0u;i<10u;i++)words[24u+i]=receipt.output_spike_counts[i];
    memcpy(&words[34],raw_sha,32u);
    memcpy(&words[42],wire_sha,32u);
    words[61]=crc32((const uint8_t *)words,61u*4u);
    /* The byte-for-byte original journal is not published until
     * all values, checksums and hardware data are in memory.
     */
    words[63]=B23_DONE;
    for(i=0u;i<B23_WORDS;i++)where[i]=words[i];
    flush(B23_JOURNAL+(uintptr_t)index*B23_ROW_BYTES,B23_ROW_BYTES);
    return 0;
}
static void commit_timing(uint32_t index,const p08_b2_image_timing *result){
    volatile uint32_t *p=(volatile uint32_t *)(uintptr_t)
                         (B23_TIMING+(uintptr_t)index*B23_ROW_BYTES);
    uint32_t words[B23_WORDS]={0};
    uint32_t i;
    const uint64_t *cycles=result->phase_cycles;
    words[0]=B23_TIMER_MAGIC;words[1]=1u;
    words[2]=index;words[3]=B23_PASS;
    words[4]=(uint32_t)result->cntfrq_el0_hz;
    words[5]=(uint32_t)(result->cntfrq_el0_hz>>32u);
    words[6]=(uint32_t)result->service_entry_cntvct;
    words[7]=(uint32_t)(result->service_entry_cntvct>>32u);
    words[8]=(uint32_t)result->service_commit_cntvct;
    words[9]=(uint32_t)(result->service_commit_cntvct>>32u);
    words[10]=(uint32_t)result->total_service_cycles;
    words[11]=(uint32_t)(result->total_service_cycles>>32u);
    for(i=0u;i<P08_B2_METER_PHASES;i++){
        words[12u+2u*i]=(uint32_t)cycles[i];
        words[13u+2u*i]=(uint32_t)(cycles[i]>>32u);
    }
    words[61]=crc32((const uint8_t *)words,61u*4u);
    words[63]=B23_DONE;
    for(i=0u;i<B23_WORDS;i++)p[i]=words[i];
    flush(B23_TIMING+(uintptr_t)index*B23_ROW_BYTES,B23_ROW_BYTES);
}
/* Distinct B4.5 reset-only sidecar (one 256-byte row per frame).
 * word0 magic differs by mode, 1 version, 2 ordinal, 3 PASS, 4 mode,
 * 5 generation, 6 context count, 7 copy bytes,
 * 8 session source SHA checks, 9 session header checks,
 * 10 per-image source header count, 11 destination header count,
 * 12 per-image destination SHA count, 13:14 actual CNTFRQ,
 * 15:16 reset ticks, 17:18 one-time bind ticks,
 * 19 guard-provisioned flag is ALWAYS 0: deliberate limited-integrity pilot,
 * 20 frozen tick count (26), 21 dispatch count (702),
 * 61 CRC32(first 61 words), 63 DONE. All other fields zero.
 * The run-level bind ticks are repeated in each row, NEVER included
 * in the per-image service time. The original journal and six-phase
 * service timer remain unchanged.
 */
static void commit_reset_profile(uint32_t index,
         const p08_b45_reset_receipt *reset,uint64_t hz,
         uint64_t reset_ticks,uint64_t bind_ticks) {
    uint32_t words[B23_WORDS]={0},i;
    volatile uint32_t *dest=(volatile uint32_t *)(uintptr_t)
        (B45_PROFILE_BASE+(uintptr_t)index*B23_ROW_BYTES);
    words[0]=B45_PROFILE_ROW_MAGIC;
    words[1]=1u; words[2]=index; words[3]=B23_PASS;
    words[4]=reset->mode; words[5]=reset->generation;
    words[6]=reset->copied_records; words[7]=reset->copied_bytes;
    words[8]=reset->session_source_sha_checks;
    words[9]=reset->session_header_checks;
    words[10]=reset->source_header_checks;
    words[11]=reset->destination_header_checks;
    words[12]=reset->destination_sha_checks;
    words[13]=(uint32_t)hz; words[14]=(uint32_t)(hz>>32u);
    words[15]=(uint32_t)reset_ticks; words[16]=(uint32_t)(reset_ticks>>32u);
    words[17]=(uint32_t)bind_ticks; words[18]=(uint32_t)(bind_ticks>>32u);
    words[19]=0u; /* UNPROTECTED PERFORMANCE EXPERIMENT, NOT lock */
    words[20]=B23_TICK_READY; words[21]=B23_DISPATCHES;
    words[61]=crc32((const uint8_t *)words,61u*4u);
    words[63]=B23_DONE;
    for(i=0u;i<B23_WORDS;i++)dest[i]=words[i];
    flush(B45_PROFILE_BASE+(uintptr_t)index*B23_ROW_BYTES,B23_ROW_BYTES);
}
int main(void){
    const uint8_t *raw=(const uint8_t *)(uintptr_t)B23_RAW_POOL;
    const uint8_t *inroutes=(const uint8_t *)(uintptr_t)P07_B4M_ROUTE_IN_BASE;
    p08_b45_reset_config reset_config={0};
    uint64_t bind_ticks=0u;
    uint64_t cntfrq;
    uint32_t index;
    int result;
    (void)app_identity;
    mailbox(UINT32_C(0xC0DE0000),B23_FIRST_FAULT_FRAME,0u,0u,0u);
    if(p03_hw_xilinx_fpd128_ready()!=0){
        mailbox(B23_FAIL,B23_FIRST_FAULT_FRAME,100u,0u,0u);
        halt();
    }
    cntfrq=observed_frequency();
    if(cntfrq==0u){
        mailbox(B23_FAIL,B23_FIRST_FAULT_FRAME,101u,0u,cntfrq);
        halt();
    }
    /* Existing original raw pool and 27 original SHA-pinned contexts MUST
     * have been staged and readback-verified by a separate approved host
     * JTAG session; A53 cannot attest external owner from addresses alone.
     */
    invalidate(B23_RAW_POOL,B23_RAW_POOL_BYTES);
    if(!sha_ok(raw,B23_RAW_POOL_BYTES,accepted_raw_pool_sha)){
        mailbox(B23_FAIL,B23_FIRST_FAULT_FRAME,102u,0u,cntfrq);
        halt();
    }
    result=begin_frozen_runtime();
    if(result!=0){
        mailbox(B23_FAIL,B23_FIRST_FAULT_FRAME,103u,(uint32_t)result,cntfrq);
        halt();
    }
    if(p08_b2_admit_routes(inroutes,P07_B4M_ROUTE_IN_BYTES,
                          &b23_input_routes)!=P08_B2_OK ||
       b23_input_routes.route_count!=frozen.input_route_count){
        mailbox(B23_FAIL,B23_FIRST_FAULT_FRAME,104u,0u,cntfrq);
        halt();
    }
    reset_config.memory.mutable_records=(uint8_t *)(uintptr_t)P03_HW_BACKING_BASE;
    reset_config.memory.immutable_backup=(const uint8_t *)(uintptr_t)B23_BACKUP;
    reset_config.memory.original_sha256=p08_b2_original_context_sha256;
    reset_config.memory.record_bytes=P08_B2_CONTEXT_TOTAL;
    reset_config.memory.backup_bytes=P08_B2_CONTEXT_TOTAL;
    reset_config.memory.invalidate=reset_invalidate;
    reset_config.memory.clean=reset_clean;
    reset_config.memory.quiescent=reset_idle;
    reset_config.memory.barrier=reset_barrier;
    reset_config.memory.cookie=&hw;
    /* EXPLICITLY UNPROTECTED PERFORMANCE PILOT ONLY.
     * No lock or protection callback is installed. Source integrity is
     * enforced by independent host/same-session stage+SHA readback and
     * post-run backup readback, NOT in-band physical write prevention.
     */
    {
        uint64_t t0=observed_counter();
        int bind_result=p08_b45_perf_reset_bind(&reset_state,&reset_config,B45_MODE);
        uint64_t t1=observed_counter();
        if(bind_result!=P08_B45_RESET_OK || t1<t0){
            mailbox(B23_FAIL,B23_FIRST_FAULT_FRAME,105u,
                    (uint32_t)(-bind_result),cntfrq);
            halt();
        }
        bind_ticks=t1-t0;
    }
    /* Prepare a fresh known-zero mailbox/journal/timer destination,
     * distinct from accepted P07 V3/B5 receipt addresses. */
    for(index=0u;index<B23_FRAMES;index++){
        const uint8_t *pixels=raw+(uintptr_t)index*784u;
        p08_b45_reset_receipt reset_receipt={0};
        p08_b2_image_timing timing={0};
        uint64_t reset_ticks=0u;
        size_t wire_bytes=0u;
        uint64_t now=observed_counter();
        uint32_t fault=0u;
        if(p08_b2_meter_start(&meter,index,cntfrq,now)!=P08_B2_METER_OK)
            fault=200u;
        if(!fault){
            uint64_t t0=observed_counter();
            int rc=p08_b45_perf_reset_image(&reset_state,&reset_receipt);
            uint64_t t1=observed_counter();
            if(rc!=P08_B45_RESET_OK || t1<t0)fault=201u;
            else reset_ticks=t1-t0;
        }
        if(!fault && p08_b2_meter_mark(&meter,P08_B2_AFTER_STATE_RESTORE,
                                      observed_counter())!=P08_B2_METER_OK)
            fault=202u;
        if(!fault && p08_b2_encode_frame(
                &b23_input_routes,pixels,
                (uint8_t *)(uintptr_t)P07_B4M_FRAME_BASE,
                P07_B4M_FRAME_MAX_BYTES,&wire_bytes)!=P08_B2_OK)
            fault=203u;
        if(!fault){
            flush(P07_B4M_FRAME_BASE,(uint32_t)wire_bytes);
            if(p08_b2_meter_mark(&meter,P08_B2_AFTER_B13_INGRESS,
                                 observed_counter())!=P08_B2_METER_OK)
                fault=204u;
        }
        if(!fault && begin_frozen_runtime()!=0)fault=205u;
        if(!fault && prepare_new_scheduler()!=0)fault=206u;
        if(!fault && p08_b2_meter_mark(&meter,P08_B2_AFTER_SCHEDULER_REINIT,
                                      observed_counter())!=P08_B2_METER_OK)
            fault=207u;
        if(!fault && p07_b4m_full_run(&scheduler,&frozen.inputs,
            &frozen.packets,
            (const uint8_t *)(uintptr_t)P07_B4M_FRAME_BASE,wire_bytes,
            read_ddr32,&cookie,&buffers,&receipt)!=P07_B4M_FULL_OK)
            fault=208u;
        if(!fault && p08_b2_meter_mark(&meter,P08_B2_AFTER_ALL_26_TICKS,
                                       observed_counter())!=P08_B2_METER_OK)
            fault=209u;
        if(!fault && (
             receipt.magic!=P07_B4M_FULL_MAGIC ||
             receipt.dispatches!=B23_DISPATCHES ||
             receipt.barriers!=B23_TICK_READY ||
             receipt.final_outs!=3u ||
             receipt.trace_compartment_count!=1010u ||
             hw.last_error!=P03_HW_OK ||
             scheduler.poisoned||pager.failed ||
             reset_receipt.magic!=P08_B45_RESET_RECEIPT_MAGIC ||
             reset_receipt.version!=P08_B45_RESET_VERSION ||
             reset_receipt.mode!=B45_MODE ||
             reset_receipt.copied_records!=27u ||
             reset_receipt.copied_bytes!=P08_B2_CONTEXT_TOTAL ||
             reset_receipt.destination_sha_checks!=0u ||
             reset_receipt.session_source_sha_checks!=
                (B45_MODE==P08_B45_AUTHENTICATED_ONCE?27u:0u) ||
             reset_receipt.source_header_checks!=
                (B45_MODE==P08_B45_AUTHENTICATED_ONCE?27u:0u) ||
             reset_receipt.destination_header_checks!=
                (B45_MODE==P08_B45_AUTHENTICATED_ONCE?27u:0u) ||
             reset_receipt.generation!=index+1u))
            fault=210u;
        if(!fault && p08_b2_meter_mark(&meter,P08_B2_AFTER_RECEIPT_VALIDATE,
                                       observed_counter())!=P08_B2_METER_OK)
            fault=211u;
        if(!fault && commit_journal(index,pixels,wire_bytes,&reset_receipt)!=0)
            fault=212u;
        if(!fault && p08_b2_meter_mark(&meter,P08_B2_AFTER_JOURNAL_COMMIT,
                                       observed_counter())!=P08_B2_METER_OK)
            fault=213u;
        if(!fault && p08_b2_meter_finish(&meter,&timing)!=P08_B2_METER_OK)
            fault=214u;
        if(fault){
            mailbox(B23_FAIL,index,fault,index,cntfrq);
            xil_printf("P08_B45_PERF_UNCHECKED_FAILED frame=%lu fault=%lu\r\n",
                       (unsigned long)index,(unsigned long)fault);
            halt();
        }
        commit_timing(index,&timing);
        /* This B4.5 reset sidecar is outside the measured original
         * service interval; it still perturbs inter-image A53 state. */
        commit_reset_profile(index,&reset_receipt,cntfrq,
                             reset_ticks,bind_ticks);
        /* UART per image intentionally excluded from image service.
         * B first 1024 data includes selected trace index 1023, which
         * must later be excluded from 1023 ordinary latency stats.
         */
        mailbox(UINT32_C(0xC0DE0000),index,0u,index+1u,cntfrq);
    }
    mailbox(B23_PASS,B23_FRAMES-1u,0u,B23_FRAMES,cntfrq);
    xil_printf("P08_B45_PERF_UNCHECKED_1024_TERMINAL_DONE=1\r\n");
    halt();
    return 0;
}
