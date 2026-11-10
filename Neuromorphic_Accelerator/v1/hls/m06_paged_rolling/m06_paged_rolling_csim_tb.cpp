// Vitis HLS C simulation, plus native g++ fallback; the production
// synthesis sources are ONLY m06_paged_rolling.cpp + accepted m04_eval.cpp.
#include "m06_paged_rolling.hpp"
#include <cstdint>
#include <iostream>
#include <vector>

static bool wheel_and_high_address() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> out;
    hls::stream<M06PageMetrics> metrics;
    std::vector<std::uint32_t> memory(
        M06_PAGED_MAX_LOGICAL_NEURONS*M06_PAGED_RECORD_WORDS,0xa5a5a5a5u);
    for (int i=0;i<16;++i) ns.write({0,0,5,0});
    ss.write({0,0,5,8});
    es.write({0,0,5});
    const std::uint32_t status=m06_paged_rolling_replay(
        ns,ss,es,out,metrics,memory.data(),memory.data(),16,1,1,20,1,1,1,4080);
    if (status!=M06_PAGE_OK || metrics.empty()) {
        std::cerr<<"M06_HLS_CSIM_DIAG high_offset status="<<status
                 <<" metrics_empty="<<metrics.empty()<<"\n";
        return false;
    }
    for (std::uint32_t t=0;t<20;++t) {
        for (std::uint32_t i=0;i<16;++i) {
            if (out.empty()) {
                std::cerr<<"M06_HLS_CSIM_DIAG high_offset trace_underflow tick="
                         <<t<<" neuron="<<i<<"\n";
                return false;
            }
            const auto x=out.read();
            const bool spike=(i==0 && t%8==0);
            if (x.tick!=t || x.neuron_id!=i || x.voltage!=0 ||
                x.spike!=spike || x.evaluated!=spike ||
                x.delivered_count!=((t%8==0)?1u:0u)) {
                std::cerr<<"M06_HLS_CSIM_DIAG high_offset trace_mismatch tick="
                         <<t<<" neuron="<<i<<" got_tick="<<x.tick
                         <<" got_id="<<x.neuron_id<<" got_v="<<x.voltage
                         <<" got_spike="<<static_cast<unsigned>(x.spike)<<" expected_spike="<<spike
                         <<" got_evaluated="<<static_cast<unsigned>(x.evaluated)
                         <<" got_delivered="<<x.delivered_count<<"\n";
                return false;
            }
        }
    }
    if (!out.empty()) {
        std::cerr<<"M06_HLS_CSIM_DIAG high_offset trace_overflow\n";
        return false;
    }
    const auto m=metrics.read();
    if (!metrics.empty() || m.page_fills!=1 ||
        m.dirty_writebacks!=1 || m.m05_evaluations!=3 ||
        m.emitted_spikes!=3) {
        std::cerr<<"M06_HLS_CSIM_DIAG high_offset bad_metrics fills="
                 <<m.page_fills<<" dirty_writebacks="<<m.dirty_writebacks
                 <<" evaluations="<<m.m05_evaluations
                 <<" spikes="<<m.emitted_spikes<<" extra_metrics="
                 <<!metrics.empty()<<"\n";
        return false;
    }
    const std::uint32_t base=4080*4;
    if (memory[base]!=0 || memory[base+1]!=17 ||
        memory[base+2]!=0 || memory[base+3]!=0) {
        std::cerr<<"M06_HLS_CSIM_DIAG high_offset canonical_image_mismatch"
                 <<" v="<<memory[base]<<" last_tick="<<memory[base+1]
                 <<" reserved2="<<memory[base+2]
                 <<" reserved3="<<memory[base+3]<<"\n";
        return false;
    }
    if (memory[(4080-1)*4]!=0xa5a5a5a5u ||
        memory[4095*4]!=0) {
        std::cerr<<"M06_HLS_CSIM_DIAG high_offset guard_before="
                 <<memory[(4080-1)*4]<<" final_voltage_word="
                 <<memory[4095*4]<<"\n";
        return false;
    }
    return true;
}

