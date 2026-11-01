#ifndef LOIHI_TWIN_V3_P07_B3_PAGER_H
#define LOIHI_TWIN_V3_P07_B3_PAGER_H
/* P07-B.3a: host-buildable plan/ack ownership state machine, NOT board MMIO.
 * Three P03 URAM slots, 27 P02 DDR records, one serial dispatch engine.
 * Dirty eviction and final flush require SUCCESS acknowledgments from a
 * later physical adapter; a failed operation irreversibly faults this run.
 */
#include <stdint.h>
#define P07_B3_CORES 27u
#define P07_B3_SLOTS 3u
#define P07_B3_TICKS 26u
#define P07_B3_RECORD_BYTES UINT64_C(0x80000)
#define P07_B3_BACKING_BASE UINT64_C(0x40000000)
#define P07_B3_FULL_IN_BYTES 0x6B000u
#define P07_B3_MUTABLE_OUT_BYTES 0x1A000u
#define P07_B3_NO_CORE UINT32_MAX
#define P07_B3_NO_SLOT UINT32_MAX
#define P07_B3_ORDER_ASCENDING 0u
#define P07_B3_ORDER_ALTERNATING 1u
#define P07_B3_OK 0
#define P07_B3_DONE 1
#define P07_B3_ERROR (-1)
#define P07_B3_FAULTED (-2)

typedef enum {
    P07_B3_PAGE_OUT=1, P07_B3_PAGE_IN=2,
    P07_B3_DISPATCH=3, P07_B3_BARRIER=4,
    P07_B3_FINAL_FLUSH=5
} p07_b3_kind;

typedef struct {
    uint32_t kind, tick, ordinal, core, slot, victim;
    uint32_t current_bank, next_bank, bytes;
    uint64_t backing_address;
} p07_b3_op;

typedef struct {
    uint32_t dispatches, barriers, page_ins, hits;
    uint32_t cold_ins, replacements, dirty_evictions, runtime_outs, final_outs;
    uint64_t read_bytes, write_bytes;
} p07_b3_traffic;

typedef struct {
    uint32_t order_mode, tick, cursor, ordinal, flush_slot;
    int32_t resident[P07_B3_SLOTS];
    uint32_t dirty[P07_B3_SLOTS];
    uint32_t last_use[P07_B3_SLOTS];
    uint32_t stage, selected_slot, selected_core, selected_victim;
    uint32_t has_pending, failed, first_failure_kind;
    p07_b3_op pending;
    p07_b3_traffic counters;
} p07_b3_pager;

/* Hard resets only the C scheduling ledger; does NOT reset PL neuron state,
 * P02 records, the external ingress image, or B2b pending packet banks. */
int p07_b3_init(p07_b3_pager *p, uint32_t order_mode);
/* Pure action preparation: repeats identical operation until acknowledged.
 * Returns DONE only after 26 global barrier ACKs and all 3 final dirty outs.
 * A barrier ACK must only be issued after B.2b verifies the entire epoch and
 * the board adapter proves there is no pending DMA/dispatch/route operation. */
int p07_b3_next(p07_b3_pager *p, p07_b3_op *out);
/* Success=1 means *physical operation* completed, not merely START issued.
 * Caller attests ACK based on later P03 quiescent/hardware result checks.
 * Any failed/mismatched ACK poisons the run; no further scheduling permitted.
 */
int p07_b3_ack(p07_b3_pager *p, const p07_b3_op *observed, int success);
uint64_t p07_b3_core_address(uint32_t core);
#endif
