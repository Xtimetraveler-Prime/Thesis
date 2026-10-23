#ifndef LOIHI_TWIN_V3_P07_B4M_EPOCH_BRIDGE_H
#define LOIHI_TWIN_V3_P07_B4M_EPOCH_BRIDGE_H
/* P07-B.4m.1: fail-closed FIRST physical integration of an already-completed
 * P03 B3c2 epoch with B1.3 canonical frame, B2b provenance, B3c3 NEXT
 * write and a real B3a barrier ACK. Portable C11; no board launch here.
 *
 * Caller MUST supply INDEPENDENT verified PL emitting-neuron evidence;
 * raw routed P03 packets alone are NOT source-spike evidence.
 * This module cannot manufacture, read, or attest the source trace.
 * The source_evidence_verified flag is a caller-provided admission decision,
 * NOT independent cryptographic or hardware verification. Production callers
 * cannot set this flag until a separate physical source-trace checker exists.
 * No change to accepted B4l first-epoch ELF/receipt.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b3c2_hw_scheduler.h"

enum { P07_B4M_BRIDGE_OK=0, P07_B4M_BRIDGE_ARGUMENT=-1,
       P07_B4M_BRIDGE_FAULT=-2 };
#define P07_B4M_BRIDGE_MAGIC UINT32_C(0x4D344231)
typedef struct {
    uint32_t magic;
    uint32_t tick;
    uint32_t physical_packet_count;
    uint32_t source_spike_count;
    uint32_t route_inserted;
    uint32_t barrier_acks;
    uint32_t destination_bank;
    uint32_t first_failure;
} p07_b4m_barrier_receipt;

/* Called ONLY when p07_b3c2_step returns P07_B3C2_BARRIER.
 * Takes complete original 27 frozen-core P03 packet views and trustworthy
 * B1.2 binding (all 27; routes must be immutable, sorted and exact).
 * scratch and frame must be disjoint, caller-owned >= P07_B3C_MAX_FRAME_BYTES.
 * A failure poisons B3c2/B3a; never resume or claim a barrier after
 * a partial physical NEXT bank write. NO ALLOCATION and NO MMIO except
 * the existing accepted B3c3 physical commit / B3c2 quiescence checks.
 */
int p07_b4m_commit_pending_barrier(
    p07_b3c2_hw_scheduler *scheduler,
    const p07_b3_op *pending,
    const p07_b2_packet_binding *frozen_binding,
    const uint16_t (*independent_source_spikes)[2],
    size_t source_spike_count,
    uint32_t source_evidence_verified,
    uint8_t *scratch,size_t scratch_bytes,
    uint8_t *frame,size_t frame_capacity,
    p07_b4m_barrier_receipt *out);
#endif
