#include "m06_paged_rolling.hpp"
#include <limits>

// The temporal wheel has at most 4096 individual signed-W16 deliveries
// across ALL neurons in one logical tick (external + recurrent, even zero).
// Therefore every legal intermediate per-neuron sum, for ANY arrival order,
// fits the closed interval [-4096*32768, +4096*32767]. In particular, the
// negative endpoint is -2^27 and the positive endpoint is below +2^27.
// A signed 32-bit BRAM cell is exact without changing the 64-bit M04 API.
// A future change to per-tick admission or term width MUST revisit this proof.
constexpr std::int64_t M05_ROLL_MIN_CURRENT =
    -static_cast<std::int64_t>(M05_INT_MAX_PER_TICK) * 32768;
constexpr std::int64_t M05_ROLL_MAX_CURRENT =
    static_cast<std::int64_t>(M05_INT_MAX_PER_TICK) * 32767;
static_assert(M05_ROLL_MIN_CURRENT >=
              std::numeric_limits<std::int32_t>::min(), "wheel underflows i32");
static_assert(M05_ROLL_MAX_CURRENT <=
              std::numeric_limits<std::int32_t>::max(), "wheel overflows i32");

// M06 distinct new HLS top retains M05 autonomous rolling temporal-wheel event
// scheduler and original M04 calculation. Every working voltage comes from
// the AXI-backed 8-slot page buffer, not a 1024-entry private voltage array.
// Trace writes stay provisional until final OK. No AXI crash atomicity.

// Dedicated 8 x 256B cache. This is the ONLY working membrane-voltage store.
// All slow canonical state transfers use the genuine HLS m_axi port. Memory
// ownership/base address is a SEPARATE platform contract; no host per tick.
static std::uint32_t m06_ensure_page(
    std::uint32_t block, std::uint32_t usable,
    const std::uint32_t *canonical_read_words,
    std::uint32_t *canonical_write_words,
    std::uint32_t data[M06_PAGED_MAX_SLOTS][M06_PAGED_PAGE_WORDS],
    std::uint8_t valid[M06_PAGED_MAX_SLOTS],
    std::uint8_t dirty[M06_PAGED_MAX_SLOTS],
    std::uint32_t tag[M06_PAGED_MAX_SLOTS],
    std::uint32_t stamp[M06_PAGED_MAX_SLOTS],
    std::uint32_t &clock,
    M06PageMetrics &metrics) {
    ++metrics.page_accesses;
    for (std::uint32_t s=0;s<usable;++s) {
        if (valid[s] && tag[s]==block) {
            ++metrics.page_hits;
            stamp[s]=++clock;
            return s;
        }
    }
    ++metrics.page_misses;
    std::uint32_t victim=0;
    bool free_found=false;
    for (std::uint32_t s=0;s<usable;++s) {
        if (!valid[s]) {
            victim=s;
            free_found=true;
            break;
        }
        if (stamp[s]<stamp[victim]) victim=s;
    }
    if (!free_found) {
        ++metrics.page_evictions;
        if (dirty[victim]) {
            for (std::uint32_t w=0;w<M06_PAGED_PAGE_WORDS;++w)
                canonical_write_words[tag[victim]*M06_PAGED_PAGE_WORDS+w]=data[victim][w];
            dirty[victim]=0;
            ++metrics.dirty_writebacks;
        }
    }
    for (std::uint32_t w=0;w<M06_PAGED_PAGE_WORDS;++w)
        data[victim][w]=canonical_read_words[block*M06_PAGED_PAGE_WORDS+w];
    valid[victim]=1;
    dirty[victim]=0;
    tag[victim]=block;
    stamp[victim]=++clock;
    ++metrics.page_fills;
    return victim;
}

static std::int32_t m06_sign16(std::uint32_t packed) {
    const std::uint32_t bits=packed&0xffffu;
    return bits>=32768u ? std::int32_t(bits)-65536 : std::int32_t(bits);
}

