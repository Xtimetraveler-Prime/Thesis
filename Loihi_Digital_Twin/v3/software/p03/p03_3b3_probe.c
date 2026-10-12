/*
 * P03.3b3: real HLS output packets + nonresident DDR NEXT delivery
 * + dirty page-out/page-in, under P03.3a autonomous scheduler.
 *
 * Two logical cores / one resident slot / two timesteps, one initially
 * provisioned event. Compiler fixture defines exact expected packet ABI.
 * The external PC only provisions DDR and launches the ELF. All scheduling,
 * page replacement, packet routing and barriers execute on Cortex-A53 #0.
 */
#include <stddef.h>
#include <stdint.h>
#include "xil_cache.h"
#include "xil_io.h"
#include "p03_hw_xilinx_io.h"
#include "p03_hw_runtime_bridge.h"
#include "p03_mmio.h"
#include "p03_3b3_fixture.h"

#define B3_MAGIC UINT32_C(0x50334233)
#define B3_VERSION UINT32_C(1)
#define B3_PASS UINT32_C(0x600D600D)
#define B3_FAIL UINT32_C(0xDEAD0000)
#define B3_POLL UINT32_C(100000000)

/* Deliberately referenced volatile ELF build stamp. The board runner MUST
 * verify this exact string in the deployed ELF, not just in source. This
 * distinguishes the updated HDR3 preflight firmware from older builds.
 * The volatile load prevents compiler constant-folding/link-time removal.
 */
static const volatile char b3_probe_build_stamp[] =
    "P03_3B3_HDR3_CAPTURE_V2";

enum {
    B3_ERR_WIDTH = 1, B3_ERR_HEADER = 2, B3_ERR_INIT = 3,
    B3_ERR_REGISTER = 4, B3_ERR_BIND = 5, B3_ERR_PACKET = 6,
    B3_ERR_RESULT = 7, B3_ERR_RUNTIME = 8,
};

enum {
    M_MAGIC=0, M_VERSION=1, M_RESULT=2, M_ERROR=3,
    M_PS_WIDTH=4, M_RUNTIME_FAULT=5, M_FAULT_PHASE=6,
    M_DISPATCHES=7, M_BARRIERS=8, M_PACKETS=9,
    M_INITIAL_PAGE_INS=10, M_PAGE_INS=11, M_PAGE_OUTS=12,
    M_PAGE_OPERATIONS=13, M_LAST_PAGE_BYTES=14,
    M_LAST_DISPATCH_COUNT=15, M_PACKET0_LO=16, M_PACKET0_HI=17,
    M_PACKET1_LO=18, M_PACKET1_HI=19,
    M_CORE1_DDR_EVENT1=20, M_CORE0_DDR_EVENT0=21,
    M_CORE1_RESIDENT_EVENT1=22, M_CORE1_CONFIG0=23,
    M_TIMESTEPS=24, M_LAST_BANK=25,
    M_CORE0_EVENT0_COUNT=26, M_CORE1_EVENT1_COUNT=27,
    M_GLOBAL_STATUS=28, M_PAGE_PENDING=29,
    M_PAGE_WRITE_BURSTS=30, M_PAGE_READ_BURSTS=31
};

static volatile uint32_t *const mailbox = (volatile uint32_t *)P03_B3_MAILBOX;
static p03_rt runtime;
static p03_hw_adapter hw;
static p03_hw_runtime_bridge bridge;
static p03_rt_ops ops;
static int (*real_drain)(void *,uint8_t,uint32_t,uint32_t,uint8_t,uint32_t *);
static uint32_t sticky_error;
static uint64_t observed_packet0;
static uint64_t observed_packet1;

static void flush_mailbox(void)
{
    __asm__ volatile("dsb sy" ::: "memory");
    Xil_DCacheFlushRange((INTPTR)P03_B3_MAILBOX, 128);
    __asm__ volatile("dsb sy" ::: "memory");
}
static void publish_failure(uint32_t code)
{
    if (!sticky_error) sticky_error = code;
    mailbox[M_MAGIC] = B3_MAGIC;
    mailbox[M_VERSION] = B3_VERSION;
    mailbox[M_RESULT] = B3_FAIL | sticky_error;
    mailbox[M_ERROR] = sticky_error;
    mailbox[M_RUNTIME_FAULT] = (uint32_t)runtime.first_fault;
    mailbox[M_FAULT_PHASE] = (uint32_t)runtime.fault_phase;
    flush_mailbox();
}
static void halt_forever(void)
{
    for (;;) __asm__ volatile("wfe");
}
/*
 * P03.3b3 read-only header preflight: preserve every PS-observed field on
 * error. The previous boolean short-circuited, hiding which core/offset
 * failed. JTAG DDR readback alone cannot prove the A53 saw identical bytes.
 *
 * Error-only mailbox overlay (indices 7..31):
 *   [7] = HDR3 marker; [8]/[9] = core0/core1 mismatch bitmasks;
 *   [10..20] = core0 observed 11 words; [21..31] = core1 observed words.
 * This overlay is NEVER written for a successful preflight.
 */
