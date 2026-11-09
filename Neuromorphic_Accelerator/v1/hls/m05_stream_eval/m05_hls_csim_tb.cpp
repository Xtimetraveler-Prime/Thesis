// Genuine Vitis HLS C-simulation *input* if tool is installed.
// This file is source-only until an operator runs the offline HLS tool.
// No board, AXI DDR or JTAG operations.
#include "m05_stream.hpp"
#include <cstdint>
#include <iostream>

namespace {
M04Request request(std::uint32_t id, std::uint32_t count, std::uint64_t tick,
                   std::int32_t prior, std::int64_t current,
                   std::int32_t bias, std::int32_t threshold,
                   std::int32_t reset, std::uint8_t bits,
                   std::uint32_t num, std::uint32_t den) {
    M04Request r{};
    r.neuron_id=id; r.neuron_count=count; r.tick=tick; r.previous_voltage=prior;
    r.aggregated_current=current; r.bias=bias; r.threshold=threshold;
    r.reset_voltage=reset; r.state_bits=bits; r.decay_num=num; r.decay_den=den;
    return r;
}
bool expect(hls::stream<M04Response> &out, std::uint32_t id,
            std::uint64_t tick, std::uint8_t status,
            std::int32_t voltage, std::uint8_t spike) {
    if (out.empty()) return false;
    const M04Response r = out.read();
    return r.neuron_id == id && r.tick == tick && r.status == status
        && r.next_voltage == voltage && r.spike == spike;
}
}

int main() {
    hls::stream<M04Request> requests;
    hls::stream<M04Response> responses;
    requests.write(request(0,3,0,-3,0,0,5,0,16,1,2));
    requests.write(request(1,3,0,0,5,0,5,-2,16,1,1));
    requests.write(request(2,3,0,0,0,0,5,0,3,1,1));
    if (m05_stream_eval(requests, responses, 3) != M05_BATCH_OK
        || !expect(responses,0,0,M04_OK,-1,0)
        || !expect(responses,1,0,M04_OK,-2,1)
        || !expect(responses,2,0,M04_INVALID_WIDTH,0,0)
        || !responses.empty()) {
        std::cerr << "FAIL: M05 per-request parity or response order\n";
        return 1;
    }
    if (m05_stream_eval(requests, responses, M05_MAX_BATCH+1)
        != M05_BATCH_TOO_LARGE || !responses.empty()) {
        std::cerr << "FAIL: oversized batch should fail before stream reads\n";
        return 1;
    }
    if (m05_stream_eval(requests, responses, 0)
        != M05_BATCH_OK || !responses.empty()) {
        std::cerr << "FAIL: zero batch\n";
        return 1;
    }
    std::cout << "PASS: M05 isolated stream C simulation oracle vectors\n";
    return 0;
}
