/* Standalone Cortex-A53 READ-ONLY shell admission probe, not inference.
 * Does NOT program PL, write DDR, initialize neurons, dispatch or page.
 * A53 executable must be built with the accepted P03 platform's BSP,
 * linker script and XSA; external build/map verification still mandatory.
 */
#include <stdint.h>
#include "xil_printf.h"
#include "p03_hw_xilinx_io.h"
#include "p07_b4b_board_admission.h"
#include "p07_b4b_xilinx_platform.h"
static p03_hw_adapter hw;
static p07_b4b_probe_receipt proof;
static uint32_t fpd_reader_cookie=1u;
int main(void){
    p03_hw_io io=p03_hw_xilinx_io();
    int rc;
    /* This emits no writes to P02 or P03 and never launches inference.
     * The FPD static-width register is inspected first by B.4b admission. */
    rc=p03_hw_init(&hw,&io,0,P03_HW_BACKING_BASE,100000u);
    if(rc!=P03_HW_OK)goto fail;
    rc=p07_b4b_probe(&hw,p07_b4b_xilinx_read_phys,
                      &fpd_reader_cookie,&proof);
    if(rc!=P07_B4B_OK)goto fail;
    if(proof.inference_authorized!=0u)goto fail;
    xil_printf("P07_B4B_READONLY_SHELL_PROBE_PASS=1\r\n");
    for(;;)__asm__ volatile("wfe");
fail:
    xil_printf("P07_B4B_READONLY_SHELL_PROBE_FAIL rc=%d\r\n",rc);
    for(;;)__asm__ volatile("wfe");
}
