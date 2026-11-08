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

int main() {
    if (!wheel_wrap_recurrent() ||
        !varying_network_sizes_across_runs() ||
        !later_overflow_invalidates_partial_stream() ||
        !wheel_wrap_recurrent()) {
        std::cerr << "FAIL: M05 rolling wheel temporal CSim vectors\n";
        return 1;
    }
    std::cout << "PASS: M05 rolling 8-slot wheel temporal CSim vectors"
              << " (native or Vitis)\n";
    return 0;
}
