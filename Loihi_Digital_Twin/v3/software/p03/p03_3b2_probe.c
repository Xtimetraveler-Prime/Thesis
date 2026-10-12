/*
 * P03.3b2 — actual KV260 Cortex-A53 runtime-to-MMIO integration gate.
 * One core, two timesteps, zero event packets. This executes real P03.3a
 * scheduling and P03.3b page/debug/dispatch/barrier primitives, NOT
 * a duplicate of the hand-coded P03.2c smoke.
 *
 * The 64-byte mailbox at 0x43FF0000 remains reserved from the halted Linux
 * image; the 512 KiB fixture at 0x40000000 is provisioned by XSDB first.
 */
#include <stddef.h>
#include <stdint.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "p03_2c_fixture.h"
#include "p03_hw_xilinx_io.h"
#include "p03_hw_runtime_bridge.h"
#include "p03_mmio.h"

#define PROBE_MAGIC UINT32_C(0x50333342) /* "P33B" */
#define PROBE_SCHEMA UINT32_C(1)
#define PROBE_PASS UINT32_C(0x600D600D)
#define PROBE_FAIL UINT32_C(0xDEAD0000)
#define PROBE_POLL_LIMIT UINT32_C(100000000)

enum {
    FAIL_PS_WIDTH = 1,
    FAIL_RECORD_HEADER = 2,
    FAIL_ADAPTER_INIT = 3,
    FAIL_CORE_REGISTRATION = 4,
    FAIL_RUNTIME_INIT = 5,
    FAIL_DEPLOYMENT = 6,
    FAIL_INPUT = 7,
    FAIL_RUNTIME = 8,
    FAIL_RESULT = 9
};

typedef struct {
    uint32_t magic, schema, result, fail_code;
    uint32_t mmio_id, mmio_version, capabilities, ps_width_raw;
    uint32_t resident_config0, page_bytes, pages_completed;
    uint32_t dispatches_completed;
    uint32_t logical_dispatches, barriers, initial_page_ins, runtime_fault;
} probe_mailbox;

static volatile probe_mailbox *const mailbox =
    (volatile probe_mailbox *)P03_SMOKE_MAILBOX_BASE;
static p03_rt runtime;
static p03_hw_adapter adapter;
static p03_hw_runtime_bridge bridge;
static p03_rt_ops runtime_ops;
static uint32_t first_fail;

static void flush_mailbox(void)
{
    __asm__ volatile("dsb sy" ::: "memory");
    Xil_DCacheFlushRange((INTPTR)P03_SMOKE_MAILBOX_BASE, 64);
    __asm__ volatile("dsb sy" ::: "memory");
}

static void publish_failure(uint32_t code)
{
    if (first_fail == 0)
        first_fail = code;
    mailbox->fail_code = first_fail;
    mailbox->runtime_fault = (uint32_t)runtime.first_fault;
    mailbox->result = PROBE_FAIL | first_fail;
    flush_mailbox();
}

static void halt_forever(void)
{
    for (;;) {
        __asm__ volatile("wfe");
    }
}

static int record_header_matches(void)
{
    uint32_t base = (uint32_t)P03_SMOKE_RECORD_BASE;
    /* AMD XSDB provisions a frozen P02.1 record. Check the on-board
     * header, core/shape/event counts and compiled fixture config.
     * Payload SHA256 verification belongs to P03.3c. Do not claim it.
     */
    Xil_DCacheInvalidateRange((INTPTR)P03_SMOKE_RECORD_BASE, 0x80000);
    __asm__ volatile("dsb sy" ::: "memory");
    return Xil_In32(base + 0x00) == UINT32_C(0x3356544C) &&
           Xil_In32(base + 0x04) == UINT32_C(0x31585443) &&
           Xil_In32(base + 0x08) == 1u &&
           Xil_In32(base + 0x0C) == 0x1000u &&
           Xil_In32(base + 0x10) == 0x80000u &&
           Xil_In32(base + 0x14) == 0u &&
           Xil_In32(base + 0x1C) == 0u &&
           Xil_In32(base + 0x2C) == 0u &&
           Xil_In32(base + 0x30) == 0u &&
           Xil_In32(base + 0x34) == 0u &&
           Xil_In32(base + 0x1000) == P03_SMOKE_EXPECT_CONFIG0;
}

static int validate_deployment(void *ctx)
{
    (void)ctx;
    if (P03_SMOKE_DISPATCH_METADATA & (UINT64_C(0xF) << 60))
        return -1;
    if ((P03_SMOKE_DISPATCH_METADATA & UINT64_C(0x7F)) != 0)
        return -1;
    return 0;
}

static int validate_backing(void *ctx)
{
    (void)ctx;
    return record_header_matches() ? 0 : -1;
}

static int load_input_and_verify_resident(void *ctx)
{
    p03_hw_adapter *hw = (p03_hw_adapter *)ctx;
    uint32_t data[8] = {0};
    /* Invoked AFTER initial page-in by the board-local policy engine.
     * Confirm the physical URAM payload through the P03.2 MMIO arbiter.
     */
    if (p03_hw_debug_word(hw, 0, P03_HW_CONFIG_DEBUG_BANK, 0, 0, data))
        return -1;
    mailbox->resident_config0 = data[0];
    if (data[0] != P03_SMOKE_EXPECT_CONFIG0)
        return -1;
    return 0; /* No input events in this safe initial integration gate. */
}

