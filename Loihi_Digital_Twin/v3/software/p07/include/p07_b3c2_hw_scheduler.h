#ifndef LOIHI_TWIN_P07_B3C2_HW_SCHEDULER_H
#define LOIHI_TWIN_P07_B3C2_HW_SCHEDULER_H
/* Native-testable policy-to-original-P03-physical-adapter binding.
 * NO right to run on KV260 until DDR/ELF/startup identity admitted.
 * Native fake bus is not physical proof. */
#include <stddef.h>
#include <stdint.h>
#include "p07_b3_pager.h"
#include "p07_b3c_packet_bridge.h"
#include "p07_b3c3_next_commit.h"
#include "p03_hw_adapter.h"
enum { P07_B3C2_OK=0, P07_B3C2_BARRIER=1, P07_B3C2_DONE=2,
       P07_B3C2_INVALID=-1, P07_B3C2_FAULTED=-2 };
/* Optional B4m physical trace probe. Must be installed before the first
 * dispatch. Called immediately after copying a dispatch's actual P03 packets
 * and BEFORE the 3-slot pager may evict/overwrite this HLS trace. Any nonzero
 * return poisons the existing B3a/B3c2 hardware scheduler. */
typedef int (*p07_b3c2_trace_hook)(void *ctx,p03_hw_adapter *hw,
    uint8_t core,uint8_t slot,uint32_t tick,uint32_t packet_count);
typedef struct {
    p07_b3_pager *pager;
    p03_hw_adapter *hw;
    uint64_t *raw_words; /* caller-owned immutable-after-capture array */
    size_t raw_capacity; /* max 8192 */
    uint64_t *temporary; /* caller-owned per-core scratch max 4096 */
    size_t temporary_capacity;
    p07_b3c_core_words cores[P07_B3_CORES]; /* source-indexed views */
    uint32_t word_count;
    uint32_t first_fault;
    uint32_t poisoned;
    p07_b3c2_trace_hook trace_hook; /* null for accepted B4l */
    void *trace_context;
} p07_b3c2_hw_scheduler;
/* No hardware actions before initialization; live P03 shell identified.
 * Caller independently proves exclusive 64MiB P02 ownership and ELF map.
 * All 27 logical IDs must already be registered with genuine P03 metadata,
 * source route axons admitted, and valid CURRENT counts populated. */
int p07_b3c2_init(p07_b3c2_hw_scheduler *s,p07_b3_pager *pager,
    p03_hw_adapter *hw,uint64_t *word_buffer,size_t word_capacity,
    uint64_t *scratch,size_t scratch_capacity);
/* Install independent P03 trace verifier before first scheduling operation.
 * Immutable across the image. Null callback is accepted for earlier B4l
 * first-epoch path but is NEVER sufficient for B4m numerical inference. */
int p07_b3c2_set_trace_hook(p07_b3c2_hw_scheduler *scheduler,
    p07_b3c2_trace_hook hook,void *context);
/* Run exactly one B3a operation. Real p03_hw_page/dispatch must return
 * completed status before B3a ACK. Capture all emitted PL words immediately
 * after each dispatch (packet bank overwritten on next dispatch).
 * BARRIER never auto-ACKed: requires complete B2b/B3c3 preflight/commit.
 */
int p07_b3c2_step(p07_b3c2_hw_scheduler *s,p07_b3_op *operation);
/* ACK after B3c3 has independently decoded every captured source and
 * committed the NEXT physical packet plan; receipt must match totals and
 * current/next parity. Never call for a mere START write or host mock. */
int p07_b3c2_barrier_ack(p07_b3c2_hw_scheduler *s,
    const p07_b3_op *operation,const p07_b3c3_receipt *receipt);
#endif
