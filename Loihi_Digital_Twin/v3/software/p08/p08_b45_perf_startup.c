/* FULL1024 bare-metal first-entry startup safety gate, PC-testable.
 * No memory security equivalence claimed; original fail-closed protected
 * reset and the accepted unprotected pilot16 reset kernel are untouched.
 */
#include "p08_b45_perf_startup.h"
#include <string.h>
#include <stdint.h>
#include <stddef.h>

static int bounded(uintptr_t base, size_t bytes) {
    return bytes <= UINTPTR_MAX - base;
}
static int disjoint(uintptr_t a, size_t na, uintptr_t b, size_t nb) {
    return bounded(a, na) && bounded(b, nb) &&
           (a + na <= b || b + nb <= a);
}
int p08_b45_perf_prepare_new_session(
    p08_b45_reset_state *state, const p08_b45_reset_config *config,
    p08_b45_reset_mode mode, p08_b45_perf_startup_receipt *receipt) {
    const p08_b2_reset_config *m;
    uintptr_t mutable_base, backup_base, state_base, hashes;
    size_t sha_bytes = P08_B2_CONTEXT_CORES * 32u;
    uint32_t reason=P08_B45_START_OK;
    if (receipt == NULL) return P08_B45_START_BAD_ARGS;
    memset(receipt, 0, sizeof(*receipt));
    if (state == NULL || config == NULL) {
        reason=P08_B45_START_BAD_ARGS;
        goto failed;
    }
    receipt->prezero_magic=state->magic;
    receipt->prezero_generation=state->generation;
    receipt->prezero_poison=state->poisoned;
    if (mode != P08_B45_AUTHENTICATED_ONCE &&
        mode != P08_B45_UNCHECKED_CONTENT) {
        reason=P08_B45_START_BAD_MODE; goto failed;
    }
    m=&config->memory;
    if (m->mutable_records==NULL || m->immutable_backup==NULL ||
        m->invalidate==NULL || m->clean==NULL || m->quiescent==NULL ||
        m->barrier==NULL) {
        reason=P08_B45_START_BAD_POINTER; goto failed;
    }
    if (m->record_bytes!=P08_B2_CONTEXT_TOTAL ||
        m->backup_bytes!=P08_B2_CONTEXT_TOTAL) {
        reason=P08_B45_START_BAD_SIZE; goto failed;
    }
    if (mode==P08_B45_AUTHENTICATED_ONCE && m->original_sha256==NULL) {
        reason=P08_B45_START_SHA_MISSING; goto failed;
    }
    mutable_base=(uintptr_t)m->mutable_records;
    backup_base=(uintptr_t)m->immutable_backup;
    state_base=(uintptr_t)state;
    if (!bounded(mutable_base,m->record_bytes) ||
        !bounded(backup_base,m->backup_bytes) ||
        !bounded(state_base,sizeof(*state))) {
        reason=P08_B45_START_ADDRESS_OVERFLOW; goto failed;
    }
    if (!disjoint(mutable_base,m->record_bytes,
                  backup_base,m->backup_bytes)) {
        reason=P08_B45_START_MUTABLE_BACKUP_OVERLAP; goto failed;
    }
    if (!disjoint(state_base,sizeof(*state),mutable_base,m->record_bytes) ||
        !disjoint(state_base,sizeof(*state),backup_base,m->backup_bytes)) {
        reason=P08_B45_START_STATE_OVERLAP; goto failed;
    }
    if (m->original_sha256!=NULL) {
        hashes=(uintptr_t)m->original_sha256;
        if (!bounded(hashes,sha_bytes)) {
            reason=P08_B45_START_ADDRESS_OVERFLOW; goto failed;
        }
        if (!disjoint(hashes,sha_bytes,mutable_base,m->record_bytes) ||
            !disjoint(hashes,sha_bytes,backup_base,m->backup_bytes) ||
            !disjoint(hashes,sha_bytes,state_base,sizeof(*state))) {
            reason=P08_B45_START_SHA_POINTER_OVERLAP; goto failed;
        }
    }
    /* Fresh standalone app entry. Ensures initial state is genuinely
     * zero independent of previous bare-metal/JTAG contents at this
     * BSS address; DOES NOT weaken bind's same-session fail-closed guard.
     * The caller must invoke this only once, before bind or ANY image.
     */
    memset(state, 0, sizeof(*state));
    receipt->reset_state_zeroed=1u;
    receipt->reason=P08_B45_START_OK;
    return P08_B45_START_OK;
failed:
    receipt->reason=reason;
    return (int)reason;
}
