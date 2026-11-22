/* SPDX-License-Identifier: MIT */
/*
 * M08.5 first-party portable DMA address math contract, not a DMA mapping.
 * Matches the RTL fence's STRICT upper-exclusive 49-bit aperture:
 *   base+allocation_bytes < 2^49 (NOT <=), start 256B aligned,
 *   first 7*256 bytes exposed, descriptor byte count fits 32 bits.
 * A valid descriptor DOES NOT prove kernel allocation, PS AFI, IOMMU
 * translation, exclusive control, or physical drain. Never derive
 * dma_addr_t from a userspace or CPU physical pointer.
 */
#ifndef M08_M085_DMA_CONTRACT_H
#define M08_M085_DMA_CONTRACT_H

#ifdef __KERNEL__
#include <linux/types.h>
typedef u64 m085_u64;
#else
#include <stdint.h>
typedef uint64_t m085_u64;
#endif

#define M085_DMA_AXI_LIMIT (1ULL << 49)
#define M085_DMA_PAGE_BYTES 256ULL
#define M085_DMA_SLOT_COUNT 7ULL
#define M085_DMA_USED_BYTES (M085_DMA_PAGE_BYTES * M085_DMA_SLOT_COUNT)
#define M085_DMA_ALLOC_FIELD_MAX 0xffffffffULL

static inline int m085_dma_descriptor_valid(m085_u64 dma_base,
                                            m085_u64 allocation_bytes,
                                            m085_u64 generation)
{
    /* Subtraction before addition prevents overflow on hostile input. */
    if (!generation || generation > M085_DMA_ALLOC_FIELD_MAX)
        return 0;
    if (dma_base & (M085_DMA_PAGE_BYTES - 1ULL))
        return 0;
    if (allocation_bytes < M085_DMA_USED_BYTES ||
        allocation_bytes > M085_DMA_ALLOC_FIELD_MAX)
        return 0;
    if (dma_base >= M085_DMA_AXI_LIMIT)
        return 0;
    /* The RTL requires the exclusive allocation end to be STRICTLY below
     * the 2^49 aperture, including the entire allocation tail.
     */
    if (allocation_bytes >= M085_DMA_AXI_LIMIT - dma_base)
        return 0;
    return 1;
}

static inline int m085_dma_slot_valid(m085_u64 slot, m085_u64 tick)
{
    return slot < M085_DMA_SLOT_COUNT && tick < 4ULL &&
           (slot != 6ULL || tick == 0ULL);
}

#endif /* M08_M085_DMA_CONTRACT_H */
