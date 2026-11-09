// Standalone HLS Csim testbench, native smoke does NOT prove Vitis/RTL.
// Checks tick seal, exact canceled signed sum, sticky errors and clear.
#include "m05_accumulator.hpp"
#include <cstdint>
#include <iostream>

namespace {
M05AccumCommand cmd(std::uint8_t op, std::uint32_t neuron, std::uint64_t tick,
                    std::int32_t current = 0, std::uint32_t count = 2) {
    M05AccumCommand c{};
    c.opcode=op; c.neuron_id=neuron; c.neuron_count=count; c.tick=tick;
    c.current=current;
    return c;
}
bool check(M05AccumCommand command, std::uint8_t status,
           std::int64_t aggregate, std::uint8_t touched,
           std::uint32_t arrivals) {
    hls::stream<M05AccumCommand> in;
    hls::stream<M05AccumResponse> out;
    in.write(command);
    if (m05_event_accumulator(in, out, 1) != M05_BATCH_OK || out.empty())
        return false;
    const auto r = out.read();
    return r.status==status && r.aggregate==aggregate &&
           r.touched==touched && r.accepted_events==arrivals &&
           r.neuron_id==command.neuron_id && r.tick==command.tick &&
           in.empty() && out.empty();
}
}
int main() {
    if (!check(cmd(M05_ACC_CLEAR,0,0),M05_ACC_OK,0,0,0) ||
        !check(cmd(M05_ACC_BEGIN,0,9),M05_ACC_OK,0,0,0) ||
        !check(cmd(M05_ACC_ADD,1,9,32767),M05_ACC_OK,0,0,1) ||
        !check(cmd(M05_ACC_ADD,1,9,-32768),M05_ACC_OK,0,0,2) ||
        !check(cmd(M05_ACC_ADD,1,9,6),M05_ACC_OK,0,0,3) ||
        !check(cmd(M05_ACC_SEAL,0,9),M05_ACC_OK,0,0,3) ||
        !check(cmd(M05_ACC_READ,1,9),M05_ACC_OK,5,1,3) ||
        !check(cmd(M05_ACC_READ,0,9),M05_ACC_OK,0,0,3) ||
        !check(cmd(M05_ACC_ADD,1,9,5),M05_ACC_BAD_PHASE,0,0,3) ||
        !check(cmd(M05_ACC_READ,1,9),M05_ACC_STICKY_FAILURE,0,0,3) ||
        !check(cmd(M05_ACC_CLEAR,0,0),M05_ACC_OK,0,0,0) ||
        !check(cmd(M05_ACC_BEGIN,0,10),M05_ACC_OK,0,0,0) ||
        !check(cmd(M05_ACC_SEAL,0,10),M05_ACC_OK,0,0,0) ||
        !check(cmd(M05_ACC_END,0,10),M05_ACC_OK,0,0,0)) {
        std::cerr << "FAIL: M05 tick-sealed accumulator Csim vectors\n";
        return 1;
    }
    hls::stream<M05AccumCommand> in;
    hls::stream<M05AccumResponse> out;
    if (m05_event_accumulator(in, out, M05_MAX_BATCH+1)
        != M05_BATCH_TOO_LARGE || !in.empty() || !out.empty()) {
        std::cerr << "FAIL: accumulator command batch guard\n";
        return 1;
    }
    std::cout << "PASS: M05 signed accumulator C simulation oracle vectors\n";
    return 0;
}
