// Independent Vitis Csim inputs (also compiled under native g++ for smoke).
// This is NOT an RTL/AXIS timing or physical memory utilization test.
#include "m05_stateful.hpp"
#include <cstdint>
#include <iostream>

static M05MemCommand command(std::uint8_t op, std::uint32_t id,
                             std::uint64_t tick, std::int32_t initial = 0,
                             std::int64_t current = 0,
                             std::int32_t bias = 0,
                             std::int32_t threshold = 5,
                             std::int32_t reset = 0,
                             std::uint32_t num = 1,
                             std::uint32_t den = 1) {
    M05MemCommand c{};
    c.opcode=op; c.neuron_id=id; c.neuron_count=1; c.tick=tick;
    c.initial_voltage=initial; c.aggregated_current=current;
    c.bias=bias; c.threshold=threshold; c.reset_voltage=reset;
    c.decay_num=num; c.decay_den=den;
    return c;
}
static bool apply(const M05MemCommand &c, std::uint8_t wanted_status,
                  std::int32_t wanted_voltage, std::uint8_t wanted_spike) {
    hls::stream<M05MemCommand> in;
    hls::stream<M05MemResponse> out;
    in.write(c);
    if (m05_stateful_service(in,out,1) != M05_BATCH_OK || out.empty())
        return false;
    const M05MemResponse x = out.read();
    return x.status == wanted_status && x.voltage == wanted_voltage &&
           x.spike == wanted_spike && x.neuron_id == c.neuron_id &&
           x.tick == c.tick && out.empty() && in.empty();
}
int main() {
    if (!apply(command(M05_MEM_CLEAR,0,0),M05_MEM_OK,0,0) ||
        !apply(command(M05_MEM_READ,0,0),M05_MEM_UNINITIALIZED,0,0) ||
        !apply(command(M05_MEM_INIT,0,0,-3),M05_MEM_OK,-3,0) ||
        !apply(command(M05_MEM_STEP,0,0,0,0,0,5,0,1,2),
               M05_MEM_OK,-1,0) ||
        !apply(command(M05_MEM_STEP,0,0,0,0,0,5,0,1,2),
               M05_MEM_DUPLICATE_TICK,0,0) ||
        !apply(command(M05_MEM_READ,0,0),M05_MEM_OK,-1,0) ||
        !apply(command(M05_MEM_STEP,0,1,0,6),
               M05_MEM_OK,0,1) ||
        !apply(command(M05_MEM_STEP,0,0),
               M05_MEM_STALE_TICK,0,0) ||
        !apply(command(M05_MEM_CLEAR,0,0),M05_MEM_OK,0,0) ||
        !apply(command(M05_MEM_READ,0,0),M05_MEM_UNINITIALIZED,0,0)) {
        std::cerr << "FAIL: persistent on-chip state contract\n";
        return 1;
    }
    hls::stream<M05MemCommand> in;
    hls::stream<M05MemResponse> out;
    if (m05_stateful_service(in, out, M05_MAX_BATCH + 1)
        != M05_BATCH_TOO_LARGE || !in.empty() || !out.empty()) {
        std::cerr << "FAIL: command batch guard\n";
        return 1;
    }
    std::cout << "PASS: M05 local-memory C simulation oracle vectors\n";
    return 0;
}