std::uint32_t m06_paged_rolling_replay(
    hls::stream<M05IntegratedNeuron> &neurons,
    hls::stream<M05IntegratedSynapse> &synapses,
    hls::stream<M05IntegratedExternal> &external_events,
    hls::stream<M05IntegratedTraceEntry> &trace,
    hls::stream<M06PageMetrics> &metrics,
    const std::uint32_t *canonical_read_words,
    std::uint32_t *canonical_write_words,
    std::uint32_t neuron_count,
    std::uint32_t synapse_count,
    std::uint32_t external_count,
    std::uint32_t ticks,
    std::uint32_t decay_num,
    std::uint32_t decay_den,
    std::uint32_t resident_slots,
    std::uint32_t canonical_first_neuron) {
#pragma HLS INTERFACE axis port=neurons
#pragma HLS INTERFACE axis port=synapses
#pragma HLS INTERFACE axis port=external_events
#pragma HLS INTERFACE axis port=trace
#pragma HLS INTERFACE axis port=metrics
#pragma HLS INTERFACE m_axi port=canonical_read_words offset=slave bundle=gmem_read depth=16384 max_read_burst_length=16
#pragma HLS INTERFACE m_axi port=canonical_write_words offset=slave bundle=gmem_write depth=16384 max_write_burst_length=16
    // These SEPARATE AXI masters are intentionally mapped to ONE canonical
    // 64KiB physical scratch image. Without explicit alias metadata, Vitis
    // may treat them as independent memories during C/RTL instrumentation,
    // and read-after-write dependency checking is unavailable. AMD UG1399
    // requires two distinct bundles, equal depth and slave/direct offsets.
    // This describes aliasing; it is NOT an AXI B-response/AR coherency fence
    // and does NOT prove the original SmartConnect physical connection.
#pragma HLS ALIAS ports=canonical_read_words,canonical_write_words distance=0
#pragma HLS INTERFACE s_axilite port=canonical_read_words bundle=control
#pragma HLS INTERFACE s_axilite port=canonical_write_words bundle=control
#pragma HLS INTERFACE s_axilite port=neuron_count bundle=control
#pragma HLS INTERFACE s_axilite port=synapse_count bundle=control
#pragma HLS INTERFACE s_axilite port=external_count bundle=control
#pragma HLS INTERFACE s_axilite port=ticks bundle=control
#pragma HLS INTERFACE s_axilite port=decay_num bundle=control
#pragma HLS INTERFACE s_axilite port=decay_den bundle=control
#pragma HLS INTERFACE s_axilite port=resident_slots bundle=control
#pragma HLS INTERFACE s_axilite port=canonical_first_neuron bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    if (neuron_count == 0 || neuron_count > M05_INT_MAX_NEURONS ||
        synapse_count > M05_INT_MAX_SYNAPSES ||
        external_count > M05_ROLLING_MAX_EXTERNAL ||
        ticks == 0 || ticks > M05_ROLLING_MAX_TICKS ||
        decay_den == 0 || decay_num > decay_den ||
        resident_slots==0 || resident_slots>M06_PAGED_MAX_SLOTS ||
        neuron_count%16!=0 || canonical_first_neuron%16!=0 ||
        canonical_first_neuron>M06_PAGED_MAX_LOGICAL_NEURONS ||
        neuron_count>M06_PAGED_MAX_LOGICAL_NEURONS-canonical_first_neuron) {
        return M06_PAGE_BAD_SHAPE;
    }

    static std::uint8_t active[M05_INT_MAX_NEURONS];
    static std::uint32_t page_words[M06_PAGED_MAX_SLOTS][M06_PAGED_PAGE_WORDS];
    static std::uint8_t page_valid[M06_PAGED_MAX_SLOTS];
    static std::uint8_t page_dirty[M06_PAGED_MAX_SLOTS];
    static std::uint32_t page_tag[M06_PAGED_MAX_SLOTS];
    static std::uint32_t page_age[M06_PAGED_MAX_SLOTS];
    std::uint32_t page_clock=0;
    M06PageMetrics page_metrics{};
    static std::int16_t bias[M05_INT_MAX_NEURONS];
    static std::int16_t threshold[M05_INT_MAX_NEURONS];
    static std::int16_t reset[M05_INT_MAX_NEURONS];
    static std::int32_t head[M05_INT_MAX_NEURONS];
    static std::int32_t next_edge[M05_INT_MAX_SYNAPSES];
    static std::uint32_t post[M05_INT_MAX_SYNAPSES];
    static std::int16_t weight[M05_INT_MAX_SYNAPSES];
    static std::uint8_t delay[M05_INT_MAX_SYNAPSES];

    static std::int32_t current[M05_ROLLING_SLOTS][M05_INT_MAX_NEURONS];
    static std::uint8_t touched[M05_ROLLING_SLOTS][M05_INT_MAX_NEURONS];
    static std::uint32_t delivery_count[M05_ROLLING_SLOTS];
    static std::uint8_t tick_spike[M05_INT_MAX_NEURONS];
    static std::uint8_t tick_evaluated[M05_INT_MAX_NEURONS];
