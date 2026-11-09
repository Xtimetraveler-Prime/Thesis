#include "m05_rolling.hpp"
#include <limits>

// The temporal wheel has at most 4096 individual signed-W16 deliveries
// across ALL neurons in one logical tick (external + recurrent, even zero).
// Therefore every legal intermediate per-neuron sum, for ANY arrival order,
// fits the closed interval [-4096*32768, +4096*32767]. In particular, the
// negative endpoint is -2^27 and the positive endpoint is below +2^27.
// A signed 32-bit BRAM cell is exact without changing the 64-bit M04 API.
// A future change to per-tick admission or term width MUST revisit this proof.
constexpr std::int64_t M05_ROLL_MIN_CURRENT =
    -static_cast<std::int64_t>(M05_INT_MAX_PER_TICK) * 32768;
constexpr std::int64_t M05_ROLL_MAX_CURRENT =
    static_cast<std::int64_t>(M05_INT_MAX_PER_TICK) * 32767;
static_assert(M05_ROLL_MIN_CURRENT >=
              std::numeric_limits<std::int32_t>::min(), "wheel underflows i32");
static_assert(M05_ROLL_MAX_CURRENT <=
              std::numeric_limits<std::int32_t>::max(), "wheel overflows i32");

// A rolling wheel of 8 exact signed-i32 aggregate buckets reuses BRAM irrespective
// of run length. This is one autonomous HLS-oriented neural-run top, with no
// Python/PS service per logical tick. Individual deliveries are COUNTED
// independently from aggregate/touch, even when zero or canceling.
// The emitted trace is speculative until the final successful return status.
std::uint32_t m05_rolling_replay(
    hls::stream<M05IntegratedNeuron> &neurons,
    hls::stream<M05IntegratedSynapse> &synapses,
    hls::stream<M05IntegratedExternal> &external_events,
    hls::stream<M05IntegratedTraceEntry> &trace,
    std::uint32_t neuron_count,
    std::uint32_t synapse_count,
    std::uint32_t external_count,
    std::uint32_t ticks,
    std::uint32_t decay_num,
    std::uint32_t decay_den) {
#pragma HLS INTERFACE axis port=neurons
#pragma HLS INTERFACE axis port=synapses
#pragma HLS INTERFACE axis port=external_events
#pragma HLS INTERFACE axis port=trace
#pragma HLS INTERFACE s_axilite port=neuron_count bundle=control
#pragma HLS INTERFACE s_axilite port=synapse_count bundle=control
#pragma HLS INTERFACE s_axilite port=external_count bundle=control
#pragma HLS INTERFACE s_axilite port=ticks bundle=control
#pragma HLS INTERFACE s_axilite port=decay_num bundle=control
#pragma HLS INTERFACE s_axilite port=decay_den bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    if (neuron_count == 0 || neuron_count > M05_INT_MAX_NEURONS ||
        synapse_count > M05_INT_MAX_SYNAPSES ||
        external_count > M05_ROLLING_MAX_EXTERNAL ||
        ticks == 0 || ticks > M05_ROLLING_MAX_TICKS ||
        decay_den == 0 || decay_num > decay_den) {
        return M05_ROLL_BAD_SHAPE;
    }

    static std::int16_t voltage[M05_INT_MAX_NEURONS];
    static std::int16_t bias[M05_INT_MAX_NEURONS];
    static std::int16_t threshold[M05_INT_MAX_NEURONS];
    static std::int16_t reset[M05_INT_MAX_NEURONS];
    static std::int32_t head[M05_INT_MAX_NEURONS];
    static std::int32_t next_edge[M05_INT_MAX_SYNAPSES];
    static std::uint32_t post[M05_INT_MAX_SYNAPSES];
    static std::int16_t weight[M05_INT_MAX_SYNAPSES];
    static std::uint8_t delay[M05_INT_MAX_SYNAPSES];

    static std::int32_t current[M05_ROLLING_SLOTS][M05_INT_MAX_NEURONS];
    static std::uint8_t touched[M05_ROLLING_SLOTS][M05_INT_MAX_NEURONS];
    static std::uint32_t delivery_count[M05_ROLLING_SLOTS];
    static std::int16_t tick_voltage[M05_INT_MAX_NEURONS];
    static std::uint8_t tick_spike[M05_INT_MAX_NEURONS];
    static std::uint8_t tick_evaluated[M05_INT_MAX_NEURONS];
