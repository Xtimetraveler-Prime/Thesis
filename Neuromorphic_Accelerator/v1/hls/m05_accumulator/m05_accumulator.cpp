#include "m05_accumulator.hpp"

std::uint32_t m05_event_accumulator(
    hls::stream<M05AccumCommand> &commands,
    hls::stream<M05AccumResponse> &responses,
    std::uint32_t command_count) {
#pragma HLS INTERFACE axis port=commands
#pragma HLS INTERFACE axis port=responses
#pragma HLS INTERFACE s_axilite port=command_count bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
    static std::int64_t sums[M05_MAX_BATCH] = {};
    static std::uint8_t touched[M05_MAX_BATCH] = {};
#pragma HLS BIND_STORAGE variable=sums type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=touched type=ram_1p impl=bram
    static std::uint64_t active_tick = 0;
    static std::uint32_t active_neurons = 0;
    static std::uint32_t deliveries = 0;
    static std::uint8_t active = 0;
    static std::uint8_t sealed = 0;
    static std::uint8_t failed = 0;

    if (command_count > M05_MAX_BATCH) return M05_BATCH_TOO_LARGE;
    for (std::uint32_t n = 0; n < command_count; ++n) {
        const M05AccumCommand cmd = commands.read();
        M05AccumResponse out{};
        out.neuron_id = cmd.neuron_id;
        out.tick = cmd.tick;
        out.aggregate = 0;
        out.touched = 0;
        out.status = M05_ACC_OK;
        out.accepted_events = deliveries;

        if (cmd.opcode == M05_ACC_CLEAR) {
            // Explicit recovery barrier. Only this command clears a fault.
            active = 0;
            sealed = 0;
            failed = 0;
            active_neurons = 0;
            deliveries = 0;
            out.accepted_events = 0;
        } else if (cmd.opcode > M05_ACC_END) {
            out.status = M05_ACC_BAD_OPCODE;
            if (active) failed = 1;
        } else if (cmd.opcode == M05_ACC_BEGIN) {
            if (active) {
                out.status = M05_ACC_ALREADY_ACTIVE;
                failed = 1;
            } else if (cmd.neuron_count == 0 ||
                       cmd.neuron_count > M05_MAX_BATCH) {
                out.status = M05_ACC_BAD_ID;
            } else {
                active = 1;
                failed = 0;
                sealed = 0;
                deliveries = 0;
                active_tick = cmd.tick;
                active_neurons = cmd.neuron_count;
                // No stale state/flag from the previous tick may become visible.
                for (std::uint32_t i = 0; i < M05_MAX_BATCH; ++i) {
                    touched[i] = 0;
                }
                out.accepted_events = 0;
            }
        } else if (!active) {
            out.status = M05_ACC_NOT_ACTIVE;
        } else if (failed) {
            out.status = M05_ACC_STICKY_FAILURE;
        } else if (cmd.tick != active_tick) {
            out.status = M05_ACC_BAD_TICK;
            failed = 1;
        } else if (cmd.opcode == M05_ACC_ADD) {
            if (sealed) {
                out.status = M05_ACC_BAD_PHASE;
                failed = 1;
            } else if (cmd.neuron_id >= active_neurons ||
                       cmd.neuron_count != active_neurons) {
                out.status = M05_ACC_BAD_ID;
                failed = 1;
            } else if (cmd.current < -32768 || cmd.current > 32767) {
                out.status = M05_ACC_BAD_CURRENT;
                failed = 1;
            } else if (deliveries >= M05_ACC_MAX_DELIVERIES_PER_TICK) {
                out.status = M05_ACC_EVENT_OVERFLOW;
                failed = 1;
            } else {
                const std::uint32_t i = cmd.neuron_id;
                // Each signed term is W16; <=4096 arrivals means i64 exact.
                // No per-contribution saturation or clipping is permitted.
                if (touched[i]) {
                    sums[i] += static_cast<std::int64_t>(cmd.current);
                } else {
                    sums[i] = static_cast<std::int64_t>(cmd.current);
                    touched[i] = 1;
                }
                ++deliveries;  // count ZERO and canceling events too
                out.accepted_events = deliveries;
            }
        } else if (cmd.opcode == M05_ACC_SEAL) {
            if (sealed) {
                out.status = M05_ACC_BAD_PHASE;
                failed = 1;
            } else {
                sealed = 1;
            }
        } else if (cmd.opcode == M05_ACC_READ) {
            if (!sealed) {
                out.status = M05_ACC_NOT_SEALED;
                failed = 1;
            } else if (cmd.neuron_id >= active_neurons ||
                       cmd.neuron_count != active_neurons) {
                out.status = M05_ACC_BAD_ID;
                failed = 1;
            } else {
                const std::uint32_t i = cmd.neuron_id;
                out.touched = touched[i];
                out.aggregate = touched[i] ? sums[i] : 0;
            }
        } else if (cmd.opcode == M05_ACC_END) {
            if (!sealed) {
                out.status = M05_ACC_NOT_SEALED;
                failed = 1;
            } else {
                active = 0;  // sums remain inaccessible until next BEGIN
                sealed = 0;
            }
        }
        responses.write(out);
    }
    return M05_BATCH_OK;
}
