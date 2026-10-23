#include "p07_b4l_b3_bindings.h"
#include "p07_a2_sha256.h"
#include <string.h>
_Static_assert(B4L_BIND_HEADER+B4L_BIND_BYTES<B4L_BIND_SIZE,
               "binding descriptor exceeds independently allocated DDR space");
static uint32_t u32(const uint8_t *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
           ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static uint64_t u64(const uint8_t *p){
    return (uint64_t)u32(p)|((uint64_t)u32(p+4)<<32);
}
static const uint8_t accepted_bundle_sha[32]={
    0x37,0x33,0xe1,0xc2,0x89,0xfb,0x57,0x04,
    0xc6,0x9b,0xe9,0x0f,0x37,0xb5,0x9a,0x25,
    0xe3,0x0d,0xde,0xdf,0x7d,0xd8,0xdc,0x30,
    0x56,0x49,0xe0,0xbe,0x23,0x8a,0xf6,0x4e};
static const uint8_t accepted_deployment_sha[32]={
    0x02,0xa6,0xb6,0x8a,0x2e,0xda,0x45,0x87,
    0xbb,0xdf,0x07,0xe3,0xaf,0x4a,0xa6,0x3b,
    0xdd,0x72,0x14,0x22,0x3e,0x85,0x3b,0x08,
    0xd8,0xf6,0x46,0x38,0x96,0x36,0x4f,0x5a};
int b4l_bind_frozen(p03_hw_adapter *hw,const uint8_t *bytes,size_t n,
                    b4l_binding_receipt *r){
    static const uint8_t magic[8]={'B','4','B','I','N','D','0','1'};
    uint8_t digest[32];
    uint32_t core,axon,total=0u,compartments=0u;
    size_t i;
    if(!hw||!bytes||!r||n!=B4L_BIND_SIZE||hw->last_error!=P03_HW_OK)
        return B4L_BIND_INVALID;
    memset(r,0,sizeof(*r));
    r->first_bad_core=UINT32_MAX;r->first_bad_axon=UINT32_MAX;
    if(memcmp(bytes,magic,sizeof(magic))!=0||
       u32(bytes+8)!=1u||u32(bytes+12)!=B4L_BIND_SIZE||
       u32(bytes+16)!=B4L_BIND_CORES||
       u32(bytes+20)!=B4L_BIND_ENTRY||
       u32(bytes+24)!=B4L_BIND_HEADER||
       u32(bytes+28)!=B4L_BIND_BYTES||
       memcmp(bytes+32,accepted_bundle_sha,32u)!=0||
       memcmp(bytes+64,accepted_deployment_sha,32u)!=0)
        return B4L_BIND_INVALID;
    for(i=B4L_BIND_HEADER+B4L_BIND_BYTES;i<B4L_BIND_SIZE;i++)
        if(bytes[i]!=0u)return B4L_BIND_INVALID;
    p07_a2_sha256(bytes+B4L_BIND_HEADER,B4L_BIND_BYTES,digest);
    if(memcmp(bytes+96,digest,32u)!=0)return B4L_BIND_SHA;
    /* Structural preflight of ALL registration entries before ANY P03
     * mutation, so truncated, swapped or bad bitmaps never partially bind.
     */
    for(core=0u;core<B4L_BIND_CORES;core++){
        const uint8_t *e=bytes+B4L_BIND_HEADER+(size_t)core*B4L_BIND_ENTRY;
        uint64_t metadata=u64(e);
        uint32_t count=u32(e+12),pop=0u;
        uint32_t ncomp=(uint32_t)e[8]|((uint32_t)e[9]<<8);
        uint32_t nax=(uint32_t)e[10]|((uint32_t)e[11]<<8);
        if(count!=core||ncomp==0u||ncomp>1024u||
           metadata!=(((uint64_t)ncomp<<7u)|((uint64_t)core)))
            return B4L_BIND_INVALID;
        for(axon=0u;axon<B4L_BIND_BITMAP;axon++){
            uint32_t b=e[16+axon];
            for(i=0u;i<8u;i++)pop+=(b>>(uint32_t)i)&1u;
        }
        if(pop!=nax)return B4L_BIND_INVALID;
        if(hw->configured[core])return B4L_BIND_INVALID;
    }
    for(core=0u;core<B4L_BIND_CORES;core++){
        const uint8_t *e=bytes+B4L_BIND_HEADER+(size_t)core*B4L_BIND_ENTRY;
        uint32_t ncomp=(uint32_t)e[8]|((uint32_t)e[9]<<8);
        if(p03_hw_register_core(hw,(uint8_t)core,u64(e),0u,0u)!=P03_HW_OK){
            r->first_bad_core=core;return B4L_BIND_ADAPTER;
        }
        for(axon=0u;axon<4096u;axon++){
            if(e[16+axon/8u] & (uint8_t)(1u<<(axon%8u))){
                if(p03_hw_register_axon(hw,(uint8_t)core,(uint16_t)axon)!=P03_HW_OK){
                    r->first_bad_core=core;r->first_bad_axon=axon;
                    return B4L_BIND_ADAPTER;
                }
                total++;
            }
        }
        r->core_count++;
        compartments+=ncomp;
    }
    r->registered_axons=total;
    r->registered_compartments=compartments;
    return B4L_BIND_OK;
}
