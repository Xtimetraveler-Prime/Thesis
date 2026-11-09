#include "m05_rolling.hpp"
#include <cstdint>
#include <iostream>

// Independent golden trace for 20 ticks, crossing physical wheel aliases
// 0->8->16 while using exactly the same 8 slots.
static bool wheel_wrap_recurrent() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, 0});
    ss.write({0, 0, 5, 8});
    es.write({0, 0, 5});
    const std::uint32_t status =
        m05_rolling_replay(ns, ss, es, trace, 1, 1, 1, 20, 1, 1);
    if (status != M05_ROLL_OK) return false;
    for (std::uint32_t t = 0; t < 20; ++t) {
        if (trace.empty()) return false;
        const M05IntegratedTraceEntry x = trace.read();
        const std::uint8_t expected = (t % 8 == 0) ? 1 : 0;
        if (x.tick != t || x.neuron_id != 0 || x.voltage != 0 ||
            x.spike != expected || x.evaluated != expected ||
            x.delivered_count != expected) return false;
    }
    return trace.empty();
}

// On later external-event overflow, t=0 may already have been streamed;
// return status invalidates *every* record including t=0. A caller must not
// interpret partial output as a successful truncated network run.
static bool later_overflow_invalidates_partial_stream() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, 0});
    for (std::uint32_t i = 0; i < 4096; ++i) {
        ss.write({0, 0, 0, 1});
    }
    es.write({0, 0, 5});
    es.write({1, 0, 0});
    const std::uint32_t status =
        m05_rolling_replay(ns, ss, es, trace, 1, 4096, 2, 3, 1, 1);
    if (status != M05_ROLL_DELIVERY_OVERFLOW || trace.empty())
        return false;
    const M05IntegratedTraceEntry prefix = trace.read();
    return prefix.tick == 0 && prefix.spike == 1 && trace.empty();
}

// The top keeps BRAM statically across ap_start calls. A smaller logical run
// must not expose rows from the larger run; a subsequent larger run must
// initialize its newly active rows before they become observable.
static bool varying_network_sizes_across_runs() {
    for (std::uint32_t epoch = 0; epoch < 3; ++epoch) {
        hls::stream<M05IntegratedNeuron> ns;
        hls::stream<M05IntegratedSynapse> ss;
        hls::stream<M05IntegratedExternal> es;
        hls::stream<M05IntegratedTraceEntry> trace;
        const std::uint32_t count = epoch == 1 ? 1 : 2;
        ns.write({0, 0, 5, 0});
        if (count == 2) ns.write({0, 0, 5, 0});
        if (epoch == 0) {
            ss.write({1, 1, 5, 8});
            es.write({0, 1, 5});
        } else {
            es.write({0, 0, 0}); // zero delivery must still wake ID 0
        }
        const std::uint32_t status = m05_rolling_replay(
            ns, ss, es, trace, count, epoch == 0 ? 1 : 0,
            1, 11, 1, 1);
        if (status != M05_ROLL_OK) return false;
        for (std::uint32_t t = 0; t < 11; ++t) {
            for (std::uint32_t i = 0; i < count; ++i) {
                if (trace.empty()) return false;
                const M05IntegratedTraceEntry x = trace.read();
                const std::uint8_t spike =
                    (epoch == 0 && i == 1 && (t == 0 || t == 8)) ? 1 : 0;
                const std::uint8_t evaluated =
                    epoch == 0 ? spike : (t == 0 && i == 0 ? 1 : 0);
                const std::uint32_t delivered =
                    t == 0 || (epoch == 0 && t == 8) ? 1 : 0;
                if (x.tick != t || x.neuron_id != i || x.voltage != 0 ||
                    x.spike != spike || x.evaluated != evaluated ||
                    x.delivered_count != delivered) return false;
            }
        }
        if (!trace.empty()) return false;
    }
    return true;
}