static bool dirty_evict_then_delayed_replay() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> out;
    hls::stream<M06PageMetrics> metrics;
    std::vector<std::uint32_t> memory(
        M06_PAGED_MAX_LOGICAL_NEURONS*M06_PAGED_RECORD_WORDS,0xa5a5a5a5u);
    for (int i=0;i<32;++i) ns.write({0,0,5,0});
    ss.write({0,0,5,8});
    es.write({0,0,5});
    es.write({1,16,5});
    const std::uint32_t status=m06_paged_rolling_replay(
        ns,ss,es,out,metrics,memory.data(),memory.data(),32,1,2,12,1,1,1,0);
    if (status!=M06_PAGE_OK || metrics.empty()) {
        std::cerr<<"M06_HLS_CSIM_DIAG dirty_evict status="<<status
                 <<" metrics_empty="<<metrics.empty()<<"\n";
        return false;
    }
    std::uint32_t spikes=0;
    for (std::uint32_t t=0;t<12;++t) {
        for (std::uint32_t i=0;i<32;++i) {
            if (out.empty()) {
                std::cerr<<"M06_HLS_CSIM_DIAG dirty_evict trace_underflow tick="
                         <<t<<" neuron="<<i<<"\n";
                return false;
            }
            const auto x=out.read();
            const bool spike=(i==0&&(t==0||t==8)) ||
                             (i==16&&t==1);
            if (x.tick!=t || x.neuron_id!=i || x.voltage!=0 ||
                x.spike!=spike || x.evaluated!=spike) {
                std::cerr<<"M06_HLS_CSIM_DIAG dirty_evict trace_mismatch tick="
                         <<t<<" neuron="<<i<<" got_tick="<<x.tick
                         <<" got_id="<<x.neuron_id<<" got_v="<<x.voltage
                         <<" got_spike="<<static_cast<unsigned>(x.spike)<<" expected_spike="<<spike
                         <<" got_evaluated="<<static_cast<unsigned>(x.evaluated)<<"\n";
                return false;
            }
            spikes+=x.spike;
        }
    }
    const auto m=metrics.read();
    if (!out.empty() || !metrics.empty() || spikes!=3 ||
        m.emitted_spikes!=3 || m.page_fills<=2 ||
        m.page_evictions==0 || m.dirty_writebacks<2 ||
        m.m05_evaluations!=3) {
        std::cerr<<"M06_HLS_CSIM_DIAG dirty_evict bad_metrics spikes="
                 <<spikes<<" metric_spikes="<<m.emitted_spikes
                 <<" fills="<<m.page_fills<<" evictions="<<m.page_evictions
                 <<" dirty_writebacks="<<m.dirty_writebacks
                 <<" evaluations="<<m.m05_evaluations<<"\n";
        return false;
    }
    if (memory[0]!=0 || memory[1]!=9 ||
        memory[16*4]!=0 || memory[16*4+1]!=2) {
        std::cerr<<"M06_HLS_CSIM_DIAG dirty_evict canonical_image_mismatch"
                 <<" n0v="<<memory[0]<<" n0last="<<memory[1]
                 <<" n16v="<<memory[16*4]
                 <<" n16last="<<memory[16*4+1]<<"\n";
        return false;
    }
    return true;
}

static bool invalid_geometry_never_writes() {
    hls::stream<M05IntegratedNeuron> ns;
    hls::stream<M05IntegratedSynapse> ss;
    hls::stream<M05IntegratedExternal> es;
    hls::stream<M05IntegratedTraceEntry> out;
    hls::stream<M06PageMetrics> metrics;
    std::vector<std::uint32_t> mem(
        M06_PAGED_MAX_LOGICAL_NEURONS*M06_PAGED_RECORD_WORDS,0xa5a5a5a5u);
    if (m06_paged_rolling_replay(ns,ss,es,out,metrics,mem.data(),mem.data(),
        16,0,0,1,1,1,0,4080)!=M06_PAGE_BAD_SHAPE) {
        std::cerr<<"M06_HLS_CSIM_DIAG invalid_geometry zero_slot_accepted\n";
        return false;
    }
    if (m06_paged_rolling_replay(ns,ss,es,out,metrics,mem.data(),mem.data(),
        32,0,0,1,1,1,8,4080)!=M06_PAGE_BAD_SHAPE) {
        std::cerr<<"M06_HLS_CSIM_DIAG invalid_geometry out_of_range_accepted\n";
        return false;
    }
    if (!out.empty() || !metrics.empty() ||
        mem[4095*4]!=0xa5a5a5a5u) {
        std::cerr<<"M06_HLS_CSIM_DIAG invalid_geometry output_or_write"
                 <<" trace_empty="<<out.empty()
                 <<" metrics_empty="<<metrics.empty()
                 <<" sentinel="<<mem[4095*4]<<"\n";
        return false;
    }
    return true;
}

int main() {
    if (!wheel_and_high_address()) {
        std::cerr<<"M06_HLS_CSIM_FAIL high-offset 20tick wheel + 4k map\n";
        return 1;
    }
    if (!dirty_evict_then_delayed_replay()) {
        std::cerr<<"M06_HLS_CSIM_FAIL dirty eviction + recurrent parity\n";
        return 1;
    }
    if (!invalid_geometry_never_writes()) {
        std::cerr<<"M06_HLS_CSIM_FAIL invalid geometry commit guard\n";
        return 1;
    }
    std::cout<<"M06_PAGED_ROLLING_HLS_CSIM_PASS "
                "M05_wheel_delay8=1 m_axi_canonical=4096records "
                "resident_slots=1 dirty_eviction=1 "
                "NO_GENERATED_RTL_NO_BOARD\n";
    return 0;
}
