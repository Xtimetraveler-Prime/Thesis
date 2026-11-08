#pragma once

#include "../m04_lif_eval/m04_eval.hpp"
#include <cstdint>

// Real Vitis HLS uses its supplied stream implementation. The tiny host-only
// fallback is for native g++ functional tests, NEVER evidence of AXIS timing.
#if defined(__SYNTHESIS__) || __has_include(<hls_stream.h>)
#include <hls_stream.h>
#else
#include <queue>
#include <stdexcept>
namespace hls {
template <typename T> class stream {
public:
    void write(const T &value) { values_.push(value); }
    T read() {
        if (values_.empty()) throw std::runtime_error("M05 host stream underflow");
        const T value = values_.front();
        values_.pop();
        return value;
    }
    bool empty() const { return values_.empty(); }
private:
    std::queue<T> values_;
};
}  // namespace hls
#endif

// 1,024 operations per invocation is a proposed on-chip batch, NOT total
// logical-network or timestep capacity and NOT the 4,096-arrival limit.
constexpr std::uint32_t M05_MAX_BATCH = 1024;
constexpr std::uint32_t M05_BATCH_OK = 0;
constexpr std::uint32_t M05_BATCH_TOO_LARGE = 1;

// Per-batch ap_ctrl_hs, NOT one A53 ap_start per logical neuron.
// Exact request/response semantics are those of accepted M02 via M04Request.
std::uint32_t m05_stream_eval(
    hls::stream<M04Request> &requests,
    hls::stream<M04Response> &responses,
    std::uint32_t request_count);
