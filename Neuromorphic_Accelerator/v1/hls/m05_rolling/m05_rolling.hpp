#pragma once
#include "../m05_integrated/m05_integrated.hpp"

// M05 experimental 8-slot *rolling* temporal-wheel alternative to the proven
// eight-tick finite-run top. Tick count may exceed slot count without growing
// the event-state memory. Max 64 ticks per invocation is a safety/test profile,
// NOT unbounded/continuous operation or a complete AXIS hardware proof.
// Inputs MUST be sorted nondecreasing by tick (unlike the finite-run top).
constexpr std::uint32_t M05_ROLLING_SLOTS = 8;
constexpr std::uint32_t M05_ROLLING_MAX_TICKS = 64;
constexpr std::uint32_t M05_ROLLING_MAX_DELAY = M05_ROLLING_SLOTS;
constexpr std::uint32_t M05_ROLLING_MAX_EXTERNAL =
    M05_ROLLING_MAX_TICKS * M05_INT_MAX_PER_TICK;

enum M05RollingStatus : std::uint32_t {
    M05_ROLL_OK = 0,
    M05_ROLL_BAD_SHAPE = 1,
    M05_ROLL_BAD_NEURON = 2,
    M05_ROLL_BAD_SYNAPSE = 3,
    M05_ROLL_BAD_EXTERNAL = 4,
    M05_ROLL_DELIVERY_OVERFLOW = 5,
    M05_ROLL_LIF_ERROR = 6,
};

// This top emits a tick's trace ONLY AFTER its own fanout capacity checks
// succeed, but earlier ticks MAY already have been emitted before a later
// failure. A NONZERO return invalidates ALL emitted rows: the consumer MUST
// buffer or discard them until the final ap_done/status is known.
// This is deliberately DIFFERENT from the eight-tick all-or-nothing top.
// A separate protocol for terminal-error invalidation remains M05 work.
std::uint32_t m05_rolling_replay(
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
