#pragma once

#include "../m05_stream_eval/m05_stream.hpp"
#include <cstdint>

// M05.3 physical-state *candidate* (not HLS-synthesized).
// A command is accepted only after reading it completely. Exactly one response
// follows every accepted command. The local arrays belong to the PL candidate,
// not to an individual simulated Loihi core, host cache block or A53 service.
enum M05MemOpcode : std::uint8_t {
    M05_MEM_CLEAR = 0,
    M05_MEM_INIT = 1,
    M05_MEM_STEP = 2,
    M05_MEM_READ = 3,
};
enum M05MemStatus : std::uint8_t {
    M05_MEM_OK = 0,
    M05_MEM_INVALID_OPCODE = 1,
    M05_MEM_INVALID_ID = 2,
    M05_MEM_UNINITIALIZED = 3,
    M05_MEM_BAD_PARAMETERS = 4,
    M05_MEM_ALREADY_INITIALIZED = 5,
    M05_MEM_DUPLICATE_TICK = 6,
    M05_MEM_STALE_TICK = 7,
};
struct M05MemCommand {
    std::uint8_t opcode;
    std::uint32_t neuron_id;
    std::uint32_t neuron_count;
    std::uint64_t tick;
    // INIT: initial_voltage. STEP: unused, state read from local RAM.
    std::int32_t initial_voltage;
    // STEP: summed signed input current, never one contribution at a time.
    std::int64_t aggregated_current;
    // INIT: per-neuron stored parameters; unused on STEP/READ.
    std::int32_t bias;
    std::int32_t threshold;
    std::int32_t reset_voltage;
    // STEP uses global per-network rational provided by scheduler.
    std::uint32_t decay_num;
    std::uint32_t decay_den;
};
struct M05MemResponse {
    std::uint32_t neuron_id;
    std::uint64_t tick;
    std::int32_t voltage;
    std::uint8_t spike;
    std::uint8_t status;
};
// A CLEAR command invalidates all local state/config rows and processed ticks.
// A STEP request for any ID/tick may be accepted at most once per CLEAR/INIT
// epoch and IDs must have strictly increasing ticks. Global tick barriers,
// skip legitimacy, queue capacity and delayed fanout remain scheduler duties.
std::uint32_t m05_stateful_service(
    hls::stream<M05MemCommand> &commands,
    hls::stream<M05MemResponse> &responses,
    std::uint32_t command_count);
