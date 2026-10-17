#ifndef LOIHI_TWIN_V3_P07_A1_INGRESS_H
#define LOIHI_TWIN_V3_P07_A1_INGRESS_H

/* Independent P07-A1 image/axon transfer. P05 v1 stays byte-identical.
 * All wire integers are explicit little-endian. Never cast bytes to structs.
 * No BSP, MMIO, dynamic memory, or modification of accepted P03/P05 APIs.
 */
#include <stddef.h>
#include <stdint.h>

#define P07_A1_VERSION 1u
#define P07_A1_HEADER_BYTES 128u
#define P07_A1_PIXEL_COUNT 784u
#define P07_A1_MAP_BYTES 1568u
#define P07_A1_IMAGE_BYTES 784u
#define P07_A1_RECORD_BYTES 2480u
#define P07_A1_INPUT_TICKS 25u
#define P07_A1_TOTAL_TICKS 26u
#define P07_A1_AXON_CAPACITY 4096u

enum {
    P07_A1_OK = 0,
    P07_A1_BAD_ARGUMENT = -1,
    P07_A1_BAD_LAYOUT = -2,
    P07_A1_BAD_CRC = -3,
    P07_A1_BAD_MAPPING = -4,
    P07_A1_BAD_TICK = -5,
    P07_A1_BAD_CAPACITY = -6
};

typedef struct {
    uint32_t core_id;
    uint32_t map_count;
    uint32_t payload_crc32;
    uint8_t ddr_sha256[32];
    uint8_t deployment_fingerprint[32];
} p07_a1_info;

/* Validate the entire immutable 2480-byte record, including reserved
 * fields, strict one-to-one mapping, nonzero provenance digests and CRCs.
 * Inspect and copy accepted provenance before any hardware access.
 */
int p07_a1_validate(const uint8_t *record, size_t record_bytes,
                    p07_a1_info *out);

/* Evaluate the frozen P06 encoder independently in C: (t + 17*i) % 25;
 * floor((s+1)*pixel/255) > floor(s*pixel/255).
 * Output is in ascending PIXEL order, carrying compiled destination axons,
 * which are not assumed to be sorted or equal to pixel indices.
 * tick 25 is always empty; caller owns destination CURRENT-bank append,
 * NEXT-bank preservation, 4096 aggregate capacity and reset in P07-A2.
 * Fail closed; never partially write out_axons on error.
 */
int p07_a1_tick_events(const uint8_t *record, size_t record_bytes,
                       uint32_t tick, uint16_t *out_axons,
                       size_t out_capacity, size_t *out_count);

#endif
