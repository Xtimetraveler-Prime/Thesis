#pragma once

#include "../m05_stream_eval/m05_stream.hpp"
#include <cstdint>

// M05.2/M05.3 FIRST INTEGRATED PL-oriented finite-horizon prototype.
// One hardware-run call receives the entire bounded configuration and all
// external events, autonomously schedules positive-delay recurrence, and
// publishes the full trace ONLY after every tick has committed successfully.
// NOT an unbounded continuous event engine, board deployment, or live AXIS proof.
constexpr std::uint32_t M05_INT_MAX_NEURONS = 1024;
constexpr std::uint32_t M05_INT_MAX_SYNAPSES = 4096;
constexpr std::uint32_t M05_INT_MAX_TICKS = 8;  // explicit finite-horizon limit
constexpr std::uint32_t M05_INT_MAX_PER_TICK = 4096;
constexpr std::uint32_t M05_INT_MAX_EXTERNAL =
    M05_INT_MAX_TICKS * M05_INT_MAX_PER_TICK;

enum M05IntegratedStatus : std::uint32_t {
    M05_INT_OK = 0,
    M05_INT_BAD_SHAPE = 1,
    M05_INT_BAD_NEURON = 2,
    M05_INT_BAD_SYNAPSE = 3,
    M05_INT_BAD_EXTERNAL = 4,
    M05_INT_DELIVERY_OVERFLOW = 5,
    M05_INT_LIF_ERROR = 6,
};

struct M05IntegratedNeuron {
    std::int32_t initial_voltage;
    std::int32_t bias;
    std::int32_t threshold;
    std::int32_t reset_voltage;
};
struct M05IntegratedSynapse {
    std::uint32_t pre;
    std::uint32_t post;
    std::int32_t weight; // signed W16
    std::uint64_t delay; // >=1; beyond finite horizon is discarded
};
struct M05IntegratedExternal {
    std::uint64_t tick;
    std::uint32_t neuron_id;
    std::int32_t current; // signed W16 individual delivery
};
struct M05IntegratedTraceEntry {
    std::uint64_t tick;
    std::uint32_t neuron_id;
    std::int32_t voltage;
    std::uint8_t spike;
    std::uint8_t evaluated; // exact sparse rule, including zero deliveries
    std::uint32_t delivered_count; // individual deliveries at this tick
};

// Each function invocation owns one complete finite run with a fresh state.
// AXI streams plus one AXI-Lite start per RUN, not per tick or neuron.
// Return status is the only publication if any invalid input/overflow occurs;
// the trace stream remains EMPTY on a failed run.
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
    std::uint32_t decay_den);
