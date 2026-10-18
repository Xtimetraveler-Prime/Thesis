#ifndef LOIHI_TWIN_V3_P07_A2_BATCH_H
#define LOIHI_TWIN_V3_P07_A2_BATCH_H
#include <stddef.h>
#include <stdint.h>
#include "p07_a1_ingress.h"

/* Distinct from P05G. Reserved P05 diagnostic DDR region reused ONLY in
 * the separate P07 application, with 512KiB immutable master at 0x43F00000,
 * ingress records at 0x43F80000, 64B batch envelope at 0x43FE0000,
 * result/trace mailbox at 0x43FF0000 (64 KiB total).
 */
#define P07_A2_MASTER_BASE UINT32_C(0x43F00000)
#define P07_A2_INPUT_BASE UINT32_C(0x43F80000)
#define P07_A2_BATCH_BASE UINT32_C(0x43FE0000)
#define P07_A2_RESULT_BASE UINT32_C(0x43FF0000)
#define P07_A2_RESULT_BYTES 65536u
#define P07_A2_BATCH_HEADER_BYTES 64u
#define P07_A2_MAX_FRAMES 16u
#define P07_A2_FRAME_RESULT_BYTES 128u
#define P07_A2_FRAME_RESULT_OFFSET 256u
#define P07_A2_TRACE_OFFSET 4096u
#define P07_A2_TRACE_BYTES (26u*42u*32u)

typedef struct {
    uint32_t frame_count;
    uint32_t trace_frame;
} p07_a2_batch_info;

int p07_a2_batch_validate(const uint8_t *header, size_t length,
                          p07_a2_batch_info *out);

#endif
