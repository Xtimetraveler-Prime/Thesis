#ifndef P07_B4B_TEST_XIL_PRINTF_H
#define P07_B4B_TEST_XIL_PRINTF_H
/* Compile-time only to check P07-B.4b startup source, NOT Xilinx BSP. */
static inline int xil_printf(const char *format, ...){
    (void)format;
    return 0;
}
#endif
