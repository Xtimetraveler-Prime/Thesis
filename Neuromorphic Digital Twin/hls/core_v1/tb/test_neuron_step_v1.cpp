#include <iostream>

#include "neuron_step_v1.hpp"

using namespace neuromorphic_hls;

namespace {

struct TestVector {
    const char *name;
    long long current_before;
    long long voltage_before;
    unsigned refractory_before;
    long long synaptic_input;
    unsigned current_decay;
    unsigned voltage_decay;
    long long threshold;
    long long bias;
    long long reset_voltage;
    unsigned refractory_ticks;
    long long expected_current;
    long long expected_voltage;
    unsigned expected_refractory;
    unsigned expected_spike;
};

bool run_case(const TestVector &v) {
    state_t current_after = 0;
    state_t voltage_after = 0;
    refractory_t refractory_after = 0;
    spike_t spiked = 0;

    neuron_step_v1(
        state_t(v.current_before),
        state_t(v.voltage_before),
        refractory_t(v.refractory_before),
        accumulator_t(v.synaptic_input),
        decay_t(v.current_decay),
        decay_t(v.voltage_decay),
        state_t(v.threshold),
        state_t(v.bias),
        state_t(v.reset_voltage),
        refractory_t(v.refractory_ticks),
        &current_after,
        &voltage_after,
        &refractory_after,
        &spiked);

    const long long actual_current = current_after.to_int64();
    const long long actual_voltage = voltage_after.to_int64();
    const unsigned actual_refractory = refractory_after.to_uint();
    const unsigned actual_spike = spiked.to_uint();

    const bool passed =
        actual_current == v.expected_current &&
        actual_voltage == v.expected_voltage &&
        actual_refractory == v.expected_refractory &&
        actual_spike == v.expected_spike;

    if (!passed) {
        std::cerr
            << "FAIL " << v.name
            << ": expected (I=" << v.expected_current
            << ", V=" << v.expected_voltage
            << ", R=" << v.expected_refractory
            << ", spike=" << v.expected_spike
            << ") got (I=" << actual_current
            << ", V=" << actual_voltage
            << ", R=" << actual_refractory
            << ", spike=" << actual_spike << ")\n";
    }

    return passed;
}

}  // namespace

int main() {
    const TestVector cases[] = {
        {
            "spike_no_decay",
            0, 0, 0, 6,
            0, 0,
            5, 0, 0, 0,
            6, 0, 0, 1,
        },
        {
            "strict_threshold_equality",
            0, 0, 0, 5,
            0, 0,
            5, 0, 0, 0,
            5, 5, 0, 0,
        },
        {
            "input_before_half_current_decay",
            0, 0, 0, 128,
            2048, 0,
            1000, 0, 0, 0,
            64, 128, 0, 0,
        },
        {
            "negative_half_decay_rounds_away_from_zero",
            -5, 0, 0, 0,
            2048, 0,
            1000, 0, 0, 0,
            -2, -5, 0, 0,
        },
        {
            "positive_working_current_saturation",
            STATE_MAX, 0, 0, 10,
            0, 0,
            STATE_MAX, 0, 0, 0,
            STATE_MAX, STATE_MAX, 0, 0,
        },
        {
            "negative_working_current_saturation",
            STATE_MIN, 0, 0, -10,
            0, 0,
            1, 0, 0, 0,
            STATE_MIN, STATE_MIN, 0, 0,
        },
        {
            "refractory_holds_reset_but_updates_current",
            100, 99, 2, 28,
            2048, 4096,
            1000, 50, -7, 3,
            64, -7, 1, 0,
        },
        {
            "spike_loads_future_refractory_ticks",
            0, 0, 0, 6,
            0, 0,
            5, 0, -1, 3,
            6, -1, 2, 1,
        },
        {
            "refractory_one_has_no_future_blocked_tick",
            0, 0, 0, 6,
            0, 0,
            5, 0, -1, 1,
            6, -1, 0, 1,
        },
        {
            "voltage_decay_then_current_then_bias",
            0, 100, 0, 10,
            0, 2048,
            100, -5, 0, 0,
            10, 55, 0, 0,
        },
        {
            "full_decay_removes_negative_current",
            -123, 0, 0, 0,
            4096, 0,
            1000, 0, 0, 0,
            0, -123, 0, 0,
        },
    };

    unsigned failures = 0;
    for (const auto &test_case : cases) {
        if (!run_case(test_case)) {
            ++failures;
        }
    }

    if (failures != 0) {
        std::cerr << failures << " M11.1 HLS test vector(s) failed\n";
        return 1;
    }

    std::cout << "M11.1 HLS neuron-step tests passed: "
              << (sizeof(cases) / sizeof(cases[0])) << " cases\n";
    return 0;
}
