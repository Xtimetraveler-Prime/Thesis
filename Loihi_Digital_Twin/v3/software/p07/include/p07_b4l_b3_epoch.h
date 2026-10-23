#ifndef LOIHI_TWIN_V3_P07_B4L_B3_EPOCH_H
#define LOIHI_TWIN_V3_P07_B4L_B3_EPOCH_H
/* B4l physical scheduler integration: ONE 27-core tick-0 epoch.
 * Reuses original B3a LRU and B3c2 -> actual P03 page/dispatch/read_packet.
 * IMPORTANT: stops BEFORE ACKing the pending B3 BARRIER.
 * This is not B2b NEXT routing, autonomous 26 ticks, or trained parity.
 */
#include <stdint.h>
#include "p07_b3c2_hw_scheduler.h"
#define P07_B4L_B3_ONE_TICK_MAGIC UINT32_C(0x31454233)
enum { P07_B4L_B3_OK=0, P07_B4L_B3_ARGUMENT=-1,
       P07_B4L_B3_FAULT=-2 };
typedef struct {
    uint32_t magic, tick, unique_dispatches, page_ins, dirty_page_outs;
    uint32_t pending_barrier, barrier_acked, physical_packets_captured;
    uint32_t source_count, first_error, faulted;
    uint32_t dispatcher_next_current_bank, dispatcher_next_bank;
    uint64_t captured_word_fnv1a, p03_page_bytes_expected;
} p07_b4l_b3_receipt;

/* Caller must first register all 27 trusted P02-core metadata and verify
 * empty/current first-tick event state, shell identity, quiescence and owner
 * of all 27 original P02 DDR records. B3c2_init itself checks P03 shell.
 * No attempt is made here to decode or route HLS emissions: the physical
 * 64-bit packet words are captured with the original P03 packet-debug path.
 */
int p07_b4l_b3_one_epoch(p07_b3c2_hw_scheduler *scheduler,
                         p07_b4l_b3_receipt *receipt);
#endif
