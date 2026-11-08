// Host text adapter ONLY; compiled for numeric tests, not synthesized.
#include "m05_stateful.hpp"

#include <charconv>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
template <typename T>
bool parse_value(const std::string &text, T &out) {
    auto result = std::from_chars(text.data(), text.data() + text.size(), out);
    return result.ec == std::errc() &&
           result.ptr == text.data() + text.size();
}
bool fields(const std::string &line, std::size_t count,
            std::vector<std::string> &out) {
    out.clear();
    std::istringstream input(line);
    std::string word;
    while (input >> word) out.push_back(word);
    return out.size() == count;
}
bool parse_command(const std::string &line, M05MemCommand &r) {
    std::vector<std::string> f;
    unsigned opcode = 0;
    if (!fields(line, 11, f) ||
        !parse_value(f[0], opcode) || opcode > 255u ||
        !parse_value(f[1], r.neuron_id) ||
        !parse_value(f[2], r.neuron_count) ||
        !parse_value(f[3], r.tick) ||
        !parse_value(f[4], r.initial_voltage) ||
        !parse_value(f[5], r.aggregated_current) ||
        !parse_value(f[6], r.bias) ||
        !parse_value(f[7], r.threshold) ||
        !parse_value(f[8], r.reset_voltage) ||
        !parse_value(f[9], r.decay_num) ||
        !parse_value(f[10], r.decay_den)) return false;
    r.opcode = static_cast<std::uint8_t>(opcode);
    return true;
}
}

int main() {
    std::string line;
    std::vector<std::string> f;
    std::uint32_t count = 0;
    if (!std::getline(std::cin, line) ||
        !fields(line, 1, f) || !parse_value(f[0], count) ||
        count > 100000u) return 2;
    std::vector<M05MemCommand> commands;
    commands.reserve(count);
    for (std::uint32_t i = 0; i < count; ++i) {
        if (!std::getline(std::cin, line)) return 2;
        M05MemCommand command{};
        if (!parse_command(line, command)) return 2;
        commands.push_back(command);
    }
    while (std::getline(std::cin, line)) {
        if (!line.empty()) return 2;
    }
    hls::stream<M05MemCommand> requests;
    hls::stream<M05MemResponse> responses;
    std::vector<M05MemResponse> all;
    all.reserve(count);
    // Multiple batch invocations in ONE process preserve real C++ static
    // arrays between ap_start-like requests; no Python state emulation.
    for (const auto &command : commands) {
        requests.write(command);
        if (m05_stateful_service(requests, responses, 1) != M05_BATCH_OK)
            return 3;
        all.push_back(responses.read());
    }
    std::cout << count << "\n";
    for (const auto &r : all) {
        std::cout << r.neuron_id << " " << r.tick << " "
                  << static_cast<unsigned>(r.status) << " "
                  << r.voltage << " "
                  << static_cast<unsigned>(r.spike) << "\n";
    }
    return 0;
}
