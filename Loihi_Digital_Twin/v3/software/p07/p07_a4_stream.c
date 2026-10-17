/* P07-A4.2a candidate persistent DDR input/output ABI: portable C11 only.
 * This module performs ZERO actual hardware actions and makes NO official
 * TEST dataset access. It is separate from accepted P07-A2 and P05.
 */
#include "include/p07_a4_stream.h"
#include "include/p07_a1_ingress.h"

#include <string.h>

_Static_assert(P07_A4_MAX_FRAMES * P07_A4_IMAGE_BYTES <= P07_A4_INPUT_CAPACITY,
               "10k raw images exceed DDR region");
_Static_assert(P07_A4_JOURNAL_HEADER_BYTES +
               P07_A4_MAX_FRAMES * P07_A4_FRAME_RESULT_BYTES <=
               P07_A4_JOURNAL_CAPACITY, "10k result records exceed DDR journal");
_Static_assert(P07_A4_DESCRIPTOR_BASE + P07_A4_HEADER_BYTES +
               P07_A4_MAP_BYTES < P07_A4_TRACE_BASE,
               "A4 descriptor/mapping overlap trace");
_Static_assert(P07_A4_BACKING_BASE + 524288u <= P07_A4_INPUT_BASE,
               "A4 image region overlaps mutable P03 core0");
_Static_assert(P07_A4_INPUT_BASE + P07_A4_INPUT_CAPACITY <= P07_A4_JOURNAL_BASE,
               "A4 images overlap result journal");
_Static_assert(P07_A4_JOURNAL_BASE + P07_A4_JOURNAL_CAPACITY <= P07_A4_MASTER_BASE,
               "A4 journal overlaps immutable master");

/* Frozen SHA256 identities from accepted A2/Track A; MUST NOT auto-learn. */
static const uint8_t MASTER_SHA[32] = {
    0x96u,0x17u,0xa8u,0x22u,0xf7u,0x4fu,0xaau,0x87u,
    0x23u,0x86u,0x9bu,0xb5u,0x76u,0xcfu,0x57u,0xb3u,
    0x8au,0xf1u,0xa1u,0xa9u,0x1au,0xc8u,0x1cu,0x47u,
    0xc2u,0x46u,0xa9u,0x42u,0x5du,0x0du,0xd9u,0x55u
};
static const uint8_t COMP_SHA[32] = {
    0xe6u,0x12u,0xa9u,0x71u,0xcdu,0xa1u,0x1fu,0xaeu,
    0x3fu,0x1bu,0xe2u,0x15u,0xc0u,0xcau,0x3eu,0xd7u,
    0xdeu,0x7bu,0x2au,0xf7u,0x33u,0x94u,0x46u,0xe9u,
    0x26u,0xceu,0x55u,0x96u,0x58u,0xdbu,0x2fu,0x7fu
};

