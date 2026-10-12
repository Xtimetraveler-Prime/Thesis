#include "p03_hw_runtime_bridge.h"
#include <stddef.h>

/* The bridge's callbacks run inside the A53 local algorithmic loop.
 * The external PC never decides slot, route, victim or barrier order.
 */
static int rt_load(void *ctx)
{
    p03_hw_runtime_bridge *b = ctx;
    uint16_t i;
    if (b->validate_deployment(b->app_cookie) != 0 ||
        p03_hw_identify(b->hw) != 0)
        return -1;
    for (i = 0; i < b->runtime->core_count; ++i)
        if (!b->hw->configured[b->runtime->logical_ids[i]])
            return -1;
    return 0;
}

static int rt_backing(void *ctx)
{
    p03_hw_runtime_bridge *b = ctx;
    return b->validate_backing(b->app_cookie);
}
static int rt_input(void *ctx)
{
    p03_hw_runtime_bridge *b = ctx;
    return b->load_input(b->app_cookie);
}
static int rt_page_in(void *ctx, uint8_t id, uint8_t slot, uint64_t *cycles)
{
    p03_hw_runtime_bridge *b = ctx;
    return p03_hw_page(b->hw, id, slot, 0, 0, cycles);
}
static int rt_page_out(void *ctx, uint8_t id, uint8_t slot, uint64_t *cycles)
{
    p03_hw_runtime_bridge *b = ctx;
    /* Save only the accepted 104 KiB mutable banks; static config/
     * axon/synapse/route banks are preserved in authoritative DDR.
     */
    return p03_hw_page(b->hw, id, slot, 1, 1, cycles);
}
static int rt_dispatch(void *ctx, uint8_t id, uint8_t slot,
                       uint32_t step, uint8_t bank,
                       uint32_t *emitted, uint64_t *cycles)
{
    p03_hw_runtime_bridge *b = ctx;
    return p03_hw_dispatch(b->hw, id, slot, step, bank, emitted, cycles);
}
static int rt_drain(void *ctx, uint8_t id, uint32_t emitted,
                    uint32_t step, uint8_t next_bank, uint32_t *committed)
{
    p03_hw_runtime_bridge *b = ctx;
    uint8_t slot;
    uint32_t i;
    uint64_t word;
    if (!committed || emitted > P03_RT_MAX_PACKETS)
        return -1;
    *committed = 0;
    for (slot = 0; slot < b->runtime->slot_count; ++slot)
        if (b->runtime->resident[slot] == (int16_t)id)
            break;
    if (slot >= b->runtime->slot_count)
        return -1;
    for (i = 0; i < emitted; ++i) {
        if (p03_hw_read_packet(b->hw, slot, (uint16_t)i, &word) != 0 ||
            p03_hw_route_word(b->hw, id, word, step, next_bank) != 0)
            return -1;
        ++(*committed);
    }
    return 0;
}
static int rt_barrier(void *ctx, uint32_t step, uint8_t next_bank)
{
    p03_hw_runtime_bridge *b = ctx;
    uint16_t k;
    /* No events may be left pending on any CURRENT bank at the barrier;
     * all future packets must already be committed to NEXT.
     */
    for (k = 0; k < b->runtime->core_count; ++k) {
        uint8_t id = b->runtime->logical_ids[k];
        if (b->hw->event_counts[id][1u - next_bank] != 0)
            return -1;
    }
    (void)step;
    return p03_hw_quiescent(b->hw);
}
static int rt_result(void *ctx, const p03_rt *runtime)
{
    p03_hw_runtime_bridge *b = ctx;
    return b->write_result(b->app_cookie, runtime);
}
static uint64_t rt_ticks(void *ctx)
{
    p03_hw_runtime_bridge *b = ctx;
    return b->read_ticks ? b->read_ticks(b->app_cookie) : UINT64_C(0);
}
static void rt_on_error(void *ctx, const p03_rt *runtime)
{
    p03_hw_runtime_bridge *b = ctx;
    if (b->on_error)
        b->on_error(b->app_cookie, runtime);
}
int p03_hw_bind_runtime(p03_hw_runtime_bridge *bridge, p03_rt_ops *out_ops)
{
    p03_rt_ops ops = {
        .load_deployment = rt_load,
        .initialize_backing = rt_backing,
        .page_in = rt_page_in,
        .page_out = rt_page_out,
        .load_input = rt_input,
        .dispatch = rt_dispatch,
        .drain_route = rt_drain,
        .barrier_ready = rt_barrier,
        .write_result = rt_result,
        .read_ticks = rt_ticks,
        .on_error = rt_on_error,
    };
    if (!bridge || !out_ops || !bridge->hw || !bridge->runtime ||
        !bridge->validate_deployment || !bridge->validate_backing ||
        !bridge->load_input || !bridge->write_result)
        return -1;
    bridge->hw->runtime = bridge->runtime;
    *out_ops = ops;
    return 0;
}
