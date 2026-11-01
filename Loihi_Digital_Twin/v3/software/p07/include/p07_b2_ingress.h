#ifndef LOIHI_TWIN_V3_P07_B2_INGRESS_H
#define LOIHI_TWIN_V3_P07_B2_INGRESS_H
/* Independent portable C11 decoder for P06B13I1. No malloc/MMIO/BSP/DDR IO.
 * Trusted mapping/digests must be independently loaded from the accepted B2.4
 * snapshot and remain immutable throughout a run. Does not enable FPGA launch.
 */
#include <stddef.h>
#include <stdint.h>
#define P07_B2_INGRESS_VERSION 1u
#define P07_B2_HEADER_BYTES 128u
#define P07_B2_IMAGE_BYTES 784u
#define P07_B2_INPUT_TICKS 25u
#define P07_B2_TOTAL_TICKS 26u
#define P07_B2_ROUTE_BYTES 6u
#define P07_B2_MAX_CORES 126u
#define P07_B2_MAX_ROUTES (P07_B2_IMAGE_BYTES * P07_B2_MAX_CORES)
#define P07_B2_MAX_FRAME_BYTES (P07_B2_HEADER_BYTES + P07_B2_MAX_ROUTES * P07_B2_ROUTE_BYTES + P07_B2_IMAGE_BYTES)
#define P07_B2_PER_CORE_DEPTH 4096u

typedef enum {
    P07_B2_OK=0, P07_B2_ARGUMENT=-1, P07_B2_HEADER=-2,
    P07_B2_DIGEST=-3, P07_B2_CRC=-4, P07_B2_BOUNDS=-5,
    P07_B2_ROUTE=-6, P07_B2_CAPACITY=-7, P07_B2_TICK=-8
} p07_b2_status;

typedef struct {
    uint32_t core_count;
    uint32_t route_count;
    const uint8_t *trusted_routes; /* 6*route_count bytes, from frozen compiled mapping */
    size_t trusted_routes_bytes;
    uint8_t compiled_sha256[32]; /* fixed from verified B2.4/B2.5 */
    uint8_t capacity_sha256[32];
} p07_b2_ingress_binding;

typedef struct {
    const uint8_t *wire;      /* borrowed: immutable after successful validation */
    size_t wire_bytes;
    const uint8_t *routes;    /* borrowed slice of wire */
    const uint8_t *pixels;    /* borrowed slice of wire */
    uint32_t route_count;
    uint32_t core_count;
} p07_b2_ingress_view;

typedef struct {
    uint16_t core_id;
    uint16_t axon_id;
} p07_b2_input_event;

typedef struct {
    uint32_t total;
    uint32_t counts[P07_B2_MAX_CORES];
    uint32_t event_crc32; /* CRC of canonical repeated LE (core:u16,axon:u16) */
} p07_b2_ingress_receipt;

/* All-or-nothing: on rejection, *out remains bit-for-bit unchanged. */
p07_b2_status p07_b2_decode_ingress(const uint8_t *wire, size_t wire_bytes,
                                     const p07_b2_ingress_binding *trusted,
                                     p07_b2_ingress_view *out);
/* Two-pass preflight; rejection never writes events[] nor receipt.
 * No inferred pixel-to-axon identity; events remain pixel/core canonical.
 * Event output storage belongs to caller (static DDR-safe for A53).
 */
p07_b2_status p07_b2_ingress_tick(const p07_b2_ingress_view *view, uint32_t tick,
                                   p07_b2_input_event *events, size_t event_capacity,
                                   p07_b2_ingress_receipt *receipt);
#endif
