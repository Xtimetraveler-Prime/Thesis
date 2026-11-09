// Native host ONLY: newline protocol around the SAME M05 batch engine.
// This is not used as an FPGA PS/PL transport, benchmark or DDR driver.
#include "m05_stream.hpp"

#include <charconv>
#include <cstdint>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

namespace {
template <typename T> bool parse_number(const std::string &s, T &out) {
    if (s.empty()) return false;
    const char *begin = s.data();
    const char *end = begin + s.size();
    auto result = std::from_chars(begin, end, out);
    return result.ec == std::errc() && result.ptr == end;
}
bool tokenize(const std::string &line, std::size_t expected,
              std::vector<std::string> &fields) {
    fields.clear();
    std::istringstream input(line);
    std::string word;
    while (input >> word) fields.push_back(word);
    return fields.size() == expected;
}
bool parse_request(const std::string &line, M04Request &r) {
    std::vector<std::string> f;
    unsigned width = 0;
    if (!tokenize(line, 11, f)) return false;
    if (!parse_number(f[0], r.neuron_id)
        || !parse_number(f[1], r.neuron_count)
        || !parse_number(f[2], r.tick)
        || !parse_number(f[3], r.previous_voltage)
        || !parse_number(f[4], r.aggregated_current)
        || !parse_number(f[5], r.bias)
        || !parse_number(f[6], r.threshold)
        || !parse_number(f[7], r.reset_voltage)
        || !parse_number(f[8], width)
        || width > 255u
        || !parse_number(f[9], r.decay_num)
        || !parse_number(f[10], r.decay_den)) return false;
    r.state_bits = static_cast<std::uint8_t>(width);
    return true;
}
}  // namespace

int main() {
    std::string line;
    if (!std::getline(std::cin, line)) return 2;
    std::vector<std::string> fields;
    std::uint32_t count = 0;
    if (!tokenize(line, 1, fields) || !parse_number(fields[0], count)
        || count > M05_MAX_BATCH) return 2;

    hls::stream<M04Request> requests;
    hls::stream<M04Response> responses;
    for (std::uint32_t i = 0; i < count; ++i) {
        if (!std::getline(std::cin, line)) return 2;
        M04Request request{};
        if (!parse_request(line, request)) return 2;
        requests.write(request);
    }
    // Reject trailing input rather than silently ignoring a partial batch.
    while (std::getline(std::cin, line)) {
        if (!line.empty()) return 2;
    }
    const std::uint32_t status = m05_stream_eval(requests, responses, count);
    if (status != M05_BATCH_OK) return 2;
    std::cout << status << " " << count << "\n";
    for (std::uint32_t i = 0; i < count; ++i) {
        const M04Response r = responses.read();
        std::cout << r.neuron_id << " " << r.tick << " "
                  << static_cast<unsigned>(r.status) << " "
                  << r.next_voltage << " "
                  << static_cast<unsigned>(r.spike) << "\n";
    }
    return 0;
}
