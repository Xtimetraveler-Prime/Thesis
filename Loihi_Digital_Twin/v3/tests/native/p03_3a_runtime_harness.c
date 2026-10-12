#include "p03_runtime.h"

#include <assert.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>

/* Native fake hardware checks policy while retaining the exact callback ABI
 * the physical Cortex-A53 adapter will implement in P03.3b.
 */
typedef struct {
    int16_t hw_slot[P03_RT_MAX_SLOTS];
    uint8_t hw_dirty[P03_RT_MAX_SLOTS];
    uint32_t writes;
    uint32_t reads;
    uint32_t dispatches;
    uint32_t routes;
    uint32_t barriers;
    uint32_t packets;
    uint32_t result_writes;
    uint32_t fault_reports;
    uint32_t refuse_barrier;
    uint32_t partial_route;
    uint32_t fail_save;
    uint64_t ticks;
    char log[16384];
    size_t log_size;
} fake_hw;

static void log_op(fake_hw *hw, char op, unsigned a, unsigned b)
{
    int n = snprintf(hw->log + hw->log_size,
                     sizeof(hw->log) - hw->log_size, "%c%u:%u;", op, a, b);
    assert(n > 0 && (size_t)n < sizeof(hw->log) - hw->log_size);
    hw->log_size += (size_t)n;
}

static void setup(fake_hw *hw)
{
    uint8_t i;
    memset(hw, 0, sizeof(*hw));
    for (i = 0; i < P03_RT_MAX_SLOTS; ++i)
        hw->hw_slot[i] = P03_RT_EMPTY_SLOT;
}

static int good(void *ctx)
{
    ((fake_hw *)ctx)->ticks += 5;
    return 0;
}
static int page_in(void *ctx, uint8_t id, uint8_t slot, uint64_t *cycles)
{
    fake_hw *hw = ctx;
    assert(slot < P03_RT_MAX_SLOTS);
    /* Every displaced dirty resident must be saved before new load. */
    assert(hw->hw_slot[slot] == P03_RT_EMPTY_SLOT ||
           hw->hw_dirty[slot] == 0);
    hw->hw_slot[slot] = id;
    hw->hw_dirty[slot] = 0;
    hw->reads++;
    hw->ticks += 20;
    *cycles = 13;
    log_op(hw, 'I', id, slot);
    return 0;
}
static int page_out(void *ctx, uint8_t id, uint8_t slot, uint64_t *cycles)
{
    fake_hw *hw = ctx;
    assert(hw->hw_slot[slot] == (int16_t)id);
    assert(hw->hw_dirty[slot]);
    log_op(hw, 'O', id, slot);
    if (hw->fail_save)
        return -1;
    hw->writes++;
    hw->hw_dirty[slot] = 0;
    hw->ticks += 11;
    *cycles = 9;
    return 0;
}
static int dispatch(void *ctx, uint8_t id, uint8_t slot, uint32_t timestep,
                    uint8_t current_bank, uint32_t *emitted, uint64_t *cycles)
{
    fake_hw *hw = ctx;
    assert(hw->hw_slot[slot] == (int16_t)id);
    assert(current_bank == (timestep & 1u));
    hw->hw_dirty[slot] = 1;
    hw->dispatches++;
    *emitted = 1;
    *cycles = 37;
    hw->ticks += 15;
    log_op(hw, 'D', id, timestep);
    return 0;
}
static int drain_route(void *ctx, uint8_t id, uint32_t emitted,
                       uint32_t timestep, uint8_t next_bank,
                       uint32_t *committed)
{
    fake_hw *hw = ctx;
    assert(emitted == 1);
    assert(next_bank == (1u - (timestep & 1u)));
    hw->routes++;
    hw->ticks += 6;
    log_op(hw, 'R', id, next_bank);
    *committed = hw->partial_route ? 0 : emitted;
    hw->packets += *committed;
    return 0;
}
static int barrier_ready(void *ctx, uint32_t timestep, uint8_t next_bank)
{
    fake_hw *hw = ctx;
    assert(next_bank == (1u - (timestep & 1u)));
    assert(hw->routes == (timestep + 1u) * 5u ||
           hw->refuse_barrier);
    hw->ticks += 4;
    log_op(hw, 'B', timestep, next_bank);
    if (hw->refuse_barrier)
        return -1;
    hw->barriers++;
    return 0;
}
static int write_result(void *ctx, const p03_rt *runtime)
{
    fake_hw *hw = ctx;
    assert(runtime->phase == P03_RT_WRITE_RESULT);
    assert(runtime->first_fault == P03_RT_FAULT_NONE);
    hw->result_writes++;
    return 0;
}
static uint64_t read_ticks(void *ctx)
{
    fake_hw *hw = ctx;
    return ++hw->ticks;
}
static void on_error(void *ctx, const p03_rt *runtime)
{
    fake_hw *hw = ctx;
    assert(runtime->phase == P03_RT_ERROR);
    assert(runtime->first_fault != P03_RT_FAULT_NONE);
    hw->fault_reports++;
}
static p03_rt_ops all_ops(void)
{
    p03_rt_ops ops = {
        .load_deployment = good,
        .initialize_backing = good,
        .page_in = page_in,
        .page_out = page_out,
        .load_input = good,
        .dispatch = dispatch,
        .drain_route = drain_route,
        .barrier_ready = barrier_ready,
        .write_result = write_result,
        .read_ticks = read_ticks,
        .on_error = on_error,
    };
    return ops;
}

