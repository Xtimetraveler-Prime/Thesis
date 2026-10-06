#include <stdint.h>

#include "xil_cache.h"
#include "xil_io.h"

#include "p03_mmio.h"
#include "p03_2c_fixture.h"

#define MAILBOX_MAGIC UINT32_C(0x50333243) /* "P32C" */
#define MAILBOX_VERSION UINT32_C(1)
#define MAILBOX_PASS UINT32_C(0x600D600D)
#define MAILBOX_FAIL UINT32_C(0xDEAD0000)

#define FAIL_MMIO_ID        UINT32_C(1)
#define FAIL_MMIO_VERSION   UINT32_C(2)
#define FAIL_CAPABILITIES   UINT32_C(3)
#define FAIL_PAGE_TIMEOUT   UINT32_C(4)
#define FAIL_PAGE_STATUS    UINT32_C(5)
#define FAIL_PAGE_BYTES     UINT32_C(6)
#define FAIL_PAGE_BURSTS    UINT32_C(7)
#define FAIL_PAGE_PENDING   UINT32_C(8)
#define FAIL_DEBUG_TIMEOUT  UINT32_C(9)
#define FAIL_DEBUG_STATUS   UINT32_C(10)
#define FAIL_DEBUG_CONFIG0  UINT32_C(11)
#define FAIL_DISPATCH_TIMEOUT UINT32_C(12)
#define FAIL_DISPATCH_STATUS  UINT32_C(13)
#define FAIL_DISPATCH_PACKET  UINT32_C(14)
#define FAIL_DISPATCH_CORE    UINT32_C(15)
#define FAIL_DISPATCH_COUNT   UINT32_C(16)
#define FAIL_DISPATCH_ACTIVE  UINT32_C(17)

#define POLL_LIMIT UINT32_C(100000000)

typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t result;
    uint32_t fail_code;

    uint32_t mmio_id;
    uint32_t mmio_version;
    uint32_t capabilities;
    uint32_t global_status;

    uint32_t page_status;
    uint32_t page_bytes;
    uint32_t page_read_bursts;
    uint32_t page_write_bursts;

    uint32_t debug_status;
    uint32_t resident_config0;
    uint32_t dispatch_status;
    uint32_t dispatch_completed;
} p03_smoke_mailbox_t;

static volatile p03_smoke_mailbox_t *const mailbox =
    (volatile p03_smoke_mailbox_t *)P03_SMOKE_MAILBOX_BASE;

static inline uintptr_t reg_addr(uint32_t offset)
{
    return P03_MMIO_BASE + (uintptr_t)offset;
}

static inline uint32_t reg_read(uint32_t offset)
{
    return Xil_In32(reg_addr(offset));
}

static inline void reg_write(uint32_t offset, uint32_t value)
{
    Xil_Out32(reg_addr(offset), value);
}

static void flush_mailbox(void)
{
    __asm__ volatile("dsb sy" ::: "memory");
    Xil_DCacheFlushRange(
        (INTPTR)P03_SMOKE_MAILBOX_BASE,
        (u32)sizeof(*mailbox)
    );
    __asm__ volatile("dsb sy" ::: "memory");
}

static void fail(uint32_t code)
{
    mailbox->result = MAILBOX_FAIL | code;
    mailbox->fail_code = code;
    mailbox->global_status = reg_read(P03_REG_GLOBAL_STATUS);
    flush_mailbox();

    for (;;) {
        __asm__ volatile("wfe");
    }
}

static uint32_t wait_sticky_done(uint32_t status_reg, uint32_t error_mask)
{
    uint32_t i;
    uint32_t status = 0;

    for (i = 0; i < POLL_LIMIT; ++i) {
        status = reg_read(status_reg);
        if (status & error_mask)
            return status;
        if (status & UINT32_C(0x2))
            return status;
    }
    return status;
}

