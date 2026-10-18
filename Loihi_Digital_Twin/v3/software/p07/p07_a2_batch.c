#include "include/p07_a2_batch.h"
#include <string.h>

static uint32_t u32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint32_t crc32_header(const uint8_t *p)
{
    uint32_t crc=UINT32_C(0xFFFFFFFF);
    uint32_t i,b;
    for (i=0u; i<P07_A2_BATCH_HEADER_BYTES; ++i) {
        uint32_t v=(i>=32u && i<36u)?0u:p[i];
        crc^=v;
        for (b=0u;b<8u;++b)
            crc=(crc>>1u)^((crc&1u)?UINT32_C(0xEDB88320):0u);
    }
    return ~crc;
}
int p07_a2_batch_validate(const uint8_t *h, size_t length,
                          p07_a2_batch_info *out)
{
    static const uint8_t magic[8]={'P','0','7','A','2','B','0','1'};
    uint32_t count,trace,i;
    if (!out) return -1;
    memset(out,0,sizeof(*out));
    if (!h || length != P07_A2_BATCH_HEADER_BYTES ||
        memcmp(h,magic,sizeof(magic)) != 0 ||
        u32(h+8u)!=1u || u32(h+16u)!=P07_A1_RECORD_BYTES ||
        u32(h+20u)!=P07_A2_INPUT_BASE || u32(h+24u)!=0u ||
        u32(h+32u)!=crc32_header(h))
        return -1;
    count=u32(h+12u); trace=u32(h+28u);
    if(count==0u || count>P07_A2_MAX_FRAMES || trace>=count ||
       (uint64_t)count*P07_A1_RECORD_BYTES >
          (uint64_t)P07_A2_BATCH_BASE-P07_A2_INPUT_BASE)
        return -1;
    for(i=36u;i<P07_A2_BATCH_HEADER_BYTES;++i)
        if(h[i]!=0u)return -1;
    out->frame_count=count;out->trace_frame=trace;
    return 0;
}
