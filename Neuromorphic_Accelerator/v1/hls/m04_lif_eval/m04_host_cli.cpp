// Host-only line protocol for independent Python M02 differential tests.
// Each input line is: id count tick old_v current bias threshold reset W num den
// Each output line is: id tick status next_v spike
#include "m04_eval.hpp"
#include <iostream>
#include <sstream>
#include <string>
int main() {
    std::string line;
    while (std::getline(std::cin, line)) {
        M04Request r{};
        unsigned bits = 0;
        std::istringstream input(line);
        if (!(input >> r.neuron_id >> r.neuron_count >> r.tick
                >> r.previous_voltage >> r.aggregated_current
                >> r.bias >> r.threshold >> r.reset_voltage
                >> bits >> r.decay_num >> r.decay_den)) {
            return 2; // rejects out-of-range numeric fields, truncated rows
        }
        std::string extra;
        if (bits > 255 || (input >> extra)) { return 2; }
        r.state_bits = static_cast<std::uint8_t>(bits);
        M04Response out{};
        m04_eval_one(r, out);
        std::cout << out.neuron_id << ' ' << out.tick << ' '
                  << unsigned(out.status) << ' ' << out.next_voltage
                  << ' ' << unsigned(out.spike) << '\n';
    }
    return std::cin.eof() ? 0 : 2;
}
