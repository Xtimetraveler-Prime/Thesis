#ifndef LOIHI_TWIN_V3_P05_DEPLOYMENT_H
#define LOIHI_TWIN_V3_P05_DEPLOYMENT_H

/* P05.1 contract checkpoint: portable, read-only validator.
 * No Xilinx/BSP dependency, dynamic memory, MMIO, or DDR writes.
 * All integers are explicit little-endian uint32_t; never cast a wire
 * byte buffer into a native C struct. This ABI is NOT the P03 manifest.
 */
#include <stddef.h>
#include <stdint.h>

#define P05_DEPLOY_MAGIC UINT32_C(0x47353050) /* bytes "P05G" */
#define P05_DEPLOY_VERSION UINT32_C(1)
#define P05_DEPLOY_HEADER_BYTES 256u
#define P05_DEPLOY_PAYLOAD_BASE UINT32_C(0x43F00000)
#define P05_DEPLOY_PAYLOAD_CAPACITY UINT32_C(0x000E0000)
#define P05_DEPLOY_HEADER_BASE UINT32_C(0x43FE0000)
#define P05_DEPLOY_MAILBOX_BASE UINT32_C(0x43FF0000)
#define P05_DEPLOY_BACKING_BASE UINT32_C(0x40000000)
#define P05_DEPLOY_RECORD_BYTES UINT32_C(0x00080000)
#define P05_DEPLOY_MAX_CORES 126u /* Last record ends before payload base. */
#define P05_DEPLOY_MAX_SLOTS 3u
#define P05_DEPLOY_MAX_STEPS 10000u
#define P05_DEPLOY_EVENT_DEPTH 4096u
#define P05_DEPLOY_CORE_BYTES 32u
#define P05_DEPLOY_EVENT_BYTES 16u
#define P05_DEPLOY_CHECKPOINT_BYTES 16u

/* Class applies to a *post-barrier* diagnostic checkpoint.
 * The physical capture and comparison are future P05.1 deliverables.
 */
#define P05_OBS_STATE0 1u
#define P05_OBS_EVENT0 2u
#define P05_OBS_EVENT1 3u
#define P05_OBS_PACKET0 4u

enum {
    P05_VALID = 0,
    P05_BAD_ARGUMENT = -1,
    P05_BAD_HEADER = -2,
    P05_BAD_CHECKSUM = -3,
    P05_BAD_CORE = -4,
    P05_BAD_EVENT = -5,
    P05_BAD_CHECKPOINT = -6,
    P05_BAD_BOUNDS = -7
};

typedef struct {
    uint32_t timesteps;
    uint32_t core_count;
    uint32_t slot_count;
    uint32_t diagnostic_mode;
    uint32_t event_count;
    uint32_t checkpoint_count;
    uint32_t payload_crc32;
    uint32_t header_crc32;
    uint32_t dispatch_count;
} p05_deployment_info;

/* Header[23] holds CRC32 with its own bytes zeroed; header[22] holds
 * CRC32(payload). Payload is precisely:
 *   core_count * 32 bytes: ID, metaLo, metaHi, config0,
 *       initial_record_CRC32, sole_registered_axon, event0_count,
 *       event1_count
 *   event_count * 16 bytes: zero-based timestep, logical_id, axon, zero
 *   checkpoint_count * 16 bytes: completed zero-based timestep,
 *       logical_id, class, expected_crc32.
 * Core rows ARE deterministic per-step service order. Inputs sorted
 * (timestep, service rank); checkpoints sorted (timestep, rank, class)
 * without duplicate checkpoint keys.
 */
int p05_deployment_validate(
    const uint8_t *header, size_t header_bytes,
    const uint8_t *payload, size_t payload_bytes,
    p05_deployment_info *out_info);

#endif
