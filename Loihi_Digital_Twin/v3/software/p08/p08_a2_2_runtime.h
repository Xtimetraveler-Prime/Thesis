#ifndef LOIHI_TWIN_V3_P08_A2_2_RUNTIME_H
#define LOIHI_TWIN_V3_P08_A2_2_RUNTIME_H
/* Instrumented copy of frozen P07-A2 wrapper: scheduling, encoding,
 * event ordering, LIF/P03 semantics remain the original project code.
 * Timing callbacks use the P03/A53 read_ticks hardware bridge. */
#include "p07_a2_runtime.h"
#include "p08_a2_2_ticks.h"

int p08_a2_2_run_frame(const uint8_t *record, size_t bytes,
                      const p07_a2_driver *driver, p07_a2_result *result,
                      p08_a2_2_tick ticks[P08_A2_2_TICKS_PER_FRAME],
                      uint32_t frame);
#endif
