#ifndef LOIHI_TWIN_V3_P07_B4A_CURRENT_INGRESS_H
#define LOIHI_TWIN_V3_P07_B4A_CURRENT_INGRESS_H
/* P07-B.4a: first physical CURRENT-input bridge, host-native admission gate.
 * Provisions accepted 27-core B1.3 external spikes into original P03 event
 * banks, joining routed NEXT from preceding tick in canonical axon order.
 * No hidden DDR reads: bare-metal caller must supply a physically verified
 * cache-coherent DDR reader. No rollback after the first external MMIO write.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b2_ingress.h"
#include "p07_b3_pager.h"
#include "p03_hw_adapter.h"
#define P07_B4A_CORES P07_B3_CORES
#define P07_B4A_DEPTH P03_HW_EVENT_DEPTH
#define P07_B4A_WORD_CAPACITY (P07_B4A_CORES * P07_B4A_DEPTH)
enum {
  P07_B4A_OK=0, P07_B4A_ARGUMENT=-1, P07_B4A_REJECT=-2,
  P07_B4A_IO_FAULT=-3, P07_B4A_POISONED=-4
};
/* Callback must return 0 only for a completed 32-bit coherent DDR read.
 * The module separately performs P03 invalidate_range/barrier before reads.
 * This callback is not provided by the accepted original P03 HW ABI.
 */
typedef int (*p07_b4a_read_ddr32)(void *context,uint64_t physical,
                                  uint32_t *value);
typedef struct {
    p07_b3_pager *pager;
    p03_hw_adapter *hw;
    const uint8_t *immutable_wire;
    size_t wire_bytes;
    uint32_t *words; /* caller-owned 27*4096 disjoint canonical merged words */
    uint32_t word_capacity;
    uint32_t tick, current_bank, wire_crc, merged_crc;
    uint32_t prior_by_core[P07_B4A_CORES];
    uint32_t final_by_core[P07_B4A_CORES];
    uint32_t external_by_core[P07_B4A_CORES];
    uint32_t prior_total, external_total, final_total;
    uint32_t prepared, attempted, poisoned, first_failure;
} p07_b4a_plan;
typedef struct {
    uint32_t tick, bank, external_total, prior_total, current_total;
    uint32_t current_by_core[P07_B4A_CORES];
    uint32_t merged_crc;
} p07_b4a_receipt;
/* All counts, route bindings, CRC, current old NEXT and physical axon masks
 * checked BEFORE a write. Uses original B2a input frame verifier and
 * P03 debug read (resident) / separately audited DDR read (nonresident).
 * Does not modify P03 event counts, event data or B3a ledger on rejection.
 */
int p07_b4a_prepare(p07_b4a_plan *plan,p07_b3_pager *pager,
    p03_hw_adapter *hw,const p07_b2_ingress_binding *trusted,
    const uint8_t *ingress,size_t ingress_bytes,
    uint32_t *words,size_t capacity,
    p07_b4a_read_ddr32 read_ddr,void *reader_context);
/* Commit B2a external spikes combined with prior routed NEXT to CURRENT.
 * Actual resident uses original P03 debug bank 6/9; nonresident uses
 * P02 backing DDR+cache clean/barrier. No page-in just to deliver input.
 * Physical partial failure poisons the image and B3a ledger permanently;
 * receipt is written only after every physical write is complete.
 */
int p07_b4a_commit(p07_b4a_plan *plan,p07_b4a_receipt *receipt);
#endif
