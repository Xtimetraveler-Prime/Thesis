#include "loihi_core_v2.hpp"

namespace loihi_v2_hls {

state_t saturate_state(wide_t value) {
#pragma HLS INLINE
    if (value > wide_t(STATE_MAX)) {
        return state_t(STATE_MAX);
    }
    if (value < wide_t(STATE_MIN)) {
        return state_t(STATE_MIN);
    }
    return state_t(value);
}

wide_t round_away_from_zero_div4096(wide_t numerator) {
#pragma HLS INLINE
    if (numerator == 0) {
        return 0;
    }
    const bool negative = numerator < 0;
    wide_t magnitude = numerator;
    if (negative) {
        magnitude = wide_t(-numerator);
    }
    const wide_t rounded = (magnitude + wide_t(DECAY_SCALE - 1)) >> 12;
    return negative ? wide_t(-rounded) : rounded;
}

state_t decayed_state(state_t value, decay_t decay) {
#pragma HLS INLINE
    const wide_t product = wide_t(value) * wide_t(decay);
    const wide_t removed = round_away_from_zero_div4096(product);
    return saturate_state(wide_t(value) - removed);
}

state_word_t pack_state_word(
    state_t current,
    state_t voltage,
    refractory_t refractory) {
#pragma HLS INLINE
    state_word_t word = 0;
    word.range(23, 0) = ap_uint<24>(current);
    word.range(47, 24) = ap_uint<24>(voltage);
    word.range(63, 48) = refractory;
    return word;
}

void unpack_state_word(
    state_word_t word,
    state_t *current,
    state_t *voltage,
    refractory_t *refractory) {
#pragma HLS INLINE
    *current = state_t(word.range(23, 0));
    *voltage = state_t(word.range(47, 24));
    *refractory = refractory_t(word.range(63, 48));
}

config_word_t pack_config_word(
    decay_t current_decay,
    decay_t voltage_decay,
    state_t threshold,
    state_t bias,
    state_t reset_voltage,
    refractory_t refractory_ticks) {
#pragma HLS INLINE
    config_word_t word = 0;
    word.range(12, 0) = current_decay;
    word.range(25, 13) = voltage_decay;
    word.range(49, 26) = ap_uint<24>(threshold);
    word.range(73, 50) = ap_uint<24>(bias);
    word.range(97, 74) = ap_uint<24>(reset_voltage);
    word.range(113, 98) = refractory_ticks;
    return word;
}

axon_word_t pack_axon_word(
    ap_uint<15> synapse_start,
    ap_uint<16> synapse_count,
    ap_uint<10> target_offset,
    ap_uint<1> valid) {
#pragma HLS INLINE
    axon_word_t word = 0;
    word.range(14, 0) = synapse_start;
    word.range(30, 15) = synapse_count;
    word.range(40, 31) = target_offset;
    word[41] = valid;
    return word;
}

synapse_word_t pack_synapse_word(
    ap_uint<10> target_compartment,
    state_t weight,
    ap_uint<6> delay,
    ap_uint<8> tag) {
#pragma HLS INLINE
    synapse_word_t word = 0;
    word.range(9, 0) = target_compartment;
    word.range(33, 10) = ap_uint<24>(weight);
    word.range(39, 34) = delay;
    word.range(47, 40) = tag;
    return word;
}

route_desc_word_t pack_route_desc_word(
    ap_uint<12> route_start,
    ap_uint<13> route_count,
    ap_uint<1> valid) {
#pragma HLS INLINE
    route_desc_word_t word = 0;
    word.range(11, 0) = route_start;
    word.range(24, 12) = route_count;
    word[25] = valid;
    return word;
}

route_word_t pack_route_word(
    ap_uint<7> destination_core,
    ap_uint<12> destination_axon) {
#pragma HLS INLINE
    route_word_t word = 0;
    word.range(6, 0) = destination_core;
    word.range(18, 7) = destination_axon;
    return word;
}

packet_word_t pack_packet_word(
    ap_uint<7> destination_core,
    ap_uint<12> destination_axon,
    ap_uint<10> source_compartment,
    ap_uint<32> target_timestep) {
#pragma HLS INLINE
    packet_word_t word = 0;
    word.range(6, 0) = destination_core;
    word.range(18, 7) = destination_axon;
    word.range(28, 19) = source_compartment;
    word.range(60, 29) = target_timestep;
    word[61] = 1;
    return word;
}

static void step_compartment(
    state_word_t before_word,
    config_word_t config_word,
    accumulator_t synaptic_input,
    state_word_t *after_word,
    spike_t *spiked) {
#pragma HLS INLINE
    state_t current_before = 0;
    state_t voltage_before = 0;
    refractory_t refractory_before = 0;
    unpack_state_word(
        before_word,
        &current_before,
        &voltage_before,
        &refractory_before);

    const decay_t current_decay = decay_t(config_word.range(12, 0));
    const decay_t voltage_decay = decay_t(config_word.range(25, 13));
    const state_t threshold = state_t(config_word.range(49, 26));
    const state_t bias = state_t(config_word.range(73, 50));
    const state_t reset_voltage = state_t(config_word.range(97, 74));
    const refractory_t refractory_ticks =
        refractory_t(config_word.range(113, 98));

    const wide_t current_sum =
        wide_t(current_before) + wide_t(synaptic_input);
    const state_t current_work = saturate_state(current_sum);
    const state_t current_after = decayed_state(current_work, current_decay);

    state_t voltage_after = 0;
    refractory_t refractory_after = 0;
    spike_t spike_after = 0;

    if (refractory_before > 0) {
        voltage_after = reset_voltage;
        refractory_after = refractory_t(refractory_before - refractory_t(1));
    } else {
        const state_t voltage_decay_base =
            decayed_state(voltage_before, voltage_decay);
        const state_t voltage_work = saturate_state(
            wide_t(voltage_decay_base)
            + wide_t(current_work)
            + wide_t(bias));

        if (voltage_work > threshold) {
            spike_after = 1;
            voltage_after = reset_voltage;
            refractory_after = refractory_ticks > 0
                ? refractory_t(refractory_ticks - refractory_t(1))
                : refractory_t(0);
        } else {
            voltage_after = voltage_work;
            refractory_after = 0;
        }
    }

    *after_word = pack_state_word(
        current_after,
        voltage_after,
        refractory_after);
    *spiked = spike_after;
}

}  // namespace loihi_v2_hls

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
    loihi_v2_hls::status_t *status_flags) {

    using namespace loihi_v2_hls;

#pragma HLS INTERFACE ap_ctrl_hs port=return
#pragma HLS INTERFACE ap_memory port=config_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=state_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=axon_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=synapse_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=route_desc_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=route_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=input_events storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=trace_words storage_type=ram_1p
#pragma HLS INTERFACE ap_memory port=packet_words storage_type=ram_1p
#pragma HLS INTERFACE ap_vld port=spike_count
#pragma HLS INTERFACE ap_vld port=packet_count
#pragma HLS INTERFACE ap_vld port=status_flags

    status_t status = 0;
    ap_uint<11> spikes = 0;
    ap_uint<13> packets = 0;

    if (compartment_count > MAX_COMPARTMENTS
        || event_count > MAX_INPUT_EVENTS
        || synapse_count > MAX_SYNAPSE_ENTRIES
        || route_count > MAX_OUTPUT_ROUTES) {
        status |= STATUS_CAPACITY;
        *spike_count = 0;
        *packet_count = 0;
        *status_flags = status;
        return;
    }

    accumulator_t accumulator[MAX_COMPARTMENTS];

clear_accumulators:
    for (int compartment = 0; compartment < MAX_COMPARTMENTS; ++compartment) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=1024
        if (compartment >= compartment_count) {
            break;
        }
        accumulator[compartment] = 0;
    }

