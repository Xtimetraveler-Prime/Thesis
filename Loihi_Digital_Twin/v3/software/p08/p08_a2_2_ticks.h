#ifndef LOIHI_TWIN_V3_P08_A2_2_TICKS_H
#define LOIHI_TWIN_V3_P08_A2_2_TICKS_H
/* EXPERIMENTAL per-tick A53 profiling. Frozen P07 journal & PL unchanged.
 * Per-tick data are independent of the accepted A2.1 P08ALAT1 sidecar.
 * Raw CNTVCT values are not FPGA PL cycles. All wire words little endian.
 */
#include <stddef.h>
#include <stdint.h>

#define P08_A2_2_TICK_BASE UINT32_C(0x43100000)
#define P08_A2_2_TICK_CAPACITY 3145728u /* 3MiB, ends at 0x433fffff */
#define P08_A2_2_TICK_HEADER 256u
#define P08_A2_2_TICK_RECORD 96u
#define P08_A2_2_TICKS_PER_FRAME 26u
#define P08_A2_2_MAX_FRAMES 1024u
#define P08_A2_2_TICK_SUCCESS UINT32_C(0x600D600D)
#define P08_A2_2_TICK_FAILURE UINT32_C(0xDEAD0001)

typedef struct {
    uint32_t frame;
    uint32_t tick;              /* 0..24 ingress, 25 final drain */
    uint32_t external_events;   /* excludes routed NEXT events */
    uint32_t emitted_packets;
    uint32_t acknowledged_packets; /* drain tick counts intentionally discarded NEXT */
    uint32_t flags;             /* bit0: final drain tick */
    uint64_t start;             /* before p07_a1_tick_events */
    uint64_t after_encode;
    uint64_t after_append;      /* CURRENT event-bank MMIO, including preflight */
    uint64_t after_dispatch;    /* P03 MMIO command, DONE poll, CSRs */
    uint64_t after_trace;       /* ten output compartments, or 42 selected */
    uint64_t after_route;       /* packet route or final drain policy */
    uint64_t after_barrier;     /* barrier_ready callback completed */
    uint64_t pl_dispatch_cycles; /* from PL register (different clock domain!) */
} p08_a2_2_tick;

/* Header: 256B, CRC32 @252. See P08_A2_2_TIMING_METHODS.md. */
int p08_a2_2_pack_header(uint8_t *out, size_t n,
                        uint32_t frames, uint32_t trace_frame,
                        uint32_t completed, uint32_t status,
                        uint32_t descriptor_crc32, uint64_t hz,
                        uint64_t start, uint64_t stop);
int p08_a2_2_pack_tick(uint8_t *out, size_t n,
                      const p08_a2_2_tick *record);
#endif