static int write_result(void *ctx, const p03_rt *rt)
{
    p03_hw_adapter *hw = (p03_hw_adapter *)ctx;
    uint32_t page_count, dispatch_count, page_bytes, id, version, caps;
    if (hw->io.read32(hw->cookie, P03_REG_ID, &id) ||
        hw->io.read32(hw->cookie, P03_REG_VERSION, &version) ||
        hw->io.read32(hw->cookie, P03_REG_CAPABILITIES, &caps) ||
        hw->io.read32(hw->cookie, P03_REG_PAGE_BYTES, &page_bytes) ||
        hw->io.read32(hw->cookie, P03_REG_PAGE_COMPLETED, &page_count) ||
        hw->io.read32(hw->cookie, P03_REG_DISPATCH_COMPLETED, &dispatch_count))
        return -1;

    mailbox->mmio_id = id;
    mailbox->mmio_version = version;
    mailbox->capabilities = caps;
    mailbox->page_bytes = page_bytes;
    mailbox->pages_completed = page_count;
    mailbox->dispatches_completed = dispatch_count;
    mailbox->logical_dispatches = rt->counters.logical_dispatches;
    mailbox->barriers = rt->counters.barriers;
    mailbox->initial_page_ins = rt->counters.initial_page_ins;
    mailbox->runtime_fault = (uint32_t)rt->first_fault;

    if (id != P03_MMIO_ID_VALUE ||
        version != P03_MMIO_VERSION_VALUE ||
        caps != UINT32_C(0x0001031F) ||
        page_bytes != P03_SMOKE_EXPECT_PAGE_BYTES ||
        page_count != 1u || dispatch_count != 2u ||
        rt->counters.logical_dispatches != 2u ||
        rt->counters.barriers != 2u ||
        rt->counters.initial_page_ins != 1u ||
        rt->counters.page_ins != 0 ||
        rt->counters.page_outs != 0 ||
        rt->counters.routed_packets != 0 ||
        rt->counters.timesteps_completed != 2u ||
        rt->first_fault != P03_RT_FAULT_NONE ||
        p03_hw_quiescent(hw) != 0)
        return -1;
    mailbox->result = PROBE_PASS;
    mailbox->fail_code = 0;
    flush_mailbox();
    return 0;
}

static void on_runtime_error(void *ctx, const p03_rt *rt)
{
    (void)ctx;
    /* Do not overwrite an earlier, more specific initialization error. */
    mailbox->runtime_fault = (uint32_t)rt->first_fault;
    publish_failure(FAIL_RUNTIME);
}

int main(void)
{
    const uint8_t ids[1] = {0};
    p03_hw_io io = p03_hw_xilinx_io();
    uint32_t raw = Xil_In32((UINTPTR)0xFD615000u);
    unsigned i;

    volatile uint32_t *words = (volatile uint32_t *)mailbox;
    for (i = 0; i < 16; ++i)
        words[i] = 0;
    mailbox->magic = PROBE_MAGIC;
    mailbox->schema = PROBE_SCHEMA;
    mailbox->ps_width_raw = raw;
    flush_mailbox();

    if (p03_hw_xilinx_fpd128_ready() != 0) {
        publish_failure(FAIL_PS_WIDTH);
        halt_forever();
    }

    if (!record_header_matches()) {
        publish_failure(FAIL_RECORD_HEADER);
        halt_forever();
    }

    if (p03_hw_init(&adapter, &io, NULL, P03_HW_BACKING_BASE,
                    PROBE_POLL_LIMIT) != P03_HW_OK) {
        publish_failure(FAIL_ADAPTER_INIT);
        halt_forever();
    }
    if (p03_hw_register_core(&adapter, 0, P03_SMOKE_DISPATCH_METADATA,
                             0, 0) != P03_HW_OK ||
        p03_hw_register_axon(&adapter, 0, 10) != P03_HW_OK) {
        publish_failure(FAIL_CORE_REGISTRATION);
        halt_forever();
    }
    if (p03_rt_init(&runtime, ids, 1, 1, 2) != 0) {
        publish_failure(FAIL_RUNTIME_INIT);
        halt_forever();
    }

    bridge.hw = &adapter;
    bridge.runtime = &runtime;
    bridge.app_cookie = &adapter;
    bridge.validate_deployment = validate_deployment;
    bridge.validate_backing = validate_backing;
    bridge.load_input = load_input_and_verify_resident;
    bridge.write_result = write_result;
    bridge.read_ticks = NULL; /* P03.3c adds PS timer capture. */
    bridge.on_error = on_runtime_error;

    if (p03_hw_bind_runtime(&bridge, &runtime_ops) != 0) {
        publish_failure(FAIL_DEPLOYMENT);
        halt_forever();
    }
    if (p03_rt_execute(&runtime, &runtime_ops, &bridge) != 0) {
        publish_failure(FAIL_RUNTIME);
        halt_forever();
    }
    if (mailbox->result != PROBE_PASS) {
        publish_failure(FAIL_RESULT);
        halt_forever();
    }
    flush_mailbox();
    halt_forever();
    return 0;
}
