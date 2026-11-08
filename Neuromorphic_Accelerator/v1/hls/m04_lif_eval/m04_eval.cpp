#include "m04_eval.hpp"

// No allocations, floats, v3 ap_int dependency, or persistent state.
// The aggregate must be formed exactly and range-checked by the scheduler.
void m04_eval_one(const M04Request &r, M04Response &out) {
    out.neuron_id = r.neuron_id;
    out.tick = r.tick;
    out.next_voltage = 0;
    out.spike = 0;
    out.status = M04_OK;

    if (r.neuron_count == 0 || r.neuron_id >= r.neuron_count) {
        out.status |= M04_INVALID_ID;
    }
    if (r.state_bits < 4 || r.state_bits > 32) {
        out.status |= M04_INVALID_WIDTH;
    }
    if (r.decay_den == 0 || r.decay_num > r.decay_den) {
        out.status |= M04_INVALID_PARAMETERS;
    }
    // No shift or division before validation: fail closed on invalid input.
    if (out.status != M04_OK) {
        return;
    }

    const std::int64_t lo = -(std::int64_t{1} << (r.state_bits - 1));
    const std::int64_t hi = (std::int64_t{1} << (r.state_bits - 1)) - 1;
    if (r.previous_voltage < lo || r.previous_voltage > hi ||
        r.bias < lo || r.bias > hi ||
        r.threshold <= 0 || r.threshold > hi ||
        r.reset_voltage < lo || r.reset_voltage > hi ||
        r.reset_voltage >= r.threshold) {
        out.status |= M04_INVALID_PARAMETERS;
        return;
    }

    // At state_bits <= 32 and decay_num <= UINT32_MAX, product is int64-safe.
    // Signed C++ division truncates toward zero, including negative voltage.
    const std::int64_t product =
        std::int64_t(r.previous_voltage) * std::int64_t(r.decay_num);
    const std::int64_t decay = product / std::int64_t(r.decay_den);
    const std::int64_t offset = decay + std::int64_t(r.bias);

    // Avoid signed int64 overflow before clamping an extreme aggregate. Exact
    // clamp of decay+bias+aggregate with ONE saturation, independent of order.
    std::int64_t bounded = 0;
    if (r.aggregated_current > hi - offset) {
        bounded = hi;
    } else if (r.aggregated_current < lo - offset) {
        bounded = lo;
    } else {
        bounded = offset + r.aggregated_current;
    }
    out.spike = (bounded >= r.threshold) ? 1 : 0;
    out.next_voltage = out.spike ? r.reset_voltage : std::int32_t(bounded);
}
