/* P08-B4.5 native reset-variant tests. Synthetic host memory only. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "p08_b45_reset_variants.h"
#include "p07_a2_sha256.h"

#define CHECK(x) do { if (!(x)) { \
    fprintf(stderr, "P08_B45_NATIVE_NO_GO line %d: %s\n", __LINE__, #x); \
    return 1; \
} } while (0)

typedef struct {
    unsigned lock_calls, lock_valid_calls, invalidate_calls;
    unsigned clean_calls, quiescent_calls, barriers;
    int locked, fail_lock, fail_lock_valid;
    int fail_invalidate_at, fail_clean_at, fail_quiescent;
} witness;

static int lock_backup(void *cookie, uintptr_t address, size_t bytes) {
    witness *w = (witness *)cookie;
    if (address == 0u || bytes != P08_B2_CONTEXT_TOTAL || w->fail_lock) return -1;
    w->lock_calls++;
    w->locked = 1;
    return 0;
}
static int lock_valid(void *cookie, uintptr_t address, size_t bytes) {
    witness *w = (witness *)cookie;
    if (address == 0u || bytes != P08_B2_CONTEXT_TOTAL) return -1;
    w->lock_valid_calls++;
    return (!w->locked || w->fail_lock_valid) ? -1 : 0;
}
static int invalidate(void *cookie, uintptr_t address, size_t bytes) {
    witness *w = (witness *)cookie;
    w->invalidate_calls++;
    if (address == 0u || bytes != P08_B2_CONTEXT_STRIDE ||
        (int)w->invalidate_calls == w->fail_invalidate_at) return -1;
    return 0;
}
static int clean(void *cookie, uintptr_t address, size_t bytes) {
    witness *w = (witness *)cookie;
    w->clean_calls++;
    if (address == 0u || bytes != P08_B2_CONTEXT_STRIDE ||
        (int)w->clean_calls == w->fail_clean_at) return -1;
    return 0;
}
static int quiescent(void *cookie) {
    witness *w = (witness *)cookie;
    w->quiescent_calls++;
    return w->fail_quiescent ? -1 : 0;
}
static void barrier(void *cookie) {
    witness *w = (witness *)cookie;
    w->barriers++;
}
static void put32(uint8_t *p, uint32_t value) {
    unsigned i;
    for (i = 0u; i < 4u; ++i) p[i] = (uint8_t)(value >> (8u * i));
}
static void make_backup(uint8_t *backup, uint8_t hashes[27][32]) {
    uint32_t core;
    for (core = 0u; core < P08_B2_CONTEXT_CORES; ++core) {
        uint8_t *row = backup + (size_t)core * P08_B2_CONTEXT_STRIDE;
        memcpy(row, "LTV3CTX1", 8u);
        put32(row + 8u, 1u);
        put32(row + 12u, 4096u);
        put32(row + 16u, P08_B2_CONTEXT_STRIDE);
        put32(row + 20u, core);
        put32(row + 32u, 64u);
        put32(row + 36u, 64u);
        row[64] = (uint8_t)(core + 1u);
        row[P08_B2_CONTEXT_STRIDE - 1u] = (uint8_t)(core * 7u + 1u);
        p07_a2_sha256(row, P08_B2_CONTEXT_STRIDE, hashes[core]);
    }
}
static void configure(p08_b45_reset_config *c, uint8_t *mutable_bytes,
                      uint8_t *backup, const uint8_t (*hashes)[32],
                      witness *w) {
    memset(c, 0, sizeof(*c));
    c->memory.mutable_records = mutable_bytes;
    c->memory.immutable_backup = backup;
    c->memory.original_sha256 = hashes;
    c->memory.record_bytes = P08_B2_CONTEXT_TOTAL;
    c->memory.backup_bytes = P08_B2_CONTEXT_TOTAL;
    c->memory.invalidate = invalidate;
    c->memory.clean = clean;
    c->memory.quiescent = quiescent;
    c->memory.barrier = barrier;
    c->memory.cookie = w;
    c->lock_backup = lock_backup;
    c->backup_lock_valid = lock_valid;
}
static int test_authenticated_once(uint8_t *backup, uint8_t *mutable_bytes,
                                   uint8_t hashes[27][32]) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    p08_b45_reset_receipt r;
    witness w = {0};
    unsigned iteration;
    configure(&c, mutable_bytes, backup, (const uint8_t (*)[32])hashes, &w);
    memset(mutable_bytes, 0xA5, P08_B2_CONTEXT_TOTAL);
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_AUTHENTICATED_ONCE) == P08_B45_RESET_OK);
    CHECK(s.session_source_sha_checks == 27u);
    CHECK(s.session_header_checks == 27u);
    CHECK(w.lock_calls == 1u && w.lock_valid_calls == 2u);
    CHECK(w.invalidate_calls == 27u);

    for (iteration = 0u; iteration < 2u; ++iteration) {
        memset(mutable_bytes, (int)(0xB0u + iteration), P08_B2_CONTEXT_TOTAL);
        memset(&r, 0xCC, sizeof(r));
        CHECK(p08_b45_reset_image(&s, &r) == P08_B45_RESET_OK);
        CHECK(memcmp(backup, mutable_bytes, P08_B2_CONTEXT_TOTAL) == 0);
        CHECK(r.magic == P08_B45_RESET_RECEIPT_MAGIC);
        CHECK(r.mode == P08_B45_AUTHENTICATED_ONCE);
        CHECK(r.generation == iteration + 1u);
        CHECK(r.copied_records == 27u && r.copied_bytes == P08_B2_CONTEXT_TOTAL);
        CHECK(r.session_source_sha_checks == 27u && r.session_header_checks == 27u);
        CHECK(r.source_header_checks == 27u && r.destination_header_checks == 27u);
        CHECK(r.destination_sha_checks == 0u);
        CHECK(w.invalidate_calls == 27u + (iteration + 1u) * 27u);
    }
    CHECK(w.clean_calls == 54u);
    CHECK(w.lock_valid_calls == 6u);
    return 0;
}
static int test_unchecked_content(uint8_t *backup, uint8_t *mutable_bytes) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    p08_b45_reset_receipt r;
    witness w = {0};
    configure(&c, mutable_bytes, backup, NULL, &w);
    memset(mutable_bytes, 0xA5, P08_B2_CONTEXT_TOTAL);
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_UNCHECKED_CONTENT) == P08_B45_RESET_OK);
    CHECK(s.session_source_sha_checks == 0u && s.session_header_checks == 0u);
    CHECK(w.lock_calls == 1u && w.invalidate_calls == 27u);

    /* Deliberately violate the mock lock to prove this mode does not inspect
     * content. This is a native negative demonstration, never a board action.
     */
    backup[128] ^= 0x5Au;
    backup[20] ^= 0x01u;
    CHECK(p08_b45_reset_image(&s, &r) == P08_B45_RESET_OK);
    CHECK(memcmp(backup, mutable_bytes, P08_B2_CONTEXT_TOTAL) == 0);
    CHECK(r.source_header_checks == 0u && r.destination_header_checks == 0u);
    CHECK(r.session_source_sha_checks == 0u && r.destination_sha_checks == 0u);
    CHECK(r.copied_records == 27u);
    return 0;
}
static int test_authenticated_once_exposes_lock_dependency(
    uint8_t *backup, uint8_t *mutable_bytes, uint8_t hashes[27][32]) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    p08_b45_reset_receipt r;
    witness w = {0};
    uint8_t original;
    configure(&c, mutable_bytes, backup, (const uint8_t (*)[32])hashes, &w);
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_AUTHENTICATED_ONCE) == P08_B45_RESET_OK);
    original = backup[128];
    /* Payload mutation after bind is outside the contract. Header-only
     * checks cannot detect it; a real persistent lock must prevent it.
     */
    backup[128] ^= 0x01u;
    CHECK(p08_b45_reset_image(&s, &r) == P08_B45_RESET_OK);
    CHECK(mutable_bytes[128] == backup[128] && mutable_bytes[128] != original);
    backup[128] = original;
    return 0;
}
static int test_bind_detects_preexisting_corruption(
    uint8_t *backup, uint8_t *mutable_bytes, uint8_t hashes[27][32]) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    witness w = {0};
    configure(&c, mutable_bytes, backup, (const uint8_t (*)[32])hashes, &w);
    backup[200] ^= 1u;
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_AUTHENTICATED_ONCE) == P08_B45_RESET_SHA);
    backup[200] ^= 1u;
    return 0;
}
static int test_lock_failure_blocks_bind(uint8_t *backup, uint8_t *mutable_bytes,
                                         uint8_t hashes[27][32]) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    witness w = {0};
    configure(&c, mutable_bytes, backup, (const uint8_t (*)[32])hashes, &w);
    w.fail_lock = 1;
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_AUTHENTICATED_ONCE) == P08_B45_RESET_LOCK);
    CHECK(w.invalidate_calls == 0u);
    return 0;
}
static int test_operational_failure_poisons(uint8_t *backup, uint8_t *mutable_bytes,
                                            uint8_t hashes[27][32]) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    p08_b45_reset_receipt r, unchanged;
    witness w = {0};
    configure(&c, mutable_bytes, backup, (const uint8_t (*)[32])hashes, &w);
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_UNCHECKED_CONTENT) == P08_B45_RESET_OK);
    memset(&r, 0xA7, sizeof(r));
    unchanged = r;
    w.fail_clean_at = 1;
    CHECK(p08_b45_reset_image(&s, &r) == P08_B45_RESET_IO);
    CHECK(s.poisoned == 1u && s.first_fault == 5u);
    CHECK(memcmp(&r, &unchanged, sizeof(r)) == 0);
    CHECK(p08_b45_reset_image(&s, &r) == P08_B45_RESET_POISONED);
    return 0;
}
static int test_lock_loss_poisons(uint8_t *backup, uint8_t *mutable_bytes,
                                  uint8_t hashes[27][32]) {
    p08_b45_reset_config c;
    p08_b45_reset_state s = {0};
    p08_b45_reset_receipt r;
    witness w = {0};
    configure(&c, mutable_bytes, backup, (const uint8_t (*)[32])hashes, &w);
    CHECK(p08_b45_reset_bind(&s, &c, P08_B45_UNCHECKED_CONTENT) == P08_B45_RESET_OK);
    w.locked = 0;
    CHECK(p08_b45_reset_image(&s, &r) == P08_B45_RESET_LOCK);
    CHECK(s.poisoned == 1u && s.first_fault == 3u);
    return 0;
}
int main(void) {
    uint8_t *backup = (uint8_t *)calloc(1u, P08_B2_CONTEXT_TOTAL);
    uint8_t *mutable_bytes = (uint8_t *)malloc(P08_B2_CONTEXT_TOTAL);
    uint8_t hashes[P08_B2_CONTEXT_CORES][32];
    CHECK(backup != NULL && mutable_bytes != NULL);
    make_backup(backup, hashes);

    CHECK(test_authenticated_once(backup, mutable_bytes, hashes) == 0);
    CHECK(test_unchecked_content(backup, mutable_bytes) == 0);
    CHECK(test_authenticated_once_exposes_lock_dependency(backup, mutable_bytes, hashes) == 0);
    CHECK(test_bind_detects_preexisting_corruption(backup, mutable_bytes, hashes) == 0);
    CHECK(test_lock_failure_blocks_bind(backup, mutable_bytes, hashes) == 0);
    CHECK(test_operational_failure_poisons(backup, mutable_bytes, hashes) == 0);
    CHECK(test_lock_loss_poisons(backup, mutable_bytes, hashes) == 0);

    free(backup);
    free(mutable_bytes);
    puts("P08_B45_AUTHENTICATED_ONCE_27_SHA_BIND_AND_LIGHTWEIGHT_RESET_PASS=1");
    puts("P08_B45_AUTHENTICATED_ONCE_NO_PER_IMAGE_SHA_PASS=1");
    puts("P08_B45_UNCHECKED_CONTENT_NO_SHA_OR_HEADER_VALIDATION_PASS=1");
    puts("P08_B45_PERSISTENT_BACKUP_LOCK_REQUIRED_AND_ENFORCED_BY_CALLBACK_PASS=1");
    puts("P08_B45_BODY_MUTATION_AFTER_BIND_IS_NOT_DETECTED_WITHOUT_REAL_LOCK=1");
    puts("P08_B45_OPERATIONAL_FAILURE_POISONS_SESSION_PASS=1");
    puts("P08_B45_PHYSICAL_KV260_EXECUTED=0");
    return 0;
}