static uint16_t rd16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8u));
}
static uint32_t rd32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8u) |
           ((uint32_t)p[2] << 16u) | ((uint32_t)p[3] << 24u);
}
static void wr16(uint8_t *p, uint16_t value)
{
    p[0] = (uint8_t)value;
    p[1] = (uint8_t)(value >> 8u);
}
static void wr32(uint8_t *p, uint32_t value)
{
    p[0]=(uint8_t)value; p[1]=(uint8_t)(value>>8u);
    p[2]=(uint8_t)(value>>16u); p[3]=(uint8_t)(value>>24u);
}
static uint32_t crc32_ieee(const uint8_t *p, size_t length)
{
    uint32_t crc=UINT32_C(0xFFFFFFFF);
    size_t i;
    for (i=0u;i<length;++i) {
        uint32_t bit;
        crc ^= (uint32_t)p[i];
        for (bit=0u;bit<8u;++bit)
            crc=(crc>>1u)^((crc&1u)?UINT32_C(0xEDB88320):0u);
    }
    return ~crc;
}
static int zeros(const uint8_t *p, size_t len)
{
    size_t i;
    for(i=0;i<len;++i) if(p[i])return 0;
    return 1;
}
static int valid_map(const uint8_t *mapping)
{
    uint8_t seen[4096u/8u]={0u};
    uint32_t i;
    for(i=0u;i<784u;++i) {
        uint32_t axon=rd16(mapping+i*2u);
        uint8_t bit;
        if(axon>=4096u)return 0;
        bit=(uint8_t)(1u<<(axon&7u));
        if(seen[axon>>3u]&bit)return 0;
        seen[axon>>3u]|=bit;
    }
    return 1;
}
int p07_a4_validate_staging(const uint8_t *d, size_t dlen,
                            const uint8_t *map, size_t maplen,
                            const uint8_t *images, size_t images_len,
                            p07_a4_descriptor *out)
{
    uint32_t count, trace;
    if(!out)return -1;
    memset(out,0,sizeof(*out));
    if(!d || !map || !images || dlen!=P07_A4_HEADER_BYTES ||
       maplen!=P07_A4_MAP_BYTES || memcmp(d,"P07A4P01",8u)!=0)
        return -1;
    count=rd32(d+16u); trace=rd32(d+48u);
    if(count<1u || count>P07_A4_MAX_FRAMES || trace>=count ||
       images_len!=(size_t)count*P07_A4_IMAGE_BYTES ||
       (size_t)count*P07_A4_IMAGE_BYTES>P07_A4_INPUT_CAPACITY ||
       P07_A4_JOURNAL_HEADER_BYTES+
         (size_t)count*P07_A4_FRAME_RESULT_BYTES>P07_A4_JOURNAL_CAPACITY)
        return -2;
    if(rd32(d+8u)!=1u || rd32(d+12u)!=P07_A4_HEADER_BYTES ||
       rd32(d+20u)!=P07_A4_IMAGE_BYTES ||
       rd32(d+24u)!=P07_A4_INPUT_BASE ||
       rd32(d+28u)!=P07_A4_INPUT_CAPACITY ||
       rd32(d+32u)!=P07_A4_JOURNAL_BASE ||
       rd32(d+36u)!=P07_A4_JOURNAL_CAPACITY ||
       rd32(d+40u)!=P07_A4_FRAME_RESULT_BYTES ||
       rd32(d+44u)!=P07_A4_TRACE_BASE ||
       rd32(d+52u)!=0u ||
       rd32(d+64u)!=784u ||
       rd32(d+68u)!=P07_A4_MAPPING_BASE ||
       rd32(d+72u)!=P07_A4_MASTER_BASE ||
       rd32(d+76u)!=P07_A4_BACKING_BASE ||
       !zeros(d+144u,108u))
        return -3;
    if(memcmp(d+80u,MASTER_SHA,32u)!=0 ||
       memcmp(d+112u,COMP_SHA,32u)!=0)
        return -4;
    if(rd32(d+252u)!=crc32_ieee(d,252u) ||
       rd32(d+60u)!=crc32_ieee(map,maplen) ||
       rd32(d+56u)!=crc32_ieee(images,images_len))
        return -5;
    if(!valid_map(map))return -6;
    out->frame_count=count;
    out->trace_frame=trace;
    out->image_crc32=rd32(d+56u);
    out->mapping_crc32=rd32(d+60u);
    out->descriptor_crc32=rd32(d+252u);
    memcpy(out->ddr_sha256,d+80u,32u);
    memcpy(out->compiled_sha256,d+112u,32u);
    return 0;
}

int p07_a4_make_ingress(const p07_a4_descriptor *verified,
                        const uint8_t *mapping, size_t mapping_bytes,
                        const uint8_t *image, size_t image_bytes,
                        uint32_t image_index,
                        uint8_t *output, size_t output_bytes)
{
    uint8_t scratch[P07_A1_RECORD_BYTES];
    if(!verified || !mapping || !image || !output ||
       mapping_bytes!=P07_A4_MAP_BYTES || image_bytes!=P07_A4_IMAGE_BYTES ||
       output_bytes!=P07_A1_RECORD_BYTES ||
       image_index>=verified->frame_count ||
       crc32_ieee(mapping,mapping_bytes)!=verified->mapping_crc32 ||
       !valid_map(mapping) ||
       memcmp(verified->ddr_sha256,MASTER_SHA,32u)!=0 ||
       memcmp(verified->compiled_sha256,COMP_SHA,32u)!=0)
        return -1;
    memset(scratch,0,sizeof(scratch));
    memcpy(scratch,"P07A1IN1",8u);
    wr32(scratch+8u,1u);
    wr32(scratch+12u,128u);
    wr32(scratch+16u,2352u);
    wr32(scratch+20u,1568u);
    wr32(scratch+24u,784u);
    wr32(scratch+28u,784u);
    wr32(scratch+32u,25u);
    wr32(scratch+36u,26u);
    wr32(scratch+40u,0u);
    wr32(scratch+44u,784u);
    wr32(scratch+48u,4096u);
    wr32(scratch+52u,0u);
    memcpy(scratch+64u,verified->ddr_sha256,32u);
    memcpy(scratch+96u,verified->compiled_sha256,32u);
    memcpy(scratch+128u,mapping,P07_A4_MAP_BYTES);
    memcpy(scratch+128u+P07_A4_MAP_BYTES,image,P07_A4_IMAGE_BYTES);
    wr32(scratch+56u,crc32_ieee(scratch+128u,2352u));
    wr32(scratch+60u,crc32_ieee(scratch,128u));
    memcpy(output,scratch,sizeof(scratch));
    return 0;
}

