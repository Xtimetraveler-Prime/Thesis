#ifndef LOIHI_TWIN_V3_P07_B4M_DISPATCH_METADATA_H
#define LOIHI_TWIN_V3_P07_B4M_DISPATCH_METADATA_H
/* B4m diagnostic V3 only: repair runtime P08 dispatch metadata using
 * already immutable, same-session physically read-back P02 context headers.
 * Does NOT edit the accepted 16KiB descriptor or any backing DDR bytes.
 */
#include <stdint.h>
#include "p03_hw_adapter.h"
#define P07_B4M_METADATA_CORES 27u
#define P07_B4M_P02_HEADER_MIN_BYTES 0x38u
#define P07_B4M_METADATA_OK 0
#define P07_B4M_METADATA_REJECT (-1)
int p07_b4m_apply_p02_counts(
    p03_hw_adapter *hw,
    const uint8_t *const headers[P07_B4M_METADATA_CORES]
);
#endif
