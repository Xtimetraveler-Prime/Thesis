#ifndef LOIHI_TWIN_V3_P07_B4M_FULL_INFERENCE_H
#define LOIHI_TWIN_V3_P07_B4M_FULL_INFERENCE_H
/* Complete A53-ready B3 26-tick INFERENCE CONTROL PATH (source ABI only).
 * Calls genuine original P03 adapter, B4a CURRENT, B3c2 HLS scheduler,
 * independent bank7 spike trace, B2b wire, B3c3 NEXT and B3 barrier.
 *
 * All pointers are caller-owned and must be pinned to exactly authenticated
 * frozen B2.4 content on a separately authorized standalone KV260 run.
 * No executable/bitstream is built or physically run by these C sources.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b4a_current_ingress.h"
#include "p07_b4m_spike_trace.h"
#include "p07_b4m_epoch_bridge.h"
#define P07_B4M_FULL_MAGIC UINT32_C(0x464D3442)
enum {P07_B4M_FULL_OK=0,P07_B4M_FULL_ARGUMENT=-1,
      P07_B4M_FULL_FAULT=-2};

typedef struct {
    uint32_t *merged_current_words; /* exactly 27 * 4096 entries */
    uint16_t (*source_spikes)[2];   /* exactly 1024 entries */
    uint8_t *frame_scratch;         /* 98,432 bytes or more */
    uint8_t *packet_frame;          /* 98,432 bytes or more */
    size_t merged_capacity,source_capacity,frame_capacity,scratch_capacity;
    p07_b4m_spike_trace trace;
} p07_b4m_full_workspace;

typedef struct {
    uint32_t magic,first_fault,barriers,dispatches,page_ins;
    uint32_t page_outs,final_outs,external_current,source_spikes;
    uint32_t captured_packets,inserted_next,classification;
    uint32_t output_spike_counts[10];
    uint32_t trace_compartment_count;
    uint64_t cumulative_trace_fnv64,read_bytes,write_bytes;
} p07_b4m_full_receipt;

/* Caller has already authenticated/bound original 27 P02 DDR records,
 * validated PS128, original P03 shell, 16KiB binding descriptor and
 * immutable B1.2 27-core routes. P03 source trace is read every dispatch
 * before slot replacement. Full 26 epochs are processed, final dirty slots
 * flushed, and output spike-count argmax (lowest index on ties) reported.
 * This is NOT numerical parity or permission to access official TEST.
 * On failure scheduler and B3a are POISONED and the output contains only
 * first_fault. Never resume a partial image.
 */
int p07_b4m_full_run(p07_b3c2_hw_scheduler *scheduler,
    const p07_b2_ingress_binding *ingress_binding,
    const p07_b2_packet_binding *packet_binding,
    const uint8_t *encoded_ingress,size_t encoded_ingress_bytes,
    p07_b4a_read_ddr32 read_ddr,void *reader,
    p07_b4m_full_workspace *workspace,
    p07_b4m_full_receipt *out);
#endif
