#include "m05_integrated.hpp"

// This is an actual single HLS-oriented top with resident memories and an
// in-fabric finite-time scheduler; the Python host never services a tick.
// The entire trace is buffered before the first AXIS output, so any overflow
// invalidates the run without a partial output trace.
std::uint32_t m05_integrated_replay(
    hls::stream<M05IntegratedNeuron> &neurons,
    hls::stream<M05IntegratedSynapse> &synapses,
    hls::stream<M05IntegratedExternal> &external_events,
    hls::stream<M05IntegratedTraceEntry> &trace,
    std::uint32_t neuron_count,
    std::uint32_t synapse_count,
    std::uint32_t external_count,
    std::uint32_t ticks,
    std::uint32_t decay_num,
    std::uint32_t decay_den) {
#pragma HLS INTERFACE axis port=neurons
#pragma HLS INTERFACE axis port=synapses
#pragma HLS INTERFACE axis port=external_events
#pragma HLS INTERFACE axis port=trace
#pragma HLS INTERFACE s_axilite port=neuron_count bundle=control
#pragma HLS INTERFACE s_axilite port=synapse_count bundle=control
#pragma HLS INTERFACE s_axilite port=external_count bundle=control
#pragma HLS INTERFACE s_axilite port=ticks bundle=control
#pragma HLS INTERFACE s_axilite port=decay_num bundle=control
#pragma HLS INTERFACE s_axilite port=decay_den bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    if (neuron_count == 0 || neuron_count > M05_INT_MAX_NEURONS ||
        synapse_count > M05_INT_MAX_SYNAPSES ||
        external_count > M05_INT_MAX_EXTERNAL ||
        ticks == 0 || ticks > M05_INT_MAX_TICKS ||
        decay_den == 0 || decay_num > decay_den) {
        return M05_INT_BAD_SHAPE;
    }

    static std::int16_t voltage[M05_INT_MAX_NEURONS];
    static std::int16_t bias[M05_INT_MAX_NEURONS];
    static std::int16_t threshold[M05_INT_MAX_NEURONS];
    static std::int16_t reset[M05_INT_MAX_NEURONS];
    static std::int32_t first[M05_INT_MAX_NEURONS];
    static std::int32_t next[M05_INT_MAX_SYNAPSES];
    static std::uint32_t posts[M05_INT_MAX_SYNAPSES];
    static std::int16_t weights[M05_INT_MAX_SYNAPSES];
    static std::uint64_t delays[M05_INT_MAX_SYNAPSES];
    static std::int64_t current[M05_INT_MAX_TICKS][M05_INT_MAX_NEURONS];
    static std::uint8_t touched[M05_INT_MAX_TICKS][M05_INT_MAX_NEURONS];
    static std::uint32_t delivery_count[M05_INT_MAX_TICKS];
    static std::int16_t trace_voltage[M05_INT_MAX_TICKS][M05_INT_MAX_NEURONS];
    static std::uint8_t trace_spike[M05_INT_MAX_TICKS][M05_INT_MAX_NEURONS];
    static std::uint8_t trace_evaluated[M05_INT_MAX_TICKS][M05_INT_MAX_NEURONS];
