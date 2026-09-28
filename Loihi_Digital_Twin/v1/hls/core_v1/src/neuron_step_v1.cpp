#include "neuron_step_v1.hpp"

namespace neuromorphic_hls {

state_t saturate_state_v1(wide_t value) {
#pragma HLS INLINE
    const wide_t minimum = STATE_MIN;
    const wide_t maximum = STATE_MAX;

    if (value > maximum) {
        return state_t(STATE_MAX);
    }
    if (value < minimum) {
        return state_t(STATE_MIN);
    }
    return state_t(value);
}

wide_t round_away_from_zero_div4096_v1(wide_t numerator) {
#pragma HLS INLINE
    if (numerator == 0) {
        return 0;
    }

    // 4096 == 2^12. For a non-zero magnitude, adding 4095 before shifting
    // implements ceil(magnitude / 4096), which is exactly M10's
    // round-away-from-zero rule for both signs.
    const bool negative = numerator < 0;

    // Vitis HLS arbitrary-precision unary minus widens the expression by one
    // bit. Assign explicitly back into wide_t instead of using ?: between
    // ap_int<65> and ap_int<64>; the reachable numerator range here is far
    // inside signed 64-bit because it comes from 24-bit state * 13-bit decay.
    wide_t magnitude = numerator;
    if (negative) {
        magnitude = wide_t(-numerator);
    }

    const wide_t rounded_magnitude = (magnitude + wide_t(DECAY_SCALE - 1)) >> 12;
    if (negative) {
        return wide_t(-rounded_magnitude);
    }
    return rounded_magnitude;
}

state_t decayed_state_v1(state_t value, decay_t decay) {
#pragma HLS INLINE
    const wide_t value_wide = value;
    const wide_t product = value_wide * wide_t(decay);
    const wide_t removed = round_away_from_zero_div4096_v1(product);
    return saturate_state_v1(value_wide - removed);
}

}  // namespace neuromorphic_hls

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
    neuromorphic_hls::spike_t *spiked) {

    using namespace neuromorphic_hls;

#pragma HLS INTERFACE ap_ctrl_hs port=return
#pragma HLS INTERFACE ap_none port=current_before
#pragma HLS INTERFACE ap_none port=voltage_before
#pragma HLS INTERFACE ap_none port=refractory_before
#pragma HLS INTERFACE ap_none port=synaptic_input
#pragma HLS INTERFACE ap_none port=current_decay
#pragma HLS INTERFACE ap_none port=voltage_decay
#pragma HLS INTERFACE ap_none port=threshold
#pragma HLS INTERFACE ap_none port=bias
#pragma HLS INTERFACE ap_none port=reset_voltage
#pragma HLS INTERFACE ap_none port=refractory_ticks

    // Output pointers use ap_vld rather than ap_none. Vitis HLS Vivado-IP
    // flow normally applies ap_vld to output pointers so the consumer and the
    // automatic C/RTL co-simulation harness know exactly when each result is
    // valid. The data values and M10 neuron semantics are unchanged.
#pragma HLS INTERFACE ap_vld port=current_after
#pragma HLS INTERFACE ap_vld port=voltage_after
#pragma HLS INTERFACE ap_vld port=refractory_after
#pragma HLS INTERFACE ap_vld port=spiked

    // CORE-NEURON-001 / CORE-ARITH-001:
    // Input is part of working current before current decay, then SAT24 is
    // applied once at the working-current boundary.
    const wide_t current_sum = wide_t(current_before) + wide_t(synaptic_input);
    const state_t current_work = saturate_state_v1(current_sum);

    // CORE-NEURON-003:
    // Stored current is always the decayed working current, even while
    // refractory or on a spike tick.
    const state_t next_current = decayed_state_v1(current_work, current_decay);

    state_t next_voltage = 0;
    refractory_t next_refractory = 0;
    spike_t next_spike = 0;

    if (refractory_before > 0) {
        // CORE-NEURON-004 / CORE-NEURON-005.
        next_voltage = reset_voltage;
        next_refractory = refractory_t(refractory_before - refractory_t(1));
        next_spike = 0;
    } else {
        // CORE-NEURON-002 / CORE-NEURON-006:
        // Voltage sees the pre-decay current_work value.
        const state_t voltage_decay_base =
            decayed_state_v1(voltage_before, voltage_decay);
        const wide_t voltage_sum = wide_t(voltage_decay_base)
                                 + wide_t(current_work)
                                 + wide_t(bias);
        const state_t voltage_work = saturate_state_v1(voltage_sum);

        // CORE-NEURON-007: strict greater-than threshold.
        if (voltage_work > threshold) {
            // CORE-NEURON-008 / CORE-NEURON-009.
            next_spike = 1;
            next_voltage = reset_voltage;
            if (refractory_ticks > 0) {
                next_refractory = refractory_t(refractory_ticks - refractory_t(1));
            } else {
                next_refractory = refractory_t(0);
            }
        } else {
            next_spike = 0;
            next_voltage = voltage_work;
            next_refractory = 0;
        }
    }

    *current_after = next_current;
    *voltage_after = next_voltage;
    *refractory_after = next_refractory;
    *spiked = next_spike;
}
