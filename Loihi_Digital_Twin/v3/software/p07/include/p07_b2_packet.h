#ifndef LOIHI_TWIN_V3_P07_B2_PACKET_H
#define LOIHI_TWIN_V3_P07_B2_PACKET_H
/* Portable read-only P06B13R1 decoder + transactional count/epoch admission.
 * Provenance must originate from actual authoritative PL emitted spikes.
 * This module neither writes a physical NEXT bank nor schedules the FPGA.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b2_ingress.h"
#define P07_B2_PACKET_ENTRY_BYTES 12u
#define P07_B2_MAX_ROUTE_BINDINGS 8192u
#define P07_B2_PACKET_MAX_BYTES (P07_B2_HEADER_BYTES + P07_B2_MAX_ROUTE_BINDINGS * P07_B2_PACKET_ENTRY_BYTES)
typedef struct {
    uint16_t source_core, source_compartment, destination_core, destination_axon;
} p07_b2_route;
typedef struct {
    uint32_t target_tick;
    uint16_t source_core, source_compartment, destination_core, destination_axon;
} p07_b2_packet;
typedef struct {
    uint32_t core_count, route_count;
    const p07_b2_route *routes; /* trusted frozen canonical source/core/axon edges */
    const uint16_t *compartments_per_core; /* core_count entries, authoritative */
    uint8_t compiled_sha256[32], capacity_sha256[32];
} p07_b2_packet_binding;
typedef struct {
    const uint8_t *wire; /* borrowed immutable until accepted next barrier */
    uint32_t emitted_tick, packet_count;
    const uint8_t *packets; /* wire+128 */
} p07_b2_packet_view;
typedef struct {
    uint32_t tick;
    uint32_t pending_current[P07_B2_MAX_CORES];
} p07_b2_epoch_state;
typedef struct {
    uint32_t emitted, consumed_routed;
    uint32_t current[P07_B2_MAX_CORES];
    uint32_t next[P07_B2_MAX_CORES];
    uint32_t emitted_by_core[P07_B2_MAX_CORES];
} p07_b2_packet_receipt;
/* -9 denotes invalid packet topology/order/provenance, -10 epoch/overflow. */
#define P07_B2_PACKET_INVALID ((p07_b2_status)-9)
#define P07_B2_PACKET_EPOCH ((p07_b2_status)-10)
/* Only after complete validation is out assigned. authoritative_spikes must be
 * supplied from a verified PL source-spike trace; NULL is fail-closed.
 * Entries are (source_core,source_compartment), sorted and unique.
 */
p07_b2_status p07_b2_packet_decode(
    const uint8_t *wire, size_t wire_bytes, const p07_b2_packet_binding *binding,
    uint32_t tick, const uint16_t (*authoritative_spikes)[2], size_t spike_count,
    p07_b2_packet_view *out);
/* Per-core external_current is independently obtained from accepted B.2a.
 * No hardware side effects and no mutation on failure. On success the next
 * pending bank counts are committed, with bank flip once per global epoch.
 */
p07_b2_status p07_b2_packet_commit(
    const p07_b2_packet_view *frame, const p07_b2_packet_binding *binding,
    const uint32_t *external_current, p07_b2_epoch_state *state,
    p07_b2_packet_receipt *receipt);
#endif
