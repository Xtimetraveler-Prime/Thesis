#include <stdint.h>

#include "xil_cache.h"
#include "xil_io.h"

#include "p03_mmio.h"
#include "p03_2c_fixture.h"

/*
 * P03.2c processor-originated read-only diagnostic.
 *
 * This does NOT issue any AXI MMIO writes and is NOT a substitute for the
 * eventual P03.2c page/resident-memory/dispatch acceptance smoke.
 * The only writes are to the existing reserved DDR result mailbox.
 */
#ifndef P03_READONLY_MMIO_BASE
#define P03_READONLY_MMIO_BASE P03_MMIO_BASE
#endif

#define READONLY_MAGIC       UINT32_C(0x50335244) /* P3RD */
#define READONLY_VERSION     UINT32_C(1)
#define READONLY_PENDING     UINT32_C(0xC0DE0000)
#define READONLY_SUCCESS     UINT32_C(0x600D600D)
#define READONLY_FAILURE     UINT32_C(0xDEAD0000)
#define READONLY_COUNT       UINT32_C(4)

#define EXPECT_ID            UINT32_C(0x4C543302)
#define EXPECT_VERSION       UINT32_C(0x00010000)
#define EXPECT_CAPS          UINT32_C(0x0001031F)
/* Temporary RTL diagnostic default read, not final MMIO ABI. */
#define EXPECT_UNMAPPED      UINT32_C(0xD1A60018)

enum {
    M_MAGIC = 0, M_VERSION, M_RESULT, M_READ_COUNT,
    M_ID, M_MMIO_VERSION, M_CAPS, M_UNMAPPED,
    M_EXPECT_ID, M_EXPECT_VERSION, M_EXPECT_CAPS, M_EXPECT_UNMAPPED,
    M_MATCH_MASK, M_COMPLETE, M_MMIO_BASE, M_MAILBOX_BASE,
};

static volatile uint32_t *const mailbox =
    (volatile uint32_t *)(uintptr_t)P03_SMOKE_MAILBOX_BASE;

static void publish(void)
{
    __asm__ volatile("dsb sy" ::: "memory");
    Xil_DCacheFlushRange((INTPTR)P03_SMOKE_MAILBOX_BASE, 64);
    __asm__ volatile("dsb sy" ::: "memory");
}

static uint32_t read_mmio(uint32_t offset)
{
    /* Full ARM system barrier before/after each device memory read. */
    __asm__ volatile("dsb sy" ::: "memory");
    uint32_t value = Xil_In32(P03_READONLY_MMIO_BASE + (uintptr_t)offset);
    __asm__ volatile("dsb sy" ::: "memory");
    return value;
}

int main(void)
{
    uint32_t mask = 0;
    unsigned i;

    for (i = 0; i < 16; ++i)
        mailbox[i] = 0xFFFFFFFFu;
    mailbox[M_MAGIC] = READONLY_MAGIC;
    mailbox[M_VERSION] = READONLY_VERSION;
    mailbox[M_RESULT] = READONLY_PENDING;
    mailbox[M_READ_COUNT] = READONLY_COUNT;
    mailbox[M_COMPLETE] = 0;
    mailbox[M_MMIO_BASE] = (uint32_t)P03_READONLY_MMIO_BASE;
    mailbox[M_MAILBOX_BASE] = (uint32_t)P03_SMOKE_MAILBOX_BASE;
    publish();

    mailbox[M_ID] = read_mmio(P03_REG_ID);
    mailbox[M_MMIO_VERSION] = read_mmio(P03_REG_VERSION);
    mailbox[M_CAPS] = read_mmio(P03_REG_CAPABILITIES);
    mailbox[M_UNMAPPED] = read_mmio(UINT32_C(0x018));

    mailbox[M_EXPECT_ID] = EXPECT_ID;
    mailbox[M_EXPECT_VERSION] = EXPECT_VERSION;
    mailbox[M_EXPECT_CAPS] = EXPECT_CAPS;
    mailbox[M_EXPECT_UNMAPPED] = EXPECT_UNMAPPED;

    if (mailbox[M_ID] == EXPECT_ID) mask |= 1u;
    if (mailbox[M_MMIO_VERSION] == EXPECT_VERSION) mask |= 2u;
    if (mailbox[M_CAPS] == EXPECT_CAPS) mask |= 4u;
    if (mailbox[M_UNMAPPED] == EXPECT_UNMAPPED) mask |= 8u;

    mailbox[M_MATCH_MASK] = mask;
    mailbox[M_RESULT] =
        (mask == 0xFu) ? READONLY_SUCCESS : READONLY_FAILURE | mask;
    mailbox[M_COMPLETE] = 0xC0DEF00Du;
    publish();

    for (;;) {
        __asm__ volatile("wfe");
    }
}
