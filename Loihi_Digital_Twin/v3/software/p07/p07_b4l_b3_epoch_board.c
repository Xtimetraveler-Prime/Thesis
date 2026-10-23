/* P07-B.4l: distinct A53 B3/P03 physical FIRST-EPOCH dispatch candidate.
 * Not a launch authorization; does not accept ingress, verify emitted-neuron
 * provenance, ACK B2b NEXT, advance tick or claim trained image inference.
 * Requires original B2.4 27 P02 records and SHA-bound 16KiB registration
 * descriptor on physical DDR, from the same operator-controlled JTAG run.
 */
#include <stdint.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "p03_mmio.h"
#include "p03_hw_xilinx_io.h"
#include "p07_b4l_b3_bindings.h"
#include "p07_b4l_b3_epoch.h"
#define MAILBOX UINT32_C(0x43FF0000)
#define RECEIPT_MAGIC UINT32_C(0x42334C34)
#define RECEIPT_PASS UINT32_C(0x600D600D)
#define RECEIPT_FAIL UINT32_C(0xDEAD0000)
#define RECEIPT_DONE UINT32_C(0xC0DEF00D)
static const volatile char elf_identity[]="P07_B4L_A53_B3_ONE_EPOCH_V1";
static volatile uint32_t *const mailbox=(volatile uint32_t *)(uintptr_t)MAILBOX;
static p03_hw_adapter hw;
static p07_b3_pager pager;
static p07_b3c2_hw_scheduler scheduler;
static p07_b4l_b3_receipt epoch;
static b4l_binding_receipt bindings;
static uint64_t raw_packets[P07_B3C_MAX_RAW_WORDS];
static uint64_t one_packet_scratch[P03_RT_MAX_PACKETS];
static uint32_t cookie;
static void fence(void) {__asm__ volatile("dsb sy" ::: "memory");}
static void publish(void) {
    fence();
    Xil_DCacheFlushRange((INTPTR)MAILBOX,256u);
    fence();
}
static void halt(void) {for(;;) __asm__ volatile("wfe");}
int main(void) {
    p03_hw_io io=p03_hw_xilinx_io();
    const uint8_t *descriptor=(const uint8_t *)(uintptr_t)B4L_BIND_BASE;
    int w=-1,init=-1,identify=-1,bind=-1,lr=-1,si=-1,run=-1;
    uint32_t i;
    (void)elf_identity;
    for(i=0;i<64u;i++)mailbox[i]=0u;
    mailbox[0]=RECEIPT_MAGIC;
    mailbox[1]=1u;
    mailbox[2]=UINT32_C(0xC0DE0000); /* pending */
    mailbox[3]=UINT32_MAX;
    publish();
    w=p03_hw_xilinx_fpd128_ready();
    if(w==0)init=p03_hw_init(&hw,&io,&cookie,P03_HW_BACKING_BASE,1000000u);
    if(init==P03_HW_OK)identify=p03_hw_identify(&hw);
    if(identify==P03_HW_OK){
        /* Descriptor is operator-verified host output, then must have been
         * physically transferred with readback in THIS standalone session.
         * The existing accepted native P07 SHA256 verifies the table.
         */
        Xil_DCacheInvalidateRange((INTPTR)B4L_BIND_BASE,B4L_BIND_SIZE);
        fence();
        bind=b4l_bind_frozen(&hw,descriptor,B4L_BIND_SIZE,&bindings);
    }
    if(bind==B4L_BIND_OK)lr=p07_b3_init(&pager,P07_B3_ORDER_ASCENDING);
    if(lr==P07_B3_OK)si=p07_b3c2_init(
        &scheduler,&pager,&hw,raw_packets,P07_B3C_MAX_RAW_WORDS,
        one_packet_scratch,P03_RT_MAX_PACKETS);
    if(si==P07_B3C2_OK)run=p07_b4l_b3_one_epoch(&scheduler,&epoch);
    mailbox[3]=epoch.first_error;
    mailbox[4]=(uint32_t)w;
    mailbox[5]=(uint32_t)init;
    mailbox[6]=(uint32_t)identify;
    mailbox[7]=(uint32_t)bind;
    mailbox[8]=(uint32_t)lr;
    mailbox[9]=(uint32_t)si;
    mailbox[10]=(uint32_t)run;
    mailbox[11]=epoch.magic;
    mailbox[12]=epoch.unique_dispatches;
    mailbox[13]=epoch.page_ins;
    mailbox[14]=epoch.dirty_page_outs;
    mailbox[15]=epoch.pending_barrier;
    mailbox[16]=epoch.barrier_acked;
    mailbox[17]=epoch.physical_packets_captured;
    mailbox[18]=epoch.source_count;
    mailbox[19]=(uint32_t)epoch.captured_word_fnv1a;
    mailbox[20]=(uint32_t)(epoch.captured_word_fnv1a>>32);
    mailbox[21]=pager.failed;
    mailbox[22]=scheduler.first_fault;
    mailbox[23]=(uint32_t)hw.last_error;
    mailbox[24]=Xil_In32((UINTPTR)P03_MMIO_BASE+P03_REG_PAGE_COMPLETED);
    mailbox[25]=Xil_In32((UINTPTR)P03_MMIO_BASE+P03_REG_DISPATCH_COMPLETED);
    mailbox[26]=Xil_In32((UINTPTR)0xFD615000u);
    mailbox[27]=0u; /* external CURRENT ingress events: zero */
    mailbox[28]=0u; /* physical emitting-neuron source trace verified: NO */
    mailbox[29]=0u; /* NEXT packets inserted: NO */
    mailbox[30]=0u; /* independent B2b barrier ack: NO */
    mailbox[31]=0u; /* frozen trained numerical parity established: NO */
    mailbox[32]=0u; /* official MNIST TEST images accessed: NO */
    mailbox[33]=bindings.core_count;
    mailbox[34]=bindings.registered_axons;
    mailbox[35]=bindings.registered_compartments;
    mailbox[36]=(uint32_t)epoch.p03_page_bytes_expected;
    mailbox[37]=(uint32_t)(epoch.p03_page_bytes_expected>>32u);
    mailbox[38]=pager.tick;
    mailbox[39]=pager.counters.barriers;
    mailbox[40]=pager.counters.dispatches;
    mailbox[41]=pager.counters.runtime_outs;
    mailbox[42]=pager.counters.page_ins;
    mailbox[43]=epoch.faulted;
    mailbox[44]=bindings.first_bad_core;
    mailbox[45]=bindings.first_bad_axon;
    mailbox[2]=(w==0&&init==P03_HW_OK&&identify==P03_HW_OK&&
        bind==B4L_BIND_OK&&lr==P07_B3_OK&&si==P07_B3C2_OK&&
        run==P07_B4L_B3_OK&&epoch.magic==P07_B4L_B3_ONE_TICK_MAGIC&&
        epoch.unique_dispatches==27u&&epoch.page_ins==27u&&
        epoch.dirty_page_outs==24u&&epoch.pending_barrier==1u&&
        epoch.barrier_acked==0u&&epoch.faulted==0u&&
        bindings.core_count==27u&&pager.tick==0u&&
        pager.counters.barriers==0u&&
        mailbox[24]>=51u&&mailbox[25]>=27u) ?
        RECEIPT_PASS:RECEIPT_FAIL;
    mailbox[63]=RECEIPT_DONE;
    publish();
    xil_printf("P07_B4L_A53_B3_ONE_EPOCH_V1 status=0x%08lx\r\n",
               (unsigned long)mailbox[2]);
    halt();
    return 0;
}
