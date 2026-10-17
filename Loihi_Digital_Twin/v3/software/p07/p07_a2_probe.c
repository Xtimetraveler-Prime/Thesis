/* Portable P07-A2 control probe using the REAL accepted P03 scheduler
 * with a deterministic mock of the hardware I/O callbacks.
 * No CPU-side substitute is presented as actual PL neuron inference.
 */
#include "include/p07_a2_runtime.h"

#include <stdio.h>
#include <string.h>

typedef struct {
    uint32_t prepare_calls, page_ins, dispatches, barriers;
    uint32_t route_calls, trace_reads, dropped_checks;
    uint16_t bank_count[2];
    uint32_t tick;
    uint8_t selected_class, silent, force_overflow;
} simulated_hardware;

static int start(void *ctx)
{
    (void)ctx;
    return 0;
}
static int initialize(void *ctx)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    return (m->bank_count[0] || m->bank_count[1]) ? -1 : 0;
}
static int page_in(void *ctx, uint8_t id, uint8_t slot, uint64_t *cycles)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    if (id != 0 || slot != 0 || !cycles || m->page_ins != 0)
        return -1;
    *cycles = 3;
    m->page_ins++;
    return 0;
}
static int page_out(void *ctx, uint8_t id, uint8_t slot, uint64_t *cycles)
{
    (void)ctx; (void)id; (void)slot; (void)cycles;
    return -1;  /* one resident logical core never evicts in this test */
}
static int load_input(void *ctx)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    if (m->force_overflow) m->bank_count[0] = 4096u;
    return 0;
}
static int dispatch(void *ctx, uint8_t id, uint8_t slot,
                    uint32_t tick, uint8_t bank, uint32_t *emitted,
                    uint64_t *cycles)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    if (id || slot || bank != (tick & 1u) || tick != m->dispatches ||
        !emitted || !cycles || m->bank_count[bank] > 4096u)
        return -1;
    m->tick = tick;
    m->bank_count[bank] = 0;
    m->dispatches++;
    *emitted = 1; /* route 1 hidden packet each tick; final must DROP */
    *cycles = 5;
    return 0;
}
static int route(void *ctx, uint8_t id, uint32_t emitted,
                 uint32_t tick, uint8_t next, uint32_t *committed)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    if (id || tick >= 25u || next != (uint8_t)(1u - (tick & 1u)) ||
        emitted != 1u || !committed || m->bank_count[next] >= 4096u)
        return -1;
    m->bank_count[next]++;
    m->route_calls++;
    *committed = emitted;
    return 0;
}
static int barrier(void *ctx, uint32_t tick, uint8_t next)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    if (tick != m->barriers || next != (uint8_t)(1u - (tick & 1u)) ||
        m->bank_count[1u - next] != 0u)
        return -1;
    if (tick == 25u && m->bank_count[next] != 0u)
        return -1;  /* final packet was not delivered */
    m->barriers++;
    return 0;
}
static int result_write(void *ctx, const p03_rt *rt)
{
    simulated_hardware *m = (simulated_hardware *)ctx;
    return (m->barriers == 26u && rt->counters.timesteps_completed == 26u)
           ? 0 : -1;
}
static int prepare(void *cookie, const uint8_t *record, size_t length,
                   p03_rt *rt, p03_rt_ops *ops, void **ops_ctx)
{
    simulated_hardware *m = (simulated_hardware *)cookie;
    p07_a1_info info;
    if (p07_a1_validate(record, length, &info) || !rt || !ops || !ops_ctx)
        return -1;
    m->prepare_calls++;
    m->page_ins = m->dispatches = m->barriers = 0;
    m->route_calls = m->trace_reads = 0;
    m->tick = 0;
    m->selected_class = (uint8_t)((record[P07_A1_HEADER_BYTES +
                                    P07_A1_MAP_BYTES] == 255u) ? 7u : 0u);
    m->silent = (uint8_t)(record[P07_A1_HEADER_BYTES +
                                    P07_A1_MAP_BYTES] == 0u);
    m->bank_count[0] = 0u;
    m->bank_count[1] = 0;
    memset(ops, 0, sizeof(*ops));
    ops->load_deployment = start;
    ops->initialize_backing = initialize;
    ops->page_in = page_in;
    ops->page_out = page_out;
    ops->load_input = load_input;
    ops->dispatch = dispatch;
    ops->drain_route = route;
    ops->barrier_ready = barrier;
    ops->write_result = result_write;
    *ops_ctx = cookie;
    return 0;
}
static int append(void *cookie, uint8_t slot, uint8_t bank,
                  const uint16_t *axons, size_t count)
{
    simulated_hardware *m = (simulated_hardware *)cookie;
    size_t i;
    if (slot || bank > 1u || count > 784u ||
        m->bank_count[bank] + count > 4096u)
        return -1;
    for (i = 0; i < count; ++i)
        if (!axons || axons[i] >= 4096u)
            return -1;
    m->bank_count[bank] = (uint16_t)(m->bank_count[bank] + count);
    return 0;
}
static int trace(void *cookie, uint8_t slot, uint16_t compartment,
                 uint32_t words[8])
{
    simulated_hardware *m = (simulated_hardware *)cookie;
    if (slot || compartment < 32u || compartment >= 42u || !words ||
        !m->dispatches || m->trace_reads >= m->dispatches * 10u)
        return -1;
    memset(words, 0, 8u * sizeof(uint32_t));
    words[6] = (m->silent || compartment != (uint16_t)(32u +
                       m->selected_class)) ? 0u : 1u;
    m->trace_reads++;
    return 0;
}
static int load(const char *path, uint8_t *buffer)
{
    FILE *fp = fopen(path, "rb");
    size_t count;
    if (!fp) return -1;
    count = fread(buffer, 1, P07_A1_RECORD_BYTES + 1u, fp);
    if (ferror(fp) || fclose(fp) || count != P07_A1_RECORD_BYTES)
        return -1;
    return 0;
}
int main(int argc, char **argv)
{
    simulated_hardware m;
    p07_a2_driver driver;
    p07_a2_result result;
    uint8_t raw[P07_A1_RECORD_BYTES + 1u];
    uint8_t corrupted[P07_A1_RECORD_BYTES];
    uint32_t frame, t, external_total;
    int code;
    if (argc != 3) return 2;
    memset(&m, 0, sizeof(m));
    driver.prepare = prepare;
    driver.append_current = append;
    driver.read_trace = trace;
    driver.cookie = &m;
    for (frame = 0; frame < 2u; ++frame) {
        if (load(argv[frame + 1u], raw)) return 3;
        if (frame == 0u) {
            memcpy(corrupted, raw, P07_A1_RECORD_BYTES);
            corrupted[1800] ^= 1u; /* Invalid P07 header/payload CRC. */
            code = p07_a2_run_frame(corrupted, sizeof(corrupted), &driver, &result);
            if (code != P07_A2_BAD_RECORD || m.prepare_calls != 0u)
                return 4;
        }
        code = p07_a2_run_frame(raw, P07_A1_RECORD_BYTES, &driver, &result);
        if (code || result.first_fault != P03_RT_FAULT_NONE ||
            result.timesteps != 26u || result.dispatches != 26u ||
            result.barriers != 26u || result.dropped_final_packets != 1u ||
            result.committed_routes != 25u || m.route_calls != 25u ||
            m.page_ins != 1u || m.trace_reads != 260u ||
            m.prepare_calls != frame + 1u || m.bank_count[0] != 0u ||
            m.bank_count[1] != 0u)
            return 5;
        external_total = 0u;
        for (t = 0; t < 26u; ++t)
            external_total += result.external_events[t];
        if (result.external_events[25] != 0u) return 6;
        if (m.silent) {
            if (result.predicted_class != 0u || !result.all_silent ||
                result.counts[0] != 0u) return 7;
        } else if (result.predicted_class != m.selected_class ||
                   result.counts[m.selected_class] != 26u ||
                   result.all_silent) return 8;
        printf("frame=%u inputs=%u class=%u silent=%u routes=%u dropped=%u\n",
               frame, external_total, result.predicted_class,
               result.all_silent, result.committed_routes,
               result.dropped_final_packets);
    }
    if (load(argv[2], raw)) return 9;
    /* Overflow is meaningful only if the frame injects at least one
     * external spike; select the non-silent user-provided fixture. */
    if (raw[P07_A1_HEADER_BYTES + P07_A1_MAP_BYTES] == 0u &&
        load(argv[1], raw)) return 9;
    if (raw[P07_A1_HEADER_BYTES + P07_A1_MAP_BYTES] == 0u) return 9;
    m.force_overflow = 1;
    code = p07_a2_run_frame(raw, P07_A1_RECORD_BYTES, &driver, &result);
    if (code != P07_A2_BAD_EXECUTION ||
        result.first_fault != P03_RT_FAULT_DISPATCH_ERROR ||
        m.dispatches != 0u || m.route_calls != 0u ||
        m.prepare_calls != 3u)
        return 10;
    puts("P07_A2_NATIVE_SCHEDULER_PASS=1");
    return 0;
}
