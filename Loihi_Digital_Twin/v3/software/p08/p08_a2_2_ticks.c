/* Portable C11 per-tick telemetry codec; no hardware access or side effects. */
#include "p08_a2_2_ticks.h"
#include "p08_a2_timing.h"
#include <string.h>

_Static_assert(P08_A2_2_TICK_HEADER +
               P08_A2_2_MAX_FRAMES * P08_A2_2_TICKS_PER_FRAME *
               P08_A2_2_TICK_RECORD <= P08_A2_2_TICK_CAPACITY,
               "P08-A2.2 tick sidecar exceeds DDR capacity");
_Static_assert(P08_A2_2_TICK_BASE >= P08_A2_BASE+P08_A2_CAPACITY,
               "P08-A2.2 overlaps A2.1 timing sidecar");
_Static_assert(P08_A2_2_TICK_BASE+P08_A2_2_TICK_CAPACITY <=
               UINT32_C(0x43F00000), "P08-A2.2 overlaps immutable master");

static void w32(uint8_t *p, uint32_t x)
{
    unsigned i;
    for(i=0;i<4u;i++)p[i]=(uint8_t)(x>>(8u*i));
}
static void w64(uint8_t *p, uint64_t x)
{
    unsigned i;
    for(i=0;i<8u;i++)p[i]=(uint8_t)(x>>(8u*i));
}
int p08_a2_2_pack_header(uint8_t *out, size_t n,
                        uint32_t frames, uint32_t trace_frame,
                        uint32_t completed, uint32_t status,
                        uint32_t descriptor_crc32, uint64_t hz,
                        uint64_t start, uint64_t stop)
{
    if(!out || n!=P08_A2_2_TICK_HEADER ||
       frames==0u || frames>P08_A2_2_MAX_FRAMES ||
       trace_frame>=frames || completed>frames || hz==0u ||
       (status!=0u && status!=P08_A2_2_TICK_SUCCESS &&
                    status!=P08_A2_2_TICK_FAILURE) ||
       (status==0u && stop!=0u) ||
       (status==P08_A2_2_TICK_SUCCESS &&
                    (completed!=frames || stop<=start)) ||
       (stop && stop<start)) return -1;
    memset(out,0,n);
    memcpy(out,"P08TCK02",8u);
    w32(out+8u,2u);
    w32(out+12u,P08_A2_2_TICK_HEADER);
    w32(out+16u,status);
    w32(out+20u,completed);
    w32(out+24u,frames);
    w32(out+28u,P08_A2_2_TICKS_PER_FRAME);
    w64(out+32u,hz);
    w32(out+40u,P08_A2_2_TICK_BASE);
    w32(out+44u,P08_A2_2_TICK_CAPACITY);
    w32(out+48u,P08_A2_2_TICK_RECORD);
    w32(out+52u,descriptor_crc32);
    w32(out+56u,trace_frame);
    w64(out+64u,start);
    w64(out+72u,stop);
    w32(out+252u,p08_a2_crc32(out,252u));
    return 0;
}
int p08_a2_2_pack_tick(uint8_t *out, size_t n,
                      const p08_a2_2_tick *r)
{
    if(!out || n!=P08_A2_2_TICK_RECORD || !r ||
       r->frame>=P08_A2_2_MAX_FRAMES ||
       r->tick>=P08_A2_2_TICKS_PER_FRAME ||
       r->flags!=(r->tick==25u?1u:0u) ||
       r->external_events>784u ||
       (r->tick==25u && r->external_events!=0u) ||
       r->acknowledged_packets>r->emitted_packets ||
       r->start==0u || r->after_encode<r->start ||
       r->after_append<r->after_encode ||
       r->after_dispatch<r->after_append ||
       r->after_trace<r->after_dispatch ||
       r->after_route<r->after_trace ||
       r->after_barrier<r->after_route) return -1;
    memset(out,0,n);
    w32(out+0u,r->frame);
    w32(out+4u,r->tick);
    w32(out+8u,r->external_events);
    w32(out+12u,r->emitted_packets);
    w32(out+16u,r->acknowledged_packets);
    w32(out+20u,r->flags);
    w64(out+24u,r->start);
    w64(out+32u,r->after_encode);
    w64(out+40u,r->after_append);
    w64(out+48u,r->after_dispatch);
    w64(out+56u,r->after_trace);
    w64(out+64u,r->after_route);
    w64(out+72u,r->after_barrier);
    w64(out+80u,r->pl_dispatch_cycles);
    w32(out+88u,p08_a2_crc32(out,88u));
    return 0;
}
