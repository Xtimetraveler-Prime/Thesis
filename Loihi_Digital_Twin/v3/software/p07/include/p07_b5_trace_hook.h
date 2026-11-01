#ifndef LOIHI_TWIN_V3_P07_B5_TRACE_HOOK_H
#define LOIHI_TWIN_V3_P07_B5_TRACE_HOOK_H
/* B5 ONLY replacement for original p07_b4m_spike_trace.c implementation.
 * Preserves original function names for original full_run(), but adds
 * mandatory fail-closed B5 raw recorder binding. This header and replacement
 * MUST NOT be included in accepted original V3 ELF or original V3 build.
 */
#include "p07_b5_raw_capture.h"
int p07_b5_trace_attach(p07_b5_raw_capture *capture);
#endif
