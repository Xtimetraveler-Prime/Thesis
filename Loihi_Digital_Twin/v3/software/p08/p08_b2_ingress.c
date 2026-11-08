#include "p08_b2_ingress.h"
#include "p07_a2_sha256.h"
#include <stdint.h>
#include <string.h>

_Static_assert(P08_B2_WIRE_BYTES==123216u,"original TRAIN0 B1.3 geometry drift");
_Static_assert(P08_B2_WIRE_BYTES<0xE0000u,"original ingress buffer overflow");

static const uint8_t accepted_route_sha[32]={
    0x38,0x02,0x68,0xc5,0xe8,0xfa,0xa2,0x66,
    0x4a,0x31,0xf9,0x93,0x68,0x3c,0x67,0x59,
    0x31,0x62,0x39,0x93,0x2d,0x96,0xb8,0xe6,
    0x81,0xdd,0xb4,0x58,0xc8,0x15,0x74,0xe8
};
static const uint8_t compiled_sha[32]={
    0x02,0xa6,0xb6,0x8a,0x2e,0xda,0x45,0x87,
    0xbb,0xdf,0x07,0xe3,0xaf,0x4a,0xa6,0x3b,
    0xdd,0x72,0x14,0x22,0x3e,0x85,0x3b,0x08,
    0xd8,0xf6,0x46,0x38,0x96,0x36,0x4f,0x5a
};
static const uint8_t audit_sha[32]={
    0x82,0xe9,0xe6,0xc1,0x12,0x64,0xc6,0x09,
    0x2d,0xbe,0x94,0xf1,0x74,0x96,0x33,0x2f,
    0xae,0x30,0x3a,0xc9,0xef,0x7d,0xfa,0xa0,
    0x1d,0x0e,0xc4,0x41,0x86,0x9a,0x94,0x98
};
static uint32_t le32(const uint8_t *p){
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8u) |
           ((uint32_t)p[2]<<16u) | ((uint32_t)p[3]<<24u);
}
static void put32(uint8_t *p,uint32_t x){
    p[0]=(uint8_t)x; p[1]=(uint8_t)(x>>8u);
    p[2]=(uint8_t)(x>>16u); p[3]=(uint8_t)(x>>24u);
}
static uint32_t crc32(const uint8_t *data,size_t size){
    uint32_t v=UINT32_C(0xFFFFFFFF);
    size_t i;
    uint32_t j;
    for(i=0u;i<size;i++){
        v ^= (uint32_t)data[i];
        for(j=0u;j<8u;j++)
            v=(v>>1u)^((v&1u)?UINT32_C(0xEDB88320):0u);
    }
    return ~v;
}
int p08_b2_admit_routes(const uint8_t *source,size_t source_len,
                        p08_b2_route_binding *out){
    static const uint8_t magic[8]={'B','4','M','I','N','G','0','1'};
    uint8_t digest[32];
    p08_b2_route_binding accepted;
    if(!source || !out || source_len!=P08_B2_ROUTE_IMAGE_BYTES)
        return P08_B2_INVALID;
    p07_a2_sha256(source,source_len,digest);
    if(memcmp(digest,accepted_route_sha,32u)!=0)
        return P08_B2_SOURCE_SHA;
    if(memcmp(source,magic,8u)!=0 ||
       le32(source+8u)!=1u ||
       le32(source+12u)!=P08_B2_ROUTE_IMAGE_BYTES ||
       le32(source+16u)!=27u ||
       le32(source+20u)!=P08_B2_EXPECTED_INPUT_ROUTES ||
       le32(source+24u)!=6u ||
       le32(source+28u)!=P08_B2_ROUTE_HEADER_BYTES ||
       memcmp(source+32u,compiled_sha,32u)!=0 ||
       memcmp(source+64u,audit_sha,32u)!=0)
        return P08_B2_INVALID;
    accepted.original_route_image=source;
    accepted.routes=source+P08_B2_ROUTE_HEADER_BYTES;
    accepted.route_count=P08_B2_EXPECTED_INPUT_ROUTES;
    accepted.admitted_tag=P08_B2_ADMITTED_TAG;
    *out=accepted;
    return P08_B2_OK;
}
int p08_b2_encode_frame(const p08_b2_route_binding *binding,
                        const uint8_t pixels[P08_B2_RAW_IMAGE_BYTES],
                        uint8_t *output,size_t capacity,size_t *out_length){
    size_t route_length=(size_t)P08_B2_EXPECTED_INPUT_ROUTES*6u;
    uint32_t payload_crc,header_crc;
    uintptr_t r,p,o;
    if(!binding || !pixels || !output || !out_length ||
       binding->admitted_tag!=P08_B2_ADMITTED_TAG ||
       binding->route_count!=P08_B2_EXPECTED_INPUT_ROUTES ||
       !binding->original_route_image ||
       binding->routes!=binding->original_route_image+P08_B2_ROUTE_HEADER_BYTES)
        return P08_B2_INVALID;
    if(capacity<P08_B2_WIRE_BYTES)return P08_B2_CAPACITY;
    /* Reject all A53 shared-buffer aliasing; input source immutable for CRC. */
    r=(uintptr_t)binding->original_route_image;
    p=(uintptr_t)pixels;
    o=(uintptr_t)output;
    if(r>UINTPTR_MAX-P08_B2_ROUTE_IMAGE_BYTES ||
       p>UINTPTR_MAX-P08_B2_RAW_IMAGE_BYTES ||
       o>UINTPTR_MAX-P08_B2_WIRE_BYTES ||
       (o<r+P08_B2_ROUTE_IMAGE_BYTES && r<o+P08_B2_WIRE_BYTES) ||
       (o<p+P08_B2_RAW_IMAGE_BYTES && p<o+P08_B2_WIRE_BYTES))
        return P08_B2_INVALID;
    memset(output,0,P08_B2_WIRE_HEADER_BYTES);
    memcpy(output,"P06B13I1",8u);
    put32(output+8u,1u);
    put32(output+12u,P08_B2_WIRE_HEADER_BYTES);
    put32(output+16u,(uint32_t)(route_length+P08_B2_RAW_IMAGE_BYTES));
    put32(output+20u,P08_B2_EXPECTED_INPUT_ROUTES);
    put32(output+24u,27u);
    put32(output+28u,P08_B2_RAW_IMAGE_BYTES);
    put32(output+32u,25u);
    put32(output+36u,26u);
    put32(output+40u,6u);
    put32(output+44u,P08_B2_RAW_IMAGE_BYTES);
    memcpy(output+64u,compiled_sha,32u);
    memcpy(output+96u,audit_sha,32u);
    memcpy(output+P08_B2_WIRE_HEADER_BYTES,binding->routes,route_length);
    memcpy(output+P08_B2_WIRE_HEADER_BYTES+route_length,
           pixels,P08_B2_RAW_IMAGE_BYTES);
    payload_crc=crc32(output+P08_B2_WIRE_HEADER_BYTES,
                      route_length+P08_B2_RAW_IMAGE_BYTES);
    put32(output+48u,payload_crc);
    header_crc=crc32(output,P08_B2_WIRE_HEADER_BYTES);
    put32(output+52u,header_crc);
    *out_length=P08_B2_WIRE_BYTES;
    return P08_B2_OK;
}
