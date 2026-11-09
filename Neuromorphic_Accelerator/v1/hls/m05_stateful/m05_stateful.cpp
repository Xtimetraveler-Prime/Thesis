#include "m05_stateful.hpp"

std::uint32_t m05_stateful_service(
    hls::stream<M05MemCommand> &commands,
    hls::stream<M05MemResponse> &responses,
    std::uint32_t command_count) {
#pragma HLS INTERFACE axis port=commands
#pragma HLS INTERFACE axis port=responses
#pragma HLS INTERFACE s_axilite port=command_count bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    // Explicit bounded internal physical state candidate. Vitis, not host
    // C++, must establish whether these become the requested BRAMs.
    static std::int16_t voltages[M05_MAX_BATCH] = {};
    static std::int16_t biases[M05_MAX_BATCH] = {};
    static std::int16_t thresholds[M05_MAX_BATCH] = {};
    static std::int16_t resets[M05_MAX_BATCH] = {};
    static std::uint8_t initialized[M05_MAX_BATCH] = {};
    static std::uint8_t processed[M05_MAX_BATCH] = {};
    static std::uint64_t last_tick[M05_MAX_BATCH] = {};
#pragma HLS BIND_STORAGE variable=voltages type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=biases type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=thresholds type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=resets type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=last_tick type=ram_1p impl=bram

    if (command_count > M05_MAX_BATCH) return M05_BATCH_TOO_LARGE;

    for (std::uint32_t cmd_index = 0; cmd_index < command_count; ++cmd_index) {
        const M05MemCommand cmd = commands.read();
        M05MemResponse reply{};
        reply.neuron_id = cmd.neuron_id;
        reply.tick = cmd.tick;
        reply.voltage = 0;
        reply.spike = 0;
        reply.status = M05_MEM_OK;

        if (cmd.opcode == M05_MEM_CLEAR) {
            // CLEAR is a command barrier. Cost is O(1K) memory operations,
            // NOT an asynchronous reset. No stale state is visible after.
            for (std::uint32_t j = 0; j < M05_MAX_BATCH; ++j) {
                initialized[j] = 0;
                processed[j] = 0;
            }
        } else if (cmd.opcode > M05_MEM_READ) {
            reply.status = M05_MEM_INVALID_OPCODE;
        } else if (cmd.neuron_count == 0 ||
                   cmd.neuron_count > M05_MAX_BATCH ||
                   cmd.neuron_id >= cmd.neuron_count) {
            reply.status = M05_MEM_INVALID_ID;
        } else {
            const std::uint32_t i = cmd.neuron_id;
            if (cmd.opcode == M05_MEM_INIT) {
                if (initialized[i]) {
                    reply.status = M05_MEM_ALREADY_INITIALIZED;
                } else {
                    // INIT validation via the same bounded M02 C++ step
                    // contract as the standalone streaming engine.
                    M04Request check{};
                    check.neuron_id = i;
                    check.neuron_count = cmd.neuron_count;
                    check.tick = cmd.tick;
                    check.previous_voltage = cmd.initial_voltage;
                    check.aggregated_current = 0;
                    check.bias = cmd.bias;
                    check.threshold = cmd.threshold;
                    check.reset_voltage = cmd.reset_voltage;
                    check.state_bits = 16;
                    check.decay_num = 1;
                    check.decay_den = 1;
                    M04Response validation{};
                    m04_eval_one(check, validation);
                    if (validation.status != M04_OK) {
                        reply.status = M05_MEM_BAD_PARAMETERS;
                    } else {
                        voltages[i] = static_cast<std::int16_t>(cmd.initial_voltage);
                        biases[i] = static_cast<std::int16_t>(cmd.bias);
                        thresholds[i] = static_cast<std::int16_t>(cmd.threshold);
                        resets[i] = static_cast<std::int16_t>(cmd.reset_voltage);
                        processed[i] = 0;
                        initialized[i] = 1;
                        reply.voltage = voltages[i];
                    }
                }
            } else if (!initialized[i]) {
                reply.status = M05_MEM_UNINITIALIZED;
            } else if (cmd.opcode == M05_MEM_READ) {
                reply.voltage = voltages[i];
            } else {
                if (processed[i] && cmd.tick == last_tick[i]) {
                    reply.status = M05_MEM_DUPLICATE_TICK;
                } else if (processed[i] && cmd.tick < last_tick[i]) {
                    reply.status = M05_MEM_STALE_TICK;
                } else if (cmd.decay_den == 0 ||
                           cmd.decay_num > cmd.decay_den) {
                    reply.status = M05_MEM_BAD_PARAMETERS;
                } else {
                    M04Request r{};
                    r.neuron_id = i;
                    r.neuron_count = cmd.neuron_count;
                    r.tick = cmd.tick;
                    r.previous_voltage = voltages[i];
                    r.aggregated_current = cmd.aggregated_current;
                    r.bias = biases[i];
                    r.threshold = thresholds[i];
                    r.reset_voltage = resets[i];
                    r.state_bits = 16;
                    r.decay_num = cmd.decay_num;
                    r.decay_den = cmd.decay_den;
                    M04Response result{};
                    m04_eval_one(r, result);
                    if (result.status != M04_OK) {
                        reply.status = M05_MEM_BAD_PARAMETERS;
                    } else {
                        voltages[i] = static_cast<std::int16_t>(result.next_voltage);
                        last_tick[i] = cmd.tick;
                        processed[i] = 1;
                        reply.voltage = result.next_voltage;
                        reply.spike = result.spike;
                    }
                }
            }
        }
        // Invalid requests cannot write neuron state and report zero voltage.
        // An error is not a successful partial inference.
        responses.write(reply);
    }
    return M05_BATCH_OK;
}
