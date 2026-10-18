#include "include/p07_a2_runtime.h"

#include <string.h>

typedef struct {
    const uint8_t *record;
    size_t record_bytes;
    const p07_a2_driver *driver;
    p07_a2_result *result;
    p03_rt_ops underlying;
    void *underlying_ctx;
} p07_internal;

static int passthrough_load(void *arg)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.load_deployment(s->underlying_ctx);
}
static int passthrough_backing(void *arg)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.initialize_backing(s->underlying_ctx);
}
static int passthrough_page_in(void *arg, uint8_t id, uint8_t slot,
                               uint64_t *cycles)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.page_in(s->underlying_ctx, id, slot, cycles);
}
static int passthrough_page_out(void *arg, uint8_t id, uint8_t slot,
                                uint64_t *cycles)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.page_out(s->underlying_ctx, id, slot, cycles);
}
static int passthrough_input(void *arg)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.load_input(s->underlying_ctx);
}
static int tick_dispatch(void *arg, uint8_t id, uint8_t slot,
                         uint32_t tick, uint8_t bank,
                         uint32_t *emitted, uint64_t *cycles)
{
    p07_internal *s = (p07_internal *)arg;
    uint16_t events[P07_A1_PIXEL_COUNT];
    size_t count = 0u;
    uint32_t words[8] = {0u};
    uint32_t cls;
    if (id != 0u || tick >= P07_A1_TOTAL_TICKS ||
        bank != (tick & 1u) || !emitted || !cycles)
        return -1;
    if (p07_a1_tick_events(s->record, s->record_bytes, tick, events,
                           P07_A1_PIXEL_COUNT, &count) != P07_A1_OK)
        return -1;
    /* Driver performs aggregate CURRENT bank preflight and owns append
     * ordering. The count does not include accepted routed NEXT traffic.
     */
    if (s->driver->append_current(s->driver->cookie, slot, bank,
                                  events, count) != 0)
        return -1;
    s->result->external_events[tick] = (uint16_t)count;
    if (s->underlying.dispatch(s->underlying_ctx, id, slot, tick, bank,
                               emitted, cycles) != 0)
        return -1;
    /* Read completed HLS trace before next dispatch or page eviction.
     * Treat trace[192] as a strict one-bit signal, never aggregate spikes.
     */
    for (cls = 0u; cls < P07_A2_OUTPUTS; ++cls) {
        uint8_t fired;
        memset(words, 0, sizeof(words));
        if (s->driver->read_trace(s->driver->cookie, slot,
                (uint16_t)(P07_A2_OUTPUT_START + cls), words) != 0)
            return -1;
        fired = (uint8_t)(words[6] & 1u);
        s->result->output_spikes[tick][cls] = fired;
        s->result->counts[cls] += fired;
    }
    return 0;
}
static int tick_route(void *arg, uint8_t id, uint32_t emitted,
                      uint32_t tick, uint8_t next_bank, uint32_t *committed)
{
    p07_internal *s = (p07_internal *)arg;
    if (!committed || id != 0u || tick >= P07_A1_TOTAL_TICKS ||
        next_bank != (uint8_t)(1u - (tick & 1u)))
        return -1;
    if (tick == P07_A1_INPUT_TICKS) {
        /* Logical timestep 25 is drain: output at 25 counts, but hidden
         * outgoing packets at 25 are discarded at image boundary.
         * P03 scheduler expects every emitted packet acknowledged, so
         * report consumed drops separately, WITHOUT writing a NEXT bank.
         */
        s->result->dropped_final_packets = emitted;
        *committed = emitted;
        return 0;
    }
    if (s->underlying.drain_route(s->underlying_ctx, id, emitted, tick,
                                   next_bank, committed) != 0)
        return -1;
    s->result->committed_routes += *committed;
    return 0;
}
static int passthrough_barrier(void *arg, uint32_t tick, uint8_t next_bank)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.barrier_ready(s->underlying_ctx, tick, next_bank);
}
static int passthrough_result(void *arg, const p03_rt *rt)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.write_result(s->underlying_ctx, rt);
}
static uint64_t passthrough_ticks(void *arg)
{
    p07_internal *s = (p07_internal *)arg;
    return s->underlying.read_ticks ?
           s->underlying.read_ticks(s->underlying_ctx) : 0u;
}
static void passthrough_error(void *arg, const p03_rt *rt)
{
    p07_internal *s = (p07_internal *)arg;
    if (s->underlying.on_error)
        s->underlying.on_error(s->underlying_ctx, rt);
}

