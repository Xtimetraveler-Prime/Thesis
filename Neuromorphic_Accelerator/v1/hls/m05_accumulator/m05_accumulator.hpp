#pragma once

#include "../m05_stream_eval/m05_stream.hpp"
#include <cstdint>

// HLS-oriented single-tick signed-event aggregator (physical PL candidate).
// The producer must route delayed synapses and assemble a complete tick.
// This block does NOT implement a temporal event FIFO or synapse fanout.
enum M05AccumOpcode : std::uint8_t {
    M05_ACC_CLEAR = 0,  // re-arm after any fault; invalidates old results
    M05_ACC_BEGIN = 1,  // new tick, physical 1024-ID bound
    M05_ACC_ADD = 2,    // one signed W16 contribution, including zero
    M05_ACC_SEAL = 3,   // no more contributions to this tick
    M05_ACC_READ = 4,   // read exact final aggregate and delivered flag
    M05_ACC_END = 5,    // close successful tick
};
enum M05AccumStatus : std::uint8_t {
    M05_ACC_OK = 0,
    M05_ACC_BAD_OPCODE = 1,
    M05_ACC_BAD_ID = 2,
    M05_ACC_NOT_ACTIVE = 3,
    M05_ACC_BAD_TICK = 4,
    M05_ACC_EVENT_OVERFLOW = 5,
    M05_ACC_BAD_CURRENT = 6,
    M05_ACC_NOT_SEALED = 7,
    M05_ACC_ALREADY_ACTIVE = 8,
    M05_ACC_BAD_PHASE = 9,
    M05_ACC_STICKY_FAILURE = 10,
};
constexpr std::uint32_t M05_ACC_MAX_DELIVERIES_PER_TICK = 4096;
struct M05AccumCommand {
    std::uint8_t opcode;
    std::uint32_t neuron_id;
    std::uint32_t neuron_count;
    std::uint64_t tick;
    std::int32_t current; // W16 signed individual contribution on ADD
};
struct M05AccumResponse {
    std::uint32_t neuron_id;
    std::uint64_t tick;
    std::int64_t aggregate;
    std::uint32_t accepted_events;
    std::uint8_t touched;
    std::uint8_t status;
};
// Aggregator has static per-neuron RAM candidates, sticky-error state and
// a readout barrier at SEAL. A bad contribution invalidates this whole tick.
// CLEAR is an explicit recovery, never silently discarding a failed result.
// No HLS II or BRAM resource proof exists without Vitis synthesis.
std::uint32_t m05_event_accumulator(
    hls::stream<M05AccumCommand> &commands,
    hls::stream<M05AccumResponse> &responses,
    std::uint32_t command_count);
