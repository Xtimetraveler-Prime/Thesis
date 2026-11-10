#include "m06_paged_adapter.hpp"
#include <array>
#include <algorithm>
#include <cstring>
#include <limits>
#include <stdexcept>
#include <utility>

namespace {
constexpr std::uint32_t RECORD_BYTES = 16;
constexpr std::uint32_t PAGE_BYTES = 256;
constexpr std::uint32_t NEURONS_PER_PAGE = PAGE_BYTES / RECORD_BYTES;
constexpr std::uint32_t MAX_SLOTS = 8;
constexpr std::uint32_t PER_TICK_LIMIT = M05_INT_MAX_PER_TICK;
constexpr std::uint32_t BAD_SHAPE = 1;
constexpr std::uint32_t BAD_NEURON = 2;
constexpr std::uint32_t BAD_EDGE = 3;
constexpr std::uint32_t BAD_EXTERNAL = 4;
constexpr std::uint32_t OVERFLOW = 5;
constexpr std::uint32_t M05_ERROR = 6;
constexpr std::uint32_t CORRUPT_RECORD = 7;

struct Page {
    std::array<std::uint8_t, PAGE_BYTES> bytes{};
    std::uint64_t last_access = 0;
    std::uint32_t logical_block = 0;
    bool present = false;
    bool dirty = false;
};

class NativePager {
public:
    NativePager(const std::vector<M05IntegratedNeuron> &neurons,
                std::uint32_t available, M06PagedCounters &counts)
        : bytes_(neurons.size() * RECORD_BYTES, 0),
          usable_(available), counters_(counts) {
        for (std::size_t i = 0; i < neurons.size(); ++i) {
            const std::uint16_t raw = static_cast<std::uint16_t>(
                neurons[i].initial_voltage);
            bytes_[i * RECORD_BYTES] = static_cast<std::uint8_t>(raw);
            bytes_[i * RECORD_BYTES + 1] =
                static_cast<std::uint8_t>(raw >> 8);
        }
    }
    std::pair<std::int32_t, std::uint32_t> read(std::uint32_t neuron) {
        const Page &p = access(neuron);
        const std::uint32_t pos = (neuron % NEURONS_PER_PAGE) * RECORD_BYTES;
        const std::uint32_t raw =
            std::uint32_t(p.bytes[pos]) |
            (std::uint32_t(p.bytes[pos+1]) << 8);
        const std::int32_t value =
            raw >= 0x8000u ? std::int32_t(raw)-65536 : std::int32_t(raw);
        std::uint32_t watermark = 0;
        for (std::uint32_t lane = 0; lane < 4; ++lane) {
            watermark |= std::uint32_t(p.bytes[pos+2+lane]) << (lane*8);
        }
        return {value, watermark};
    }
    void update(std::uint32_t neuron, std::int32_t voltage,
                std::uint32_t last_completed_plus_one) {
        Page &p = access(neuron);
        const std::uint32_t pos = (neuron % NEURONS_PER_PAGE)*RECORD_BYTES;
        const auto raw = static_cast<std::uint16_t>(voltage);
        p.bytes[pos] = static_cast<std::uint8_t>(raw);
        p.bytes[pos+1] = static_cast<std::uint8_t>(raw >> 8);
        for (std::uint32_t lane = 0; lane < 4; ++lane)
            p.bytes[pos+2+lane] = static_cast<std::uint8_t>(
                last_completed_plus_one >> (lane*8));
        p.dirty = true;
    }
    void flush() {
        for (std::uint32_t i = 0; i < usable_; ++i)
            if (pages_[i].present && pages_[i].dirty)
                writeback(pages_[i]);
    }
    const std::vector<std::uint8_t> &canonical() const { return bytes_; }

private:
    Page &access(std::uint32_t neuron) {
        if (neuron >= bytes_.size() / RECORD_BYTES)
            throw std::out_of_range("neuron outside canonical image");
        const std::uint32_t block = neuron / NEURONS_PER_PAGE;
        ++counters_.page_accesses;
        for (std::uint32_t s = 0; s < usable_; ++s) {
            Page &p = pages_[s];
            if (p.present && p.logical_block == block) {
                ++counters_.page_hits;
                p.last_access = ++clock_;
                return p;
            }
        }
        ++counters_.page_misses;
        std::uint32_t selected = 0;
        bool free_found = false;
        for (std::uint32_t s = 0; s < usable_; ++s) {
            if (!pages_[s].present) {
                selected = s;
                free_found = true;
                break;
            }
            if (pages_[s].last_access < pages_[selected].last_access)
                selected = s;
        }
        Page &p = pages_[selected];
        if (!free_found) {
            ++counters_.evictions;
            if (p.dirty) writeback(p);
        }
        std::memcpy(p.bytes.data(), &bytes_[block * PAGE_BYTES], PAGE_BYTES);
        p.logical_block = block;
        p.present = true;
        p.dirty = false;
        p.last_access = ++clock_;
        ++counters_.fills;
        counters_.read_bytes += PAGE_BYTES;
        return p;
    }
    void writeback(Page &p) {
        std::memcpy(&bytes_[p.logical_block*PAGE_BYTES],
                    p.bytes.data(), PAGE_BYTES);
        p.dirty = false;
        ++counters_.dirty_writebacks;
        counters_.written_bytes += PAGE_BYTES;
    }
    std::vector<std::uint8_t> bytes_;  // HOST canonical mock, NOT PS DDR
    std::array<Page, MAX_SLOTS> pages_{};
    std::uint32_t usable_;
    std::uint64_t clock_ = 0;
    M06PagedCounters &counters_;
};

struct Arrival {
    std::uint32_t dst;
    std::int32_t current;
};

bool valid_cell(const M05IntegratedNeuron &n) {
    return n.initial_voltage >= -32768 && n.initial_voltage <= 32767 &&
           n.bias >= -32768 && n.bias <= 32767 &&
           n.threshold > 0 && n.threshold <= 32767 &&
           n.reset_voltage >= -32768 && n.reset_voltage <= 32767 &&
           n.reset_voltage < n.threshold;
}
} // namespace