#pragma HLS BIND_STORAGE variable=voltage type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=bias type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=threshold type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=reset type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=current type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=touched type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=tick_voltage type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=tick_spike type=ram_2p impl=bram

    // Fresh logical run every invocation; no reliance on power-on BRAM
    // contents. Reset only the *admitted* neuron IDs. ID >= neuron_count
    // cannot be accessed in this run: all external destinations, synapse
    // endpoints and worklist traversal are individually range checked.
    // When a later run admits MORE neurons, its larger initialization
    // footprint cleans those previously inaccessible RAM rows as well.
    // This avoids 8*1024 unconditional current/touch clears for tiny runs.
    // Do not remove the per-tick wheel-slot clear below: the t+8 alias
    // must be released before scheduling recurrent spikes with delay==8.
    for (std::uint32_t slot = 0; slot < M05_ROLLING_SLOTS; ++slot) {
        delivery_count[slot] = 0;
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            current[slot][i] = 0;
            touched[slot][i] = 0;
        }
    }
    for (std::uint32_t i = 0; i < neuron_count; ++i) {
        head[i] = -1;
    }
    for (std::uint32_t i = 0; i < neuron_count; ++i) {
        const M05IntegratedNeuron p = neurons.read();
        if (p.initial_voltage < -32768 || p.initial_voltage > 32767 ||
            p.bias < -32768 || p.bias > 32767 ||
            p.threshold <= 0 || p.threshold > 32767 ||
            p.reset_voltage < -32768 || p.reset_voltage > 32767 ||
            p.reset_voltage >= p.threshold) {
            return M05_ROLL_BAD_NEURON;
        }
        voltage[i] = static_cast<std::int16_t>(p.initial_voltage);
        bias[i] = static_cast<std::int16_t>(p.bias);
        threshold[i] = static_cast<std::int16_t>(p.threshold);
        reset[i] = static_cast<std::int16_t>(p.reset_voltage);
    }
    // Linked adjacency; parallel and recurrent self-edges are independent.
    for (std::uint32_t j = 0; j < synapse_count; ++j) {
        const M05IntegratedSynapse e = synapses.read();
        if (e.pre >= neuron_count || e.post >= neuron_count ||
            e.weight < -32768 || e.weight > 32767 ||
            e.delay == 0 || e.delay > M05_ROLLING_MAX_DELAY) {
            return M05_ROLL_BAD_SYNAPSE;
        }
        next_edge[j] = head[e.pre];
        head[e.pre] = static_cast<std::int32_t>(j);
        post[j] = e.post;
        weight[j] = static_cast<std::int16_t>(e.weight);
        delay[j] = static_cast<std::uint8_t>(e.delay);
    }

    // One-element lookahead permits sorted future input without preloading
    // the full external horizon into on-chip storage. This is a FUNCTIONAL
    // ordering contract; live ready/valid stalls are not yet characterized.
    M05IntegratedExternal pending{};
    std::uint8_t have_pending = 0;
    std::uint32_t consumed = 0;

    for (std::uint32_t t = 0; t < ticks; ++t) {
        const std::uint32_t slot = t % M05_ROLLING_SLOTS;
        // Ingest *all* external arrivals for t, including zero deliveries.
        // Future events remain in the lookahead until their matching tick.
        while (have_pending || consumed < external_count) {
            if (!have_pending) {
                pending = external_events.read();
                ++consumed;
                have_pending = 1;
            }
            if (pending.tick >= ticks ||
                pending.neuron_id >= neuron_count ||
                pending.current < -32768 || pending.current > 32767 ||
                pending.tick < t) {
                return M05_ROLL_BAD_EXTERNAL;
            }
            if (pending.tick > t) break;
            if (delivery_count[slot] >= M05_INT_MAX_PER_TICK) {
                return M05_ROLL_DELIVERY_OVERFLOW;
            }
            ++delivery_count[slot];
            current[slot][pending.neuron_id] +=
                static_cast<std::int32_t>(pending.current);
            touched[slot][pending.neuron_id] = 1;
            have_pending = 0;
        }

        const std::uint32_t this_tick_deliveries = delivery_count[slot];
        // Evaluate all neurons using only current-tick aggregates. No same-
        // tick event propagation is possible because all delays are positive.
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            const std::uint8_t evaluate =
                (voltage[i] != 0 || bias[i] != 0 || touched[slot][i]) ? 1 : 0;
            std::uint8_t spike = 0;
            if (evaluate) {
                M04Request request{};
                request.neuron_id = i;
                request.neuron_count = neuron_count;
                request.tick = t;
                request.previous_voltage = voltage[i];
                // Sign-extend the exact i32 aggregate for unchanged M04 i64
                // request semantics; do NOT saturate per contribution.
                request.aggregated_current =
                    static_cast<std::int64_t>(current[slot][i]);
                request.bias = bias[i];
                request.threshold = threshold[i];
                request.reset_voltage = reset[i];
                request.state_bits = 16;
                request.decay_num = decay_num;
                request.decay_den = decay_den;
                M04Response response{};
                m04_eval_one(request, response);
                if (response.status != M04_OK) return M05_ROLL_LIF_ERROR;
                voltage[i] = static_cast<std::int16_t>(response.next_voltage);
                spike = response.spike;
            }
            tick_voltage[i] = voltage[i];
            tick_spike[i] = spike;
            tick_evaluated[i] = evaluate;
        }

        // Release t's wheel slot BEFORE routing spikes. Crucial when delay
        // == 8: future t+8 aliases this exact physical BRAM slot.
        delivery_count[slot] = 0;
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            current[slot][i] = 0;
            touched[slot][i] = 0;
        }
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            if (!tick_spike[i]) continue;
            for (std::int32_t edge = head[i]; edge != -1;
                 edge = next_edge[edge]) {
                const std::uint32_t future = t + delay[edge];
                if (future >= ticks) continue;
                const std::uint32_t future_slot =
                    future % M05_ROLLING_SLOTS;
                if (delivery_count[future_slot] >= M05_INT_MAX_PER_TICK) {
                    return M05_ROLL_DELIVERY_OVERFLOW;
                }
                ++delivery_count[future_slot];
                const std::uint32_t dest = post[edge];
                current[future_slot][dest] +=
                    static_cast<std::int32_t>(weight[edge]);
                touched[future_slot][dest] = 1;
            }
        }
        // Publish the tick only after its recurrence fanout checks pass.
        // A late failure invalidates ALL earlier streamed rows as a run.
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            M05IntegratedTraceEntry out{};
            out.tick = t;
            out.neuron_id = i;
            out.voltage = tick_voltage[i];
            out.spike = tick_spike[i];
            out.evaluated = tick_evaluated[i];
            out.delivered_count = this_tick_deliveries;
            trace.write(out);
        }
    }
    return M05_ROLL_OK;
}
