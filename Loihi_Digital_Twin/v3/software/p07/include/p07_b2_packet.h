#ifndef LOIHI_TWIN_V3_P07_B2_PACKET_H
#define LOIHI_TWIN_V3_P07_B2_PACKET_H
/* P07-B.2b portable C11. Standalone-compatible, NOT running A53 firmware.
 * Output routes and spike provenance must originate from independently
 * verified frozen deployment/PL trace; untrusted frames cannot bind themselves.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b2_ingress.h"
#define P07_B2B_PACKET_BYTES 12u
#define P07_B2B_FRAME_HEADER 128u
#define P07_B2B_STAGING_BYTES 0x000E0000u
#define P07_B2B_MAX_FRAME_PACKETS ((P07_B2B_STAGING_BYTES-P07_B2B_FRAME_HEADER)/P07_B2B_PACKET_BYTES)
#define P07_B2B_COMPARTMENTS 1024u

typedef enum {
    P07_B2B_OK=0, P07_B2B_ARGUMENT=-1, P07_B2B_HEADER=-2,
    P07_B2B_DIGEST=-3, P07_B2B_CRC=-4, P07_B2B_BOUNDS=-5,
    P07_B2B_ROUTE=-6, P07_B2B_ORDER=-7, P07_B2B_PROVENANCE=-8,
    P07_B2B_CAPACITY=-9, P07_B2B_TICK=-10, P07_B2B_FINAL=-11
} p07_b2b_status;
/* Source-ordered trusted route tuple, not the B1.3 wire record. */
typedef struct {
    uint16_t source_core, source_compartment, destination_core, destination_axon;
} p07_b2b_route;
typedef struct {uint16_t core, compartment;} p07_b2b_origin;
typedef struct {
    uint32_t target_tick;
    uint16_t source_core, source_compartment, destination_core, destination_axon;
} p07_b2b_packet;
typedef struct {
    uint32_t core_count, route_count;
    const p07_b2b_route *routes;
    const uint16_t *compartments_per_core; /* core_count entries */
    uint8_t compiled_sha256[32], capacity_sha256[32];
} p07_b2b_binding;
typedef struct {
    const uint8_t *wire; /* immutable borrowed packet frame */
    size_t wire_bytes;
    uint32_t emitted_tick, packet_count;
    const uint8_t *payload; /* Python SpikePacket.logical_key order */
    uint32_t source_counts[P07_B2_MAX_CORES];
    uint32_t destination_counts[P07_B2_MAX_CORES];
} p07_b2b_frame_view;
typedef struct {
    uint32_t tick, current_bank, external_total, routed_current, routed_next;
    uint32_t current_by_core[P07_B2_MAX_CORES];
    uint32_t next_by_core[P07_B2_MAX_CORES];
    uint32_t emitted_by_core[P07_B2_MAX_CORES];
    uint32_t packet_payload_crc32;
} p07_b2b_receipt;
typedef struct {
    const p07_b2_ingress_view *ingress;
    const p07_b2b_binding *binding;
    p07_b2_input_event *pending; /* caller-owned NEXT buffer */
    size_t pending_capacity;
    uint32_t tick, pending_count;
    uint32_t pending_by_core[P07_B2_MAX_CORES];
} p07_b2b_epoch;
/* No writes to out on any rejection. Authenticated source-spike list is
 * required to detect a wholly omitted emitting source; zero count may be NULL.
 */
p07_b2b_status p07_b2b_decode(const uint8_t *frame, size_t frame_bytes,
     const p07_b2b_binding *trusted, uint32_t emitted_tick,
     const p07_b2b_origin *source_spikes, size_t source_count,
     p07_b2b_frame_view *out);
/* Caller-owned pending buffer. Reinitialize/reset for each 26-tick image. */
p07_b2b_status p07_b2b_epoch_init(p07_b2b_epoch *state,
     const p07_b2_ingress_view *ingress, const p07_b2b_binding *trusted,
     p07_b2_input_event *pending, size_t pending_capacity);
/* Two-phase admission: no pending/state/receipt writes on rejection.
 * Success stages NEXT events; it does NOT perform physical bank/MMIO writes.
 */
p07_b2b_status p07_b2b_step(p07_b2b_epoch *state,
     const uint8_t *packet_frame, size_t frame_bytes,
     const p07_b2b_origin *source_spikes, size_t source_count,
     p07_b2b_receipt *out);
#endif