M06PagedReplayResult m06_paged_replay_with_m05_stream(
    const std::vector<M05IntegratedNeuron> &neurons,
    const std::vector<M05IntegratedSynapse> &edges,
    const std::vector<M05IntegratedExternal> &external,
    std::uint32_t ticks, std::uint32_t decay_num,
    std::uint32_t decay_den, std::uint32_t slots) {
    M06PagedReplayResult result{};
    const std::uint32_t n = static_cast<std::uint32_t>(neurons.size());
    if (n < NEURONS_PER_PAGE || n > M05_INT_MAX_NEURONS ||
        n % NEURONS_PER_PAGE != 0 || slots == 0 || slots > MAX_SLOTS ||
        ticks == 0 || ticks > M05_ROLLING_MAX_TICKS ||
        decay_den == 0 || decay_num > decay_den ||
        edges.size() > M05_INT_MAX_SYNAPSES ||
        external.size() > std::size_t(ticks)*PER_TICK_LIMIT) {
        result.status = BAD_SHAPE;
        return result;
    }
    for (const auto &cell : neurons) {
        if (!valid_cell(cell)) {
            result.status = BAD_NEURON;
            return result;
        }
    }
    std::vector<std::vector<M05IntegratedSynapse>> adjacency(n);
    for (const auto &edge : edges) {
        if (edge.pre >= n || edge.post >= n ||
            edge.weight < -32768 || edge.weight > 32767 ||
            edge.delay == 0 || edge.delay > M05_ROLLING_MAX_DELAY) {
            result.status = BAD_EDGE;
            return result;
        }
        adjacency[edge.pre].push_back(edge);
    }
    std::vector<std::vector<Arrival>> arrivals(ticks);
    std::uint64_t last_external_tick = 0;
    for (const auto &item : external) {
        if (item.tick >= ticks || item.neuron_id >= n ||
            item.current < -32768 || item.current > 32767 ||
            item.tick < last_external_tick) {
            result.status = BAD_EXTERNAL;
            return result;
        }
        last_external_tick = item.tick;
        auto &at = arrivals[static_cast<std::size_t>(item.tick)];
        if (at.size() >= PER_TICK_LIMIT) {
            result.status = OVERFLOW;
            return result;
        }
        at.push_back({item.neuron_id,item.current});
    }
    NativePager pager(neurons, slots, result.counters);
    // TEST-ONLY trace observer; scheduler eligibility uses nonzero status
    // updated strictly from the unchanged M05 HLS stream service's response.
    std::vector<std::int32_t> trace_voltage(n, 0);
    std::vector<std::uint8_t> active(n, 0);
    for (std::uint32_t i=0; i<n; ++i) {
        trace_voltage[i] = neurons[i].initial_voltage;
        active[i] = neurons[i].initial_voltage != 0;
    }
    for (std::uint32_t t=0; t<ticks; ++t) {
        std::vector<std::int64_t> current(n, 0);
        std::vector<std::uint8_t> touched(n, 0);
        const auto &today=arrivals[t];
        const auto delivered=static_cast<std::uint32_t>(today.size());
        if (delivered > PER_TICK_LIMIT) {
            result.status = OVERFLOW;
            result.trace.clear();
            return result;
        }
        for (const auto &item : today) {
            current[item.dst] += item.current; // exactly aggregate first
            touched[item.dst] = 1; // zero or canceling deliveries still wake
        }
        std::vector<std::uint32_t> spiking;
        std::vector<M05IntegratedTraceEntry> tick_records;
        tick_records.reserve(n);
        for (std::uint32_t i=0; i<n; ++i) {
            const auto &cell = neurons[i];
            const bool evaluated = active[i] || cell.bias != 0 || touched[i];
            std::uint8_t spike=0;
            if (evaluated) {
                const auto prev = pager.read(i);
                if (prev.second > t) {
                    result.status = CORRUPT_RECORD;
                    result.trace.clear();
                    return result;
                }
                M04Request req{};
                req.neuron_id = i;
                req.neuron_count = n;
                req.tick = t;
                req.previous_voltage = prev.first;
                req.aggregated_current = current[i];
                req.bias = cell.bias;
                req.threshold = cell.threshold;
                req.reset_voltage = cell.reset_voltage;
                req.state_bits = 16;
                req.decay_num = decay_num;
                req.decay_den = decay_den;
                hls::stream<M04Request> requests;
                hls::stream<M04Response> responses;
                requests.write(req);
                if (m05_stream_eval(requests, responses, 1) != M05_BATCH_OK ||
                    responses.empty()) {
                    result.status = M05_ERROR;
                    result.trace.clear();
                    return result;
                }
                const M04Response resp=responses.read();
                ++result.counters.m05_stream_calls;
                if (resp.status != M04_OK ||
                    resp.neuron_id != i || resp.tick != t) {
                    result.status = M05_ERROR;
                    result.trace.clear();
                    return result;
                }
                pager.update(i, resp.next_voltage, t+1);
                trace_voltage[i] = resp.next_voltage;
                active[i] = (resp.next_voltage != 0);
                spike = resp.spike;
                ++result.counters.evaluated;
                result.counters.spike_count += spike;
                if (spike) spiking.push_back(i);
            }
            tick_records.push_back({t,i,trace_voltage[i],spike,
                                    static_cast<std::uint8_t>(evaluated),
                                    delivered});
        }
        // Preserve M05 delayed fanout only AFTER the tick's neurons update.
        // If future arrivals exceed 4096, no trace is published; partial
        // host canonical writebacks are not crash/AXI atomic.
        for (const auto neuron : spiking) {
            for (const auto &edge : adjacency[neuron]) {
                const std::uint64_t future=t+edge.delay;
                if (future >= ticks) continue;
                auto &scheduled=arrivals[static_cast<std::size_t>(future)];
                if (scheduled.size() >= PER_TICK_LIMIT) {
                    result.status = OVERFLOW;
                    result.trace.clear();
                    return result;
                }
                scheduled.push_back({edge.post,edge.weight});
            }
        }
        result.trace.insert(result.trace.end(),
                            tick_records.begin(), tick_records.end());
    }
    pager.flush();
    result.canonical_after_flush = pager.canonical();
    return result;
}
