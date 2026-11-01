#ifndef LOIHI_TWIN_V3_P07_B4M_SPIKE_TRACE_H
#define LOIHI_TWIN_V3_P07_B4M_SPIKE_TRACE_H
/* The ORIGINAL P03 HLS writes a 256-bit trace word for EVERY compartment:
 * bits [63:0] before_state, [127:64] accumulated_input,
 * [191:128] after_state, [192] independent emitted spike flag.
 * P03 debug bank 7 reads this trace while the dispatched core is resident.
 * Read bank 1's actual state after each HLS dispatch to cross-check the
 * trace after_state. Not inferred from output packet words.
 * All 27 cores (even zero-spike cores) require complete fresh trace reads.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b3c2_hw_scheduler.h"
#define P07_B4M_TRACE_SPIKE_CAP 1024u
#define P07_B4M_TRACE_MAGIC UINT32_C(0x5452344D)
enum {P07_B4M_TRACE_OK=0,P07_B4M_TRACE_INVALID=-1,
      P07_B4M_TRACE_FAULT=-2};
typedef struct {
    p03_hw_adapter *hw;
    p07_b3c2_hw_scheduler *scheduler;
    uint16_t (*spikes)[2]; /* caller-owned array of exactly capacity entries */
    size_t capacity;
    uint32_t tick,seen[P07_B3_CORES],read_count,spike_count;
    uint32_t expected_compartments,observed_compartments;
    uint32_t verified,poisoned,first_fault;
    uint64_t fnv64;
} p07_b4m_spike_trace;
typedef struct {
    uint32_t magic,tick,source_count,compartments_checked,spikes;
    uint64_t fnv64;
} p07_b4m_trace_receipt;
/* Validate total original compiled compartment-count <= caller's capacity,
 * accepted registered metadata, zero event error state and correct tick.
 * A frozen production B2.4 model currently has 1010 compartments.
 */
int p07_b4m_trace_init(p07_b4m_spike_trace *trace,
    p07_b3c2_hw_scheduler *scheduler,uint16_t (*spikes)[2],size_t capacity);
/* Register this directly as B3c2's trace hook; invoked before slot eviction
 * and before dispatch ACK. Reads all 8 trace words AND 2 state words for
 * every processed compartment via existing P03 MMIO host debug bank.
 */
int p07_b4m_trace_on_dispatch(void *context,p03_hw_adapter *hw,
    uint8_t core,uint8_t slot,uint32_t tick,uint32_t packet_count);
/* Only succeeds after 27 complete source traces; sorts original independent
 * spike tuples in canonical (core,compartment) order for B2b. A later
 * source_spikes verification may compare these to B1.2 trusted routes.
 */
int p07_b4m_trace_finalize(p07_b4m_spike_trace *trace,
    p07_b4m_trace_receipt *receipt);
/* Prepare for next tick only after successful verified physical B3 barrier
 * ACK; keep spike buffer stable until NEXT bank commit completes.
 */
int p07_b4m_trace_advance(p07_b4m_spike_trace *trace);
#endif
