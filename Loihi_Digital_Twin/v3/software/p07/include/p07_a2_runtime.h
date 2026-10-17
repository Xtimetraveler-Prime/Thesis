#ifndef LOIHI_TWIN_V3_P07_A2_RUNTIME_H
#define LOIHI_TWIN_V3_P07_A2_RUNTIME_H
/* P07-A2 one-image A53 control policy. Portable C11; accepted P03 scheduler
 * executes all 26 timesteps. Board callbacks are not assumed to have run.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_a1_ingress.h"
#include "p03_runtime.h"

#define P07_A2_OUTPUT_START 32u
#define P07_A2_OUTPUTS 10u
#define P07_A2_COMPARTMENTS 42u

enum {
    P07_A2_OK = 0,
    P07_A2_BAD_ARGUMENT = -1,
    P07_A2_BAD_RECORD = -2,
    P07_A2_BAD_SETUP = -3,
    P07_A2_BAD_EXECUTION = -4
};

typedef struct {
    uint32_t counts[P07_A2_OUTPUTS];
    uint8_t output_spikes[P07_A1_TOTAL_TICKS][P07_A2_OUTPUTS];
    uint16_t external_events[P07_A1_TOTAL_TICKS];
    uint32_t dropped_final_packets;
    uint32_t predicted_class;
    uint32_t all_silent;
    uint32_t timesteps;
    uint32_t dispatches;
    uint32_t barriers;
    uint32_t committed_routes; /* Actual NEXT writes, excludes final drops. */
    p03_rt_fault first_fault;
    p03_rt_phase fault_phase;
} p07_a2_result;

/* prepare() MUST restore the immutable, known-good full P02 core0 image
 * BEFORE each frame, clear all PS/PL event/packet counts and readouts, bind
 * the accepted P03 bridge callbacks, and register 816 actual axon IDs.
 * It MUST fail before page/dispatch on fingerprint/provenance mismatch.
 * The driver owns hardware state, DDR, and cache coherency.
 */
typedef struct {
    int (*prepare)(void *cookie, const uint8_t *record, size_t bytes,
                   p03_rt *runtime, p03_rt_ops *ops, void **ops_ctx);
    /* append_current: A53/PL must preflight aggregate COUNT+external <=4096,
     * then append ordered raw 32-bit axon indices to CURRENT, preserving
     * routed NEXT events from prior tick. Fail before first append on overflow.
     */
    int (*append_current)(void *cookie, uint8_t slot, uint8_t current_bank,
                          const uint16_t *axons, size_t count);
    /* Trace contains 8 little-endian uint32 words from the P03 256-bit
     * trace bank. Bit 192 (word 6 bit 0) marks a firing compartment.
     * Called at every completed dispatch for output compartments 32..41.
     */
    int (*read_trace)(void *cookie, uint8_t slot, uint16_t compartment,
                      uint32_t words[8]);
    void *cookie;
} p07_a2_driver;

/* One complete independent image with a fresh logical/physical context.
 * Never rewrites incoming record; never accesses official test labels.
 * On any failure result contains first P03 fault when available, no
 * misleading successful classification. Caller must discard failed frame.
 */
int p07_a2_run_frame(const uint8_t *record, size_t bytes,
                     const p07_a2_driver *driver, p07_a2_result *result);

#endif