process_events:
    for (int event = 0; event < MAX_INPUT_EVENTS; ++event) {
#pragma HLS LOOP_TRIPCOUNT min=0 max=4096
        if (event >= event_count) {
            break;
        }

        const unsigned axon_id = input_events[event].to_uint();
        const axon_word_t axon = axon_words[axon_id];
        if (axon.range(63, 42) != 0) {
            status |= STATUS_RESERVED_BITS;
        }
        if (axon[41] == 0) {
            status |= STATUS_INVALID_AXON;
            continue;
        }

        const unsigned synapse_start = axon.range(14, 0).to_uint();
        const unsigned row_count = axon.range(30, 15).to_uint();
        const unsigned target_offset = axon.range(40, 31).to_uint();
        const unsigned row_end = synapse_start + row_count;

        if (row_end > synapse_count || row_end > MAX_SYNAPSE_ENTRIES) {
            status |= STATUS_SYNAPSE_ROW_BOUNDS;
            continue;
        }

    traverse_synapses:
        for (int row_offset = 0; row_offset < MAX_SYNAPSE_ENTRIES; ++row_offset) {
#pragma HLS LOOP_TRIPCOUNT min=0 max=32768
            if (row_offset >= row_count) {
                break;
            }
            const synapse_word_t synapse =
                synapse_words[synapse_start + row_offset];
            if (synapse.range(63, 48) != 0) {
                status |= STATUS_RESERVED_BITS;
            }
            const ap_uint<6> delay = synapse.range(39, 34);
            if (delay != 0) {
                status |= STATUS_UNSUPPORTED_DELAY;
                continue;
            }

            const unsigned relative_target = synapse.range(9, 0).to_uint();
            const unsigned target = target_offset + relative_target;
            if (target >= compartment_count || target >= MAX_COMPARTMENTS) {
                status |= STATUS_TARGET_BOUNDS;
                continue;
            }
            const state_t weight = state_t(synapse.range(33, 10));
            accumulator[target] =
                accumulator[target] + accumulator_t(weight);
        }
    }