#define B3_HEADER_DIAG_MAGIC UINT32_C(0x48445233) /* HDR3 */
#define B3_HEADER_FIELD_COUNT 11u
static const uint32_t header_offsets[B3_HEADER_FIELD_COUNT] = {
    0u, 4u, 8u, 12u, 16u, 20u, 24u, 28u, 44u, 48u, 52u
};

static uint32_t check_header(uintptr_t base, uint32_t core,
                             uint32_t event0, uint32_t observed[11])
{
    uint32_t expected[B3_HEADER_FIELD_COUNT] = {
        UINT32_C(0x3356544C), UINT32_C(0x31585443),
        1u, UINT32_C(0x1000), UINT32_C(0x80000),
        core, 0u, 0u, event0, 0u, 0u
    };
    uint32_t mismatches = 0u;
    unsigned i;

    Xil_DCacheInvalidateRange((INTPTR)base, 0x80000);
    __asm__ volatile("dsb sy" ::: "memory");
    for (i = 0; i < B3_HEADER_FIELD_COUNT; ++i) {
        observed[i] = Xil_In32(base + (uintptr_t)header_offsets[i]);
        if (observed[i] != expected[i])
            mismatches |= (UINT32_C(1) << i);
    }
    return mismatches;
}
static int validate_deployment(void *ctx)
{
    (void)ctx;
    return ((P03_B3_META0 & UINT64_C(0x7F)) == 0 &&
            (P03_B3_META1 & UINT64_C(0x7F)) == 1) ? 0 : -1;
}
static int validate_backing(void *ctx)
{
    uint32_t first[11], second[11], bad0, bad1;
    unsigned i;
    (void)ctx;

    /* Read both records even when core0 fails, so a single failed
     * physical run distinguishes a bad record from a visibility issue
     * affecting the entire PS DDR aperture.
     */
    bad0 = check_header(P03_B3_RECORD0, 0, 1, first);
    bad1 = check_header(P03_B3_RECORD1, 1, 0, second);
    if (bad0 != 0u || bad1 != 0u) {
        mailbox[7] = B3_HEADER_DIAG_MAGIC;
        mailbox[8] = bad0;
        mailbox[9] = bad1;
        for (i = 0; i < B3_HEADER_FIELD_COUNT; ++i) {
            mailbox[10u + i] = first[i];
            mailbox[21u + i] = second[i];
        }
        flush_mailbox();
        return -1;
    }
    return 0;
}
static int validate_resident_input(void *ctx)
{
    p03_hw_adapter *adapter = ctx;
    uint32_t data[8] = {0};
    if (p03_hw_debug_word(adapter, 0, P03_HW_CONFIG_DEBUG_BANK,0,0,data) ||
        data[0] != P03_B3_CONFIG0)
        return -1;
    if (p03_hw_debug_word(adapter, 0, P03_HW_EVENT0_DEBUG_BANK,0,0,data) ||
        data[0] != P03_B3_EXPECT_INITIAL_EVENT0_CORE0)
        return -1;
    return 0;
}
static int strict_drain(void *ctx, uint8_t src, uint32_t emitted,
                        uint32_t step, uint8_t next_bank, uint32_t *committed)
{
    uint64_t packet;
    uint64_t expected = 0;
    /* These expectations validate REAL packets read from the FPGA output
     * memory before invoking the unchanged production packet router.
     */
    if (step == 0 && src == 0) {
        expected = P03_B3_EXPECT_PACKET0;
        /* Source0 -> dest core1, axon11, target timestep1. */
    } else if (step == 1 && src == 1) {
        expected = P03_B3_EXPECT_PACKET1;
    } else if (emitted != 0) {
        publish_failure(B3_ERR_PACKET);
        return -1;
    }

    if (expected != 0) {
        uint8_t slot;
        if (emitted != 1u) {
            publish_failure(B3_ERR_PACKET);
            return -1;
        }
        for (slot=0;slot<runtime.slot_count;++slot)
            if (runtime.resident[slot] == (int16_t)src) break;
        if (slot>=runtime.slot_count ||
            p03_hw_read_packet(&hw,slot,0,&packet) != P03_HW_OK) {
            publish_failure(B3_ERR_PACKET);
            return -1;
        }
        /* Persist actual HLS packet bytes EVEN ON A MISMATCH, so a failed
         * hardware run can be diagnosed without a live JTAG debugger.
         */
        if (src == 0) {
            observed_packet0 = packet;
            mailbox[M_PACKET0_LO] = (uint32_t)packet;
            mailbox[M_PACKET0_HI] = (uint32_t)(packet >> 32);
        } else {
            observed_packet1 = packet;
            mailbox[M_PACKET1_LO] = (uint32_t)packet;
            mailbox[M_PACKET1_HI] = (uint32_t)(packet >> 32);
        }
        flush_mailbox();
        if (packet != expected) {
            publish_failure(B3_ERR_PACKET);
            return -1;
        }
    }
    return real_drain(ctx,src,emitted,step,next_bank,committed);
}
static void on_error(void *ctx, const p03_rt *rt)
{
    (void)ctx;
    (void)rt;
    publish_failure(B3_ERR_RUNTIME);
}

