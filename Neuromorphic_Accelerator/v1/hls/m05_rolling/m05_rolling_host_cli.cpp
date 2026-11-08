#include "m05_rolling.hpp"
#include <cstdint>
#include <iostream>
#include <string>

// NATIVE TEST ADAPTER ONLY, NOT PS/AXI driver.
// Header: n edges ext ticks decay_num decay_den
// n rows: initial_v bias threshold reset
// edges rows: pre post weight delay (delay 1..8)
// ext rows: tick neuron current (sorted nondecreasing by tick)
// First output: status accepted_rows. On ANY nonzero final status, discard
// every speculative prior AXIS trace row; print status and 0 rows.
int main() {
    std::uint32_t n = 0, s = 0, e = 0, ticks = 0, num = 0, den = 0;
    if (!(std::cin >> n >> s >> e >> ticks >> num >> den)) return 2;
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> out;
    const bool valid_shape =
        n != 0 && n <= M05_INT_MAX_NEURONS &&
        s <= M05_INT_MAX_SYNAPSES &&
        e <= M05_ROLLING_MAX_EXTERNAL &&
        ticks != 0 && ticks <= M05_ROLLING_MAX_TICKS &&
        den != 0 && num <= den;
    if (valid_shape) {
        for (std::uint32_t i = 0; i < n; ++i) {
            M05IntegratedNeuron v{};
            if (!(std::cin >> v.initial_voltage >> v.bias >>
                  v.threshold >> v.reset_voltage)) return 2;
            ns.write(v);
        }
        for (std::uint32_t i = 0; i < s; ++i) {
            M05IntegratedSynapse v{};
            if (!(std::cin >> v.pre >> v.post >> v.weight >> v.delay))
                return 2;
            ss.write(v);
        }
        for (std::uint32_t i = 0; i < e; ++i) {
            M05IntegratedExternal v{};
            if (!(std::cin >> v.tick >> v.neuron_id >> v.current))
                return 2;
            es.write(v);
        }
        std::string unexpected;
        if (std::cin >> unexpected) return 2;
    }
    const std::uint32_t status = m05_rolling_replay(
        ns, ss, es, out, n, s, e, ticks, num, den);
    const std::uint32_t rows = status == M05_ROLL_OK ? n * ticks : 0;
    std::cout << status << " " << rows << "\n";
    for (std::uint32_t i = 0; i < rows; ++i) {
        const M05IntegratedTraceEntry x = out.read();
        std::cout << x.tick << " " << x.neuron_id << " " << x.voltage
                  << " " << unsigned(x.spike) << " "
                  << unsigned(x.evaluated) << " "
                  << x.delivered_count << "\n";
    }
    if (status == M05_ROLL_OK && !out.empty()) return 3;
    return 0;
}
