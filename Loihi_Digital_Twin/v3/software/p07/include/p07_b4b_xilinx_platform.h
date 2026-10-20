#ifndef LOIHI_TWIN_P07_B4B_XILINX_PLATFORM_H
#define LOIHI_TWIN_P07_B4B_XILINX_PLATFORM_H
#include "p07_b4b_board_admission.h"
/* Bare-metal Cortex-A53 only: Xilinx BSP physical 32-bit reads.
 * Call exclusively via P07-B.4b allowlisted B4a DDR reader. */
int p07_b4b_xilinx_read_phys(void *unused,uint64_t physical,
                            uint32_t *out);
/* Distinct allowlist: read-only full P02 mutable-region audit only. */
int p07_b4b_xilinx_read_mutable(void *unused,uint64_t physical,
                                uint32_t *out);
#endif
