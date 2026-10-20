#include "p07_b4b_xilinx_platform.h"
#include "xil_io.h"
#if !defined(__aarch64__) && !defined(P07_B4B_TEST_HOST_BSP)
#error "P07-B.4b physical DDR reader requires standalone AArch64, not host x86"
#endif
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
#if defined(P07_B4B_TEST_HOST_BSP)
    /* Test-only fake BSP build: never a physical A53 transport. */
    __asm__ volatile("" ::: "memory");
#else
    __asm__ volatile("dsb sy" ::: "memory");
#endif
    return P07_B4B_OK;
}
