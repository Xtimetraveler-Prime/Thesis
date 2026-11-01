/* P07-B.4m: NEW experimental standalone A53 26-tick physical candidate.
 * NO accepted physical parity claim. Original B4l B3 first-epoch ELF/source
 * remain unchanged. Requires fresh same-session model/descriptor/route/
 * ingress physical byte readback and separate low DDR ownership assessment.
 */
#include <stdint.h>
#include <string.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "p03_mmio.h"
#include "p03_hw_xilinx_io.h"
#include "p07_b4l_b3_bindings.h"
#include "p07_b4m_frozen_routes.h"
#include "p07_b4m_full_inference.h"
#define B4M_MAILBOX UINT32_C(0x43FF0000)
#define B4M_MAILBOX_MAGIC UINT32_C(0x42344D31)
#define B4M_MAILBOX_PASS UINT32_C(0x600D600D)
#define B4M_MAILBOX_FAIL UINT32_C(0xDEAD0000)
#define B4M_MAILBOX_DONE UINT32_C(0xC0DEF00D)
static const volatile char elf_identity[]="P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1";
static volatile uint32_t *const mailbox=(volatile uint32_t *)(uintptr_t)B4M_MAILBOX;
static p03_hw_adapter hw;
static p07_b3_pager pager;
static p07_b3c2_hw_scheduler scheduler;
static uint32_t cookie;
static b4l_binding_receipt binding_receipt;
static p07_b4m_frozen_binding frozen;
static p07_b4m_full_receipt receipt;
static p07_b4m_full_workspace buffers;
static uint64_t packet_words[P07_B3C_MAX_RAW_WORDS];
static uint64_t p03_scratch[P03_RT_MAX_PACKETS];
static p07_b2_route route_buffer[P07_B2_MAX_ROUTE_BINDINGS];
static uint16_t compartment_buffer[P07_B3_CORES];
static uint16_t verified_spikes[P07_B4M_TRACE_SPIKE_CAP][2];
static uint32_t current_words[P07_B4A_WORD_CAPACITY];
static uint8_t packet_scratch[P07_B3C_MAX_FRAME_BYTES];
static uint8_t packet_frame[P07_B3C_MAX_FRAME_BYTES];
static void fence(void){__asm__ volatile("dsb sy" ::: "memory");}
static void publish(void){
    fence();Xil_DCacheFlushRange((INTPTR)B4M_MAILBOX,256u);fence();
}
static void halt(void){for(;;)__asm__ volatile("wfe");}
static uint32_t le32(const uint8_t *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|
           ((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);
}
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
int main(void){
    const uint8_t *const descriptor=(const uint8_t *)(uintptr_t)B4L_BIND_BASE;
    const uint8_t *const routes=(const uint8_t *)(uintptr_t)P07_B4M_ROUTE_OUT_BASE;
    const uint8_t *const ingress_routes=(const uint8_t *)(uintptr_t)P07_B4M_ROUTE_IN_BASE;
    const uint8_t *const wire=(const uint8_t *)(uintptr_t)P07_B4M_FRAME_BASE;
    p03_hw_io io=p03_hw_xilinx_io();
    int width=-1,init=-1,id=-1,bound=-1,mounted=-1,
        paging=-1,scheduling=-1,inference=-1;
    uint32_t frame_bytes=0u,i;
    (void)elf_identity;
    for(i=0u;i<64u;i++)mailbox[i]=0u;
    mailbox[0]=B4M_MAILBOX_MAGIC;
    mailbox[1]=1u;
    mailbox[2]=UINT32_C(0xC0DE0000);
    mailbox[3]=UINT32_MAX;
    publish();
    width=p03_hw_xilinx_fpd128_ready();
    if(width==0)init=p03_hw_init(&hw,&io,&cookie,
                                 P03_HW_BACKING_BASE,1000000u);
    if(init==P03_HW_OK)id=p03_hw_identify(&hw);
    if(id==P03_HW_OK){
        /* Physical host must first SHA/readback-verify all of these
         * original immutable bytes. Runtime invalidates PS cache lines
         * to see the contents that the dedicated XSDB session staged.
         */
        Xil_DCacheInvalidateRange((INTPTR)B4L_BIND_BASE,B4L_BIND_SIZE);
        Xil_DCacheInvalidateRange((INTPTR)P07_B4M_ROUTE_OUT_BASE,
                                   P07_B4M_ROUTE_OUT_BYTES);
        Xil_DCacheInvalidateRange((INTPTR)P07_B4M_ROUTE_IN_BASE,
                                   P07_B4M_ROUTE_IN_BYTES);
        Xil_DCacheInvalidateRange((INTPTR)P07_B4M_FRAME_BASE,
                                   P07_B4M_FRAME_MAX_BYTES);
        fence();
        bound=b4l_bind_frozen(&hw,descriptor,B4L_BIND_SIZE,&binding_receipt);
    }
    if(bound==B4L_BIND_OK){
        mounted=p07_b4m_mount_frozen_routes(&frozen,routes,
            P07_B4M_ROUTE_OUT_BYTES,ingress_routes,
            P07_B4M_ROUTE_IN_BYTES,&hw,route_buffer,
            P07_B2_MAX_ROUTE_BINDINGS,compartment_buffer,P07_B3_CORES);
    }
    if(mounted==P07_B4M_ROUTE_OK){
        frame_bytes=le32(wire+16u);
        if(frame_bytes>P07_B4M_FRAME_MAX_BYTES-P07_B2_HEADER_BYTES ||
           frame_bytes+P07_B2_HEADER_BYTES>P07_B2_MAX_FRAME_BYTES)
            mounted=P07_B4M_ROUTE_INVALID;
        else frame_bytes+=P07_B2_HEADER_BYTES;
    }
    if(mounted==P07_B4M_ROUTE_OK)
        paging=p07_b3_init(&pager,P07_B3_ORDER_ASCENDING);
    if(paging==P07_B3_OK)
        scheduling=p07_b3c2_init(&scheduler,&pager,&hw,
                                 packet_words,P07_B3C_MAX_RAW_WORDS,
                                 p03_scratch,P03_RT_MAX_PACKETS);
    if(scheduling==P07_B3C2_OK){
        memset(&buffers,0,sizeof(buffers));
        buffers.merged_current_words=current_words;
        buffers.merged_capacity=P07_B4A_WORD_CAPACITY;
        buffers.source_spikes=verified_spikes;
        buffers.source_capacity=P07_B4M_TRACE_SPIKE_CAP;
        buffers.frame_scratch=packet_scratch;
        buffers.scratch_capacity=sizeof(packet_scratch);
        buffers.packet_frame=packet_frame;
        buffers.frame_capacity=sizeof(packet_frame);
        inference=p07_b4m_full_run(&scheduler,&frozen.inputs,
            &frozen.packets,wire,frame_bytes,read_ddr32,&cookie,
            &buffers,&receipt);
    }
    mailbox[3]=(inference==P07_B4M_FULL_OK)?0u:receipt.first_fault;
    mailbox[4]=(uint32_t)width;mailbox[5]=(uint32_t)init;
    mailbox[6]=(uint32_t)id;mailbox[7]=(uint32_t)bound;
    mailbox[8]=(uint32_t)mounted;mailbox[9]=(uint32_t)paging;
    mailbox[10]=(uint32_t)scheduling;mailbox[11]=(uint32_t)inference;
    mailbox[12]=receipt.magic;
    mailbox[13]=receipt.barriers;mailbox[14]=receipt.dispatches;
    mailbox[15]=receipt.page_ins;mailbox[16]=receipt.page_outs;
    mailbox[17]=receipt.final_outs;mailbox[18]=receipt.external_current;
    mailbox[19]=receipt.source_spikes;mailbox[20]=receipt.captured_packets;
    mailbox[21]=receipt.inserted_next;mailbox[22]=receipt.classification;
    mailbox[23]=binding_receipt.registered_axons;
    mailbox[24]=receipt.trace_compartment_count;
    mailbox[25]=(uint32_t)receipt.cumulative_trace_fnv64;
    mailbox[26]=(uint32_t)(receipt.cumulative_trace_fnv64>>32u);
    mailbox[27]=(uint32_t)receipt.read_bytes;
    mailbox[28]=(uint32_t)(receipt.read_bytes>>32u);
    mailbox[29]=(uint32_t)receipt.write_bytes;
    mailbox[30]=(uint32_t)(receipt.write_bytes>>32u);
    mailbox[31]=frame_bytes;
    for(i=0u;i<10u;i++)mailbox[32u+i]=receipt.output_spike_counts[i];
    mailbox[42]=pager.failed;
    mailbox[43]=scheduler.poisoned;
    mailbox[44]=(uint32_t)hw.last_error;
    mailbox[45]=receipt.first_fault;
    mailbox[46]=Xil_In32((UINTPTR)P03_MMIO_BASE+P03_REG_DISPATCH_COMPLETED);
    mailbox[2]=(width==0&&init==P03_HW_OK&&id==P03_HW_OK&&
        bound==B4L_BIND_OK&&mounted==P07_B4M_ROUTE_OK&&
        paging==P07_B3_OK&&scheduling==P07_B3C2_OK&&
        inference==P07_B4M_FULL_OK&&receipt.magic==P07_B4M_FULL_MAGIC&&
        receipt.dispatches==702u&&receipt.barriers==26u&&
        receipt.final_outs==3u&&receipt.trace_compartment_count==1010u&&
        !pager.failed&&!scheduler.poisoned&&hw.last_error==P03_HW_OK)?
        B4M_MAILBOX_PASS:B4M_MAILBOX_FAIL;
    mailbox[63]=B4M_MAILBOX_DONE;
    publish();
    xil_printf("P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1 status=0x%08lx\r\n",
        (unsigned long)mailbox[2]);
    halt();
    return 0;
}
