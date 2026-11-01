#ifndef P07_B4B_TEST_XIL_IO_H
#define P07_B4B_TEST_XIL_IO_H
#include <stdint.h>
#include <stddef.h>
typedef uintptr_t UINTPTR;
uint32_t p07_b4b_fake_xil_read(UINTPTR address);
static inline uint32_t Xil_In32(UINTPTR address){
    return p07_b4b_fake_xil_read(address);
}
#endif
