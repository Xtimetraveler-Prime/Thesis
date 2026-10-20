#ifndef LOIHI_TWIN_V3_P07_B3C_PACKET_BRIDGE_H
#define LOIHI_TWIN_V3_P07_B3C_PACKET_BRIDGE_H
/*
 * P07-B.3c1 proposed physical-readback -> independently bound B1.3 frame.
 * Native/host verifiable, C11, no heap, no destination DDR/MMIO writes.
 * Does not constitute an A53 ELF, physical source-spike attestation,
 * real CORE/NEXT insertion, or a 27-core FPGA inference.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b2_packet.h"
#include "p07_b3_pager.h"
#include "p03_hw_adapter.h"
#define P07_B3C_MAX_CORES P07_B3_CORES
#define P07_B3C_MAX_RAW_WORDS P07_B2_MAX_ROUTE_BINDINGS
#define P07_B3C_MAX_FRAME_BYTES (P07_B2_HEADER_BYTES + 12u*P07_B3C_MAX_RAW_WORDS)
typedef struct {
    uint8_t source_core;
    uint8_t slot;
    uint16_t packet_count;
    const uint64_t *words;  /* immutable, obtained from verified PL packet bank */
} p07_b3c_core_words;
typedef struct {
    uint32_t core_count, word_count;
    uint32_t count[P07_B3C_MAX_CORES];
    uint64_t words[P07_B3C_MAX_RAW_WORDS];
} p07_b3c_capture;
typedef int (*p07_b3c_packet_reader)(void *ctx,uint8_t slot,uint16_t index,uint64_t *out);
enum { P07_B3C_OK=0, P07_B3C_BAD_ARGUMENT=-1, P07_B3C_BAD_FRAME=-2,
       P07_B3C_CAPACITY=-3, P07_B3C_READ_ERROR=-4,
       P07_B3C_B13_REJECT=-5 };
/*
 * Capture one completed source PL packet bank. A failure leaves capture's
 * committed counts/words untouched; do not retry a broken physical run.
 * Caller owns a disjoint temporary workspace of up to 4096 64-bit words;
 * no large A53 stack array is allocated by this routine.
 * The external caller owns quiescence and complete source-spike evidence.
 */
int p07_b3c_capture_core(p07_b3c_capture *cap, uint32_t source_core,
    uint8_t slot, uint32_t emitted, uint64_t *workspace,
    size_t workspace_words, p07_b3c_packet_reader reader,void *ctx);
/* Bind to the ACTUAL accepted P03 hardware debug packet adapter. Do not
 * pass an uninitialized board adapter or assume this is a physical test. */
int p07_b3c_p03_reader(void *ctx,uint8_t slot,uint16_t index,uint64_t *word);
/*
 * Construct canonical P06B13R1 packet bytes using caller-owned scratch;
 * full strict B.2b decoder verifies canonical B1.2 routes, independent
 * trusted SHA identities and authoritative emitting-neuron provenance.
 * Output and output length untouched on failure. The source list must
 * come from independent HLS evidence, never inferred from packet words.
 * Both buffers require max 98,432 bytes; they must not overlap.
 */
int p07_b3c_encode_frame(const p07_b3c_core_words *cores,
    size_t core_count,uint32_t emitted_tick,
    const p07_b2_packet_binding *binding,
    const uint16_t (*source_spikes)[2],size_t spike_count,
    uint8_t *scratch,size_t scratch_capacity,
    uint8_t *frame,size_t frame_capacity,size_t *frame_bytes);
#endif
