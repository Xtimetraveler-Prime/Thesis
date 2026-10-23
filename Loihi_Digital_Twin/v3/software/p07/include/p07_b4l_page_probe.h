#ifndef P07_B4L_PAGE_PROBE_H
#define P07_B4L_PAGE_PROBE_H
/* B4l hardware paging bring-up: 27 logical cores, exactly three slots.
 * Pure C11 and injected operations; real board uses the accepted P03
 * p03_hw_page / p03_hw_debug_word transport. NO inference/dispatch.
 */
#include <stdint.h>
#define B4L_PROBE_CORES 27u
#define B4L_PROBE_SLOTS 3u
#define B4L_PROBE_RECORD_BYTES 0x80000u
#define B4L_PROBE_BASE UINT64_C(0x40000000)
#define B4L_PROBE_CONFIG_OFFSET 0x1000u
#define B4L_PROBE_AXON_OFFSET 0x7000u
#define B4L_PROBE_SYNAPSE_OFFSET 0xF000u
#define B4L_PROBE_ROUTE_DESCRIPTOR_OFFSET 0x4F000u
#define B4L_PROBE_ROUTE_OFFSET 0x50000u
#define B4L_PROBE_STATE_OFFSET 0x5000u
#define B4L_PROBE_DIRTY_MASK UINT32_C(0x00000100)
#define B4L_PROBE_PAGE_INS 28u
#define B4L_PROBE_PAGE_OUTS 1u
#define B4L_PROBE_FAIL  (-1)
#define B4L_PROBE_OK     0

typedef struct {
    int (*page)(void *ctx, uint32_t core, uint32_t slot,
                int page_out, int mutable_only, uint64_t *cycles);
    /* Read/write one 32-bit low state/config word through real PL debug. */
    int (*debug)(void *ctx, uint32_t slot, uint32_t bank,
                 int write, uint32_t *value);
    /* Noncoherent physical DDR word read with cache invalidation. */
    int (*ddr_read)(void *ctx, uint64_t physical_address, uint32_t *value);
} b4l_probe_ops;

typedef struct {
    uint32_t unique_cores, page_ins, page_outs;
    uint32_t state_before, state_dirty, state_ddr_saved, state_restored;
    uint32_t last_core, last_slot, first_error, done;
    uint64_t page_cycles;
} b4l_probe_receipt;

/* Error latched; no subsequent paging after a failed physical operation.
 * In particular PAGE_OUT must finish and be confirmed before slot-0
 * may be evicted for core 3. The original frozen model stays unchanged
 * on the host; the actual DDR copy is deliberately mutated as a test.
 */
int b4l_probe_run(const b4l_probe_ops *ops, void *ctx,
                  b4l_probe_receipt *receipt);
#endif
