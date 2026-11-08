#include "m05_integrated.hpp"
#include <cstdint>
#include <iostream>

// Run genuine Vitis CSim and C/RTL co-sim against a small independent trace.
// Extended M02 dense/event oracle parity is exercised by Python native tests.
static bool self_recurrence() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, -1});
    ss.write({0, 0, 3, 1});
    es.write({0, 0, 5});
    std::uint32_t result = m05_integrated_replay(
        ns, ss, es, trace, 1, 1, 1, 4, 1, 1);
    if (result != M05_INT_OK) return false;
    // t0 spike-> reset -1; t1 -1+3=2; t2 2; t3 2.
    const std::int32_t expected[] = {-1, 2, 2, 2};
    const std::uint8_t spiked[] = {1, 0, 0, 0};
    const std::uint32_t counts[] = {1, 1, 0, 0};
    for (std::uint32_t t = 0; t < 4; ++t) {
        if (trace.empty()) return false;
        M05IntegratedTraceEntry x = trace.read();
        if (x.tick != t || x.neuron_id != 0 ||
            x.voltage != expected[t] || x.spike != spiked[t] ||
            x.evaluated != 1 || x.delivered_count != counts[t]) return false;
    }
    return trace.empty();
}
static bool two_neuron_signed_delayed_trace() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, -2});
    ns.write({-3, 1, 6, 0});
    ss.write({0, 0, -3, 1}); // self recurrence
    ss.write({0, 0, 4, 2});  // parallel self recurrence
    ss.write({0, 1, 6, 1});
    ss.write({1, 0, -2, 3});
    es.write({0, 0, 5}); // inclusive threshold
    es.write({0, 1, 0}); // zero still touched
    es.write({1, 0, 0}); // zero + recurrent arrival
    es.write({2, 1, -2});
    es.write({3, 1, 5});
    const std::uint32_t status = m05_integrated_replay(
        ns, ss, es, trace, 2, 4, 5, 6, 1, 2);
    if (status != M05_INT_OK) return false;
    // Independently precalculated dense M02 contract: tick-major order,
    // post-commit voltages, spikes and individual delivery counts.
    const std::int32_t voltages[6][2] = {
        {-2, 0}, {-4, 0}, {2, -1}, {1, 0}, {-2, 1}, {-1, 1}
    };
    const std::uint8_t spikes[6][2] = {
        {1, 0}, {0, 1}, {0, 0}, {0, 1}, {0, 0}, {0, 0}
    };
    const std::uint32_t counts[6] = {2, 3, 2, 1, 1, 0};
    for (std::uint32_t t = 0; t < 6; ++t) {
        for (std::uint32_t i = 0; i < 2; ++i) {
            if (trace.empty()) return false;
            const M05IntegratedTraceEntry x = trace.read();
            if (x.tick != t || x.neuron_id != i ||
                x.voltage != voltages[t][i] || x.spike != spikes[t][i] ||
                x.evaluated != 1 || x.delivered_count != counts[t]) return false;
        }
    }
    return trace.empty();
}
static bool reject_without_partial_trace() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    ns.write({0, 0, 5, 0});
    for (std::uint32_t j = 0; j < 4097; ++j) es.write({0, 0, 0});
    std::uint32_t result = m05_integrated_replay(
        ns, ss, es, trace, 1, 0, 4097, 1, 1, 1);
    return result == M05_INT_DELIVERY_OVERFLOW && trace.empty();
}
int main() {
    // A full successful run after a previous failed run must not see stale
    // state or queued future events (fresh-run logical reset).
    if (!self_recurrence() || !two_neuron_signed_delayed_trace() ||
        !reject_without_partial_trace() || !self_recurrence()) {
        std::cerr << "FAIL: M05 integrated temporal CSim vectors\n";
        return 1;
    }
    std::cout << "PASS: M05 integrated temporal CSim oracle vectors (native or Vitis)\n";
    return 0;
}
