#include "p03_runtime.h"

#include <stddef.h>
#include <string.h>

/* Only the policy engine belongs here. Physical AXI/DDR, cache maintenance,
 * packet/event encoding and timer implementations are supplied by the PS
 * board adapter in P03.3b. No bare-metal BSP dependency leaks into this file.
 */

static uint64_t now_ticks(const p03_rt_ops *ops, void *ctx)
{
    return ops->read_ticks ? ops->read_ticks(ctx) : UINT64_C(0);
}

static int fail(p03_rt *rt, const p03_rt_ops *ops, void *ctx,
                p03_rt_fault code)
{
    if (rt->first_fault == P03_RT_FAULT_NONE) {
        rt->first_fault = code;
        rt->fault_phase = rt->phase;
        rt->phase = P03_RT_ERROR;
        if (ops && ops->on_error)
            ops->on_error(ctx, rt);
    } else {
        rt->phase = P03_RT_ERROR;
    }
    return -1;
}

int p03_rt_init(p03_rt *rt, const uint8_t *logical_ids,
                uint16_t core_count, uint8_t slot_count, uint32_t timesteps)
{
    uint16_t i;
    uint8_t seen[P03_RT_MAX_CORES] = {0};

    if (rt == NULL)
        return -1;
    memset(rt, 0, sizeof(*rt));
    for (i = 0; i < P03_RT_MAX_SLOTS; ++i)
        rt->resident[i] = P03_RT_EMPTY_SLOT;
    rt->phase = P03_RT_RESET;
    rt->fault_phase = P03_RT_RESET;

    if (logical_ids == NULL || core_count == 0 ||
        core_count > P03_RT_MAX_CORES ||
        slot_count == 0 || slot_count > P03_RT_MAX_SLOTS ||
        timesteps == 0)
        return fail(rt, NULL, NULL, P03_RT_FAULT_INVALID_RUN_CONFIG);

    for (i = 0; i < core_count; ++i) {
        if (logical_ids[i] >= P03_RT_MAX_CORES || seen[logical_ids[i]])
            return fail(rt, NULL, NULL, P03_RT_FAULT_INVALID_RUN_CONFIG);
        seen[logical_ids[i]] = 1;
        rt->logical_ids[i] = logical_ids[i];
    }
    rt->core_count = core_count;
    rt->slot_count = slot_count;
    rt->requested_timesteps = timesteps;
    return 0;
}

static int valid_ops(const p03_rt_ops *ops)
{
    return ops && ops->load_deployment && ops->initialize_backing &&
           ops->page_in && ops->page_out && ops->load_input &&
           ops->dispatch && ops->drain_route && ops->barrier_ready &&
           ops->write_result;
}

/* Return resident slot or EMPTY_SLOT without mutating the victim pointer. */
static int find_resident(const p03_rt *rt, uint8_t id)
{
    uint8_t s;
    for (s = 0; s < rt->slot_count; ++s)
        if (rt->resident[s] == (int16_t)id)
            return s;
    return P03_RT_EMPTY_SLOT;
}

