#ifndef LOIHI_TWIN_V3_P08_B2_CONTEXT_RESET_H
#define LOIHI_TWIN_V3_P08_B2_CONTEXT_RESET_H
/* P08-B2.2: NEW 27x512KiB P02 image reset component, portable C11.
 * Binds independent host-pinned per-record original SHA256 (B4l1 index).
 * Does NOT prove DDR owner, PL slot reset, numerical parity, or board safety.
 */
#include <stddef.h>
#include <stdint.h>
#define P08_B2_CONTEXT_CORES 27u
#define P08_B2_CONTEXT_STRIDE 0x80000u
#define P08_B2_CONTEXT_TOTAL (P08_B2_CONTEXT_CORES * P08_B2_CONTEXT_STRIDE)
#define P08_B2_CONTEXT_BASE UINT32_C(0x40000000)
#define P08_B2_CONTEXT_END UINT32_C(0x40D80000)
#define P08_B2_BACKUP_BASE UINT32_C(0x43000000)
#define P08_B2_BACKUP_END UINT32_C(0x43D80000)
#define P08_B2_CONTEXT_MAGIC UINT32_C(0x43524238)
enum {
    P08_B2_RESET_OK=0, P08_B2_RESET_INVALID=-1,
    P08_B2_RESET_SHA=-2, P08_B2_RESET_IO=-3,
    P08_B2_RESET_POISONED=-4
};
typedef int (*p08_b2_memory_range)(void *cookie,uintptr_t address,size_t n);
typedef int (*p08_b2_quiescent)(void *cookie);
typedef void (*p08_b2_fence)(void *cookie);
typedef struct {
    uint8_t *mutable_records; /* 27 contiguous 512KiB direct-mapped DDR */
    const uint8_t *immutable_backup; /* independent, provisioned verified 27x512KiB */
    const uint8_t (*original_sha256)[32]; /* 27 trusted SHA256 from B4l1 index */
    size_t record_bytes,backup_bytes; /* both MUST exactly 14155776 */
    p08_b2_memory_range invalidate,clean;
    p08_b2_quiescent quiescent;
    p08_b2_fence barrier;
    void *cookie;
} p08_b2_reset_config;
typedef struct {
    uint32_t magic,generation,poisoned,first_fault;
    p08_b2_reset_config config;
} p08_b2_reset_state;
typedef struct {
    uint32_t generation,verified_records,copied_bytes;
    uint32_t verified_after_copy,reset_magic;
} p08_b2_reset_receipt;
/* Source backup remains immutable for entire 1024-image run and must be
 * from freshly physically read-back verified ORIGINAL P07-B B4l1 source.
 * Software SHA bind is NOT a substitute for same-session physical proof.
 */
int p08_b2_reset_bind(p08_b2_reset_state *state,
                      const p08_b2_reset_config *config);
/* All 27 originals are checked BEFORE first backing DDR write.
 * Each 512KiB destination is D-cache-cleaned, barriered, invalidated,
 * and SHA readback verified after memcpy. No retry after ANY write fault.
 * Caller must reinitialize P03 software metadata, pager, scheduler, trace
 * and rebind original P07 frozen routes before calling 26tick inference.
 */
int p08_b2_reset_image(p08_b2_reset_state *state,
                       p08_b2_reset_receipt *receipt);
#endif