static int result(void *ctx, const p03_rt *rt)
{
    p03_hw_adapter *adapter = ctx;
    uint32_t cfg[8] = {0}, event[8] = {0};
    uint32_t ps_error = 0;
    uint32_t counts[6] = {0};
    uintptr_t core0_event_addr = P03_B3_RECORD0 + (uintptr_t)UINT32_C(0x54000);
    uintptr_t core1_event_addr = P03_B3_RECORD1 + (uintptr_t)UINT32_C(0x58000);

    if (adapter->runtime->resident[0] != 1 ||
        p03_hw_debug_word(adapter,0,P03_HW_CONFIG_DEBUG_BANK,0,0,cfg) ||
        p03_hw_debug_word(adapter,0,P03_HW_EVENT1_DEBUG_BANK,0,0,event))
        return -1;

    Xil_DCacheInvalidateRange((INTPTR)core0_event_addr,64);
    Xil_DCacheInvalidateRange((INTPTR)core1_event_addr,64);
    __asm__ volatile("dsb sy" ::: "memory");

    mailbox[M_CORE1_DDR_EVENT1] = Xil_In32(core1_event_addr);
    mailbox[M_CORE0_DDR_EVENT0] = Xil_In32(core0_event_addr);
    mailbox[M_CORE1_RESIDENT_EVENT1] = event[0];
    mailbox[M_CORE1_CONFIG0] = cfg[0];

    mailbox[M_PACKET0_LO] = (uint32_t)observed_packet0;
    mailbox[M_PACKET0_HI] = (uint32_t)(observed_packet0 >> 32);
    mailbox[M_PACKET1_LO] = (uint32_t)observed_packet1;
    mailbox[M_PACKET1_HI] = (uint32_t)(observed_packet1 >> 32);

    mailbox[M_DISPATCHES] = rt->counters.logical_dispatches;
    mailbox[M_BARRIERS] = rt->counters.barriers;
    mailbox[M_PACKETS] = rt->counters.routed_packets;
    mailbox[M_INITIAL_PAGE_INS] = rt->counters.initial_page_ins;
    mailbox[M_PAGE_INS] = rt->counters.page_ins;
    mailbox[M_PAGE_OUTS] = rt->counters.page_outs;
    mailbox[M_TIMESTEPS] = rt->counters.timesteps_completed;
    mailbox[M_LAST_BANK] = rt->current_event_bank;
    mailbox[M_CORE0_EVENT0_COUNT] = adapter->event_counts[0][0];
    mailbox[M_CORE1_EVENT1_COUNT] = adapter->event_counts[1][1];

    if (adapter->io.read32(adapter->cookie,P03_REG_PAGE_COMPLETED,&counts[0]) ||
        adapter->io.read32(adapter->cookie,P03_REG_PAGE_BYTES,&counts[1]) ||
        adapter->io.read32(adapter->cookie,P03_REG_DISPATCH_COMPLETED,&counts[2]) ||
        adapter->io.read32(adapter->cookie,P03_REG_GLOBAL_STATUS,&counts[3]) ||
        adapter->io.read32(adapter->cookie,P03_REG_PAGE_PENDING_BYTES,&counts[4]) ||
        adapter->io.read32(adapter->cookie,P03_REG_PAGE_WRITE_BURSTS,&ps_error))
        return -1;
    mailbox[M_PAGE_OPERATIONS] = counts[0];
    mailbox[M_LAST_PAGE_BYTES] = counts[1];
    mailbox[M_LAST_DISPATCH_COUNT] = counts[2];
    mailbox[M_GLOBAL_STATUS] = counts[3];
    mailbox[M_PAGE_PENDING] = counts[4];
    mailbox[M_PAGE_WRITE_BURSTS] = ps_error;
    if (adapter->io.read32(adapter->cookie,P03_REG_PAGE_READ_BURSTS,&ps_error))
        return -1;
    mailbox[M_PAGE_READ_BURSTS] = ps_error;

    if (rt->counters.logical_dispatches != 4u ||
        rt->counters.barriers != 2u ||
        rt->counters.routed_packets != 2u ||
        rt->counters.initial_page_ins != 1u ||
        rt->counters.page_ins != 3u ||
        rt->counters.page_outs != 3u ||
        rt->counters.timesteps_completed != 2u ||
        rt->current_event_bank != 0u ||
        rt->first_fault != P03_RT_FAULT_NONE ||
        observed_packet0 != P03_B3_EXPECT_PACKET0 ||
        observed_packet1 != P03_B3_EXPECT_PACKET1 ||
        cfg[0] != P03_B3_CONFIG1 ||
        event[0] != P03_B3_EXPECT_EVENT1_CORE1 ||
        mailbox[M_CORE1_DDR_EVENT1] != P03_B3_EXPECT_EVENT1_CORE1 ||
        mailbox[M_CORE0_DDR_EVENT0] != P03_B3_EXPECT_EVENT0_CORE0 ||
        adapter->event_counts[0][0] != 1u ||
        adapter->event_counts[1][1] != 0u ||
        counts[0] != 7u || counts[1] != P03_B3_PAGE_IN_BYTES ||
        counts[2] != 4u || counts[3] != 0 || counts[4] != 0 ||
        p03_hw_quiescent(adapter) != P03_HW_OK)
        return -1;
    mailbox[M_RESULT] = B3_PASS;
    mailbox[M_ERROR] = 0;
    flush_mailbox();
    return 0;
}

