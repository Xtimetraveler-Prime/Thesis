// Host-only text adapter; never part of synthesis.
#include "m05_accumulator.hpp"
#include <charconv>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
template<typename T> bool parse(const std::string &s, T &v) {
    auto result = std::from_chars(s.data(), s.data() + s.size(), v);
    return result.ec == std::errc() &&
           result.ptr == s.data() + s.size();
}
bool decode(const std::string &line, M05AccumCommand &cmd) {
    std::istringstream input(line);
    std::vector<std::string> f;
    std::string word;
    while (input >> word) f.push_back(word);
    unsigned op = 0;
    if (f.size() != 5 || !parse(f[0], op) || op > 255u ||
        !parse(f[1], cmd.neuron_id) || !parse(f[2], cmd.neuron_count) ||
        !parse(f[3], cmd.tick) || !parse(f[4], cmd.current)) return false;
    cmd.opcode = static_cast<std::uint8_t>(op);
    return true;
}
}
int main() {
    std::string line;
    if (!std::getline(std::cin, line)) return 2;
    std::uint32_t count = 0;
    if (!parse(line, count) || count > 100000u) return 2;
    std::vector<M05AccumCommand> commands;
    commands.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
        if (!std::getline(std::cin, line)) return 2;
        M05AccumCommand cmd{};
        if (!decode(line, cmd)) return 2;
        commands.push_back(cmd);
    }
    while (std::getline(std::cin, line)) {
        if (!line.empty()) return 2;
    }
    hls::stream<M05AccumCommand> requests;
    hls::stream<M05AccumResponse> responses;
    std::vector<M05AccumResponse> out;
    out.reserve(count);
    for (const auto &command : commands) {
        requests.write(command);
        if (m05_event_accumulator(requests, responses, 1) != M05_BATCH_OK)
            return 3;
        out.push_back(responses.read());
    }
    std::cout << count << "\n";
    for (const auto &r : out)
        std::cout << r.neuron_id << " " << r.tick << " "
                  << static_cast<unsigned>(r.status) << " "
                  << r.aggregate << " "
                  << static_cast<unsigned>(r.touched) << " "
                  << r.accepted_events << "\n";
    return 0;
}
