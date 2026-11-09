#pragma once
#include "../m05_rolling/m05_rolling.hpp"
#include <cstdint>

// M06 Vitis-HLS-targeted autonomous rolling neural TOP.
// Preserves accepted M05 event wheel, positive-delay fanout, full trace ABI,
// M04 arithmetic and per-run speculative output status rules.
// Crucially there is NO full on-chip working voltage array. Every working
// voltage comes from a 16B canonical record in an 8x256B on-chip page cache.
// canonical_read_words and canonical_write_words are separate m_axi masters
// to match the ORIGINAL SmartConnect S00 READ and S03 WRITE port ROLES.
// They MUST be mapped to the SAME independently owned physical canonical
// region; 32-bit HLS to 256-bit SI width adaptation remains unverified.
// Each master uses logical byte offsets,
// NOT an approved PS physical address or a memory safety/ownership grant.
// The canonical buffer must expose 16,384 x 32-bit words = 64KiB for the
// configured 4,096 logical-state address aperture. AXI-Lite selects an aligned
// 16-neuron canonical_first_neuron for each bounded, contiguous tile. A single invocation
// still admits at most the ACCEPTED M05 1,024 neurons/64 ticks.
constexpr std::uint32_t M06_PAGED_MAX_LOGICAL_NEURONS = 4096;
constexpr std::uint32_t M06_PAGED_RECORD_WORDS = 4;   // 16-byte state record
constexpr std::uint32_t M06_PAGED_PAGE_WORDS = 64;    // 256-byte state block
constexpr std::uint32_t M06_PAGED_MAX_SLOTS = 8;      // 2048B on-chip data

enum M06PagedStatus : std::uint32_t {
    M06_PAGE_OK = 0,
    M06_PAGE_BAD_SHAPE = 1,
    M06_PAGE_BAD_NEURON = 2,
    M06_PAGE_BAD_SYNAPSE = 3,
    M06_PAGE_BAD_EXTERNAL = 4,
    M06_PAGE_DELIVERY_OVERFLOW = 5,
    M06_PAGE_LIF_ERROR = 6,
    M06_PAGE_STATE_CORRUPTION = 7,
};

struct M06PageMetrics {
    std::uint32_t page_accesses;
    std::uint32_t page_hits;
    std::uint32_t page_misses;
    std::uint32_t page_evictions;
    std::uint32_t dirty_writebacks;
    std::uint32_t page_fills;
    std::uint32_t m05_evaluations;
    std::uint32_t emitted_spikes;
};

// This is a NEW candidate HLS top: no synthesized-IP verification until
// real Vitis 2025.2 C synthesis and subsequent RTL test. It does not
// replace or mutate the previously accepted m05_rolling_replay top.
// A nonzero status INVALIDATES any previously streamed trace, and also
// quarantines the externally visible canonical image (non-atomic writes).
// The host MUST establish separate exclusive canonical DDR ownership.
std::uint32_t m06_paged_rolling_replay(
    hls::stream<M05IntegratedNeuron> &neurons,
    hls::stream<M05IntegratedSynapse> &synapses,
    hls::stream<M05IntegratedExternal> &external_events,
    hls::stream<M05IntegratedTraceEntry> &trace,
    hls::stream<M06PageMetrics> &metrics,
    const std::uint32_t *canonical_read_words,
    std::uint32_t *canonical_write_words,
    std::uint32_t neuron_count,
    std::uint32_t synapse_count,
    std::uint32_t external_count,
    std::uint32_t ticks,
    std::uint32_t decay_num,
    std::uint32_t decay_den,
    std::uint32_t resident_slots,
    std::uint32_t canonical_first_neuron);
