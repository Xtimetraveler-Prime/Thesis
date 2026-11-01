#ifndef LOIHI_TWIN_V3_P07_B5_RAW_CAPTURE_H
#define LOIHI_TWIN_V3_P07_B5_RAW_CAPTURE_H
/*
 * P07-B.5.3 experimental original-HLS bank7 RAW trace DDR sidecar.
 * PC native source / candidate only; NOT built in accepted V3 A53 ELF,
 * NOT physically executed, NOT evidence that a trace came from FPGA.
 *
 * Exact layout: 26 ticks x 1010 original compartments x 32 bytes,
 * little-endian 8 x uint32 trace registers per compartment, ascending
 * logical-core then ascending compartment order within each tick.
 * B5 firmware must attach record() exactly where ORIGINAL V3 already
 * read each freshly completed HLS bank7 trace word, BEFORE page eviction.
 * Accepted production P03 adapter, P03 HLS, V3 firmware and B2.4 weights
 * stay unchanged. New physical DDR sidecar ownership is UNPROVEN.
 */
#include <stddef.h>
#include <stdint.h>

#define P07_B5_CAPTURE_MAGIC UINT32_C(0x42354331)
#define P07_B5_CAPTURE_CORES 27u
#define P07_B5_CAPTURE_TICKS 26u
#define P07_B5_CAPTURE_NEURONS 1010u
#define P07_B5_CAPTURE_WORDS_PER_NEURON 8u
#define P07_B5_CAPTURE_BYTES (P07_B5_CAPTURE_TICKS*P07_B5_CAPTURE_NEURONS*32u)
#define P07_B5_CAPTURE_WORDS (P07_B5_CAPTURE_BYTES/sizeof(uint32_t))
#define P07_B5_CAPTURE_RECORDS (P07_B5_CAPTURE_TICKS*P07_B5_CAPTURE_NEURONS)
/* This address is only a candidate. Proven non-overlap with the B4m
 * source model/bindings/routes/ingress/mailbox is NOT a proof of
 * physical DDR ownership relative to FSBL/TF-A/PMU/Linux/memory maps.
 * Do not use this address on real hardware until independently admitted.
 */
#define P07_B5_CAPTURE_DDR_CANDIDATE_BASE UINT32_C(0x42000000)
#define P07_B5_CAPTURE_DDR_CANDIDATE_END (P07_B5_CAPTURE_DDR_CANDIDATE_BASE+P07_B5_CAPTURE_BYTES)

enum {
  P07_B5_CAPTURE_OK=0,
  P07_B5_CAPTURE_INVALID=-1,
  P07_B5_CAPTURE_ORDER=-2,
  P07_B5_CAPTURE_RESERVED=-3,
  P07_B5_CAPTURE_INCOMPLETE=-4
};
typedef struct {
    uint32_t magic,active,fault,finished,word_capacity,next_record;
    uint32_t core_prefix[P07_B5_CAPTURE_CORES];
    uint16_t core_compartments[P07_B5_CAPTURE_CORES];
    volatile uint32_t *ddr_words;
} p07_b5_raw_capture;

/* Sidecar memory must be independently OWNED/authorized BEFORE use;
 * this function itself does not establish that proof.
 * Require contiguous uint32_t writable words and exactly 210080 words.
 * The only writes it performs are a zero reset inside that provided range.
 */
int p07_b5_capture_begin(p07_b5_raw_capture *r,
    volatile uint32_t *sidecar,size_t words,
    const uint16_t core_compartments[P07_B5_CAPTURE_CORES]);

/* Append one real P03 debug-bank7 256-bit word. A53 LE is required;
 * original HLS trace[4..5] includes committed after state and trace[6]
 * bit0 is the independent spike flag. Exactly one call per neuron,
 * in tick/core/comp order; rejects duplicates, omission, out-of-order
 * and nonzero reserved bits BEFORE touching memory.
 */
int p07_b5_capture_record(p07_b5_raw_capture *r,
    uint32_t tick,uint32_t core,uint32_t compartment,
    const uint32_t trace8[P07_B5_CAPTURE_WORDS_PER_NEURON]);

/* Success requires ALL 26*1010 original records; caller must then
 * flush cache for EXACT SIDE-CAR address/range and publish a separately
 * versioned B5 physical mailbox BEFORE physical JTAG readback.
 */
int p07_b5_capture_finalize(p07_b5_raw_capture *r);
#endif
