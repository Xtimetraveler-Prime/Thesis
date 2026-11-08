#include "m05_integrated.hpp"
#include <cstdint>
#include <iostream>\n#include <string>

// Test adapter only. Input frames:
// N S E T DECAY_NUM DECAY_DEN
// N lines: initial_v bias threshold reset
// S lines: pre post weight delay
// E lines: tick neuron_id current
// Output first line: status emitted_trace_rows; subsequent rows:
// tick neuron voltage spike evaluated delivered_count
int main() {
    std::uint32_t n = 0, s = 0, e = 0, t = 0, dnum = 0, dden = 0;
    if (!(std::cin >> n >> s >> e >> t >> dnum >> dden))
        return 2;
    // Only load admissible payload sizes into host streams; for oversized
    // headers, call the actual HLS top to obtain its status without reads.
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> out;
    const bool shape = n != 0 && n <= M05_INT_MAX_NEURONS &&
                       s <= M05_INT_MAX_SYNAPSES &&
                       e <= M05_INT_MAX_EXTERNAL &&
                       t != 0 && t <= M05_INT_MAX_TICKS &&
                       dden != 0 && dnum <= dden;
    if (shape) {
        for (std::uint32_t i = 0; i < n; ++i) {
            M05IntegratedNeuron p{};
            if (!(std::cin >> p.initial_voltage >> p.bias >>
                  p.threshold >> p.reset_voltage)) return 2;
            ns.write(p);
        }
        for (std::uint32_t i = 0; i < s; ++i) {
            M05IntegratedSynapse edge{};
            if (!(std::cin >> edge.pre >> edge.post >>
                  edge.weight >> edge.delay)) return 2;
            ss.write(edge);
        }
        for (std::uint32_t i = 0; i < e; ++i) {
            M05IntegratedExternal x{};
            if (!(std::cin >> x.tick >> x.neuron_id >> x.current)) return 2;
            es.write(x);
        }
    }
    // Reject unconsumed fields instead of silently ignoring malformed framing.
    std::string extra;
    if (std::cin >> extra) return 2;
    std::uint32_t result = m05_integrated_replay(
        ns, ss, es, out, n, s, e, t, dnum, dden);
    const std::uint32_t rows = result == M05_INT_OK ? n * t : 0;
    std::cout << result << " " << rows << "\n";
    for (std::uint32_t i = 0; i < rows; ++i) {
        M05IntegratedTraceEntry x = out.read();
        std::cout << x.tick << " " << x.neuron_id << " "
                  << x.voltage << " " << unsigned(x.spike) << " "
                  << unsigned(x.evaluated) << " "
                  << x.delivered_count << "\n";
    }
    if (!out.empty()) return 3; // no extra output
    return 0;
}
