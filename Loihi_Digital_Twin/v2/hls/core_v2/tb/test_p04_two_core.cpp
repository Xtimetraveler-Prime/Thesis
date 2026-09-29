#include <iostream>

#include "loihi_core_v2.hpp"

using namespace loihi_v2_hls;

namespace {

constexpr unsigned P04_SEED_MAX_COMPARTMENTS = 4;
constexpr unsigned P04_SEED_MAX_EVENTS = 8;
constexpr unsigned P04_SEED_MAX_PACKETS = 8;
constexpr unsigned P04_FIXTURE_MAX_AXON = 64;

struct Word128Seed {
    unsigned index;
    unsigned long long lo;
    unsigned long long hi;
};

struct Word64Seed {
    unsigned index;
    unsigned long long word;
};

struct Word32Seed {
    unsigned index;
    unsigned word;
};

struct ExpectedCompartment {
    unsigned long long state_before;
    long long synaptic_input;
    unsigned long long state_after;
    unsigned spike;
};

struct CoreSeed {
    unsigned core_id;
    unsigned compartment_count;
    unsigned synapse_count;
    unsigned route_count;
    const Word128Seed *config;
    unsigned config_count;
    const Word64Seed *state;
    unsigned state_count;
    const Word64Seed *axon;
    unsigned axon_count;
    const Word64Seed *synapse;
    unsigned synapse_seed_count;
    const Word32Seed *route_desc;
    unsigned route_desc_count;
    const Word32Seed *route;
    unsigned route_seed_count;
};

struct CoreTickExpected {
    unsigned event_count;
    unsigned events[P04_SEED_MAX_EVENTS];
    ExpectedCompartment expected[P04_SEED_MAX_COMPARTMENTS];
    unsigned packet_count;
    unsigned long long packets[P04_SEED_MAX_PACKETS];
};

struct TwoCoreTickSeed {
    unsigned timestep;
    CoreTickExpected core[2];
    unsigned local_packet_count;
    unsigned remote_packet_count;
};

struct P04ScenarioSeed {
    const char *name;
    CoreSeed core[2];
    const TwoCoreTickSeed *ticks;
    unsigned tick_count;
};

#include "generated_p04_vectors.inc"

struct CoreMemory {
    config_word_t config_words[MAX_COMPARTMENTS];
    state_word_t state_words[MAX_COMPARTMENTS];
    axon_word_t axon_words[MAX_INPUT_AXONS];
    synapse_word_t synapse_words[MAX_SYNAPSE_ENTRIES];
    route_desc_word_t route_desc_words[MAX_COMPARTMENTS];
    route_word_t route_words[MAX_OUTPUT_ROUTES];
    event_axon_t input_events[MAX_INPUT_EVENTS];
    trace_word_t trace_words[MAX_COMPARTMENTS];
    packet_word_t packet_words[MAX_OUTPUT_ROUTES];
};

static CoreMemory memories[2];

void clear_core(CoreMemory &memory) {
    for (int i = 0; i < MAX_COMPARTMENTS; ++i) {
        memory.config_words[i] = 0;
        memory.state_words[i] = 0;
        memory.route_desc_words[i] = 0;
        memory.trace_words[i] = 0;
    }
    for (int i = 0; i < MAX_INPUT_AXONS; ++i) {
        memory.axon_words[i] = 0;
        memory.input_events[i] = 0;
    }
    for (int i = 0; i < MAX_SYNAPSE_ENTRIES; ++i) {
        memory.synapse_words[i] = 0;
    }
    for (int i = 0; i < MAX_OUTPUT_ROUTES; ++i) {
        memory.route_words[i] = 0;
        memory.packet_words[i] = 0;
    }
}

void load_core(const CoreSeed &seed, CoreMemory &memory) {
    clear_core(memory);
    for (unsigned i = 0; i < seed.config_count; ++i) {
        config_word_t word = 0;
        word.range(63, 0) = seed.config[i].lo;
        word.range(127, 64) = seed.config[i].hi;
        memory.config_words[seed.config[i].index] = word;
    }
    for (unsigned i = 0; i < seed.state_count; ++i) {
        memory.state_words[seed.state[i].index] = seed.state[i].word;
    }
    for (unsigned i = 0; i < seed.axon_count; ++i) {
        memory.axon_words[seed.axon[i].index] = seed.axon[i].word;
    }
    for (unsigned i = 0; i < seed.synapse_seed_count; ++i) {
        memory.synapse_words[seed.synapse[i].index] = seed.synapse[i].word;
    }
    for (unsigned i = 0; i < seed.route_desc_count; ++i) {
        memory.route_desc_words[seed.route_desc[i].index] = seed.route_desc[i].word;
    }
    for (unsigned i = 0; i < seed.route_seed_count; ++i) {
        memory.route_words[seed.route[i].index] = seed.route[i].word;
    }
}

bool same_events_unordered(
    const event_axon_t *actual,
    unsigned actual_count,
    const unsigned *expected,
    unsigned expected_count) {
    if (actual_count != expected_count || expected_count > P04_SEED_MAX_EVENTS) {
        return false;
    }
    bool used[P04_SEED_MAX_EVENTS] = {};
    for (unsigned i = 0; i < actual_count; ++i) {
        const unsigned value = actual[i].to_uint();
        bool found = false;
        for (unsigned j = 0; j < expected_count; ++j) {
            if (!used[j] && value == expected[j]) {
                used[j] = true;
                found = true;
                break;
            }
        }
        if (!found) {
            return false;
        }
    }
    return true;
}

unsigned compare_core_tick(
    const char *scenario,
    const CoreSeed &core_seed,
    const CoreTickExpected &expected,
    CoreMemory &memory,
    unsigned actual_event_count,
    unsigned timestep,
    ap_uint<13> *packet_count_out) {
    unsigned failures = 0;

    if (!same_events_unordered(
            memory.input_events,
            actual_event_count,
            expected.events,
            expected.event_count)) {
        ++failures;
        std::cerr << "FAIL P04 " << scenario << " t=" << timestep
                  << " core=" << core_seed.core_id
                  << ": routed input-event set mismatch\n";
    }

    ap_uint<11> spike_count = 0;
    ap_uint<13> packet_count = 0;
    status_t status = 0;

    loihi_core_v2_tick(
        core_seed.compartment_count,
        actual_event_count,
        core_seed.synapse_count,
        core_seed.route_count,
        timestep,
        memory.config_words,
        memory.state_words,
        memory.axon_words,
        memory.synapse_words,
        memory.route_desc_words,
        memory.route_words,
        memory.input_events,
        memory.trace_words,
        memory.packet_words,
        &spike_count,
        &packet_count,
        &status);

    unsigned expected_spikes = 0;
    for (unsigned compartment = 0;
         compartment < core_seed.compartment_count;
         ++compartment) {
        const ExpectedCompartment &want = expected.expected[compartment];
        const trace_word_t trace = memory.trace_words[compartment];
        const unsigned long long before = trace.range(63, 0).to_uint64();
        const long long synaptic =
            ap_int<64>(trace.range(127, 64)).to_int64();
        const unsigned long long after = trace.range(191, 128).to_uint64();
        const unsigned spike = trace[192] ? 1u : 0u;
        expected_spikes += want.spike;

        if (before != want.state_before
            || synaptic != want.synaptic_input
            || after != want.state_after
            || spike != want.spike
            || memory.state_words[compartment].to_uint64() != want.state_after
            || trace.range(255, 193) != 0) {
            ++failures;
            std::cerr << "FAIL P04 " << scenario << " t=" << timestep
                      << " core=" << core_seed.core_id
                      << " compartment=" << compartment
                      << ": differential state/trace mismatch\n";
        }
    }

    if (status != 0) {
        ++failures;
        std::cerr << "FAIL P04 " << scenario << " t=" << timestep
                  << " core=" << core_seed.core_id
                  << ": status=0x" << std::hex << status.to_uint()
                  << std::dec << "\n";
    }
    if (spike_count.to_uint() != expected_spikes) {
        ++failures;
        std::cerr << "FAIL P04 " << scenario << " t=" << timestep
                  << " core=" << core_seed.core_id
                  << ": spike_count=" << spike_count.to_uint()
                  << " expected=" << expected_spikes << "\n";
    }
    if (packet_count.to_uint() != expected.packet_count) {
        ++failures;
        std::cerr << "FAIL P04 " << scenario << " t=" << timestep
                  << " core=" << core_seed.core_id
                  << ": packet_count=" << packet_count.to_uint()
                  << " expected=" << expected.packet_count << "\n";
    } else {
        for (unsigned packet = 0; packet < expected.packet_count; ++packet) {
            const unsigned long long actual = memory.packet_words[packet].to_uint64();
            if (actual != expected.packets[packet]) {
                ++failures;
                std::cerr << "FAIL P04 " << scenario << " t=" << timestep
                          << " core=" << core_seed.core_id
                          << " packet=" << packet
                          << ": packet word mismatch\n";
            }
        }
    }

    *packet_count_out = packet_count;
    return failures;
}

bool route_packet(
    unsigned source_core,
    packet_word_t packet,
    unsigned timestep,
    event_axon_t next_events[2][P04_SEED_MAX_EVENTS],
    unsigned next_event_count[2],
    unsigned *local_count,
    unsigned *remote_count) {
    if (!packet[61] || packet.range(63, 62) != 0) {
        return false;
    }
    const unsigned destination = packet.range(6, 0).to_uint();
    const unsigned axon = packet.range(18, 7).to_uint();
    const unsigned target_timestep = packet.range(60, 29).to_uint();
    if (destination > 1
        || axon >= P04_FIXTURE_MAX_AXON
        || target_timestep != timestep + 1
        || next_event_count[destination] >= P04_SEED_MAX_EVENTS) {
        return false;
    }
    next_events[destination][next_event_count[destination]++] = axon;
    if (destination == source_core) {
        ++(*local_count);
    } else {
        ++(*remote_count);
    }
    return true;
}

unsigned run_scenario(const P04ScenarioSeed &scenario, bool reverse_service) {
    load_core(scenario.core[0], memories[0]);
    load_core(scenario.core[1], memories[1]);

    unsigned failures = 0;
    unsigned event_count[2] = {
        scenario.ticks[0].core[0].event_count,
        scenario.ticks[0].core[1].event_count,
    };
    for (unsigned core = 0; core < 2; ++core) {
        for (unsigned i = 0; i < event_count[core]; ++i) {
            memories[core].input_events[i] = scenario.ticks[0].core[core].events[i];
        }
    }

    for (unsigned tick_index = 0; tick_index < scenario.tick_count; ++tick_index) {
        const TwoCoreTickSeed &tick = scenario.ticks[tick_index];
        ap_uint<13> packet_count[2] = {0, 0};
        const unsigned first = reverse_service ? 1u : 0u;
        const unsigned second = reverse_service ? 0u : 1u;

        failures += compare_core_tick(
            scenario.name,
            scenario.core[first],
            tick.core[first],
            memories[first],
            event_count[first],
            tick.timestep,
            &packet_count[first]);
        failures += compare_core_tick(
            scenario.name,
            scenario.core[second],
            tick.core[second],
            memories[second],
            event_count[second],
            tick.timestep,
            &packet_count[second]);

        event_axon_t next_events[2][P04_SEED_MAX_EVENTS] = {};
        unsigned next_event_count[2] = {0, 0};
        unsigned local_count = 0;
        unsigned remote_count = 0;

        const unsigned source_order[2] = {first, second};
        for (unsigned source_index = 0; source_index < 2; ++source_index) {
            const unsigned source = source_order[source_index];
            const unsigned count = packet_count[source].to_uint();
            for (unsigned ordinal = 0; ordinal < count; ++ordinal) {
                const unsigned packet_index = reverse_service
                    ? count - ordinal - 1
                    : ordinal;
                if (!route_packet(
                        source,
                        memories[source].packet_words[packet_index],
                        tick.timestep,
                        next_events,
                        next_event_count,
                        &local_count,
                        &remote_count)) {
                    ++failures;
                    std::cerr << "FAIL P04 " << scenario.name
                              << " t=" << tick.timestep
                              << ": packet routing integrity failure\n";
                }
            }
        }

        if (local_count != tick.local_packet_count
            || remote_count != tick.remote_packet_count) {
            ++failures;
            std::cerr << "FAIL P04 " << scenario.name
                      << " t=" << tick.timestep
                      << ": local/remote count=" << local_count << "/"
                      << remote_count << " expected="
                      << tick.local_packet_count << "/"
                      << tick.remote_packet_count << "\n";
        }

        for (unsigned core = 0; core < 2; ++core) {
            for (int i = 0; i < MAX_INPUT_EVENTS; ++i) {
                memories[core].input_events[i] = 0;
            }
            event_count[core] = next_event_count[core];
            for (unsigned i = 0; i < next_event_count[core]; ++i) {
                memories[core].input_events[i] = next_events[core][i];
            }
        }
    }

    if (failures == 0) {
        std::cout << "P04 HLS two-core scenario passed: " << scenario.name
                  << " service=" << (reverse_service ? "reverse" : "forward")
                  << " ticks=" << scenario.tick_count << "\n";
    }
    return failures;
}

}  // namespace

int main() {
    unsigned failures = 0;
    for (unsigned scenario = 0; scenario < P04_SCENARIO_COUNT; ++scenario) {
        failures += run_scenario(P04_SCENARIOS[scenario], false);
        failures += run_scenario(P04_SCENARIOS[scenario], true);
    }

    if (failures != 0) {
        std::cerr << failures << " P04 two-core HLS differential check(s) failed\n";
        return 1;
    }
    std::cout << "PASS: P04 Python/HLS two-core integration differential completed successfully.\n";
    return 0;
}