int p07_a4_pack_result(const p07_a4_compact_result *src,
                       uint8_t *dst, size_t dst_bytes)
{
    uint8_t scratch[P07_A4_FRAME_RESULT_BYTES]={0u};
    uint16_t counts[10]={0u};
    uint32_t t,cls,winner=0u,active=0u;
    if(!src || !dst || dst_bytes!=P07_A4_FRAME_RESULT_BYTES ||
       src->image_index>=P07_A4_MAX_FRAMES ||
       src->external_event_total>25u*784u)return -1;
    wr32(scratch+0u,src->image_index);
    wr32(scratch+4u,src->pixel_crc32);
    wr32(scratch+8u,P07_A4_OK_STATUS);
    wr32(scratch+20u,src->committed_routes);
    wr32(scratch+24u,src->dropped_final_packets);
    wr32(scratch+28u,src->external_event_total);
    for(t=0u;t<26u;++t)for(cls=0u;cls<10u;++cls) {
        uint8_t b=src->output_spikes[t][cls];
        uint32_t bit=t*10u+cls;
        if(b>1u)return -1;
        if(b) {
            uint32_t offset=52u+(bit/32u)*4u;
            wr32(scratch+offset,rd32(scratch+offset)|
                 (UINT32_C(1)<<(bit%32u)));
            ++counts[cls];
            active=1u;
        }
    }
    for(cls=0u;cls<10u;++cls) {
        wr16(scratch+32u+cls*2u,counts[cls]);
        if(counts[cls]>counts[winner])winner=cls;
    }
    wr32(scratch+12u,winner);
    wr32(scratch+16u,!active?1u:0u);
    wr32(scratch+88u,src->cycles_low32);
    wr32(scratch+92u,crc32_ieee(scratch,92u));
    memcpy(dst,scratch,sizeof(scratch));
    return 0;
}

int p07_a4_validate_result(const uint8_t *r, size_t len,
                           const uint8_t *pixels, size_t pixels_len,
                           uint32_t expected_index)
{
    uint16_t counts[10]={0u};
    uint32_t t,cls,winner=0u,active=0u;
    if(!r || !pixels || len!=P07_A4_FRAME_RESULT_BYTES ||
       pixels_len!=P07_A4_IMAGE_BYTES || expected_index>=P07_A4_MAX_FRAMES)
        return -1;
    if(rd32(r)!=expected_index ||
       rd32(r+4u)!=crc32_ieee(pixels,pixels_len) ||
       rd32(r+8u)!=P07_A4_OK_STATUS ||
       rd32(r+12u)>9u || rd32(r+16u)>1u ||
       rd32(r+28u)>25u*784u ||
       rd32(r+92u)!=crc32_ieee(r,92u))
        return -2;
    /* 9 words=288 bits; only the first 260 output bits are legal. */
    if((rd32(r+84u) & UINT32_C(0xFFFFFFF0))!=0u)
        return -3;
    for(t=0u;t<26u;++t)for(cls=0u;cls<10u;++cls) {
        uint32_t bit=t*10u+cls;
        uint32_t has=(rd32(r+52u+(bit/32u)*4u)>>(bit%32u))&1u;
        counts[cls]+=(uint16_t)has;
        active|=has;
    }
    for(cls=0u;cls<10u;++cls) {
        if(rd16(r+32u+cls*2u)!=counts[cls])return -4;
        if(counts[cls]>counts[winner])winner=cls;
    }
    if(rd32(r+12u)!=winner || rd32(r+16u)!=(active?0u:1u))
        return -5;
    return 0;
}

int p07_a4_make_journal_header(uint8_t *dst, size_t bytes,
                               uint32_t count, uint32_t trace_frame,
                               uint32_t descriptor_crc32,
                               uint32_t status, uint32_t completed,
                               uint32_t first_fault)
{
    uint8_t scratch[P07_A4_JOURNAL_HEADER_BYTES]={0u};
    if(!dst || bytes!=P07_A4_JOURNAL_HEADER_BYTES ||
       count<1u || count>P07_A4_MAX_FRAMES ||
       trace_frame>=count || completed>count ||
       (status==P07_A4_OK_STATUS &&
         (completed!=count || first_fault!=UINT32_MAX)))
        return -1;
    memcpy(scratch,"P07A4R01",8u);
    wr32(scratch+8u,1u);
    wr32(scratch+12u,P07_A4_JOURNAL_HEADER_BYTES);
    wr32(scratch+16u,status);
    wr32(scratch+20u,count);
    wr32(scratch+24u,completed);
    wr32(scratch+28u,first_fault);
    wr32(scratch+32u,descriptor_crc32);
    wr32(scratch+36u,trace_frame);
    wr32(scratch+40u,0u);
    wr32(scratch+252u,crc32_ieee(scratch,252u));
    memcpy(dst,scratch,sizeof(scratch));
    return 0;
}
