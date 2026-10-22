/* P07-B.4l dedicated standalone A53 probe: physical 27/3 page engine.
 * Run ONLY after fresh JTAG halt, accepted P03 bitstream and original
 * 27x512KiB frozen P02 DDR staging in the SAME SESSION (reboot destroys it).
 * NO neural inference, packets, ticks or official TEST access.
 * Modifies one transient state word at core-0 DDR after dirty page-out.
 */
#include <stdint.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "xil_printf.h"
#include "p03_hw_adapter.h"
#include "p03_hw_xilinx_io.h"
#include "p07_b4l_page_probe.h"

#define B4L_MAILBOX_ADDR UINT32_C(0x43FF0000)
#define B4L_DONE UINT32_C(0xC0DEF00D)
#define B4L_MAILBOX_MAGIC UINT32_C(0x5042344C) /* 'L4BP' in LE */
#define B4L_MAILBOX_PASS UINT32_C(0x600D600D)
#define B4L_MAILBOX_FAIL UINT32_C(0xDEAD0000)
#define B4L_MAILBOX_VERSION 1u
static const volatile char build_identity[]="P07_B4L_A53_27CORE_PAGING_PROBE_V1";
static volatile uint32_t *const mailbox=(volatile uint32_t *)(uintptr_t)B4L_MAILBOX_ADDR;
static p03_hw_adapter hw;
static b4l_probe_receipt receipt;
static uint32_t board_cookie=1u;

static void fence(void) { __asm__ volatile("dsb sy" ::: "memory"); }
static void publish(void) {
    fence();
    Xil_DCacheFlushRange((INTPTR)B4L_MAILBOX_ADDR,256u);
    fence();
}
static int board_page(void *ctx,uint32_t core,uint32_t slot,
                      int page_out,int mutable_only,uint64_t *cycles) {
    (void)ctx;
    return p03_hw_page(&hw,(uint8_t)core,(uint8_t)slot,
                       page_out,mutable_only,cycles);
}
static int board_debug(void *ctx,uint32_t slot,uint32_t bank,
                       int write,uint32_t *value) {
    uint32_t words[8]={0};
    (void)ctx;
    if (!value||slot>=B4L_PROBE_SLOTS||bank>1u) return -1;
    /* On a write retain the rest of the accepted resident word, especially
     * upper 32 state bits; write only low 32 as diagnostic mutation.
     */
    if (p03_hw_debug_word(&hw,(uint8_t)slot,(uint8_t)bank,
                          0u,0,words)!=P03_HW_OK) return -1;
    if (write) {
        words[0]=*value;
        if (p03_hw_debug_word(&hw,(uint8_t)slot,(uint8_t)bank,
                              0u,1,words)!=P03_HW_OK) return -1;
    } else {
        *value=words[0];
    }
    return 0;
}
static int board_ddr_read(void *ctx,uint64_t address,uint32_t *value) {
    (void)ctx;
    if (!value||address>UINT64_C(0xFFFFFFFF)
            ||(address&3u)!=0u||address<B4L_PROBE_BASE
            ||address+4u>B4L_PROBE_BASE+
                         B4L_PROBE_RECORD_BYTES*B4L_PROBE_CORES)
        return -1;
    Xil_DCacheInvalidateRange((INTPTR)(address&~UINT64_C(63)),64u);
    fence();
    *value=Xil_In32((UINTPTR)address);
    return 0;
}
static void halt(void) {
    for(;;) __asm__ volatile("wfe");
}
int main(void) {
    p03_hw_io io=p03_hw_xilinx_io();
    b4l_probe_ops ops={board_page,board_debug,board_ddr_read};
    int init_rc=-1,identify_rc=-1,run_rc=-1,width_rc=-1;
    unsigned i;
    (void)build_identity;
    for (i=0u;i<64u;i++) mailbox[i]=0u;
    mailbox[0]=B4L_MAILBOX_MAGIC;
    mailbox[1]=B4L_MAILBOX_VERSION;
    mailbox[2]=UINT32_C(0xC0DE0000); /* pending != success */
    mailbox[3]=UINT32_C(0xFFFFFFFF); /* first failure */
    mailbox[24]=B4L_PROBE_CORES;
    mailbox[25]=B4L_PROBE_SLOTS;
    mailbox[26]=B4L_PROBE_BASE;
    mailbox[27]=B4L_PROBE_RECORD_BYTES;
    mailbox[28]=B4L_PROBE_DIRTY_MASK;
    publish();
    width_rc=p03_hw_xilinx_fpd128_ready();
    if (width_rc==0)
        init_rc=p03_hw_init(&hw,&io,&board_cookie,P03_HW_BACKING_BASE,1000000u);
    if (init_rc==P03_HW_OK)
        identify_rc=p03_hw_identify(&hw);
    if (identify_rc==P03_HW_OK) {
        for (i=0u;i<B4L_PROBE_CORES;i++) {
            /* No HLS dispatch; only physical full-page and debug operations.
             * The metadata registration is required by p03_hw_page().
             */
            if (p03_hw_register_core(&hw,(uint8_t)i,(uint64_t)i,0u,0u)!=P03_HW_OK)
                break;
        }
        if (i==B4L_PROBE_CORES)
            run_rc=b4l_probe_run(&ops,&board_cookie,&receipt);
    }
    mailbox[3]=receipt.first_error;
    mailbox[4]=(uint32_t)width_rc;
    mailbox[5]=(uint32_t)init_rc;
    mailbox[6]=(uint32_t)identify_rc;
    mailbox[7]=(uint32_t)run_rc;
    mailbox[8]=receipt.unique_cores;
    mailbox[9]=receipt.page_ins;
    mailbox[10]=receipt.page_outs;
    mailbox[11]=receipt.state_before;
    mailbox[12]=receipt.state_dirty;
    mailbox[13]=receipt.state_ddr_saved;
    mailbox[14]=receipt.state_restored;
    mailbox[15]=receipt.last_core;
    mailbox[16]=receipt.last_slot;
    mailbox[17]=(uint32_t)receipt.page_cycles;
    mailbox[18]=(uint32_t)(receipt.page_cycles>>32);
    mailbox[19]=(uint32_t)hw.last_error;
    mailbox[20]=receipt.done;
    mailbox[21]=Xil_In32((UINTPTR)0xFD615000u);
    mailbox[22]=Xil_In32((UINTPTR)P03_MMIO_BASE+P03_REG_PAGE_COMPLETED);
    mailbox[23]=0u; /* no neural inference executed */
    mailbox[2]=(width_rc==0 && init_rc==P03_HW_OK &&
                identify_rc==P03_HW_OK && run_rc==B4L_PROBE_OK &&
                receipt.done==1u && receipt.unique_cores==27u &&
                receipt.page_ins==28u && receipt.page_outs==1u &&
                receipt.state_dirty==receipt.state_restored &&
                receipt.state_dirty==receipt.state_ddr_saved &&
                receipt.state_dirty!=receipt.state_before) ?
                B4L_MAILBOX_PASS : B4L_MAILBOX_FAIL;
    mailbox[63]=B4L_DONE;
    publish();
    xil_printf("P07_B4L_A53_27CORE_PAGING_PROBE_V1 result=0x%08lx\r\n",
               (unsigned long)mailbox[2]);
    halt();
    return 0;
}
