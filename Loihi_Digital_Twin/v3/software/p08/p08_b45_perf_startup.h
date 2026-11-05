#ifndef P08_B45_PERF_STARTUP_H
#define P08_B45_PERF_STARTUP_H
/*
 * Distinct full1024 standalone A53 STARTUP-ONLY reset-state admission.
 * The original reset kernel and both physically accepted pilot16 binaries
 * stay untouched. This module NEVER accesses DDR backing/backup, writes
 * XMPU or fakes hardware protection. A fresh standalone run has exactly
 * one explicit reset-state zero-init after validating isolated geometry.
 */
#include "p08_b45_perf_reset.h"
#include <stdint.h>
enum {
    P08_B45_START_OK = 0,
    P08_B45_START_BAD_ARGS = 1,
    P08_B45_START_BAD_MODE = 2,
    P08_B45_START_BAD_POINTER = 3,
    P08_B45_START_BAD_SIZE = 4,
    P08_B45_START_SHA_MISSING = 5,
    P08_B45_START_ADDRESS_OVERFLOW = 6,
    P08_B45_START_MUTABLE_BACKUP_OVERLAP = 7,
    P08_B45_START_STATE_OVERLAP = 8,
    P08_B45_START_SHA_POINTER_OVERLAP = 9
};
typedef struct {
    uint32_t reason;
    uint32_t prezero_magic;
    uint32_t prezero_generation;
    uint32_t prezero_poison;
    uint32_t reset_state_zeroed;
} p08_b45_perf_startup_receipt;
/* Called once per freshly loaded A53 ELF, BEFORE p08_b45_perf_reset_bind.
 * Never called per-image, and never clears a legitimate live session.
 * An invalid geometry or callback returns a precise code and leaves state
 * unchanged. Cache-safe original backup and mutable memory are UNTOUCHED.
 */
int p08_b45_perf_prepare_new_session(
    p08_b45_reset_state *state, const p08_b45_reset_config *config,
    p08_b45_reset_mode mode, p08_b45_perf_startup_receipt *receipt);
#endif
