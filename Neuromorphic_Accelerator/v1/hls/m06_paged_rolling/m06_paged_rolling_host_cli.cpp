// HOST-NATIVE adapter for NEW M06 HLS candidate; NOT board, AXI timing,
// PS/DDR ownership, or generated Vitis RTL. Real implementation compiled
// from m06_paged_rolling.cpp and UNCHANGED accepted M04 arithmetic.
#include "m06_paged_rolling.hpp"
#include <cstdint>
#include <iomanip>
#include <iostream>
#include <string>
#include <vector>

int main() {
    // n edges inputs ticks decay_num decay_den resident_slots canonical_base
    std::uint32_t n=0, s=0, e=0, ticks=0, num=0, den=0, slots=0, base=0;
    if (!(std::cin>>n>>s>>e>>ticks>>num>>den>>slots>>base)) return 2;
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> trace;
    hls::stream<M06PageMetrics> stats;
    std::vector<std::uint32_t> canonical(
        M06_PAGED_MAX_LOGICAL_NEURONS*M06_PAGED_RECORD_WORDS,
        0xa5a5a5a5u);
    const bool bounded_input =
        n<=M05_INT_MAX_NEURONS && s<=M05_INT_MAX_SYNAPSES &&
        e<=M05_ROLLING_MAX_EXTERNAL;
    if (!bounded_input) return 2;
    for (std::uint32_t i=0;i<n;++i) {
        M05IntegratedNeuron x{};
        if (!(std::cin>>x.initial_voltage>>x.bias>>
              x.threshold>>x.reset_voltage)) return 2;
        ns.write(x);
    }
    for (std::uint32_t i=0;i<s;++i) {
        M05IntegratedSynapse x{};
        if (!(std::cin>>x.pre>>x.post>>x.weight>>x.delay)) return 2;
        ss.write(x);
    }
    for (std::uint32_t i=0;i<e;++i) {
        M05IntegratedExternal x{};
        if (!(std::cin>>x.tick>>x.neuron_id>>x.current)) return 2;
        es.write(x);
    }
    std::string extra;
    if (std::cin>>extra) return 2;
    const std::uint32_t status = m06_paged_rolling_replay(
        ns,ss,es,trace,stats,canonical.data(),canonical.data(),n,s,e,ticks,num,den,
        slots,base);
    const std::uint32_t count = (status==M06_PAGE_OK) ? n*ticks : 0;
    std::cout << status << " " << count << "\n";
    for (std::uint32_t i=0;i<count;++i) {
        if (trace.empty()) return 3;
        const auto row=trace.read();
        std::cout << row.tick << " " << row.neuron_id << " " <<
            row.voltage << " " << unsigned(row.spike) << " " <<
            unsigned(row.evaluated) << " " << row.delivered_count << "\n";
    }
    if (status==M06_PAGE_OK && (!trace.empty() || stats.empty())) return 3;
    if (status==M06_PAGE_OK) {
        const auto m=stats.read();
        if (!stats.empty()) return 3;
        std::cout << "CACHE " << m.page_accesses << " " << m.page_hits <<
            " " << m.page_misses << " " << m.page_evictions << " " <<
            m.dirty_writebacks << " " << m.page_fills << " " <<
            m.m05_evaluations << " " << m.emitted_spikes << "\n";
        std::cout << "STATE " << std::hex << std::setfill('0');
        for (std::uint32_t neuron=0;neuron<n;++neuron) {
            for (std::uint32_t w=0;w<4;++w) {
                const std::uint32_t val=canonical[(base+neuron)*4+w];
                for (std::uint32_t byte=0;byte<4;++byte)
                    std::cout << std::setw(2) <<
                        static_cast<unsigned>((val>>(byte*8))&255u);
            }
        }
        std::cout << std::dec << "\n";
    }
    // Outside selected M05 contiguous tile, including the final physical
    // 4095th neuron, no canonical word may be modified by this invocation.
    bool guard_ok=true;
    for (std::uint32_t neuron=0;neuron<M06_PAGED_MAX_LOGICAL_NEURONS;++neuron) {
        if (neuron>=base && neuron<base+n) continue;
        for (std::uint32_t w=0;w<4;++w) {
            if (canonical[neuron*4+w]!=0xa5a5a5a5u)
                guard_ok=false;
        }
    }
    std::cout << "GUARD " << (guard_ok ? "PASS" : "FAIL") << "\n";
    return guard_ok ? 0 : 4;
}