int main(void)
{
    uint32_t status;
    uint32_t active;
    uint64_t metadata = P03_SMOKE_DISPATCH_METADATA;

    mailbox->magic = MAILBOX_MAGIC;
    mailbox->version = MAILBOX_VERSION;
    mailbox->result = 0;
    mailbox->fail_code = 0;
    mailbox->mmio_id = 0;
    mailbox->mmio_version = 0;
    mailbox->capabilities = 0;
    mailbox->global_status = 0;
    mailbox->page_status = 0;
    mailbox->page_bytes = 0;
    mailbox->page_read_bursts = 0;
    mailbox->page_write_bursts = 0;
    mailbox->debug_status = 0;
    mailbox->resident_config0 = 0;
    mailbox->dispatch_status = 0;
    mailbox->dispatch_completed = 0;
    flush_mailbox();

    mailbox->mmio_id = reg_read(P03_REG_ID);
    if (mailbox->mmio_id != P03_MMIO_ID_VALUE)
        fail(FAIL_MMIO_ID);

    mailbox->mmio_version = reg_read(P03_REG_VERSION);
    if (mailbox->mmio_version != P03_MMIO_VERSION_VALUE)
        fail(FAIL_MMIO_VERSION);

    mailbox->capabilities = reg_read(P03_REG_CAPABILITIES);
    if (mailbox->capabilities != UINT32_C(0x0001031F))
        fail(FAIL_CAPABILITIES);

    /*
     * Page core0's accepted 512 KiB backing record into resident slot 0.
     * The page mover transfers the 428 KiB resident payload.
     */
    reg_write(P03_REG_PAGE_CONFIG, UINT32_C(0));
    reg_write(P03_REG_PAGE_BASE_LO, (uint32_t)P03_SMOKE_RECORD_BASE);
    reg_write(P03_REG_PAGE_BASE_HI, UINT32_C(0));
    reg_write(P03_REG_PAGE_COMMAND, P03_CMD_START);

    status = wait_sticky_done(P03_REG_PAGE_STATUS, UINT32_C(0xFC));
    mailbox->page_status = status;
    if (!(status & UINT32_C(0x2)))
        fail(FAIL_PAGE_TIMEOUT);
    if (status & UINT32_C(0xFC))
        fail(FAIL_PAGE_STATUS);

    mailbox->page_bytes = reg_read(P03_REG_PAGE_BYTES);
    if (mailbox->page_bytes != P03_SMOKE_EXPECT_PAGE_BYTES)
        fail(FAIL_PAGE_BYTES);

    mailbox->page_read_bursts = reg_read(P03_REG_PAGE_READ_BURSTS);
    mailbox->page_write_bursts = reg_read(P03_REG_PAGE_WRITE_BURSTS);
    if (mailbox->page_read_bursts != P03_SMOKE_EXPECT_PAGE_READ_BURSTS ||
        mailbox->page_write_bursts != P03_SMOKE_EXPECT_PAGE_WRITE_BURSTS)
        fail(FAIL_PAGE_BURSTS);

    if (reg_read(P03_REG_PAGE_PENDING_BYTES) != 0)
        fail(FAIL_PAGE_PENDING);

    /*
     * Read config[0] back from resident slot 0 / bank 0 through the same
     * low-rate resident-memory path P03.3 will use for packet/event handling.
     */
    reg_write(P03_REG_DEBUG_CONFIG, UINT32_C(0));
    reg_write(P03_REG_DEBUG_ADDR, UINT32_C(0));
    reg_write(P03_REG_DEBUG_COMMAND, P03_CMD_START);

    status = wait_sticky_done(P03_REG_DEBUG_STATUS, UINT32_C(0x18));
    mailbox->debug_status = status;
    if (!(status & UINT32_C(0x2)))
        fail(FAIL_DEBUG_TIMEOUT);
    if ((status & UINT32_C(0x18)) || !(status & UINT32_C(0x4)))
        fail(FAIL_DEBUG_STATUS);

    mailbox->resident_config0 = reg_read(P03_REG_DEBUG_RDATA0);
    if (mailbox->resident_config0 != P03_SMOKE_EXPECT_CONFIG0)
        fail(FAIL_DEBUG_CONFIG0);

    /*
     * Dispatch core0 with no current events.  This proves A53->MMIO->dispatch
     * command ownership without changing state or producing packets.
     */
    reg_write(P03_REG_DISPATCH_CONFIG, UINT32_C(0));
    reg_write(P03_REG_DISPATCH_META_LO, (uint32_t)metadata);
    reg_write(P03_REG_DISPATCH_META_HI, (uint32_t)(metadata >> 32));
    reg_write(P03_REG_DISPATCH_TIMESTEP, UINT32_C(0));
    reg_write(P03_REG_DISPATCH_COMMAND, P03_CMD_START);

    status = wait_sticky_done(P03_REG_DISPATCH_STATUS, UINT32_C(0x7C));
    mailbox->dispatch_status = status;
    if (!(status & UINT32_C(0x2)))
        fail(FAIL_DISPATCH_TIMEOUT);
    if (status & UINT32_C(0x7C))
        fail(FAIL_DISPATCH_STATUS);

    if (reg_read(P03_REG_DISPATCH_PACKET_CNT) != 0)
        fail(FAIL_DISPATCH_PACKET);
    if (reg_read(P03_REG_DISPATCH_CORE_STATUS) != 0)
        fail(FAIL_DISPATCH_CORE);

    mailbox->dispatch_completed = reg_read(P03_REG_DISPATCH_COMPLETED);
    if (mailbox->dispatch_completed != 1)
        fail(FAIL_DISPATCH_COUNT);

    active = reg_read(P03_REG_DISPATCH_ACTIVE);
    if ((active & UINT32_C(0x3)) != 0 ||
        ((active >> 8) & UINT32_C(0x1)) != 0 ||
        ((active >> 16) & UINT32_C(0x7F)) != 0)
        fail(FAIL_DISPATCH_ACTIVE);

    mailbox->global_status = reg_read(P03_REG_GLOBAL_STATUS);
    mailbox->result = MAILBOX_PASS;
    mailbox->fail_code = 0;
    flush_mailbox();

    for (;;) {
        __asm__ volatile("wfe");
    }
}