#pragma HLS BIND_STORAGE variable=page_words type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=bias type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=threshold type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=reset type=ram_1p impl=bram
#pragma HLS BIND_STORAGE variable=current type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=touched type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=tick_spike type=ram_2p impl=bram

    // Treat every ap_start as a NEW logical epoch; stale cached blocks from
    // previous runs cannot be read. Canonical off-chip array is exclusively
    // owned by this invocation and is rewritten from neuron input streams.
    for (std::uint32_t ps=0;ps<M06_PAGED_MAX_SLOTS;++ps) {
        page_valid[ps]=0;
        page_dirty[ps]=0;
        page_tag[ps]=0;
        page_age[ps]=0;
    }
    // Fresh logical run every invocation; no reliance on power-on BRAM
    // contents. Reset only the *admitted* neuron IDs. ID >= neuron_count
    // cannot be accessed in this run: all external destinations, synapse
    // endpoints and worklist traversal are individually range checked.
    // When a later run admits MORE neurons, its larger initialization
    // footprint cleans those previously inaccessible RAM rows as well.
    // This avoids 8*1024 unconditional current/touch clears for tiny runs.
    // Do not remove the per-tick wheel-slot clear below: the t+8 alias
    // must be released before scheduling recurrent spikes with delay==8.
    for (std::uint32_t slot = 0; slot < M05_ROLLING_SLOTS; ++slot) {
        delivery_count[slot] = 0;
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            current[slot][i] = 0;
            touched[slot][i] = 0;
        }
    }
    for (std::uint32_t i = 0; i < neuron_count; ++i) {
        head[i] = -1;
    }
    for (std::uint32_t i = 0; i < neuron_count; ++i) {
        const M05IntegratedNeuron p = neurons.read();
        if (p.initial_voltage < -32768 || p.initial_voltage > 32767 ||
            p.bias < -32768 || p.bias > 32767 ||
            p.threshold <= 0 || p.threshold > 32767 ||
            p.reset_voltage < -32768 || p.reset_voltage > 32767 ||
            p.reset_voltage >= p.threshold) {
            return M05_ROLL_BAD_NEURON;
        }
        active[i] = (p.initial_voltage != 0) ? 1 : 0;
        // One 16B canonical record (4 little-endian 32b words) per neuron.
        // The upper 16b of word0 are reserved, and word1 is tick+1.
        // The other words are reserved and initialized to zero.
        const std::uint32_t word=(canonical_first_neuron+i)*4u;
        canonical_write_words[word+0]=static_cast<std::uint16_t>(p.initial_voltage);
        canonical_write_words[word+1]=0;
        canonical_write_words[word+2]=0;
        canonical_write_words[word+3]=0;
        bias[i] = static_cast<std::int16_t>(p.bias);
        threshold[i] = static_cast<std::int16_t>(p.threshold);
        reset[i] = static_cast<std::int16_t>(p.reset_voltage);
    }
    // Linked adjacency; parallel and recurrent self-edges are independent.
    for (std::uint32_t j = 0; j < synapse_count; ++j) {
        const M05IntegratedSynapse e = synapses.read();
        if (e.pre >= neuron_count || e.post >= neuron_count ||
            e.weight < -32768 || e.weight > 32767 ||
            e.delay == 0 || e.delay > M05_ROLLING_MAX_DELAY) {
            return M05_ROLL_BAD_SYNAPSE;
        }
        next_edge[j] = head[e.pre];
        head[e.pre] = static_cast<std::int32_t>(j);
        post[j] = e.post;
        weight[j] = static_cast<std::int16_t>(e.weight);
        delay[j] = static_cast<std::uint8_t>(e.delay);
    }

    // One-element lookahead permits sorted future input without preloading
    // the full external horizon into on-chip storage. This is a FUNCTIONAL
    // ordering contract; live ready/valid stalls are not yet characterized.
    M05IntegratedExternal pending{};
    std::uint8_t have_pending = 0;
    std::uint32_t consumed = 0;

    for (std::uint32_t t = 0; t < ticks; ++t) {
        const std::uint32_t slot = t % M05_ROLLING_SLOTS;
        // Ingest *all* external arrivals for t, including zero deliveries.
        // Future events remain in the lookahead until their matching tick.
        while (have_pending || consumed < external_count) {
            if (!have_pending) {
                pending = external_events.read();
                ++consumed;
                have_pending = 1;
            }
            if (pending.tick >= ticks ||
                pending.neuron_id >= neuron_count ||
                pending.current < -32768 || pending.current > 32767 ||
                pending.tick < t) {
                return M05_ROLL_BAD_EXTERNAL;
            }
            if (pending.tick > t) break;
            if (delivery_count[slot] >= M05_INT_MAX_PER_TICK) {
                return M05_ROLL_DELIVERY_OVERFLOW;
            }
            ++delivery_count[slot];
            current[slot][pending.neuron_id] +=
                static_cast<std::int32_t>(pending.current);
            touched[slot][pending.neuron_id] = 1;
            have_pending = 0;
        }

        const std::uint32_t this_tick_deliveries = delivery_count[slot];
        // Evaluate all neurons using only current-tick aggregates. No same-
        // tick event propagation is possible because all delays are positive.
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            const std::uint8_t evaluate =
                (active[i] || bias[i] != 0 || touched[slot][i]) ? 1 : 0;
            std::uint8_t spike = 0;
            if (evaluate) {
                const std::uint32_t global=canonical_first_neuron+i;
                const std::uint32_t pg=global/16u;
                const std::uint32_t row=(global%16u)*4u;
                const std::uint32_t pslot=m06_ensure_page(
                    pg,resident_slots,canonical_read_words,canonical_write_words,page_words,
                    page_valid,page_dirty,page_tag,page_age,
                    page_clock,page_metrics);
                if (page_words[pslot][row+1]>t)
                    return M06_PAGE_STATE_CORRUPTION;
                M04Request request{};
                request.neuron_id = i;
                request.neuron_count = neuron_count;
                request.tick = t;
                request.previous_voltage = m06_sign16(page_words[pslot][row]);
                // Sign-extend exact signed-i32 aggregate to unchanged M04 i64.
                request.aggregated_current =
                    static_cast<std::int64_t>(current[slot][i]);
                request.bias = bias[i];
                request.threshold = threshold[i];
                request.reset_voltage = reset[i];
                request.state_bits = 16;
                request.decay_num = decay_num;
                request.decay_den = decay_den;
                M04Response response{};
                m04_eval_one(request, response);
                if (response.status != M04_OK) return M06_PAGE_LIF_ERROR;
                // Dirty 16B canonical row stays in the resident page until
                // acknowledgement of a full-block AXI writeback/flush.
                page_words[pslot][row] =
                    (page_words[pslot][row]&0xffff0000u) |
                    static_cast<std::uint16_t>(response.next_voltage);
                page_words[pslot][row+1]=t+1;
                page_dirty[pslot]=1;
                active[i]=(response.next_voltage!=0) ? 1 : 0;
                spike=response.spike;
                ++page_metrics.m05_evaluations;
                page_metrics.emitted_spikes+=spike;
            }
            tick_spike[i] = spike;
            tick_evaluated[i] = evaluate;
        }

        // Release t's wheel slot BEFORE routing spikes. Crucial when delay
        // == 8: future t+8 aliases this exact physical BRAM slot.
        delivery_count[slot] = 0;
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            current[slot][i] = 0;
            touched[slot][i] = 0;
        }
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            if (!tick_spike[i]) continue;
            for (std::int32_t edge = head[i]; edge != -1;
                 edge = next_edge[edge]) {
                const std::uint32_t future = t + delay[edge];
                if (future >= ticks) continue;
                const std::uint32_t future_slot =
                    future % M05_ROLLING_SLOTS;
                if (delivery_count[future_slot] >= M05_INT_MAX_PER_TICK) {
                    return M05_ROLL_DELIVERY_OVERFLOW;
                }
                ++delivery_count[future_slot];
                const std::uint32_t dest = post[edge];
                current[future_slot][dest] +=
                    static_cast<std::int32_t>(weight[edge]);
                touched[future_slot][dest] = 1;
            }
        }
        // Publish the tick only after its recurrence fanout checks pass.
        // A late failure invalidates ALL earlier streamed rows as a run.
        for (std::uint32_t i = 0; i < neuron_count; ++i) {
            M05IntegratedTraceEntry out{};
            out.tick = t;
            out.neuron_id = i;
            // Even a silent neuron's trace voltage is sourced from the
            // page cache; no duplicated full-network voltage RAM exists.
            const std::uint32_t global=canonical_first_neuron+i;
            const std::uint32_t pslot=m06_ensure_page(
                global/16u,resident_slots,canonical_read_words,canonical_write_words,page_words,
                page_valid,page_dirty,page_tag,page_age,
                page_clock,page_metrics);
            out.voltage = m06_sign16(
                page_words[pslot][(global%16u)*4u]);
            out.spike = tick_spike[i];
            out.evaluated = tick_evaluated[i];
            out.delivered_count = this_tick_deliveries;
            trace.write(out);
        }
    }
    // Flush every dirty resident page to the canonical m_axi image BEFORE
    // declaring success. These writes are not AXI transactionally atomic.
    for (std::uint32_t ps=0;ps<resident_slots;++ps) {
        if (!page_valid[ps] || !page_dirty[ps]) continue;
        for (std::uint32_t w=0;w<M06_PAGED_PAGE_WORDS;++w)
            canonical_write_words[page_tag[ps]*M06_PAGED_PAGE_WORDS+w]=
                page_words[ps][w];
        page_dirty[ps]=0;
        ++page_metrics.dirty_writebacks;
    }
    metrics.write(page_metrics);
    return M06_PAGE_OK;
}
