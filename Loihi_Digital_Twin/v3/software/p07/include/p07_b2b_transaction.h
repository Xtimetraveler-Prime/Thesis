#ifndef LOIHI_TWIN_V3_P07_B2B_TRANSACTION_H
#define LOIHI_TWIN_V3_P07_B2B_TRANSACTION_H
/* P07-B.2b: owner-supplied ordered NEXT tuples, transactional host-native C11.
 * The previously accepted count-only p07_b2_packet_* API stays unchanged.
 * Not hardware bank insertion, a standalone ELF, or scaled execution permission.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b2_packet.h"
#define P07_B2B_PENDING_MAX P07_B2_MAX_ROUTE_BINDINGS
typedef struct {
    const p07_b2_ingress_view *ingress; /* immutable validated B.2a input */
    const p07_b2_packet_binding *binding; /* independent trusted route tables */
    p07_b2_input_event *pending; /* caller-owned buffer, never stacks new frame */
    size_t pending_capacity;
    uint32_t tick, pending_count;
    uint32_t pending_by_core[P07_B2_MAX_CORES];
} p07_b2b_transaction;
typedef struct {
    uint32_t tick, current_bank, external_events, routed_current, routed_next;
    uint32_t current_by_core[P07_B2_MAX_CORES];
    uint32_t next_by_core[P07_B2_MAX_CORES];
    uint32_t emitted_by_core[P07_B2_MAX_CORES];
    uint32_t packet_payload_crc32; /* CRC of 12-byte B1.3 routed records */
    uint32_t ordered_next_crc32; /* CRC of packed LE <HH> core/axon tuples */
} p07_b2b_tx_receipt;
/* No memory buffer clears at initialization. The caller must separately
 * reset physical neuron/context state and banks before starting each image. */
p07_b2_status p07_b2b_transaction_init(p07_b2b_transaction *state,
    const p07_b2_ingress_view *ingress, const p07_b2_packet_binding *binding,
    p07_b2_input_event *pending, size_t pending_capacity);
/* Accept a fully verified B1.3 frame plus independently observed emitting
 * source list. source_spikes may be null only when spike_count == 0.
 * On ANY error: state, pending buffer (all bytes), and receipt unchanged.
 * Successful NEXT tuple order exactly matches canonical B1.3 packet order.
 * No MMIO / writes to PL/DDR occur in these functions. */
p07_b2_status p07_b2b_transaction_step(p07_b2b_transaction *state,
    const uint8_t *wire, size_t wire_bytes,
    const uint16_t (*source_spikes)[2], size_t spike_count,
    p07_b2b_tx_receipt *receipt);
#endif