int p03_rt_execute(p03_rt *rt, const p03_rt_ops *ops, void *ctx)
{
    uint64_t control_begin, inference_begin;
    uint8_t slot;
    uint16_t k;
    uint32_t timestep;

    if (rt == NULL)
        return -1;
    if (rt->phase != P03_RT_RESET || rt->first_fault != P03_RT_FAULT_NONE)
        return fail(rt, ops, ctx, P03_RT_FAULT_CONTROL_PROTOCOL);
    if (!valid_ops(ops))
        return fail(rt, ops, ctx, P03_RT_FAULT_INVALID_RUN_CONFIG);
    if (rt->core_count == 0 || rt->slot_count == 0 ||
        rt->requested_timesteps == 0)
        return fail(rt, ops, ctx, P03_RT_FAULT_INVALID_RUN_CONFIG);

    control_begin = now_ticks(ops, ctx);
    rt->external_control_locked = 1;
    rt->phase = P03_RT_LOAD_DEPLOYMENT;
    if (ops->load_deployment(ctx) != 0)
        return fail(rt, ops, ctx, P03_RT_FAULT_DEPLOYMENT_INVALID);

    rt->phase = P03_RT_INITIALIZE_BACKING;
    if (ops->initialize_backing(ctx) != 0)
        return fail(rt, ops, ctx, P03_RT_FAULT_BACKING_ABI);

    rt->phase = P03_RT_INITIALIZE_RESIDENT_SET;
    for (slot = 0; slot < rt->slot_count && slot < rt->core_count; ++slot) {
        uint64_t cycles = 0;
        if (ops->page_in(ctx, rt->logical_ids[slot], slot, &cycles) != 0)
            return fail(rt, ops, ctx, P03_RT_FAULT_PAGE_ERROR);
        rt->resident[slot] = (int16_t)rt->logical_ids[slot];
        ++rt->counters.initial_page_ins;
        rt->counters.pl_page_cycles += cycles;
    }

    inference_begin = now_ticks(ops, ctx);
    rt->phase = P03_RT_LOAD_INPUT;
    if (ops->load_input(ctx) != 0)
        return fail(rt, ops, ctx, P03_RT_FAULT_INVALID_RUN_CONFIG);

    for (timestep = 0; timestep < rt->requested_timesteps; ++timestep) {
        uint8_t next_bank = (uint8_t)(1u - rt->current_event_bank);
        rt->phase = P03_RT_TIMESTEP_BEGIN;
        rt->completed_count = 0;
        rt->pending_packets = 0;
        memset(rt->completed, 0, sizeof(rt->completed));

        for (k = 0; k < rt->core_count; ++k) {
            uint8_t id = rt->logical_ids[k];
            int resident_slot;
            uint32_t emitted = 0;
            uint32_t committed = 0;
            uint64_t cycles = 0;
            uint64_t t0;

            rt->phase = P03_RT_SELECT_LOGICAL_CORE;
            if (rt->completed[k])
                return fail(rt, ops, ctx, P03_RT_FAULT_CONTROL_PROTOCOL);

            rt->phase = P03_RT_ENSURE_RESIDENT;
            resident_slot = find_resident(rt, id);
            if (resident_slot == P03_RT_EMPTY_SLOT) {
                int16_t victim_id;
                slot = rt->next_victim_slot;
                rt->next_victim_slot = (uint8_t)((slot + 1u) % rt->slot_count);
                victim_id = rt->resident[slot];

                if (victim_id != P03_RT_EMPTY_SLOT && rt->dirty[slot]) {
                    rt->phase = P03_RT_SAVE_VICTIM;
                    cycles = 0;
                    if (ops->page_out(ctx, (uint8_t)victim_id, slot,
                                      &cycles) != 0)
                        return fail(rt, ops, ctx, P03_RT_FAULT_PAGE_ERROR);
                    rt->dirty[slot] = 0;
                    ++rt->counters.page_outs;
                    rt->counters.pl_page_cycles += cycles;
                }
                rt->phase = P03_RT_LOAD_REQUESTED;
                cycles = 0;
                if (ops->page_in(ctx, id, slot, &cycles) != 0)
                    return fail(rt, ops, ctx, P03_RT_FAULT_PAGE_ERROR);
                if (victim_id != P03_RT_EMPTY_SLOT)
                    ++rt->counters.evictions;
                rt->resident[slot] = (int16_t)id;
                rt->dirty[slot] = 0;
                ++rt->counters.page_ins;
                rt->counters.pl_page_cycles += cycles;
                resident_slot = slot;
            } else {
                ++rt->counters.page_hits;
            }

            rt->phase = P03_RT_DISPATCH_CORE;
            cycles = 0;
            if (ops->dispatch(ctx, id, (uint8_t)resident_slot, timestep,
                              rt->current_event_bank, &emitted, &cycles) != 0)
                return fail(rt, ops, ctx, P03_RT_FAULT_DISPATCH_ERROR);
            if (emitted > P03_RT_MAX_PACKETS)
                return fail(rt, ops, ctx, P03_RT_FAULT_EVENT_OVERFLOW);
            rt->dirty[resident_slot] = 1; /* Conservative mutable ownership */
            ++rt->counters.logical_dispatches;
            rt->counters.pl_dispatch_cycles += cycles;
            rt->pending_packets = emitted;

            rt->phase = P03_RT_DRAIN_AND_ROUTE_PACKETS;
            t0 = now_ticks(ops, ctx);
            if (ops->drain_route(ctx, id, emitted, timestep,
                                 next_bank, &committed) != 0)
                return fail(rt, ops, ctx, P03_RT_FAULT_PACKET_FORMAT);
            rt->counters.ps_route_ticks += now_ticks(ops, ctx) - t0;
            if (committed > emitted)
                return fail(rt, ops, ctx, P03_RT_FAULT_PACKET_FORMAT);
            rt->pending_packets -= committed;
            rt->counters.routed_packets += committed;
            if (rt->pending_packets != 0)
                return fail(rt, ops, ctx, P03_RT_FAULT_BARRIER_INCOMPLETE);
            if (committed != 0) {
                /* NEXT-event insertion may mutate *any* resident slot,
                 * not just the dispatched source. Until P03.3b exposes
                 * per-destination dirty acknowledgments, conservatively
                 * save every resident victim before its later eviction.
                 */
                uint8_t r;
                for (r = 0; r < rt->slot_count; ++r)
                    if (rt->resident[r] != P03_RT_EMPTY_SLOT)
                        rt->dirty[r] = 1;
            }

            rt->phase = P03_RT_MARK_LOGICAL_CORE_COMPLETE;
            rt->completed[k] = 1;
            ++rt->completed_count;
        }

        rt->phase = P03_RT_BARRIER_CHECK;
        if (rt->completed_count != rt->core_count ||
            rt->pending_packets != 0)
            return fail(rt, ops, ctx, P03_RT_FAULT_BARRIER_INCOMPLETE);
        {
            uint64_t t0 = now_ticks(ops, ctx);
            if (ops->barrier_ready(ctx, timestep, next_bank) != 0)
                return fail(rt, ops, ctx, P03_RT_FAULT_BARRIER_INCOMPLETE);
            rt->counters.ps_barrier_ticks += now_ticks(ops, ctx) - t0;
        }
        ++rt->counters.barriers;
        rt->phase = P03_RT_SWAP_EVENT_BANKS;
        rt->current_event_bank = next_bank;

        rt->phase = P03_RT_ADVANCE_TIMESTEP;
        ++rt->counters.timesteps_completed;
        rt->current_timestep = timestep + 1u;
    }

    rt->phase = P03_RT_FINALIZE;
    rt->counters.ps_inference_ticks = now_ticks(ops, ctx) - inference_begin;
    rt->counters.ps_control_ticks = now_ticks(ops, ctx) - control_begin;
    rt->phase = P03_RT_WRITE_RESULT;
    if (ops->write_result(ctx, rt) != 0)
        return fail(rt, ops, ctx, P03_RT_FAULT_CONTROL_PROTOCOL);
    rt->phase = P03_RT_DONE;
    return 0;
}
