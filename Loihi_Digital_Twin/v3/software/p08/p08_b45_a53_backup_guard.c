#include "p08_b45_a53_backup_guard.h"
#include "p08_b2_context_reset.h"

/* Deliberately NO MMIO writes, XMPU programming, or security changes.
 * This is NOT an implementation of read-only DDR protection.
 * No hardware inference is authorized with this adapter.
 */
int p08_b45_a53_backup_lock(void *cookie, uintptr_t address, size_t bytes) {
    (void)cookie;
    (void)address;
    (void)bytes;
    return -1;
}
int p08_b45_a53_backup_lock_valid(void *cookie, uintptr_t address, size_t bytes) {
    (void)cookie;
    (void)address;
    (void)bytes;
    return -1;
}
