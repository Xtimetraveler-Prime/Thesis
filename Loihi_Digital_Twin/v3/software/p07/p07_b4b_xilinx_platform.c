#include "p07_b4b_xilinx_platform.h"
#include "xil_io.h"
/* Deliberately no Xil_DCacheInvalidateRange here: B.4a handles ownership
 * with P03 invalidate_range/barrier over the exact old-CURRENT span. */
int p07_b4b_xilinx_read_phys(void *unused,uint64_t physical,
                            uint32_t *out){
    (void)unused;
    if(!out ||
       !(physical==P07_B4B_FPD_REG ||
         (physical>=P03_HW_BACKING_BASE &&
          physical<=P07_B4B_CORE_END-4u &&
          ((physical-P03_HW_BACKING_BASE)%P03_HW_RECORD_BYTES>=P03_HW_EVENT0_OFFSET &&
           (physical-P03_HW_BACKING_BASE)%P03_HW_RECORD_BYTES <
             P03_HW_EVENT1_OFFSET+P03_HW_EVENT_DEPTH*4u))) ||
       (physical&UINT64_C(3))!=0u || physical>UINT32_MAX)
        return P07_B4B_RANGE;
    /* AArch64 standalone BSP: reads are physical only when MMU and memory
     * attributes are separately verified by the board-ownership gate. */
    *out=Xil_In32((UINTPTR)physical);
    __asm__ volatile("dsb sy" ::: "memory");
    return P07_B4B_OK;
}
