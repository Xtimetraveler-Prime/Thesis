#pragma once
#include <cstdint>

// M02 revision-1 one-neuron/tick boundary. This is a HOST-TESTED candidate;
// not a synthesized IP, memory protocol, scheduler, or hardware timing claim.
struct M04Request {
    std::uint32_t neuron_id;
    std::uint32_t neuron_count;
    std::uint64_t tick;
    std::int32_t previous_voltage;
    std::int64_t aggregated_current;
    std::int32_t bias;
    std::int32_t threshold;
    std::int32_t reset_voltage;
    std::uint8_t state_bits;
    std::uint32_t decay_num;
    std::uint32_t decay_den;
};
struct M04Response {
    std::uint32_t neuron_id;
    std::uint64_t tick;
    std::int32_t next_voltage;
    std::uint8_t spike;
    std::uint8_t status;
};

enum M04Status : std::uint8_t {
    M04_OK = 0,
    M04_INVALID_ID = 1,
    M04_INVALID_WIDTH = 2,
    M04_INVALID_PARAMETERS = 4,
};

void m04_eval_one(const M04Request &request, M04Response &response);
