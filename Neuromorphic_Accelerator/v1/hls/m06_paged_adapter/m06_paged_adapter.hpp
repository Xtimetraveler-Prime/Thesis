#pragma once
#include "../m05_rolling/m05_rolling.hpp"
#include <cstdint>
#include <vector>

// M06 INTEGRATION HARNESS: uses the UNCHANGED M05 streaming HLS neural
// arithmetic top and an explicit bounded, byte-addressed canonical pager.
// Host C++ correctness ONLY. This adapter and its vector-backed scheduler
// are NOT an HLS-synthesized AXI state port, PL DMA, or DDR address owner.
//
// Each canonical neuron record is 16B (M06 option-B):
// bytes [0:1] signed16 voltage; [2:5] little-endian tick+1; [6:15] reserved.
// Every active neuron computes using ORIGINAL m05_stream_eval. No duplicate
// working-voltage array is permitted in the scheduler.
struct M06PagedCounters {
    std::uint64_t page_accesses = 0;
    std::uint64_t page_hits = 0;
    std::uint64_t page_misses = 0;
    std::uint64_t evictions = 0;
    std::uint64_t dirty_writebacks = 0;
    std::uint64_t fills = 0;
    std::uint64_t read_bytes = 0;
    std::uint64_t written_bytes = 0;
    std::uint64_t m05_stream_calls = 0;
    std::uint64_t evaluated = 0;
    std::uint64_t spike_count = 0;
};

struct M06PagedReplayResult {
    std::uint32_t status = 0;
    std::vector<M05IntegratedTraceEntry> trace;
    M06PagedCounters counters;
    std::vector<std::uint8_t> canonical_after_flush;
};

// Native C++ source/cosimulation harness, not an FPGA callable top.
// The owner-accepted M05 rolling top is left byte-for-byte unchanged;
// one M05 STREAM EVAL request is serviced per active logical neuron.
M06PagedReplayResult m06_paged_replay_with_m05_stream(
    const std::vector<M05IntegratedNeuron> &neurons,
    const std::vector<M05IntegratedSynapse> &edges,
    const std::vector<M05IntegratedExternal> &external,
    std::uint32_t ticks, std::uint32_t decay_num,
    std::uint32_t decay_den, std::uint32_t slots);
