/* P07-B.4i, isolated physical ADMISSION ONLY, derived from accepted
 * P03.2c mailbox technique and P07-B.4c read-only probe.
 * The sole intentional DDR writes are the 64-byte 0x43FF0000 mailbox.
 * CPU/low-DDR and mailbox ownership must be independently admitted before dow.
 * No paging, packets, spikes, inference, or protected P02 context writes.
 */
#include <stdint.h>
#include "xil_cache.h"
#include "xil_printf.h"
#include "p03_hw_xilinx_io.h"
#include "p07_b4b_board_admission.h"
#include "p07_b4b_xilinx_platform.h"

#define MBOX_ADDR UINT32_C(0x43FF0000)
#define MBOX_MAGIC UINT32_C(0x50374249) /* P7BI */
#define MBOX_DONE UINT32_C(0xC0DEF00D)
#define MBOX_PASS UINT32_C(0x600D600D)
#define MBOX_FAIL UINT32_C(0xDEAD0000)

static const char identity[] = "P07_B4I_A53_MAILBOX_FPD128_PROBE_V1";
static volatile uint32_t *const mailbox = (volatile uint32_t *)(uintptr_t)MBOX_ADDR;
static p03_hw_adapter hw;
static p07_b4b_probe_receipt receipt;
static uint32_t cookie = 1u;

static void publish(void) {
    __asm__ volatile("dsb sy" ::: "memory");
    Xil_DCacheFlushRange((INTPTR)MBOX_ADDR, 64);
    __asm__ volatile("dsb sy" ::: "memory");
}

int main(void) {
    p03_hw_io io = p03_hw_xilinx_io();
    int init_rc, probe_rc = P07_B4B_BAD_ARGUMENT;
    uint32_t raw = 0;
    unsigned i;
    for (i=0; i<16u; ++i) mailbox[i]=0u;
    mailbox[0]=MBOX_MAGIC;
    mailbox[1]=1u;
    mailbox[2]=UINT32_C(0xC0DE0000); /* pending, never success */
    mailbox[3]=UINT32_C(0xFFFFFFFF);
    mailbox[4]=UINT32_C(0xFFFFFFFF);
    mailbox[12]=0u; /* never inference */
    mailbox[13]=MBOX_ADDR;
    publish();

    /* Same standalone initialization and original B4b read-only admission
     * as B4c; no custom FPGA commands or data-model shortcuts. */
    init_rc=p03_hw_init(&hw,&io,&cookie,P03_HW_BACKING_BASE,100000u);
    if(init_rc==P03_HW_OK)
        probe_rc=p07_b4b_probe(&hw,p07_b4b_xilinx_read_phys,
                               &cookie,&receipt);
    (void)p07_b4b_xilinx_read_phys(&cookie,P07_B4B_FPD_REG,&raw);
    mailbox[3]=(uint32_t)init_rc;
    mailbox[4]=(uint32_t)probe_rc;
    mailbox[5]=raw;
    if(probe_rc==P07_B4B_OK) {
        mailbox[6]=receipt.shell_id;
        mailbox[7]=receipt.shell_version;
        mailbox[8]=receipt.capabilities;
        mailbox[9]=receipt.global_status;
        mailbox[10]=receipt.page_pending;
        mailbox[11]=receipt.read_only_shell_probe_pass;
        mailbox[12]=receipt.inference_authorized;
    }
    mailbox[2]=(init_rc==P03_HW_OK && probe_rc==P07_B4B_OK &&
                receipt.read_only_shell_probe_pass==1u &&
                receipt.inference_authorized==0u) ? MBOX_PASS : MBOX_FAIL;
    mailbox[15]=MBOX_DONE;
    publish();
    xil_printf("%s result=0x%08lx\r\n",identity,
               (unsigned long)mailbox[2]);
    for(;;) __asm__ volatile("wfe");
}
