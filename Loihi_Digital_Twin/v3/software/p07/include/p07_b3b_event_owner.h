#ifndef LOIHI_TWIN_V3_P07_B3B_EVENT_OWNER_H
#define LOIHI_TWIN_V3_P07_B3B_EVENT_OWNER_H
/* P07-B.3b candidate: host C11 simulated P02 event-slice ownership.
 * B2a ingress + B2b complete NEXT tuples + B3a ACK pager, no MMIO.
 * No full P02 neuron state image, actual URAM cache, or A53 ELF provided.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b3_pager.h"
#include "p07_b2b_transaction.h"
#define P07_B3B_DEPTH 4096u
#define P07_B3B_OK 0
#define P07_B3B_DONE 1
#define P07_B3B_REJECT (-1)
#define P07_B3B_POISON (-2)
/* Event 0/1 bank each contains exactly 4096 little-endian 32-bit axon words
 * at P03 context offsets 0x54000/0x58000. Only counts[bank] entries active.
 */
typedef struct {
    uint32_t count[2];
    uint32_t axon[2][P07_B3B_DEPTH];
} p07_b3b_event_slice;
typedef struct {
    p07_b3_pager *pager; /* accepted B3a single-engine ACK state */
    p07_b2b_transaction *transport; /* B2b trusted, immutable ingress/binding */
    p07_b3b_event_slice *backing; /* caller owns 27 mock DDR context slices */
    p07_b3b_event_slice *slot; /* caller owns 3 mock URAM slot slices */
    p07_b2_input_event *scratch; /* caller owns >= transport->pending_capacity */
    size_t scratch_capacity;
    uint32_t tick_started, poisoned, first_error;
    uint32_t current_expected[P07_B3_CORES];
    uint32_t current_consumed[P07_B3_CORES];
    uint8_t dispatched[P07_B3_CORES];
    uint32_t resident_next, nonresident_next;
    uint32_t barriers_committed;
} p07_b3b_owner;
/* Initializes a HOST mock of event-bank slices from all-zero backing.
 * Caller must supply separately validated P02 initial bank zeros and a
 * verified physical ownership map before any real deployment. */
int p07_b3b_init(p07_b3b_owner *o,p07_b3_pager *pager,
    p07_b2b_transaction *transport,p07_b3b_event_slice *backing,
    p07_b3b_event_slice *slots,p07_b2_input_event *scratch,
    size_t scratch_capacity);
/* Calls B3a_next and begins CURRENT epoch on first operation. */
int p07_b3b_next(p07_b3b_owner *o,p07_b3_op *op);
/* For PAGE_IN/OUT/DISPATCH/FINAL_FLUSH only. An ACK represents completed
 * physical action in future firmware; this model cannot supply real proof.
 * ERROR is sticky and never silently retries or advances the global tick. */
int p07_b3b_ack(p07_b3b_owner *o,const p07_b3_op *op,int success);
/* At BARRIER, independently validates all 27 dispatched CURRENT banks and
 * the original B2b packet/SHA/CRC/provenance into scratch, then performs a
 * single host-memory commit to resident/nonresident NEXT event banks,
 * followed by the accepted transport state and receipt. No hardware writes.
 * A failed transaction poisons B3a; backing/slot/transport stay unchanged.
 */
int p07_b3b_barrier(p07_b3b_owner *o,const p07_b3_op *op,
    const uint8_t *packet_wire,size_t packet_bytes,
    const uint16_t (*spikes)[2],size_t spike_count,
    p07_b2b_tx_receipt *receipt);
/* Pure inspect: current bank lives in resident slot or DDR backing, never
 * both authoritative. Returns active count and 32-bit axon word at index. */
int p07_b3b_read(const p07_b3b_owner *o,uint32_t core,uint32_t bank,
    uint32_t index,uint32_t *axon_out);
#endif
