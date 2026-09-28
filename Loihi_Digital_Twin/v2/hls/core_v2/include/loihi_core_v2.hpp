#pragma once

#include "ap_int.h"

namespace loihi_v2_hls {

constexpr int MAX_COMPARTMENTS = 1024;
constexpr int MAX_INPUT_AXONS = 4096;
constexpr int MAX_INPUT_EVENTS = 4096;
constexpr int MAX_OUTPUT_ROUTES = 4096;
constexpr int MAX_SYNAPSE_ENTRIES = 32768;

constexpr int STATE_BITS = 24;
constexpr int REFRACTORY_BITS = 16;
constexpr int DECAY_BITS = 13;
constexpr int DECAY_SCALE = 4096;
constexpr int STATE_MIN = -(1 << (STATE_BITS - 1));
constexpr int STATE_MAX = (1 << (STATE_BITS - 1)) - 1;

using state_t = ap_int<STATE_BITS>;
using refractory_t = ap_uint<REFRACTORY_BITS>;
using decay_t = ap_uint<DECAY_BITS>;
using accumulator_t = ap_int<64>;
using wide_t = ap_int<64>;
using spike_t = ap_uint<1>;
using config_word_t = ap_uint<128>;
using state_word_t = ap_uint<64>;
using axon_word_t = ap_uint<64>;
using synapse_word_t = ap_uint<64>;
using route_desc_word_t = ap_uint<32>;
using route_word_t = ap_uint<32>;
using trace_word_t = ap_uint<256>;
using packet_word_t = ap_uint<64>;
// Logical axon IDs occupy 12 bits. The physical event memory uses a 16-bit
// word so the BRAM interface has a conventional byte/power-of-two width; the
// upper four bits are reserved and are written as zero by project tooling.
using event_axon_t = ap_uint<16>;
using status_t = ap_uint<32>;

constexpr unsigned STATUS_CAPACITY = 1u << 0;
constexpr unsigned STATUS_INVALID_AXON = 1u << 1;
constexpr unsigned STATUS_SYNAPSE_ROW_BOUNDS = 1u << 2;
constexpr unsigned STATUS_UNSUPPORTED_DELAY = 1u << 3;
constexpr unsigned STATUS_TARGET_BOUNDS = 1u << 4;
constexpr unsigned STATUS_ROUTE_ROW_BOUNDS = 1u << 5;
constexpr unsigned STATUS_PACKET_OVERFLOW = 1u << 6;
constexpr unsigned STATUS_RESERVED_BITS = 1u << 7;

state_t saturate_state(wide_t value);
wide_t round_away_from_zero_div4096(wide_t numerator);
state_t decayed_state(state_t value, decay_t decay);

state_word_t pack_state_word(
    state_t current,
    state_t voltage,
    refractory_t refractory);

void unpack_state_word(
    state_word_t word,
    state_t *current,
    state_t *voltage,
    refractory_t *refractory);

config_word_t pack_config_word(
    decay_t current_decay,
    decay_t voltage_decay,
    state_t threshold,
    state_t bias,
    state_t reset_voltage,
    refractory_t refractory_ticks);

axon_word_t pack_axon_word(
    ap_uint<15> synapse_start,
    ap_uint<16> synapse_count,
    ap_uint<10> target_offset,
    ap_uint<1> valid);

synapse_word_t pack_synapse_word(
    ap_uint<10> target_compartment,
    state_t weight,
    ap_uint<6> delay,
    ap_uint<8> tag);

route_desc_word_t pack_route_desc_word(
    ap_uint<12> route_start,
    ap_uint<13> route_count,
    ap_uint<1> valid);

route_word_t pack_route_word(
    ap_uint<7> destination_core,
    ap_uint<12> destination_axon);

packet_word_t pack_packet_word(
    ap_uint<7> destination_core,
    ap_uint<12> destination_axon,
    ap_uint<10> source_compartment,
    ap_uint<32> target_timestep);

}  // namespace loihi_v2_hls

// Process one algorithmic timestep for one logical FPGA-v2 core.
//
// Memories are explicit top-level ports.  Configuration, axon/synapse tables,
// route tables, and the event list are read-only for one invocation; state is
// updated in place.  Trace and packet outputs expose the normalized P02/P03
// differential boundary.
void loihi_core_v2_tick(
    ap_uint<11> compartment_count,
    ap_uint<13> event_count,
    ap_uint<16> synapse_count,
    ap_uint<13> route_count,
    ap_uint<32> timestep,
    const loihi_v2_hls::config_word_t config_words[loihi_v2_hls::MAX_COMPARTMENTS],
    loihi_v2_hls::state_word_t state_words[loihi_v2_hls::MAX_COMPARTMENTS],
    const loihi_v2_hls::axon_word_t axon_words[loihi_v2_hls::MAX_INPUT_AXONS],
    const loihi_v2_hls::synapse_word_t synapse_words[loihi_v2_hls::MAX_SYNAPSE_ENTRIES],
    const loihi_v2_hls::route_desc_word_t route_desc_words[loihi_v2_hls::MAX_COMPARTMENTS],
    const loihi_v2_hls::route_word_t route_words[loihi_v2_hls::MAX_OUTPUT_ROUTES],
    const loihi_v2_hls::event_axon_t input_events[loihi_v2_hls::MAX_INPUT_EVENTS],
    loihi_v2_hls::trace_word_t trace_words[loihi_v2_hls::MAX_COMPARTMENTS],
    loihi_v2_hls::packet_word_t packet_words[loihi_v2_hls::MAX_OUTPUT_ROUTES],
    ap_uint<11> *spike_count,
    ap_uint<13> *packet_count,
    loihi_v2_hls::status_t *status_flags);
