#include "p03_hw_xilinx_io.h"
#include "p03_mmio.h"

#include "xil_cache.h"
#include "xil_io.h"

static void ps_barrier(void *cookie)
{
    (void)cookie;
    __asm__ volatile("dsb sy" ::: "memory");
}

static int ps_read32(void *cookie, uint32_t offset, uint32_t *value)
{
    (void)cookie;
    if (!value || offset >= P03_MMIO_RANGE_BYTES || (offset & 3u))
        return -1;
    *value = Xil_In32(P03_MMIO_BASE + (uintptr_t)offset);
    return 0;
}
static int ps_write32(void *cookie, uint32_t offset, uint32_t value)
{
    (void)cookie;
    if (offset >= P03_MMIO_RANGE_BYTES || (offset & 3u))
        return -1;
    Xil_Out32(P03_MMIO_BASE + (uintptr_t)offset, value);
    ps_barrier(cookie);
    return 0;
}
static int ps_clean(void *cookie, uint64_t addr, uint32_t length)
{
    (void)cookie;
    if (addr > UINT64_C(0xFFFFFFFF) || length == 0)
        return -1;
    ps_barrier(cookie);
    Xil_DCacheFlushRange((INTPTR)addr, length);
    ps_barrier(cookie);
    return 0;
}
static int ps_invalidate(void *cookie, uint64_t addr, uint32_t length)
{
    (void)cookie;
    if (addr > UINT64_C(0xFFFFFFFF) || length == 0)
        return -1;
    ps_barrier(cookie);
    Xil_DCacheInvalidateRange((INTPTR)addr, length);
    ps_barrier(cookie);
    return 0;
}
static int ps_store_ddr32(void *cookie, uint64_t addr, uint32_t value)
{
    (void)cookie;
    if (addr < P03_HW_BACKING_BASE ||
        addr + 4u > P03_HW_BACKING_BASE + P03_HW_BACKING_BYTES ||
        (addr & 3u))
        return -1;
    Xil_Out32((UINTPTR)addr, value);
    return 0;
}

p03_hw_io p03_hw_xilinx_io(void)
{
    p03_hw_io io = {
        .read32 = ps_read32,
        .write32 = ps_write32,
        .clean_range = ps_clean,
        .invalidate_range = ps_invalidate,
        .store_ddr32 = ps_store_ddr32,
        .barrier = ps_barrier,
    };
    return io;
}
