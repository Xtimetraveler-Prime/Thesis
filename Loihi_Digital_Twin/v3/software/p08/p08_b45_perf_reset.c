/* EXPLICIT UNPROTECTED PERFORMANCE-ONLY CLONE. NOT A SECURITY PROVIDER.
 * No XMPU configuration or read-only backup guarantee is asserted.
 * Original fail-closed p08_b45_reset_variants.c and A53 guard remain unchanged.
 * Pre- and post-session independent original backup SHA checks REQUIRED externally.
 * Only run after dedicated CPU/DDR takeover, signed physical staging and
 * same-session physical readback under separately approved pilot gate.
 */
#include "p08_b45_perf_reset.h"
#include "p07_a2_sha256.h"
#include <string.h>

_Static_assert(P08_B2_CONTEXT_CORES == 27u, "original logical-core count drift");
_Static_assert(P08_B2_CONTEXT_STRIDE == 524288u, "original context stride drift");
_Static_assert(P08_B2_CONTEXT_TOTAL == 14155776u, "original context byte count drift");

static uint32_t load32_le(const uint8_t *p) {
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8u) |
           ((uint32_t)p[2] << 16u) |
           ((uint32_t)p[3] << 24u);
}

static int valid_record_header(const uint8_t *p, uint32_t core) {
    static const uint8_t magic[8] = {'L','T','V','3','C','T','X','1'};
    return memcmp(p, magic, sizeof(magic)) == 0 &&
           load32_le(p + 8u) == 1u &&
           load32_le(p + 12u) == 4096u &&
           load32_le(p + 16u) == P08_B2_CONTEXT_STRIDE &&
           load32_le(p + 20u) == core &&
           load32_le(p + 24u) == 0u &&
           load32_le(p + 28u) == 0u &&
           load32_le(p + 32u) > 0u &&
           load32_le(p + 32u) <= 1024u &&
           load32_le(p + 36u) > 0u &&
           load32_le(p + 36u) <= 32768u &&
           load32_le(p + 40u) <= 4096u &&
           load32_le(p + 44u) == 0u &&
           load32_le(p + 48u) == 0u &&
           load32_le(p + 52u) == 0u;
}

static int nonzero_sha(const uint8_t digest[32]) {
    uint32_t i;
    for (i = 0u; i < 32u; ++i) {
        if (digest[i] != 0u) return 1;
    }
    return 0;
}

static int ranges_disjoint(uintptr_t a, size_t a_bytes,
                           uintptr_t b, size_t b_bytes) {
    if (a_bytes > UINTPTR_MAX - a || b_bytes > UINTPTR_MAX - b) return 0;
    return (a + a_bytes <= b) || (b + b_bytes <= a);
}

static int config_valid(const p08_b45_reset_state *state,
                        const p08_b45_reset_config *config,
                        p08_b45_reset_mode mode) {
    const p08_b2_reset_config *m;
    uintptr_t mutable_base, backup_base;
    size_t hash_bytes = P08_B2_CONTEXT_CORES * 32u;

    if (state == NULL || config == NULL) return 0;
    if (mode != P08_B45_AUTHENTICATED_ONCE &&
        mode != P08_B45_UNCHECKED_CONTENT) return 0;

    m = &config->memory;
    if (m->mutable_records == NULL || m->immutable_backup == NULL ||
        m->invalidate == NULL || m->clean == NULL ||
        m->quiescent == NULL || m->barrier == NULL ||
        0) return 0;
    if (m->record_bytes != P08_B2_CONTEXT_TOTAL ||
        m->backup_bytes != P08_B2_CONTEXT_TOTAL) return 0;
    if (mode == P08_B45_AUTHENTICATED_ONCE &&
        m->original_sha256 == NULL) return 0;

    mutable_base = (uintptr_t)m->mutable_records;
    backup_base = (uintptr_t)m->immutable_backup;
    if (!ranges_disjoint(mutable_base, m->record_bytes,
                         backup_base, m->backup_bytes)) return 0;
    if (!ranges_disjoint((uintptr_t)state, sizeof(*state),
                         mutable_base, m->record_bytes) ||
        !ranges_disjoint((uintptr_t)state, sizeof(*state),
                         backup_base, m->backup_bytes)) return 0;

    if (m->original_sha256 != NULL) {
        uintptr_t hashes = (uintptr_t)m->original_sha256;
        if (!ranges_disjoint(hashes, hash_bytes,
                             mutable_base, m->record_bytes) ||
            !ranges_disjoint(hashes, hash_bytes,
                             backup_base, m->backup_bytes) ||
            !ranges_disjoint(hashes, hash_bytes,
                             (uintptr_t)state, sizeof(*state))) return 0;
    }
    return 1;
}

static int poison(p08_b45_reset_state *state,
                  uint32_t stage, int result) {
    if (state != NULL) {
        if (state->poisoned == 0u) state->first_fault = stage;
        state->poisoned = 1u;
    }
    return result;
}

