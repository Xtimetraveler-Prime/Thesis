#ifndef LOIHI_TWIN_V3_P08_B45_RESET_VARIANTS_H
#define LOIHI_TWIN_V3_P08_B45_RESET_VARIANTS_H

/*
 * P08-B4.5 experimental reset variants.
 *
 * Separate from the accepted P08-B2.2 production reset and P08-B4.4.2
 * full-SHA profiling implementation.
 *
 * Both modes retain operational safety checks: range validation, positive
 * quiescence, cache maintenance, barriers, callback error handling and
 * irreversible poisoning after a partial reset failure.
 *
 * AUTHENTICATED_ONCE authenticates all 27 original records once at bind,
 * then checks P02 headers on each image reset.
 *
 * UNCHECKED_CONTENT performs no SHA256 or P02 header/content checks. It is a
 * performance-bound experiment, NOT a recommended production configuration.
 *
 * Both modes require a platform callback that establishes persistent,
 * exclusive, read-only ownership of the immutable backup region and another
 * callback that confirms that protection remains active. Native tests use
 * mocks only; a no-op callback is NOT acceptable for physical KV260 use.
 */
#include <stddef.h>
#include <stdint.h>
#include "p08_b2_context_reset.h"

#define P08_B45_RESET_STATE_MAGIC UINT32_C(0x52343538)
#define P08_B45_RESET_RECEIPT_MAGIC UINT32_C(0x52343552)
#define P08_B45_RESET_VERSION 1u

typedef enum {
    P08_B45_AUTHENTICATED_ONCE = 1u,
    P08_B45_UNCHECKED_CONTENT = 2u
} p08_b45_reset_mode;

enum {
    P08_B45_RESET_OK = 0,
    P08_B45_RESET_INVALID = -1,
    P08_B45_RESET_SHA = -2,
    P08_B45_RESET_IO = -3,
    P08_B45_RESET_POISONED = -4,
    P08_B45_RESET_HEADER = -5,
    P08_B45_RESET_LOCK = -6
};

/*
 * lock_backup must establish protection/ownership for the complete immutable
 * backup range until the session ends or the platform is reset. It must not
 * merely assert that the range looks unused.
 *
 * backup_lock_valid must cheaply confirm that the same protection remains
 * active. Neither callback may hash or scan the backup contents.
 */
typedef int (*p08_b45_backup_lock_fn)(void *cookie,
                                      uintptr_t address,
                                      size_t bytes);
typedef int (*p08_b45_backup_lock_valid_fn)(void *cookie,
                                            uintptr_t address,
                                            size_t bytes);

typedef struct {
    p08_b2_reset_config memory;
    p08_b45_backup_lock_fn lock_backup;
    p08_b45_backup_lock_valid_fn backup_lock_valid;
} p08_b45_reset_config;

typedef struct {
    uint32_t magic;
    uint32_t mode;
    uint32_t generation;
    uint32_t poisoned;
    uint32_t first_fault;
    uint32_t session_source_sha_checks;
    uint32_t session_header_checks;
    p08_b45_reset_config config;
} p08_b45_reset_state;

typedef struct {
    uint32_t magic;
    uint32_t version;
    uint32_t mode;
    uint32_t generation;
    uint32_t copied_records;
    uint32_t copied_bytes;
    uint32_t session_source_sha_checks;
    uint32_t session_header_checks;
    uint32_t source_header_checks;
    uint32_t destination_header_checks;
    uint32_t destination_sha_checks;
    uint32_t reserved;
} p08_b45_reset_receipt;

/* AUTHENTICATED_ONCE requires original_sha256. UNCHECKED_CONTENT permits NULL. */
int p08_b45_reset_bind(p08_b45_reset_state *state,
                       const p08_b45_reset_config *config,
                       p08_b45_reset_mode mode);

/* No receipt is published unless the complete image reset succeeds. */
int p08_b45_reset_image(p08_b45_reset_state *state,
                        p08_b45_reset_receipt *receipt);

#endif