static void test_5over3_7steps(void)
{
    const uint8_t ids[] = {0, 1, 2, 3, 4};
    p03_rt rt;
    fake_hw hw;
    p03_rt_ops ops = all_ops();
    setup(&hw);
    assert(p03_rt_init(&rt, ids, 5, 3, 7) == 0);
    assert(rt.phase == P03_RT_RESET);
    assert(p03_rt_execute(&rt, &ops, &hw) == 0);
    assert(rt.phase == P03_RT_DONE);
    assert(rt.first_fault == P03_RT_FAULT_NONE);
    assert(rt.external_control_locked);
    assert(rt.counters.logical_dispatches == 35);
    assert(rt.counters.routed_packets == 35);
    assert(rt.counters.barriers == 7);
    assert(rt.counters.timesteps_completed == 7);
    assert(rt.counters.initial_page_ins == 3);
    assert(rt.counters.page_ins + rt.counters.page_hits == 35);
    assert(rt.counters.page_outs == hw.writes);
    assert(rt.counters.evictions == rt.counters.page_ins);
    assert(rt.counters.pl_dispatch_cycles == 35u * 37u);
    assert(rt.counters.pl_page_cycles == hw.reads * 13u + hw.writes * 9u);
    assert(rt.counters.ps_inference_ticks > 0);
    assert(rt.counters.ps_control_ticks >= rt.counters.ps_inference_ticks);
    assert(rt.current_timestep == 7);
    assert(rt.current_event_bank == 1);
    assert(hw.dispatches == 35 && hw.routes == 35 && hw.barriers == 7);
    assert(hw.packets == 35 && hw.result_writes == 1 && !hw.fault_reports);
    assert(strstr(hw.log, "D0:0;R0:1;") != NULL);
    assert(strstr(hw.log, "O0:0;I3:0;") != NULL);
    puts("PASS: P03.3a native five-over-three seven-barrier scheduling");
}

static void test_failed_route_prevents_barrier(void)
{
    const uint8_t ids[] = {0, 1, 2, 3, 4};
    p03_rt rt;
    fake_hw hw;
    p03_rt_ops ops = all_ops();
    setup(&hw);
    hw.partial_route = 1;
    assert(p03_rt_init(&rt, ids, 5, 3, 2) == 0);
    assert(p03_rt_execute(&rt, &ops, &hw) == -1);
    assert(rt.phase == P03_RT_ERROR);
    assert(rt.first_fault == P03_RT_FAULT_BARRIER_INCOMPLETE);
    assert(rt.fault_phase == P03_RT_DRAIN_AND_ROUTE_PACKETS);
    assert(rt.counters.barriers == 0);
    assert(rt.current_event_bank == 0);
    assert(hw.fault_reports == 1);
    assert(p03_rt_execute(&rt, &ops, &hw) == -1);
    assert(rt.first_fault == P03_RT_FAULT_BARRIER_INCOMPLETE);
    assert(hw.fault_reports == 1);
    puts("PASS: P03.3a partial packet route fails closed");
}

static void test_failed_dirty_save_precedes_load(void)
{
    const uint8_t ids[] = {0, 1, 2, 3, 4};
    p03_rt rt;
    fake_hw hw;
    p03_rt_ops ops = all_ops();
    setup(&hw);
    hw.fail_save = 1;
    assert(p03_rt_init(&rt, ids, 5, 3, 1) == 0);
    assert(p03_rt_execute(&rt, &ops, &hw) == -1);
    assert(rt.phase == P03_RT_ERROR);
    assert(rt.first_fault == P03_RT_FAULT_PAGE_ERROR);
    assert(rt.fault_phase == P03_RT_SAVE_VICTIM);
    assert(rt.counters.page_ins == 0);
    assert(hw.reads == 3);
    assert(hw.hw_slot[0] == 0);
    assert(rt.counters.barriers == 0);
    puts("PASS: P03.3a dirty victim must save before reload");
}

static void test_barrier_refusal(void)
{
    const uint8_t ids[] = {0, 1, 2, 3, 4};
    p03_rt rt;
    fake_hw hw;
    p03_rt_ops ops = all_ops();
    setup(&hw);
    hw.refuse_barrier = 1;
    assert(p03_rt_init(&rt, ids, 5, 3, 1) == 0);
    assert(p03_rt_execute(&rt, &ops, &hw) == -1);
    assert(rt.first_fault == P03_RT_FAULT_BARRIER_INCOMPLETE);
    assert(rt.fault_phase == P03_RT_BARRIER_CHECK);
    assert(rt.current_event_bank == 0);
    assert(rt.counters.barriers == 0);
    puts("PASS: P03.3a barrier quiescence required for bank swap");
}

static void test_invalid_deployments(void)
{
    const uint8_t dup[] = {4, 4};
    const uint8_t out_of_range[] = {0, 128};
    const uint8_t valid[] = {0, 1};
    p03_rt rt;
    assert(p03_rt_init(&rt, dup, 2, 3, 1) == -1);
    assert(rt.phase == P03_RT_ERROR);
    assert(rt.first_fault == P03_RT_FAULT_INVALID_RUN_CONFIG);
    assert(p03_rt_init(&rt, out_of_range, 2, 3, 1) == -1);
    assert(p03_rt_init(&rt, valid, 0, 3, 1) == -1);
    assert(p03_rt_init(&rt, valid, 2, 4, 1) == -1);
    assert(p03_rt_init(&rt, valid, 2, 3, 0) == -1);
    assert(p03_rt_init(&rt, valid, 2, 2, 1) == 0);
    assert(rt.phase == P03_RT_RESET && rt.first_fault == P03_RT_FAULT_NONE);
    puts("PASS: P03.3a invalid configuration blocked and reset explicit");
}

int main(void)
{
    test_5over3_7steps();
    test_failed_route_prevents_barrier();
    test_failed_dirty_save_precedes_load();
    test_barrier_refusal();
    test_invalid_deployments();
    puts("PASS: P03.3a complete host-native C runtime policy suite");
    return 0;
}