int p08_b45_perf_reset_bind(p08_b45_reset_state *state,
                       const p08_b45_reset_config *config,
                       p08_b45_reset_mode mode) {
    p08_b45_reset_state accepted;
    const p08_b2_reset_config *m;
    uint32_t core;

    if (state != NULL && state->magic == P08_B45_RESET_STATE_MAGIC) {
        return state->poisoned ? P08_B45_RESET_POISONED :
                                 P08_B45_RESET_INVALID;
    }
    if (!config_valid(state, config, mode)) return P08_B45_RESET_INVALID;

    m = &config->memory;
    if (m->quiescent(m->cookie) != 0) return P08_B45_RESET_IO;

    /* PERFORMANCE-ONLY: NO IMMUTABLE BACKUP LOCK/PROTECTION CLAIM. */
    memset(&accepted, 0, sizeof(accepted));
    accepted.magic = P08_B45_RESET_STATE_MAGIC;
    accepted.mode = (uint32_t)mode;
    accepted.config = *config;

    /* Both variants invalidate source cache once after protection. The
     * authenticated variant validates all 27 headers and SHA digests once.
     */
    for (core = 0u; core < P08_B2_CONTEXT_CORES; ++core) {
        const uint8_t *src = m->immutable_backup +
                             (size_t)core * P08_B2_CONTEXT_STRIDE;
        if (m->invalidate(m->cookie, (uintptr_t)src,
                          P08_B2_CONTEXT_STRIDE) != 0) {
            return P08_B45_RESET_IO;
        }
        m->barrier(m->cookie);

        if (mode == P08_B45_AUTHENTICATED_ONCE) {
            uint8_t actual[32];
            if (!valid_record_header(src, core)) return P08_B45_RESET_HEADER;
            accepted.session_header_checks++;
            if (!nonzero_sha(m->original_sha256[core])) {
                return P08_B45_RESET_SHA;
            }
            p07_a2_sha256(src, P08_B2_CONTEXT_STRIDE, actual);
            if (memcmp(actual, m->original_sha256[core], 32u) != 0) {
                return P08_B45_RESET_SHA;
            }
            accepted.session_source_sha_checks++;
        }
    }

    *state = accepted;
    return P08_B45_RESET_OK;
}

int p08_b45_perf_reset_image(p08_b45_reset_state *state,
                        p08_b45_reset_receipt *out) {
    p08_b45_reset_receipt done = {0};
    p08_b2_reset_config *m;
    uint32_t core;

    if (state == NULL || out == NULL ||
        state->magic != P08_B45_RESET_STATE_MAGIC) {
        return P08_B45_RESET_INVALID;
    }
    if (state->poisoned != 0u) return P08_B45_RESET_POISONED;
    if (state->generation == UINT32_MAX) {
        return poison(state, 1u, P08_B45_RESET_INVALID);
    }

    m = &state->config.memory;
    if (m->quiescent(m->cookie) != 0) {
        return poison(state, 2u, P08_B45_RESET_IO);
    }
    /* Authenticated-once mode checks every source header before the first
     * destructive write. It does NOT hash the source payload again.
     */
    if (state->mode == P08_B45_AUTHENTICATED_ONCE) {
        for (core = 0u; core < P08_B2_CONTEXT_CORES; ++core) {
            const uint8_t *src = m->immutable_backup +
                                 (size_t)core * P08_B2_CONTEXT_STRIDE;
            if (!valid_record_header(src, core)) {
                return poison(state, 4u, P08_B45_RESET_HEADER);
            }
            done.source_header_checks++;
        }
    }

    for (core = 0u; core < P08_B2_CONTEXT_CORES; ++core) {
        const uint8_t *src = m->immutable_backup +
                             (size_t)core * P08_B2_CONTEXT_STRIDE;
        uint8_t *dest = m->mutable_records +
                        (size_t)core * P08_B2_CONTEXT_STRIDE;

        memcpy(dest, src, P08_B2_CONTEXT_STRIDE);
        if (m->clean(m->cookie, (uintptr_t)dest,
                     P08_B2_CONTEXT_STRIDE) != 0) {
            return poison(state, 5u, P08_B45_RESET_IO);
        }
        m->barrier(m->cookie);
        if (m->invalidate(m->cookie, (uintptr_t)dest,
                          P08_B2_CONTEXT_STRIDE) != 0) {
            return poison(state, 6u, P08_B45_RESET_IO);
        }
        m->barrier(m->cookie);

        if (state->mode == P08_B45_AUTHENTICATED_ONCE) {
            if (!valid_record_header(dest, core)) {
                return poison(state, 7u, P08_B45_RESET_HEADER);
            }
            done.destination_header_checks++;
        }
        done.copied_records++;
    }

    if (m->quiescent(m->cookie) != 0) {
        return poison(state, 8u, P08_B45_RESET_IO);
    }
    done.magic = P08_B45_RESET_RECEIPT_MAGIC;
    done.version = P08_B45_RESET_VERSION;
    done.mode = state->mode;
    done.generation = ++state->generation;
    done.copied_bytes = P08_B2_CONTEXT_TOTAL;
    done.session_source_sha_checks = state->session_source_sha_checks;
    done.session_header_checks = state->session_header_checks;
    done.destination_sha_checks = 0u;
    *out = done;
    return P08_B45_RESET_OK;
}
