#pragma once

#include "ap_int.h"

namespace neuromorphic_hls {

// Frozen M10 FPGA-v1 architectural widths.
constexpr int STATE_BITS = 24;
constexpr int REFRACTORY_BITS = 16;
constexpr int DECAY_BITS = 13;
constexpr int DECAY_SCALE = 4096;
constexpr int STATE_MIN = -(1 << (STATE_BITS - 1));
constexpr int STATE_MAX = (1 << (STATE_BITS - 1)) - 1;

using state_t = ap_int<STATE_BITS>;
using refractory_t = ap_uint<REFRACTORY_BITS>;
using decay_t = ap_uint<DECAY_BITS>;
using spike_t = ap_uint<1>;

// M11.1 uses a deliberately wide scalar at the boundary between synaptic
// accumulation and the neuron datapath. The later core-integration milestone
// will freeze the physical accumulator/event-capacity profile.
using accumulator_t = ap_int<64>;
using wide_t = ap_int<64>;

state_t saturate_state_v1(wide_t value);
wide_t round_away_from_zero_div4096_v1(wide_t numerator);
state_t decayed_state_v1(state_t value, decay_t decay);

}  // namespace neuromorphic_hls

// Synthesizable one-neuron transition for the frozen M10 FPGA-v1 profile.
//
// Keep the HLS top-level function in the global namespace. The arithmetic
// helpers and fixed-width types remain namespaced, but the global synthesis
// boundary matches the form expected by Vitis HLS C/RTL co-simulation stub
// generation. No neuron arithmetic or state semantics depend on this wrapper
// placement.
//
// This is intentionally a pure state transition: no static storage, packet
// routing, synapse traversal, or tick counter is hidden inside the function.
// Those pieces are layered around this datapath in later M11 sub-milestones.
void neuron_step_v1(
    neuromorphic_hls::state_t current_before,
    neuromorphic_hls::state_t voltage_before,
    neuromorphic_hls::refractory_t refractory_before,
    neuromorphic_hls::accumulator_t synaptic_input,
    neuromorphic_hls::decay_t current_decay,
    neuromorphic_hls::decay_t voltage_decay,
    neuromorphic_hls::state_t threshold,
    neuromorphic_hls::state_t bias,
    neuromorphic_hls::state_t reset_voltage,
    neuromorphic_hls::refractory_t refractory_ticks,
    neuromorphic_hls::state_t *current_after,
    neuromorphic_hls::state_t *voltage_after,
    neuromorphic_hls::refractory_t *refractory_after,
    neuromorphic_hls::spike_t *spiked);
