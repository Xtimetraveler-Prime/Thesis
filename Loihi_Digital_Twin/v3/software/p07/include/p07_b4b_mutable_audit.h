#ifndef LOIHI_TWIN_P07_B4B_MUTABLE_AUDIT_H
#define LOIHI_TWIN_P07_B4B_MUTABLE_AUDIT_H
/* READ-ONLY P02 mutable-state equality to independently trusted snapshots.
 * CRC is accidental-corruption detection, not cryptographic authorization.
 * No DDR records are written, erased, provisioned, reset or inferred here.
 */
#include <stddef.h>
#include <stdint.h>
#include "p07_b4b_board_admission.h"
#include "p07_b3_pager.h"
#define P07_B4B_MUTABLE_SECTIONS 5u
typedef struct {
    uint32_t expected_crc[P07_B3_CORES][P07_B4B_MUTABLE_SECTIONS];
} p07_b4b_expected_mutable;
typedef struct {
    uint32_t checked_cores, checked_regions;
    uint64_t inspected_bytes;
    uint32_t digest_crc; /* checksum of verified little-endian CRC tuples */
} p07_b4b_mutable_receipt;
enum {P07_B4B_AUDIT_OK=0,P07_B4B_AUDIT_ARG=-1,
      P07_B4B_AUDIT_NOT_IDLE=-2,P07_B4B_AUDIT_IO=-3,
      P07_B4B_AUDIT_MISMATCH=-4};
/* Caller must have already installed verified frozen pristine P02 records,
 * flushed all PS writes and independently excluded Linux/other DDR masters.
 * Requires 27 registered cores, empty slots, zero live event counts, idle
 * original P03 hardware. Zero events != zero all other mutable state!
 * A failure leaves *receipt unchanged; first-bad location if provided
 * reports absolute P02 DDR physical word address.
 */
int p07_b4b_audit_mutable(const p07_b4b_expected_mutable *expected,
    p03_hw_adapter *hw,const p07_b3_pager *pager,
    p07_b4b_read_phys32 read_phys,void *read_context,
    p07_b4b_mutable_receipt *receipt,uint64_t *first_bad);
#endif
