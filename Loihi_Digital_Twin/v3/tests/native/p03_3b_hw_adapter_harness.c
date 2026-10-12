#include "p03_hw_adapter.h"
#include "p03_hw_runtime_bridge.h"
#include "p03_mmio.h"
#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

typedef struct {
    uint32_t regs[1024];
    uint32_t writes, reads, cleans, invalidates, stores, fences;
    uint32_t last_page_config, last_dispatch_config, last_event_value;
    uint32_t last_event_bank, last_event_index;
    uint64_t last_ddr_addr;
    int fail_page, fail_debug, fail_dispatch, fail_store;
    uint32_t program_count, result_count, faults;
} mock;

static int mread(void *cookie, uint32_t off, uint32_t *value)
{
    mock *m = cookie;
    if (off >= 4096 || (off & 3u)) return -1;
    m->reads++;
    *value = m->regs[off / 4u];
    return 0;
}
static int mwrite(void *cookie, uint32_t off, uint32_t value)
{
    mock *m = cookie;
    if (off >= 4096 || (off & 3u)) return -1;
    m->writes++;
    m->regs[off / 4u] = value;
    if (off == P03_REG_PAGE_CONFIG)
        m->last_page_config = value;
    if (off == P03_REG_DISPATCH_CONFIG)
        m->last_dispatch_config = value;
    if (off == P03_REG_PAGE_COMMAND && (value & P03_CMD_START)) {
        m->regs[P03_REG_PAGE_STATUS / 4u] = m->fail_page ? 0x8u : 2u;
        m->regs[P03_REG_PAGE_BYTES / 4u] =
            (m->last_page_config & P03_PAGE_CONFIG_MUTABLE_ONLY)
            ? P03_HW_MUTABLE_BYTES : P03_HW_FULL_PAGE_BYTES;
        m->regs[P03_REG_PAGE_PENDING_BYTES / 4u] = 0;
        m->regs[P03_REG_PAGE_CYCLES_LO / 4u] = 33;
        m->regs[P03_REG_PAGE_CYCLES_HI / 4u] = 0;
    }
    if (off == P03_REG_DISPATCH_COMMAND && (value & P03_CMD_START)) {
        m->regs[P03_REG_DISPATCH_STATUS / 4u] = m->fail_dispatch ? 8u : 2u;
        m->regs[P03_REG_DISPATCH_CYCLES_LO / 4u] = 12;
        m->regs[P03_REG_DISPATCH_ACTIVE / 4u] =
            (m->regs[P03_REG_DISPATCH_META_LO / 4u] & 0x7Fu) << 16 |
            m->last_dispatch_config;
        m->regs[P03_REG_DISPATCH_CORE_STATUS / 4u] = 0;
        m->regs[P03_REG_DISPATCH_PACKET_CNT / 4u] = 0;
    }
    if (off == P03_REG_DEBUG_COMMAND && (value & P03_CMD_START)) {
        m->regs[P03_REG_DEBUG_STATUS / 4u] = m->fail_debug ? 8u :
           ((m->regs[P03_REG_DEBUG_CONFIG / 4u] & 1u) ? 2u : 6u);
        if (m->regs[P03_REG_DEBUG_CONFIG / 4u] & 1u) {
            m->last_event_bank =
                (m->regs[P03_REG_DEBUG_CONFIG / 4u] >> 12) & 15u;
            m->last_event_index = m->regs[P03_REG_DEBUG_ADDR / 4u];
            m->last_event_value = m->regs[P03_REG_DEBUG_WDATA0 / 4u];
        }
    }
    return 0;
}
static int mclean(void *cookie, uint64_t addr, uint32_t bytes)
{
    mock *m = cookie;
    assert(addr >= P03_HW_BACKING_BASE);
    assert(bytes > 0);
    m->cleans++;
    return 0;
}
static int minvalidate(void *cookie, uint64_t addr, uint32_t bytes)
{
    mock *m = cookie;
    assert(addr >= P03_HW_BACKING_BASE);
    assert(bytes > 0);
    m->invalidates++;
    return 0;
}
static int mstore(void *cookie, uint64_t addr, uint32_t value)
{
    mock *m = cookie;
    if (m->fail_store) return -1;
    m->stores++;
    m->last_ddr_addr = addr;
    m->last_event_value = value;
    return 0;
}
static void mfence(void *cookie)
{
    ((mock *)cookie)->fences++;
}
static p03_hw_io mock_io(void)
{
    p03_hw_io ops = {
        .read32 = mread, .write32 = mwrite,
        .clean_range = mclean, .invalidate_range = minvalidate,
        .store_ddr32 = mstore, .barrier = mfence,
    };
    return ops;
}
static void setup(mock *m, p03_hw_adapter *hw)
{
    p03_hw_io io = mock_io();
    memset(m, 0, sizeof(*m));
    m->regs[P03_REG_ID / 4u] = P03_MMIO_ID_VALUE;
    m->regs[P03_REG_VERSION / 4u] = P03_MMIO_VERSION_VALUE;
    m->regs[P03_REG_CAPABILITIES / 4u] = 0x0001031Fu;
    assert(p03_hw_init(hw, &io, m, P03_HW_BACKING_BASE, 10) == 0);
}
static uint64_t meta(uint8_t id)
{
    return (uint64_t)id | (UINT64_C(1) << 7) |
           (UINT64_C(1) << 18) | (UINT64_C(1) << 34);
}
static uint64_t packet(uint8_t dest, uint32_t axon, uint32_t target)
{
    return (uint64_t)dest | ((uint64_t)axon << 7) |
           ((uint64_t)target << 29) | (UINT64_C(1) << 61);
}
static void test_page_debug_dispatch(void)
{
    mock m;
    p03_hw_adapter hw;
    uint64_t cycles = 0;
    uint32_t n = 999, data[8] = {0};
    setup(&m, &hw);
    assert(p03_hw_identify(&hw) == 0);
    assert(p03_hw_register_core(&hw, 5, meta(5), 0, 2) == 0);
    assert(p03_hw_page(&hw, 5, 1, 0, 0, &cycles) == 0);
    assert(cycles == 33 && m.cleans == 1 && m.invalidates == 0);
    assert(m.last_page_config == (1u << 8));
    assert(m.regs[P03_REG_PAGE_BASE_LO / 4u] ==
           (uint32_t)(P03_HW_BACKING_BASE + 5u * P03_HW_RECORD_BYTES));
    assert(p03_hw_debug_word(&hw, 1, P03_HW_CONFIG_DEBUG_BANK,
                             0, 0, data) == 0);
    assert(p03_hw_dispatch(&hw, 5, 1, 9, 1, &n, &cycles) == 0);
    assert(cycles == 12 && n == 0);
    assert(m.last_dispatch_config == 0x101u);
    assert(m.regs[P03_REG_DISPATCH_META_LO / 4u] == (uint32_t)meta(5));
    assert((m.regs[P03_REG_DISPATCH_META_HI / 4u] >> 15 & 0x1FFFu) == 2);
    assert(hw.event_counts[5][1] == 0 && hw.event_counts[5][0] == 0);
    assert(p03_hw_page(&hw, 5, 1, 1, 1, &cycles) == 0);
    assert(m.last_page_config ==
          (1u << 8 | P03_PAGE_CONFIG_PAGE_OUT | P03_PAGE_CONFIG_MUTABLE_ONLY));
    assert(m.invalidates == 2);
    puts("PASS: P03.3b native MMIO page/debug/dispatch nonzero core and mutable save");
}
static void test_packet_routing(void)
{
    mock m;
    p03_hw_adapter hw;
    p03_rt rt;
    const uint8_t ids[] = {0, 1, 2};
    setup(&m, &hw);
    assert(p03_rt_init(&rt, ids, 3, 2, 2) == 0);
    hw.runtime = &rt;
    assert(p03_hw_register_core(&hw, 0, meta(0), 0, 0) == 0);
    assert(p03_hw_register_core(&hw, 1, meta(1), 0, 0) == 0);
    assert(p03_hw_register_core(&hw, 2, meta(2), 0, 0) == 0);
    assert(p03_hw_register_axon(&hw, 1, 43) == 0);
    assert(p03_hw_register_axon(&hw, 2, 59) == 0);
    assert(p03_hw_register_axon(&hw, 2, 41) == 0);
    rt.resident[0] = 0;
    rt.resident[1] = 1;
    assert(p03_hw_route_word(&hw, 0, packet(1, 43, 1), 0, 1) == 0);
    assert(m.last_event_bank == P03_HW_EVENT1_DEBUG_BANK);
    assert(m.last_event_value == 43 && m.last_event_index == 0);
    assert(hw.event_counts[1][1] == 1);
    assert(p03_hw_route_word(&hw, 0, packet(2, 59, 1), 0, 1) == 0);
    assert(m.stores == 1 && m.last_event_value == 59);
    assert(m.last_ddr_addr == P03_HW_BACKING_BASE +
           2u * P03_HW_RECORD_BYTES + P03_HW_EVENT1_OFFSET);
    assert(hw.event_counts[2][1] == 1);
    assert(p03_hw_route_word(&hw, 0, packet(2, 41, 1), 0, 1) == 0);
    assert(m.last_ddr_addr == P03_HW_BACKING_BASE +
           2u * P03_HW_RECORD_BYTES + P03_HW_EVENT1_OFFSET + 4);
    assert(hw.event_counts[2][1] == 2);
    assert(p03_hw_route_word(&hw, 0, packet(2, 59, 9), 0, 1) ==
           P03_HW_PACKET_INVALID);
    assert(hw.event_counts[2][1] == 2 && m.stores == 2);
    /* Sticky fault requires explicit re-init; no more MMIO on invalid. */
    assert(p03_hw_route_word(&hw, 0, packet(2, 1, 1), 0, 1) != 0);
    puts("PASS: P03.3b resident/DDR NEXT packet delivery and timestep validation");
}
static void test_overflow_and_bus_failure(void)
{
    mock m;
    p03_hw_adapter hw;
    p03_rt rt;
    uint64_t cycles = 0;
    const uint8_t ids[] = {0};
    setup(&m, &hw);
    assert(p03_rt_init(&rt, ids, 1, 1, 1) == 0);
    hw.runtime = &rt;
    assert(p03_hw_register_core(&hw, 0, meta(0), 0, 4096) == 0);
    assert(p03_hw_register_axon(&hw, 0, 3) == 0);
    rt.resident[0] = 0;
    assert(p03_hw_route_word(&hw, 0, packet(0, 3, 1), 0, 1) ==
           P03_HW_OVERFLOW);
    setup(&m, &hw);
    assert(p03_hw_register_core(&hw, 0, meta(0), 0, 0) == 0);
    m.fail_page = 1;
    assert(p03_hw_page(&hw, 0, 0, 0, 0, &cycles) == P03_HW_PROTOCOL);
    assert(hw.last_status & 8u);
    puts("PASS: P03.3b packet capacity and page MMIO error fail closed");
}
static int good(void *ctx) { (void)ctx; return 0; }
static int result(void *ctx, const p03_rt *rt)
{
    mock *m = ctx;
    assert(rt->counters.logical_dispatches == 2);
    assert(rt->counters.barriers == 2);
    ++m->result_count;
    return 0;
}
static void fault(void *ctx, const p03_rt *rt)
{
    mock *m = ctx;
    (void)rt;
    ++m->faults;
}
static void test_native_runtime_bridge(void)
{
    mock m;
    p03_hw_adapter hw;
    p03_rt rt;
    p03_hw_runtime_bridge bridge;
    p03_rt_ops ops;
    const uint8_t ids[] = {0};
    setup(&m, &hw);
    assert(p03_rt_init(&rt, ids, 1, 1, 2) == 0);
    assert(p03_hw_register_core(&hw, 0, meta(0), 0, 0) == 0);
    memset(&bridge, 0, sizeof(bridge));
    bridge.hw = &hw;
    bridge.runtime = &rt;
    bridge.app_cookie = &m;
    bridge.validate_deployment = good;
    bridge.validate_backing = good;
    bridge.load_input = good;
    bridge.write_result = result;
    bridge.on_error = fault;
    assert(p03_hw_bind_runtime(&bridge, &ops) == 0);
    assert(p03_rt_execute(&rt, &ops, &bridge) == 0);
    assert(rt.phase == P03_RT_DONE && m.result_count == 1 && m.faults == 0);
    assert(rt.counters.initial_page_ins == 1);
    assert(rt.counters.page_ins == 0 && rt.counters.page_hits == 2);
    puts("PASS: P03.3b 2-step native policy-to-MMIO bridge");
}
int main(void)
{
    test_page_debug_dispatch();
    test_packet_routing();
    test_overflow_and_bus_failure();
    test_native_runtime_bridge();
    puts("PASS: P03.3b host-native hardware adapter suite");
    return 0;
}
