/* P07-B.4c candidate A53 read-only board admission application.
 * Never dispatch, page, write DDR or initialize contexts.
 * Running on KV260 requires separately approved physical boot/DDR owner gate.
 */
#include <stdint.h>
#include "xil_printf.h"
#include "p03_hw_xilinx_io.h"
#include "p07_b4b_board_admission.h"
#include "p07_b4b_xilinx_platform.h"

/* Emitted into ELF, independently inspected after actual Vitis linkage. */
static const char build_identity[] =
    "P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1";
static p03_hw_adapter hw;
static p07_b4b_probe_receipt receipt;
static uint32_t reader_cookie=1u;

int main(void){
    p03_hw_io io=p03_hw_xilinx_io();
    int rc;
    xil_printf("%s\r\n",build_identity);
    rc=p03_hw_init(&hw,&io,&reader_cookie,P03_HW_BACKING_BASE,100000u);
    if(rc==P03_HW_OK)
        rc=p07_b4b_probe(&hw,p07_b4b_xilinx_read_phys,
                          &reader_cookie,&receipt);
    if(rc==P07_B4B_OK &&
       receipt.read_only_shell_probe_pass==1u &&
       receipt.inference_authorized==0u){
        xil_printf("P07_B4C_READONLY_ADMISSION_PROBE_PASS=1\r\n");
    }else{
        xil_printf("P07_B4C_READONLY_ADMISSION_PROBE_FAIL=%d\r\n",rc);
    }
    /* Deliberately halt. No page, dispatch, DDR store or result mailbox. */
    for(;;)__asm__ volatile("wfe");
}
