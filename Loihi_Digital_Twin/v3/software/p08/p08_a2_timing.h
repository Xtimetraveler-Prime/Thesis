#ifndef LOIHI_TWIN_V3_P08_A2_TIMING_H
#define LOIHI_TWIN_V3_P08_A2_TIMING_H
/* Experimental latency-only companion to the FROZEN P07A4R01 journal.
 * This is a separate, disposable 1MiB region, not a P07 wire ABI revision.
 * All integer fields little-endian; all intervals are raw A53 CNTVCT ticks
 * except the two PL hardware-cycle counters. No CPU/PL Hz is invented.
 */
#include <stddef.h>
#include <stdint.h>

#define P08_A2_BASE UINT32_C(0x43000000)
#define P08_A2_CAPACITY 1048576u
#define P08_A2_HEADER_BYTES 256u
#define P08_A2_RECORD_BYTES 96u
#define P08_A2_MAX_FRAMES 10000u
#define P08_A2_VERSION 1u
#define P08_A2_OK_STATUS UINT32_C(0x600D600D)
#define P08_A2_FAIL_STATUS UINT32_C(0xDEAD0001)

typedef struct {
    uint32_t image_index;
    uint32_t flags; /* bit 0 => selected full-trace frame */
    uint64_t service_start;     /* execute_image entry */
    uint64_t after_ingress;     /* validated 2480B ingress generated */
    uint64_t after_neural;      /* 26-tick p07_a2_run_frame complete */
    uint64_t after_commit;      /* P07 record and selected trace flushed */
    uint64_t pl_dispatch_cycles; /* PL clock domain, NOT CNTVCT */
    uint64_t pl_page_cycles;     /* PL clock domain, NOT CNTVCT */
    uint64_t ps_inference_ticks; /* excludes initial page-in & write_result */
    uint64_t ps_control_ticks;   /* P03 callback interval, not all service */
    uint64_t ps_route_ticks;
    uint64_t ps_barrier_ticks;
} p08_a2_record;

uint32_t p08_a2_crc32(const uint8_t *buf, size_t n);
int p08_a2_pack_header(uint8_t *out, size_t size, uint32_t frame_count,
                        uint32_t trace_frame, uint32_t completed,
                        uint32_t status, uint64_t cntfrq_hz,
                        uint64_t dataset_start, uint64_t dataset_stop);
int p08_a2_pack_record(uint8_t *out, size_t size, const p08_a2_record *record);
#endif
