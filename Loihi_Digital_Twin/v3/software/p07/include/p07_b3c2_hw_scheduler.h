#ifndef LOIHI_TWIN_P07_B3C2_HW_SCHEDULER_H
#define LOIHI_TWIN_P07_B3C2_HW_SCHEDULER_H
/* Native-testable policy-to-original-P03-physical-adapter binding.
 * NO right to run on KV260 until DDR/ELF/startup identity admitted.
 * Native fake bus is not physical proof. */
#include <stddef.h>
#include <stdint.h>
#include "p07_b3_pager.h"
#include "p07_b3c_packet_bridge.h"
#include "p03_hw_adapter.h"
enum { P07_B3C2_OK=0, P07_B3C2_BARRIER=1, P07_B3C2_DONE=2,
       P07_B3C2_INVALID=-1, P07_B3C2_FAULTED=-2 };
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
} p07_b3c2_hw_scheduler;
/* No hardware actions before initialization; live P03 shell identified.
 * Caller independently proves exclusive 64MiB P02 ownership and ELF map.
 * All 27 logical IDs must already be registered with genuine P03 metadata,
 * source route axons admitted, and valid CURRENT counts populated. */
int p07_b3c2_init(p07_b3c2_hw_scheduler *s,p07_b3_pager *pager,
    p03_hw_adapter *hw,uint64_t *word_buffer,size_t word_capacity,
    uint64_t *scratch,size_t scratch_capacity);
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
    const p07_b3_op *operation,uint32_t committed_next_packets);
#endif
