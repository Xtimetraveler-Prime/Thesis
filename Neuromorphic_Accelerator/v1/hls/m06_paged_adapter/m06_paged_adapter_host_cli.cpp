// M06 NATIVE-ONLY adapter CLI. This is not an FPGA PS driver or AXI
// streamer. One stdin test case; exact unchanged M05 neural HLS top linked.
#include "m06_paged_adapter.hpp"
#include <cstdint>
#include <iostream>
#include <iomanip>
#include <vector>

int main() {
    std::uint32_t n=0, e=0, external=0, ticks=0, numerator=0, denominator=0,
                  slots=0;
    if (!(std::cin >> n >> e >> external >> ticks >> numerator >>
          denominator >> slots)) return 2;
    if (n > M05_INT_MAX_NEURONS || e > M05_INT_MAX_SYNAPSES ||
        external > M05_ROLLING_MAX_EXTERNAL) return 2;
    std::vector<M05IntegratedNeuron> cells;
    std::vector<M05IntegratedSynapse> edges;
    std::vector<M05IntegratedExternal> currents;
    cells.reserve(n);
    edges.reserve(e);
    currents.reserve(external);
    for (std::uint32_t i=0;i<n;++i) {
        M05IntegratedNeuron x{};
        if (!(std::cin >> x.initial_voltage >> x.bias >>
              x.threshold >> x.reset_voltage)) return 2;
        cells.push_back(x);
    }
    for (std::uint32_t i=0;i<e;++i) {
        M05IntegratedSynapse x{};
        if (!(std::cin >> x.pre >> x.post >> x.weight >> x.delay)) return 2;
        edges.push_back(x);
    }
    for (std::uint32_t i=0;i<external;++i) {
        M05IntegratedExternal x{};
        if (!(std::cin >> x.tick >> x.neuron_id >> x.current)) return 2;
        currents.push_back(x);
    }
    std::string junk;
    if (std::cin >> junk) return 2;
    const M06PagedReplayResult got = m06_paged_replay_with_m05_stream(
        cells,edges,currents,ticks,numerator,denominator,slots);
    std::cout << got.status << " " << got.trace.size() << "\n";
    for (const auto &line : got.trace) {
        std::cout << line.tick << " " << line.neuron_id << " " <<
            line.voltage << " " << static_cast<unsigned>(line.spike) << " " <<
            static_cast<unsigned>(line.evaluated) << " " <<
            line.delivered_count << "\n";
    }
    const auto &c = got.counters;
    std::cout << "CACHE " << c.page_accesses << " " << c.page_hits <<
        " " << c.page_misses << " " << c.evictions << " " <<
        c.dirty_writebacks << " " << c.fills << " " <<
        c.read_bytes << " " << c.written_bytes << " " <<
        c.m05_stream_calls << " " << c.evaluated << " " <<
        c.spike_count << "\n";
    // Independent TEST-ONLY byte snapshot. The cache implementation is
    // responsible for flushing dirty rows before the adapter returns.
    // Hex is NOT a physical DDR or AXI memory dump.
    std::cout << "STATE " << std::hex << std::setfill('0');
    for (const std::uint8_t byte : got.canonical_after_flush)
        std::cout << std::setw(2) << static_cast<unsigned>(byte);
    std::cout << "\n";
    return 0;
}