// This genuine-Vitis-ready regression exercises the full 64-tick supported
// horizon, multiple wheel wraps and signed recurrent event coalescing.
// Golden values are computed by a SMALL INDEPENDENT dense-tick oracle in
// the TESTBENCH ONLY (never compiled as a synthesis source).
// It intentionally does not use m04_eval_one or the rolling scheduler.
static bool dense_oracle_64_tick_mixed_network() {
    const M05IntegratedNeuron params[2] = {
        {-3, 1, 6, -2}, {0, 0, 4, 0}
    };
    const M05IntegratedSynapse edges[5] = {
        {0, 0, 2, 8}, {0, 1, 5, 1}, {0, 1, -3, 1},
        {1, 0, -4, 3}, {1, 1, 4, 8}
    };
    const M05IntegratedExternal events[10] = {
        {0, 0, 7}, {0, 0, -2}, {0, 1, 4},
        {7, 0, 6}, {8, 1, -1}, {15, 0, 12},
        {16, 1, 4}, {32, 0, 7}, {55, 1, 4}, {63, 0, 0}
    };
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    for (std::uint32_t i = 0; i < 2; ++i) ns.write(params[i]);
    for (std::uint32_t i = 0; i < 5; ++i) ss.write(edges[i]);
    for (std::uint32_t i = 0; i < 10; ++i) es.write(events[i]);
    if (m05_rolling_replay(ns, ss, es, trace, 2, 5, 10, 64, 1, 2) !=
        M05_ROLL_OK) return false;

    std::int32_t v[2] = {-3, 0};
    std::uint8_t spike_at[64][2] = {};
    for (std::uint32_t tick = 0; tick < 64; ++tick) {
        std::int64_t arrivals[2] = {0, 0};
        std::uint8_t touched[2] = {0, 0};
        std::uint32_t count = 0;
        // Deliberately scan ALL external records and edges, independent of
        // the device's streaming lookahead and adjacency list/wheel.
        for (std::uint32_t j = 0; j < 10; ++j) {
            if (events[j].tick == tick) {
                arrivals[events[j].neuron_id] += events[j].current;
                touched[events[j].neuron_id] = 1;
                ++count;
            }
        }
        for (std::uint32_t j = 0; j < 5; ++j) {
            const M05IntegratedSynapse edge = edges[j];
            if (tick >= edge.delay &&
                spike_at[tick - static_cast<std::uint32_t>(edge.delay)]
                        [edge.pre] != 0) {
                arrivals[edge.post] += edge.weight;
                touched[edge.post] = 1;
                ++count;
            }
        }
        for (std::uint32_t neuron = 0; neuron < 2; ++neuron) {
            const std::uint8_t evaluated =
                (v[neuron] != 0 || params[neuron].bias != 0 ||
                 touched[neuron] != 0) ? 1 : 0;
            std::uint8_t spike = 0;
            if (evaluated) {
                // Independent signed truncation toward zero.
                const std::int64_t product = std::int64_t(v[neuron]);
                const std::int64_t leak = product < 0
                    ? -((-product) / 2) : product / 2;
                std::int64_t candidate = leak +
                    std::int64_t(params[neuron].bias) + arrivals[neuron];
                if (candidate < -32768) candidate = -32768;
                if (candidate > 32767) candidate = 32767;
                spike = candidate >= params[neuron].threshold ? 1 : 0;
                v[neuron] = spike ? params[neuron].reset_voltage :
                    static_cast<std::int32_t>(candidate);
            }
            spike_at[tick][neuron] = spike;
            if (trace.empty()) return false;
            const M05IntegratedTraceEntry result = trace.read();
            if (result.tick != tick || result.neuron_id != neuron ||
                result.voltage != v[neuron] ||
                result.spike != spike || result.evaluated != evaluated ||
                result.delivered_count != count) {
                std::cerr << "M05 rolling dense-oracle mismatch tick="
                          << tick << " neuron=" << neuron << "\\n";
                return false;
            }
        }
    }
    return trace.empty();
}

// Bad external order is only detected when the lookahead is consumed.
// Earlier speculative AXIS rows can exist; they MUST be rejected by any
// real receiver when final status != M05_ROLL_OK.
static bool late_bad_external_invalidates_prefix() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, 0});
    es.write({0, 0, 0});
    es.write({3, 0, 5});
    es.write({1, 0, 1}); // out-of-order behind the lookahead tick
    const std::uint32_t status =
        m05_rolling_replay(ns, ss, es, trace, 1, 0, 3, 8, 1, 1);
    if (status != M05_ROLL_BAD_EXTERNAL) return false;
    for (std::uint32_t tick = 0; tick < 3; ++tick) {
        if (trace.empty()) return false;
        const M05IntegratedTraceEntry x = trace.read();
        if (x.tick != tick || x.neuron_id != 0 ||
            x.voltage != 0 || x.spike != 0 ||
            x.evaluated != (tick == 0 ? 1 : 0) ||
            x.delivered_count != (tick == 0 ? 1u : 0u)) return false;
    }
    return trace.empty();
}