int p07_a2_run_frame(const uint8_t *record, size_t bytes,
                     const p07_a2_driver *driver, p07_a2_result *result)
{
    p07_a1_info info;
    p03_rt rt;
    p07_internal s;
    p03_rt_ops ops;
    uint8_t core0 = 0u;
    uint32_t cls;
    int rc;

    if (!result) return P07_A2_BAD_ARGUMENT;
    memset(result, 0, sizeof(*result));
    if (!driver || !driver->prepare || !driver->append_current ||
        !driver->read_trace || !record)
        return P07_A2_BAD_ARGUMENT;
    if (p07_a1_validate(record, bytes, &info) != P07_A1_OK)
        return P07_A2_BAD_RECORD;
    if (p03_rt_init(&rt, &core0, 1u, 1u, P07_A1_TOTAL_TICKS) != 0)
        return P07_A2_BAD_SETUP;
    memset(&s, 0, sizeof(s));
    s.record = record;
    s.record_bytes = bytes;
    s.driver = driver;
    s.result = result;
    /* Board preparation MUST reset physical state before any dispatch,
     * verify the immutable artifact and register all 816 axon bindings.
     */
    if (driver->prepare(driver->cookie, record, bytes, &rt,
                        &s.underlying, &s.underlying_ctx) != 0)
        return P07_A2_BAD_SETUP;
    if (!s.underlying_ctx ||
        !s.underlying.load_deployment || !s.underlying.initialize_backing ||
        !s.underlying.page_in || !s.underlying.page_out ||
        !s.underlying.load_input || !s.underlying.dispatch ||
        !s.underlying.drain_route || !s.underlying.barrier_ready ||
        !s.underlying.write_result)
        return P07_A2_BAD_SETUP;

    ops.load_deployment = passthrough_load;
    ops.initialize_backing = passthrough_backing;
    ops.page_in = passthrough_page_in;
    ops.page_out = passthrough_page_out;
    ops.load_input = passthrough_input;
    ops.dispatch = tick_dispatch;
    ops.drain_route = tick_route;
    ops.barrier_ready = passthrough_barrier;
    ops.write_result = passthrough_result;
    ops.read_ticks = passthrough_ticks;
    ops.on_error = passthrough_error;

    rc = p03_rt_execute(&rt, &ops, &s);
    result->first_fault = rt.first_fault;
    result->fault_phase = rt.fault_phase;
    result->timesteps = rt.counters.timesteps_completed;
    result->barriers = rt.counters.barriers;
    result->dispatches = rt.counters.logical_dispatches;
    if (rc != 0 || rt.phase != P03_RT_DONE || rt.first_fault != P03_RT_FAULT_NONE ||
        result->timesteps != P07_A1_TOTAL_TICKS ||
        result->barriers != P07_A1_TOTAL_TICKS ||
        result->dispatches != P07_A1_TOTAL_TICKS)
        return P07_A2_BAD_EXECUTION;

    result->all_silent = 1u;
    result->predicted_class = 0u;
    for (cls = 0; cls < P07_A2_OUTPUTS; ++cls) {
        if (result->counts[cls]) result->all_silent = 0u;
        if (result->counts[cls] > result->counts[result->predicted_class])
            result->predicted_class = cls;
    }
    return P07_A2_OK;
}
