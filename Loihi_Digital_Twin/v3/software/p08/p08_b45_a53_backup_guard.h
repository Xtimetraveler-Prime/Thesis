#ifndef P08_B45_A53_BACKUP_GUARD_H
#define P08_B45_A53_BACKUP_GUARD_H

/* P08-B4.5 fail-closed platform ownership/protection boundary.
 * The shipped platform adapter intentionally refuses both backup locking
 * and lock verification. This permits offline Vitis ELF builds and source
 * review, but deliberately prevents physical inference until an independently
 * audited and operator-approved DDR master/ownership protection provider
 * replaces this file in a separate, newly signed candidate.
 */
#include <stddef.h>
#include <stdint.h>

#define P08_B45_A53_GUARD_PROVISIONED 0u
int p08_b45_a53_backup_lock(void *cookie, uintptr_t address, size_t bytes);
int p08_b45_a53_backup_lock_valid(void *cookie, uintptr_t address, size_t bytes);

#endif