update_compartments:
    for (int compartment = 0; compartment < MAX_COMPARTMENTS; ++compartment) {
#pragma HLS LOOP_TRIPCOUNT min=1 max=1024
        if (compartment >= compartment_count) {
            break;
        }

        const config_word_t config_word = config_words[compartment];
        if (config_word.range(127, 114) != 0) {
            status |= STATUS_RESERVED_BITS;
        }

        const state_word_t before_word = state_words[compartment];
        state_word_t after_word = 0;
        spike_t spiked = 0;
        step_compartment(
            before_word,
            config_word,
            accumulator[compartment],
            &after_word,
            &spiked);
        state_words[compartment] = after_word;

        trace_word_t trace = 0;
        trace.range(63, 0) = before_word;
        trace.range(127, 64) = ap_uint<64>(accumulator[compartment]);
        trace.range(191, 128) = after_word;
        trace[192] = spiked;
        trace_words[compartment] = trace;

        if (!spiked) {
            continue;
        }
        ++spikes;

        const route_desc_word_t descriptor = route_desc_words[compartment];
        if (descriptor.range(31, 26) != 0) {
            status |= STATUS_RESERVED_BITS;
        }
        if (descriptor[25] == 0) {
            continue;
        }

        const unsigned route_start = descriptor.range(11, 0).to_uint();
        const unsigned row_count = descriptor.range(24, 12).to_uint();
        const unsigned row_end = route_start + row_count;
        if (row_end > route_count || row_end > MAX_OUTPUT_ROUTES) {
            status |= STATUS_ROUTE_ROW_BOUNDS;
            continue;
        }

    traverse_routes:
        for (int row_offset = 0; row_offset < MAX_OUTPUT_ROUTES; ++row_offset) {
#pragma HLS LOOP_TRIPCOUNT min=0 max=4096
            if (row_offset >= row_count) {
                break;
            }
            if (packets >= MAX_OUTPUT_ROUTES) {
                status |= STATUS_PACKET_OVERFLOW;
                break;
            }
            const route_word_t route = route_words[route_start + row_offset];
            if (route.range(31, 19) != 0) {
                status |= STATUS_RESERVED_BITS;
            }
            packet_words[packets.to_uint()] = pack_packet_word(
                ap_uint<7>(route.range(6, 0)),
                ap_uint<12>(route.range(18, 7)),
                ap_uint<10>(compartment),
                ap_uint<32>(timestep + 1));
            ++packets;
        }
    }

    *spike_count = spikes;
    *packet_count = packets;
    *status_flags = status;
}