#pragma HLS BIND_STORAGE variable=voltage type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=bias type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=threshold type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=reset type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=current type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=touched type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=trace_voltage type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=trace_spike type=ram_2p impl=bram

    // Reinitialize logical memory contents on every invocation, including
    // after an earlier rejected run. Do not depend on BRAM power-on values.
    for (std::uint32_t t = 0; t < M05_INT_MAX_TICKS; ++t) {
        delivery_count[t] = 0;
        for (std::uint32_t i = 0; i < M05_INT_MAX_NEURONS; ++i) {
            touched[t][i] = 0;
            current[t][i] = 0;
        }
    }
    for (std::uint32_t i = 0; i < M05_INT_MAX_NEURONS; ++i) {
        first[i] = -1;
    }

    // All inputs are read in fixed-count sections. The testbench must send
    // exactly these counts; AXIS will naturally stall on incomplete sections.
    for (std::uint32_t i = 0; i < neuron_count; ++i) {
        M05IntegratedNeuron p = neurons.read();
        if (p.initial_voltage < -32768 || p.initial_voltage > 32767 ||
            p.bias < -32768 || p.bias > 32767 ||
            p.threshold <= 0 || p.threshold > 32767 ||
            p.reset_voltage < -32768 || p.reset_voltage > 32767 ||
            p.reset_voltage >= p.threshold) {
            return M05_INT_BAD_NEURON;
        }
        voltage[i] = static_cast<std::int16_t>(p.initial_voltage);
        bias[i] = static_cast<std::int16_t>(p.bias);
        threshold[i] = static_cast<std::int16_t>(p.threshold);
        reset[i] = static_cast<std::int16_t>(p.reset_voltage);
    }
    // CSR-like adjacency lists: one linked-list head per neuron and one
    // next pointer per edge; self/parallel edges are independent entries.
    for (std::uint32_t j = 0; j < synapse_count; ++j) {
        M05IntegratedSynapse e = synapses.read();
        if (e.pre >= neuron_count || e.post >= neuron_count ||
            e.weight < -32768 || e.weight > 32767 || e.delay == 0) {
            return M05_INT_BAD_SYNAPSE;
        }
        posts[j] = e.post;
        weights[j] = static_cast<std::int16_t>(e.weight);
        delays[j] = e.delay;
        next[j] = first[e.pre];
        first[e.pre] = static_cast<std::int32_t>(j);
    }
    // External event order does NOT matter: no saturation until after the
    // exact sum of <=4096 individual W16 terms is formed for each tick.
    for (std::uint32_t j = 0; j < external_count; ++j) {
        M05IntegratedExternal e = external_events.read();
        if (e.tick >= ticks || e.neuron_id >= neuron_count ||
            e.current < -32768 || e.current > 32767) {
            return M05_INT_BAD_EXTERNAL;
        }
        const std::uint32_t t = static_cast<std::uint32_t>(e.tick);
        if (delivery_count[t] >= M05_INT_MAX_PER_TICK) {
            return M05_INT_DELIVERY_OVERFLOW;
        }
        ++delivery_count[t]; // count zero and canceling deliveries individually
        current[t][e.neuron_id] += static_cast<std::int64_t>(e.current);
        touched[t][e.neuron_id] = 1;
    }

    // This loop is the global tick barrier: only t+delay is scheduled during
    // tick t; no neuron observes another neuron's new voltage in the same tick.
    for (std::uint32_t t = 0; t < ticks; ++t) {
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            std::uint8_t spike = 0;
            const std::uint8_t evaluate =
                (voltage[i] != 0 || bias[i] != 0 || touched[t][i]) ? 1 : 0;
            if (evaluate) {
                M04Request request{};
                request.neuron_id = i;
                request.neuron_count = neuron_count;
                request.tick = t;
                request.previous_voltage = voltage[i];
                request.aggregated_current = current[t][i];
                request.bias = bias[i];
                request.threshold = threshold[i];
                request.reset_voltage = reset[i];
                request.state_bits = 16;
                request.decay_num = decay_num;
                request.decay_den = decay_den;
                M04Response response{};
                m04_eval_one(request, response); // EXACT accepted M02 math
                if (response.status != M04_OK) return M05_INT_LIF_ERROR;
                voltage[i] = static_cast<std::int16_t>(response.next_voltage);
                spike = response.spike;
            }
            trace_voltage[t][i] = voltage[i];
            trace_spike[t][i] = spike;
            trace_evaluated[t][i] = evaluate;
            if (spike) {
                // Delay >=1 prevents same-tick feedback. Large delays beyond
                // this finite run are correctly ignored (not an error).
                for (std::int32_t edge = first[i]; edge != -1; edge = next[edge]) {
                    const std::uint64_t delay = delays[edge];
                    if (delay < static_cast<std::uint64_t>(ticks - t)) {
                        const std::uint32_t future =
                            t + static_cast<std::uint32_t>(delay);
                        if (delivery_count[future] >= M05_INT_MAX_PER_TICK) {
                            return M05_INT_DELIVERY_OVERFLOW;
                        }
                        ++delivery_count[future];
                        const std::uint32_t dest = posts[edge];
                        current[future][dest] +=
                            static_cast<std::int64_t>(weights[edge]);
                        touched[future][dest] = 1;
                    }
                }
            }
        }
    }

    // No AXIS output is made until all ticks have succeeded, including
    // future-capacity checks. This prevents a partially accepted trace.
    for (std::uint32_t t = 0; t < ticks; ++t) {
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            M05IntegratedTraceEntry out{};
            out.tick = t;
            out.neuron_id = i;
            out.voltage = trace_voltage[t][i];
            out.spike = trace_spike[t][i];
            out.evaluated = trace_evaluated[t][i];
            out.delivered_count = delivery_count[t];
            trace.write(out);
        }
    }
    return M05_INT_OK;
}
