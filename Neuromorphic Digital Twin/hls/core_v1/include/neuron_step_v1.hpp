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

// Synthesizable one-neuron transition for the frozen M10 FPGA-v1 profile.
//
// This is intentionally a pure state transition: no static storage, packet
// routing, synapse traversal, or tick counter is hidden inside the function.
// Those pieces are layered around this datapath in later M11 sub-milestones.
void neuron_step_v1(
    state_t current_before,
    state_t voltage_before,
    refractory_t refractory_before,
    accumulator_t synaptic_input,
    decay_t current_decay,
    decay_t voltage_decay,
    state_t threshold,
    state_t bias,
    state_t reset_voltage,
    refractory_t refractory_ticks,
    state_t *current_after,
    state_t *voltage_after,
    refractory_t *refractory_after,
    spike_t *spiked);

}  // namespace neuromorphic_hls
