#ifndef P08_B45_PERF_RESET_H
#define P08_B45_PERF_RESET_H
/*
 * P08-B4.5 reduced-integrity PERFORMANCE TEST ONLY.
 * APIs intentionally distinct from protected reset variants. They do NOT
 * request or imply a DDR-XMPU lock. Original source/target are frozen.
 * All other configuration bounds, quiescence/cache/barrier, poisoning,
 * SHA-once and lightweight header / unchecked behaviors are inherited.
 */
#include "p08_b45_reset_variants.h"
int p08_b45_perf_reset_bind(p08_b45_reset_state *state,
                             const p08_b45_reset_config *config,
                             p08_b45_reset_mode mode);
int p08_b45_perf_reset_image(p08_b45_reset_state *state,
                              p08_b45_reset_receipt *out);
#endif
