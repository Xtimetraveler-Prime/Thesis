#include <iostream>

#include "loihi_core_v2.hpp"

using namespace loihi_v2_hls;

namespace {

constexpr unsigned SEED_MAX_COMPARTMENTS = 8;
constexpr unsigned SEED_MAX_EVENTS = 8;
constexpr unsigned SEED_MAX_PACKETS = 8;

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

struct TickSeed {
    unsigned timestep;
    unsigned event_count;
    unsigned events[SEED_MAX_EVENTS];
    ExpectedCompartment expected[SEED_MAX_COMPARTMENTS];
    unsigned packet_count;
    unsigned long long packets[SEED_MAX_PACKETS];
};

#include "generated_p03_vectors.inc"

static config_word_t config_words[MAX_COMPARTMENTS];
static state_word_t state_words[MAX_COMPARTMENTS];
static axon_word_t axon_words[MAX_INPUT_AXONS];
static synapse_word_t synapse_words[MAX_SYNAPSE_ENTRIES];
static route_desc_word_t route_desc_words[MAX_COMPARTMENTS];
static route_word_t route_words[MAX_OUTPUT_ROUTES];
static event_axon_t input_events[MAX_INPUT_EVENTS];
static trace_word_t trace_words[MAX_COMPARTMENTS];
static packet_word_t packet_words[MAX_OUTPUT_ROUTES];

void clear_memories() {
    for (int i = 0; i < MAX_COMPARTMENTS; ++i) {
        config_words[i] = 0;
        state_words[i] = 0;
        route_desc_words[i] = 0;
        trace_words[i] = 0;
    }
    for (int i = 0; i < MAX_INPUT_AXONS; ++i) {
        axon_words[i] = 0;
        input_events[i] = 0;
    }
    for (int i = 0; i < MAX_SYNAPSE_ENTRIES; ++i) {
        synapse_words[i] = 0;
    }
    for (int i = 0; i < MAX_OUTPUT_ROUTES; ++i) {
        route_words[i] = 0;
        packet_words[i] = 0;
    }
}

void load_seed() {
    clear_memories();
    for (unsigned i = 0; i < P03_CONFIG_SEED_COUNT; ++i) {
        config_word_t word = 0;
        word.range(63, 0) = P03_CONFIG_SEEDS[i].lo;
        word.range(127, 64) = P03_CONFIG_SEEDS[i].hi;
        config_words[P03_CONFIG_SEEDS[i].index] = word;
    }
    for (unsigned i = 0; i < P03_STATE_SEED_COUNT; ++i) {
        state_words[P03_STATE_SEEDS[i].index] = P03_STATE_SEEDS[i].word;
    }
    for (unsigned i = 0; i < P03_AXON_SEED_COUNT; ++i) {
        axon_words[P03_AXON_SEEDS[i].index] = P03_AXON_SEEDS[i].word;
    }
    for (unsigned i = 0; i < P03_SYNAPSE_SEED_COUNT; ++i) {
        synapse_words[P03_SYNAPSE_SEEDS[i].index] = P03_SYNAPSE_SEEDS[i].word;
    }
    for (unsigned i = 0; i < P03_ROUTE_DESC_SEED_COUNT; ++i) {
        route_desc_words[P03_ROUTE_DESC_SEEDS[i].index] =
            P03_ROUTE_DESC_SEEDS[i].word;
    }
    for (unsigned i = 0; i < P03_ROUTE_SEED_COUNT; ++i) {
        route_words[P03_ROUTE_SEEDS[i].index] = P03_ROUTE_SEEDS[i].word;
    }
}

bool run_differential_corpus() {
    load_seed();
    unsigned failures = 0;

    for (unsigned tick_index = 0; tick_index < P03_TICK_COUNT; ++tick_index) {
        const TickSeed &seed = P03_TICKS[tick_index];
        for (int i = 0; i < MAX_INPUT_EVENTS; ++i) {
            input_events[i] = 0;
        }
        for (unsigned i = 0; i < seed.event_count; ++i) {
            input_events[i] = seed.events[i];
        }

        ap_uint<11> spike_count = 0;
        ap_uint<13> packet_count = 0;
        status_t status = 0;

        loihi_core_v2_tick(
            P03_SEED_COMPARTMENT_COUNT,
            seed.event_count,
            P03_SEED_SYNAPSE_COUNT,
            P03_SEED_ROUTE_COUNT,
            seed.timestep,
            config_words,
            state_words,
            axon_words,
            synapse_words,
            route_desc_words,
            route_words,
            input_events,
            trace_words,
            packet_words,
            &spike_count,
            &packet_count,
            &status);

        unsigned expected_spike_count = 0;
        for (unsigned compartment = 0;
             compartment < P03_SEED_COMPARTMENT_COUNT;
             ++compartment) {
            const ExpectedCompartment &expected = seed.expected[compartment];
            const trace_word_t trace = trace_words[compartment];
            const unsigned long long actual_before =
                trace.range(63, 0).to_uint64();
            const long long actual_synaptic_input =
                ap_int<64>(trace.range(127, 64)).to_int64();
            const unsigned long long actual_after =
                trace.range(191, 128).to_uint64();
            const unsigned actual_spike = trace[192] ? 1u : 0u;

            expected_spike_count += expected.spike;
            const bool compartment_ok =
                actual_before == expected.state_before
                && actual_synaptic_input == expected.synaptic_input
                && actual_after == expected.state_after
                && actual_spike == expected.spike
                && state_words[compartment].to_uint64() == expected.state_after
                && trace.range(255, 193) == 0;

            if (!compartment_ok) {
                ++failures;
                std::cerr
                    << "FAIL P03 tick " << seed.timestep
                    << " compartment " << compartment
                    << ": before=" << actual_before
                    << " expected_before=" << expected.state_before
                    << " syn=" << actual_synaptic_input
                    << " expected_syn=" << expected.synaptic_input
                    << " after=" << actual_after
                    << " expected_after=" << expected.state_after
                    << " spike=" << actual_spike
                    << " expected_spike=" << expected.spike
                    << "\n";
            }
        }

        if (status != 0) {
            ++failures;
            std::cerr << "FAIL P03 tick " << seed.timestep
                      << ": status_flags=0x" << std::hex
                      << status.to_uint() << std::dec << "\n";
        }
        if (spike_count.to_uint() != expected_spike_count) {
            ++failures;
            std::cerr << "FAIL P03 tick " << seed.timestep
                      << ": spike_count=" << spike_count.to_uint()
                      << " expected=" << expected_spike_count << "\n";
        }
        if (packet_count.to_uint() != seed.packet_count) {
            ++failures;
            std::cerr << "FAIL P03 tick " << seed.timestep
                      << ": packet_count=" << packet_count.to_uint()
                      << " expected=" << seed.packet_count << "\n";
        } else {
            for (unsigned packet = 0; packet < seed.packet_count; ++packet) {
                const unsigned long long actual = packet_words[packet].to_uint64();
                if (actual != seed.packets[packet]) {
                    ++failures;
                    std::cerr << "FAIL P03 tick " << seed.timestep
                              << " packet " << packet
                              << ": actual=" << actual
                              << " expected=" << seed.packets[packet] << "\n";
                }
            }
        }
    }

    if (failures != 0) {
        std::cerr << failures << " P03 differential check(s) failed\n";
        return false;
    }
    std::cout << "P03 Python/HLS one-core differential passed: "
              << P03_TICK_COUNT << " ticks, "
              << P03_SEED_COMPARTMENT_COUNT << " compartments\n";
    return true;
}

bool run_integrity_checks() {
    load_seed();
    ap_uint<11> spikes = 0;
    ap_uint<13> packets = 0;
    status_t status = 0;

    // Capacity guard: 1025 compartments is representable by the 11-bit count
    // port but must be rejected before any memory traversal.
    loihi_core_v2_tick(
        1025,
        0,
        P03_SEED_SYNAPSE_COUNT,
        P03_SEED_ROUTE_COUNT,
        0,
        config_words,
        state_words,
        axon_words,
        synapse_words,
        route_desc_words,
        route_words,
        input_events,
        trace_words,
        packet_words,
        &spikes,
        &packets,
        &status);
    if ((status.to_uint() & STATUS_CAPACITY) == 0) {
        std::cerr << "FAIL P03 capacity guard did not assert STATUS_CAPACITY\n";
        return false;
    }

    load_seed();
    input_events[0] = 99;  // unconfigured axon table entry
    status = 0;
    loihi_core_v2_tick(
        P03_SEED_COMPARTMENT_COUNT,
        1,
        P03_SEED_SYNAPSE_COUNT,
        P03_SEED_ROUTE_COUNT,
        0,
        config_words,
        state_words,
        axon_words,
        synapse_words,
        route_desc_words,
        route_words,
        input_events,
        trace_words,
        packet_words,
        &spikes,
        &packets,
        &status);
    if ((status.to_uint() & STATUS_INVALID_AXON) == 0) {
        std::cerr << "FAIL P03 invalid-axon guard did not assert STATUS_INVALID_AXON\n";
        return false;
    }

    std::cout << "P03 runtime integrity guards passed\n";
    return true;
}

}  // namespace

int main() {
    if (!run_differential_corpus()) {
        return 1;
    }
    if (!run_integrity_checks()) {
        return 1;
    }
    std::cout << "P03 one-core HLS C-simulation suite passed\n";
    return 0;
}
