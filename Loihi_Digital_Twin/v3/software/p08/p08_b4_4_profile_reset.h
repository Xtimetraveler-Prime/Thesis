#ifndef LOIHI_TWIN_V3_P08_B4_4_PROFILE_RESET_H
#define LOIHI_TWIN_V3_P08_B4_4_PROFILE_RESET_H
/*
 * P08-B4.4.1: EXPERIMENTAL replacement for only p08_b2_reset_image.
 * Original production P08-B2.2/.3 functions and signed ELF UNMODIFIED.
 * Must be built as a DISTINCT profiling image and independently prove
 * original 27x512KiB SHA checks and original 1024-image numerical parity.
 * THIS HEADER DOES NOT AUTHORIZE JTAG OR MODIFY PHYSICAL DDR OWNER.
 *
 * Each phase is a sum of disjoint CNTVCT snapshots. The phase totals
 * do not include time spent reading the counter; unattributed time
 * = complete - sum(5). No PL or calibrated physical speed is claimed.
 */
#include <stdint.h>
#include "p08_b2_context_reset.h"
#define P08_B44_RESET_PROFILE_MAGIC UINT32_C(0x52504434)
#define P08_B44_RESET_PROFILE_VERSION 1u
#define P08_B44_RESET_PROFILE_PHASES 5u
#define P08_B44_RESET_PROFILE_CORES 27u
enum p08_b44_reset_phase {
    P08_B44_SOURCE_CACHE_INVALIDATE=0,
    P08_B44_SOURCE_SHA256=1,
    P08_B44_MUTABLE_MEMCPY=2,
    P08_B44_MUTABLE_CACHE_CLEAN_INVALIDATE=3,
    P08_B44_MUTABLE_SHA256=4
};
typedef uint64_t (*p08_b44_counter_now)(void *cookie);
typedef struct {
    uint32_t magic, version, verified_records, generation;
    uint64_t total_ticks;
    uint64_t phase_ticks[P08_B44_RESET_PROFILE_PHASES];
    uint64_t unattributed_ticks;
    uint32_t copied_bytes,source_sha_checks,destination_sha_checks;
    uint32_t reserved;
} p08_b44_reset_profile;
/* Requires a previously successfully bound original reset_state.
 * On success returned reset receipt exactly matches original
 * p08_b2_reset_image and 27 immutable 512KiB contexts remain untouched.
 * No successful profile on partial failure; same stage/poison semantics.
 * Counter regression/overflow fails closed, not a timing result.
 */
int p08_b44_profile_reset_image(
    p08_b2_reset_state *state, p08_b2_reset_receipt *receipt,
    p08_b44_counter_now now, void *clock_cookie,
    p08_b44_reset_profile *profile);
#endif
