/* Host-testable P08-A2 latency sidecar byte writer. No hardware dependencies. */
#include "p08_a2_timing.h"
#include <string.h>

_Static_assert(P08_A2_HEADER_BYTES + P08_A2_RECORD_BYTES * P08_A2_MAX_FRAMES
               <= P08_A2_CAPACITY, "P08-A2 timing sidecar DDR overflow");
_Static_assert(P08_A2_BASE + P08_A2_CAPACITY <= UINT32_C(0x43F00000),
               "P08-A2 timing collides with frozen P07 master/descriptor");

static void u32(uint8_t *p, uint32_t v) {
    unsigned i;
    for (i=0; i<4u; ++i) p[i]=(uint8_t)(v>>(8u*i));
}
static void u64(uint8_t *p, uint64_t v) {
    unsigned i;
    for (i=0; i<8u; ++i) p[i]=(uint8_t)(v>>(8u*i));
}
uint32_t p08_a2_crc32(const uint8_t *buf, size_t n) {
    uint32_t crc=UINT32_C(0xFFFFFFFF);
    size_t i;
    unsigned j;
    if (!buf && n) return 0;
    for(i=0;i<n;++i) {
        crc^=buf[i];
        for(j=0;j<8u;++j)
            crc=(crc>>1u) ^ ((crc&1u)?UINT32_C(0xEDB88320):0u);
    }
    return ~crc;
}
int p08_a2_pack_header(uint8_t *out,size_t size,uint32_t count,
                        uint32_t trace,uint32_t done,uint32_t status,
                        uint64_t freq,uint64_t begin,uint64_t stop) {
    if(!out || size!=P08_A2_HEADER_BYTES || !count ||
       count>P08_A2_MAX_FRAMES || trace>=count || done>count || !freq ||
       (status!=0u && status!=P08_A2_OK_STATUS &&
                         status!=P08_A2_FAIL_STATUS) ||
       (status==P08_A2_OK_STATUS && (done!=count || stop<begin)) ||
       (status==0u && stop!=0u) || (stop && stop<begin))
        return -1;
    memset(out,0,size);
    memcpy(out,"P08ALAT1",8u);
    u32(out+8u,P08_A2_VERSION);
    u32(out+12u,P08_A2_HEADER_BYTES);
    u32(out+16u,status);
    u32(out+20u,done);
    u32(out+24u,count);
    u32(out+28u,trace);
    u64(out+32u,freq);
    u64(out+40u,begin);
    u64(out+48u,stop);
    u32(out+56u,P08_A2_RECORD_BYTES);
    u32(out+60u,P08_A2_BASE);
    u32(out+64u,P08_A2_CAPACITY);
    u32(out+252u,p08_a2_crc32(out,252u));
    return 0;
}
int p08_a2_pack_record(uint8_t *out,size_t size,
                       const p08_a2_record *r) {
    if(!out || size!=P08_A2_RECORD_BYTES || !r ||
       r->image_index>=P08_A2_MAX_FRAMES || (r->flags & ~1u) ||
       !r->service_start || r->after_ingress<r->service_start ||
       r->after_neural<r->after_ingress ||
       r->after_commit<r->after_neural ||
       r->ps_inference_ticks>r->after_neural-r->service_start ||
       r->ps_control_ticks>r->after_neural-r->service_start)
        return -1;
    memset(out,0,size);
    u32(out+0u,r->image_index);
    u32(out+4u,r->flags);
    u64(out+8u,r->service_start);
    u64(out+16u,r->after_ingress);
    u64(out+24u,r->after_neural);
    u64(out+32u,r->after_commit);
    u64(out+40u,r->pl_dispatch_cycles);
    u64(out+48u,r->pl_page_cycles);
    u64(out+56u,r->ps_inference_ticks);
    u64(out+64u,r->ps_control_ticks);
    u64(out+72u,r->ps_route_ticks);
    u64(out+80u,r->ps_barrier_ticks);
    u32(out+88u,p08_a2_crc32(out,88u));
    return 0;
}
