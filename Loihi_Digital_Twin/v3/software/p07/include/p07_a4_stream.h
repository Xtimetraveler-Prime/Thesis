#ifndef LOIHI_TWIN_V3_P07_A4_STREAM_H
#define LOIHI_TWIN_V3_P07_A4_STREAM_H

/* P07-A4.2a: new *candidate*, portable DDR wire ABI for persistent A53.
 * The accepted P07-A2/P03/P05 code is not modified.
 * No board ownership: this header and source have native tests ONLY.
 */
#include <stddef.h>
#include <stdint.h>

#define P07_A4_HEADER_BYTES 256u
#define P07_A4_MAP_BYTES 1568u
#define P07_A4_IMAGE_BYTES 784u
#define P07_A4_MAX_FRAMES 10000u
#define P07_A4_INPUT_BASE UINT32_C(0x41000000)
#define P07_A4_INPUT_CAPACITY UINT32_C(0x800000)
#define P07_A4_JOURNAL_BASE UINT32_C(0x42000000)
#define P07_A4_JOURNAL_CAPACITY UINT32_C(0x100000)
#define P07_A4_JOURNAL_HEADER_BYTES 256u
#define P07_A4_FRAME_RESULT_BYTES 96u
#define P07_A4_DESCRIPTOR_BASE UINT32_C(0x43FE0000)
#define P07_A4_MAPPING_BASE UINT32_C(0x43FE0100)
#define P07_A4_MASTER_BASE UINT32_C(0x43F00000)
#define P07_A4_BACKING_BASE UINT32_C(0x40000000)
#define P07_A4_TRACE_BASE UINT32_C(0x43FF0000)
#define P07_A4_OK_STATUS UINT32_C(0x600D600D)

typedef struct {
    uint32_t frame_count;
    uint32_t trace_frame;
    uint32_t image_crc32;
    uint32_t mapping_crc32;
    uint32_t descriptor_crc32;
    uint8_t ddr_sha256[32];
    uint8_t compiled_sha256[32];
} p07_a4_descriptor;

typedef struct {
    uint32_t image_index;
    uint32_t pixel_crc32;
    uint32_t committed_routes;
    uint32_t dropped_final_packets;
    uint32_t external_event_total;
    uint32_t cycles_low32;  /* NOT a complete wall-clock latency */
    uint8_t output_spikes[26][10];
} p07_a4_compact_result;

/* All records are explicit little-endian bytes, NOT C native structs.
 * Validate all 10k payload bytes and mapping before dispatching core0.
 * No touched output or neural hardware on error.
 */
int p07_a4_validate_staging(const uint8_t *descriptor, size_t descriptor_bytes,
                            const uint8_t *mapping, size_t mapping_bytes,
                            const uint8_t *pixels, size_t pixel_bytes,
                            p07_a4_descriptor *out);

/* Derive exact accepted P07-A1 2480-byte record from one raw 784-byte
 * image + pinned mapping and identities. Caller must have accepted a
 * full dataset with validate_staging before calling. Mapping CRC is
 * rechecked for each frame to reject late mutation.
 */
int p07_a4_make_ingress(const p07_a4_descriptor *verified,
                        const uint8_t *mapping, size_t mapping_bytes,
                        const uint8_t *pixels, size_t pixel_bytes,
                        uint32_t image_index,
                        uint8_t *output, size_t output_bytes);

/* Compact result packer/parser for independent A53/host parity.
 * Packer computes 10 spike counts, readout and per-tick 10-bit mask
 * from binary output_spikes; no labels supplied to hardware.
 */
int p07_a4_pack_result(const p07_a4_compact_result *src,
                       uint8_t *dst, size_t dst_bytes);
int p07_a4_validate_result(const uint8_t *record, size_t bytes,
                           const uint8_t *pixels, size_t pixels_bytes,
                           uint32_t expected_index);

int p07_a4_make_journal_header(uint8_t *dst, size_t bytes,
                               uint32_t count, uint32_t trace_frame,
                               uint32_t descriptor_crc32,
                               uint32_t status, uint32_t completed,
                               uint32_t first_fault);

#endif