// Exact arithmetic extremes for the i32 temporal-current BRAM candidate.
// Each tick is admitted with precisely 4096 signed W16 contributions; the
// *unclipped* sums are +134213632 and -134217728, respectively. One clipped
// LIF update follows the whole signed sum, never per-arrival clipping.
static bool all_positive_and_negative_4096_arrivals() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, 0});
    for (std::uint32_t i = 0; i < 4096; ++i) {
        es.write({0, 0, 32767});
    }
    for (std::uint32_t i = 0; i < 4096; ++i) {
        es.write({8, 0, -32768});
    }
    if (m05_rolling_replay(ns, ss, es, trace, 1, 0, 8192, 9, 1, 1)
        != M05_ROLL_OK) return false;
    for (std::uint32_t t = 0; t < 9; ++t) {
        if (trace.empty()) return false;
        const M05IntegratedTraceEntry x = trace.read();
        const std::int32_t expected_voltage = t == 8 ? -32768 : 0;
        const std::uint8_t expected_spike = t == 0 ? 1 : 0;
        const std::uint8_t expected_evaluated =
            (t == 0 || t == 8) ? 1 : 0;
        const std::uint32_t expected_deliveries =
            (t == 0 || t == 8) ? 4096u : 0u;
        if (x.tick != t || x.neuron_id != 0 ||
            x.voltage != expected_voltage ||
            x.spike != expected_spike ||
            x.evaluated != expected_evaluated ||
            x.delivered_count != expected_deliveries) return false;
    }
    return trace.empty();
}

// Positive-delay recurrence also uses the same i32 future-current wheel.
// 4096 independent parallel synapses fire into ID 1 at t+8. There must be
// no BRAM-slot alias corruption when t==8 reuses the physical slot of t==0.
static bool all_negative_4096_delayed_synapses() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, 0});
    ns.write({0, 0, 5, 0});
    for (std::uint32_t i = 0; i < 4096; ++i) {
        ss.write({0, 1, -32768, 8});
    }
    es.write({0, 0, 5});
    if (m05_rolling_replay(ns, ss, es, trace, 2, 4096, 1, 9, 1, 1)
        != M05_ROLL_OK) return false;
    for (std::uint32_t t = 0; t < 9; ++t) {
        for (std::uint32_t i = 0; i < 2; ++i) {
            if (trace.empty()) return false;
            const M05IntegratedTraceEntry x = trace.read();
            const bool source_spike = t == 0 && i == 0;
            const bool negative_delivery = t == 8 && i == 1;
            const std::int32_t voltage = negative_delivery ? -32768 : 0;
            const std::uint8_t evaluated =
                (source_spike || negative_delivery) ? 1 : 0;
            const std::uint32_t deliveries =
                t == 0 ? 1u : (t == 8 ? 4096u : 0u);
            if (x.tick != t || x.neuron_id != i ||
                x.voltage != voltage ||
                x.spike != (source_spike ? 1 : 0) ||
                x.evaluated != evaluated ||
                x.delivered_count != deliveries) return false;
        }
    }
    return trace.empty();
}

int main() {
    if (!wheel_wrap_recurrent() ||
        !all_positive_and_negative_4096_arrivals() ||
        !all_negative_4096_delayed_synapses() ||
        !dense_oracle_64_tick_mixed_network() ||
        !varying_network_sizes_across_runs() ||
        !later_overflow_invalidates_partial_stream() ||
        !late_bad_external_invalidates_prefix() ||
        !wheel_wrap_recurrent()) {
        std::cerr << "FAIL: M05 rolling wheel temporal CSim vectors\n";
        return 1;
    }
    std::cout << "PASS: M05 rolling 8-slot wheel temporal CSim vectors"
              << " (native or Vitis)\n";
    return 0;
}
