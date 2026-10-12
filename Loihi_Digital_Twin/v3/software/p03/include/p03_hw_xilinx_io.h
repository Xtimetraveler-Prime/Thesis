#ifndef LOIHI_TWIN_V3_P03_HW_XILINX_IO_H
#define LOIHI_TWIN_V3_P03_HW_XILINX_IO_H
#include "p03_hw_adapter.h"

/* Bare-metal Xilinx BSP transport for the physically validated
 * FPD HPM0 128-bit PS -> SmartConnect -> 32-bit AXI-Lite shell.
 * Call only after the static PS width selector has been checked and
 * firmware has reserved the P02 64 MiB DDR backing window.
 */
/* Verify FPD_SLCR.afi_fs dw_ss0_sel[9:8] == 2 (128-bit).
 * Read-only, never changes the static width selector.
 */
int p03_hw_xilinx_fpd128_ready(void);
p03_hw_io p03_hw_xilinx_io(void);
#endif
