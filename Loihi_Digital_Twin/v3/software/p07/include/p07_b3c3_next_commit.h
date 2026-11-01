#ifndef LOIHI_TWIN_P07_B3C3_NEXT_COMMIT_H
#define LOIHI_TWIN_P07_B3C3_NEXT_COMMIT_H
/* Physically addressable P03 bank insertion with independent B2b preflight.
 * Native fake-bus tests are NOT KV260 physical acceptance. Nonrollbackable
 * partial writes cause sticky poison, never a false successful barrier.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b3_pager.h"
#include "p07_b2_packet.h"
#include "p03_hw_adapter.h"
enum {P07_B3C3_OK=0,P07_B3C3_INVALID=-1,P07_B3C3_PRECHECK=-2,
      P07_B3C3_IO_FAILED=-3,P07_B3C3_FAULTED=-4};
#define P07_B3C3_RECEIPT_MAGIC UINT32_C(0x33433342)
typedef struct {
    const uint8_t *wire; /* borrowed immutable through commit */
    size_t wire_bytes;
    p07_b3_pager *pager;
    p03_hw_adapter *hw;
    uint32_t tick, bank, packet_count, frame_crc;
    uint32_t destination_count[P07_B3_CORES];
    uint32_t admitted, attempted, poisoned, first_fault;
} p07_b3c3_plan;
typedef struct {
    uint32_t magic, tick, bank, inserted_count;
    uint32_t frame_crc, source_packet_count;
} p07_b3c3_receipt;
/* PREPARE is side-effect-free on event-bank words, event_counts and LRU
 * ledger. Needs independently trusted immutable B1.2 routes and compiled
 * SHA/capacity audit, plus independent actual PL emitted-neuron trace.
 * Every destination must already be registered with P03 axon binding.
 * Reject NEXT nonempty, CURRENT not empty, or incoherent barrier state.
 */
int p07_b3c3_prepare(p07_b3c3_plan *out,p07_b3_pager *pager,
    p03_hw_adapter *hw,const p07_b2_packet_binding *binding,
    const uint8_t *frame,size_t frame_bytes,
    const uint16_t (*source_spikes)[2],size_t spike_count);
/* COMMIT uses accepted P03 debug bank 6/9 for currently resident target,
 * otherwise DDR record+0x54000/0x58000 with clean/barrier callbacks.
 * No paging solely to deliver NEXT. On ANY failure the run is poisoned,
 * even if some physical events were written: physical rollback unsupported.
 * Receipt is assigned only if ALL writes and PL quiescence are acknowledged.
 */
int p07_b3c3_commit(p07_b3c3_plan *plan,p07_b3c3_receipt *receipt);
#endif