int main(void)
{
    const uint8_t ids[2] = {0,1};
    p03_hw_io io = p03_hw_xilinx_io();
    uint32_t raw = Xil_In32((UINTPTR)0xFD615000u);
    unsigned i;
    for (i=0;i<32;++i) mailbox[i] = 0;
    mailbox[M_MAGIC] = B3_MAGIC;
    mailbox[M_VERSION] = B3_VERSION;
    mailbox[M_PS_WIDTH] = raw;
    flush_mailbox();
    if (b3_probe_build_stamp[0] != 'P') {
        publish_failure(B3_ERR_INIT);
        halt_forever();
    }
    if (p03_hw_xilinx_fpd128_ready() != 0) {
        publish_failure(B3_ERR_WIDTH); halt_forever();
    }
    if (validate_backing(NULL) != 0) {
        publish_failure(B3_ERR_HEADER); halt_forever();
    }
    if (p03_hw_init(&hw,&io,NULL,P03_HW_BACKING_BASE,B3_POLL)) {
        publish_failure(B3_ERR_INIT); halt_forever();
    }
    if (p03_hw_register_core(&hw,0,P03_B3_META0,1,0) ||
        p03_hw_register_core(&hw,1,P03_B3_META1,0,0) ||
        p03_hw_register_axon(&hw,0,10) ||
        p03_hw_register_axon(&hw,0,20) ||
        p03_hw_register_axon(&hw,1,11)) {
        publish_failure(B3_ERR_REGISTER); halt_forever();
    }
    if (p03_rt_init(&runtime,ids,2,1,2) != 0) {
        publish_failure(B3_ERR_INIT); halt_forever();
    }
    bridge.hw = &hw;
    bridge.runtime = &runtime;
    bridge.app_cookie = &hw;
    bridge.validate_deployment = validate_deployment;
    bridge.validate_backing = validate_backing;
    bridge.load_input = validate_resident_input;
    bridge.write_result = result;
    bridge.read_ticks = NULL;
    bridge.on_error = on_error;
    if (p03_hw_bind_runtime(&bridge,&ops) != 0) {
        publish_failure(B3_ERR_BIND); halt_forever();
    }
    real_drain = ops.drain_route;
    ops.drain_route = strict_drain;
    if (p03_rt_execute(&runtime,&ops,&bridge) != 0)
        publish_failure(B3_ERR_RUNTIME);
    if (mailbox[M_RESULT] != B3_PASS)
        publish_failure(B3_ERR_RESULT);
    flush_mailbox();
    halt_forever();
    return 0;
}
