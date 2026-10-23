#include "p07_b4m_frozen_routes.h"
#include "p07_a2_sha256.h"
#include <string.h>

_Static_assert(sizeof(p07_b2_route)==8u,"original P06B13R1 route ABI");
_Static_assert(P07_B2_MAX_ROUTE_BINDINGS==8192u ||
               P07_B2_MAX_ROUTE_BINDINGS==10000u,
               "original native gate or separate full B4m dense routing ceiling");
_Static_assert(P07_B4M_ROUTE_HEAD+P07_B4M_ROUTE_COMP_BYTES+
    8u*P07_B2_MAX_ROUTE_BINDINGS<=P07_B4M_ROUTE_OUT_BYTES,
    "output route bin overlaps P05 header or mailbox");
_Static_assert(P07_B4M_ROUTE_HEAD+6u*P07_B2_MAX_ROUTES<=
    P07_B4M_ROUTE_IN_BYTES,"input route bin exceeds staging region");
_Static_assert(P07_B4M_ROUTE_OUT_BASE+P07_B4M_ROUTE_OUT_BYTES<=
    UINT32_C(0x43FE0000),"route output overlaps P05 metadata");
_Static_assert(P07_B4M_ROUTE_IN_BASE+P07_B4M_ROUTE_IN_BYTES<=
    P07_B4M_FRAME_BASE,"routes overlap original B4m input frame");
static const uint8_t compiled_sha[32]={
    0x02,0xa6,0xb6,0x8a,0x2e,0xda,0x45,0x87,
    0xbb,0xdf,0x07,0xe3,0xaf,0x4a,0xa6,0x3b,
    0xdd,0x72,0x14,0x22,0x3e,0x85,0x3b,0x08,
    0xd8,0xf6,0x46,0x38,0x96,0x36,0x4f,0x5a};
static const uint8_t cap_sha[32]={
    0x82,0xe9,0xe6,0xc1,0x12,0x64,0xc6,0x09,
    0x2d,0xbe,0x94,0xf1,0x74,0x96,0x33,0x2f,
    0xae,0x30,0x3a,0xc9,0xef,0x7d,0xfa,0xa0,
    0x1d,0x0e,0xc4,0x41,0x86,0x9a,0x94,0x98};
static uint16_t le16(const uint8_t *p){
    return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8u));
}
static uint32_t le32(const uint8_t *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8u)|
           ((uint32_t)p[2]<<16u)|((uint32_t)p[3]<<24u);
}
static int route_cmp(p07_b2_route a,p07_b2_route b){
    if(a.source_core!=b.source_core)
        return a.source_core<b.source_core?-1:1;
    if(a.source_compartment!=b.source_compartment)
        return a.source_compartment<b.source_compartment?-1:1;
    if(a.destination_core!=b.destination_core)
        return a.destination_core<b.destination_core?-1:1;
    if(a.destination_axon!=b.destination_axon)
        return a.destination_axon<b.destination_axon?-1:1;
    return 0;
}
static p07_b2_route read_route(const uint8_t *p){
    p07_b2_route r;
    r.source_core=le16(p);r.source_compartment=le16(p+2u);
    r.destination_core=le16(p+4u);r.destination_axon=le16(p+6u);
    return r;
}
static int checked_image(const uint8_t *p,size_t bytes,const char magic[8],
                         uint32_t size,uint32_t entry,uint32_t *count){
    uint8_t digest[32];size_t i;
    if(!p||bytes!=size||memcmp(p,magic,8u)||
       le32(p+8u)!=1u||le32(p+12u)!=size||
       le32(p+16u)!=27u||le32(p+24u)!=entry||
       le32(p+28u)!=P07_B4M_ROUTE_HEAD||
       memcmp(p+32u,compiled_sha,32u)||
       memcmp(p+64u,cap_sha,32u))
        return P07_B4M_ROUTE_INVALID;
    *count=le32(p+20u);
    if((*count>P07_B2_MAX_ROUTE_BINDINGS && entry==8u)||
       (*count>P07_B2_MAX_ROUTES && entry==6u)||
       (uint64_t)P07_B4M_ROUTE_HEAD+
           (uint64_t)(*count)*entry+
           (entry==8u?P07_B4M_ROUTE_COMP_BYTES:0u)>bytes)
        return P07_B4M_ROUTE_INVALID;
    p07_a2_sha256(p+P07_B4M_ROUTE_HEAD,
                  bytes-P07_B4M_ROUTE_HEAD,digest);
    if(memcmp(digest,p+96u,32u))return P07_B4M_ROUTE_SHA;
    /* Explicit pad zeros: a CRC-valid but hidden unused packet/route row
     * must not escape this physical deployment admission.
     */
    for(i=P07_B4M_ROUTE_HEAD+(size_t)(*count)*entry+
          (entry==8u?P07_B4M_ROUTE_COMP_BYTES:0u);i<bytes;i++)
        if(p[i])return P07_B4M_ROUTE_INVALID;
    return P07_B4M_ROUTE_OK;
}
int p07_b4m_mount_frozen_routes(
    p07_b4m_frozen_binding *out,
    const uint8_t *outimage,size_t outbytes,
    const uint8_t *inimage,size_t inbytes,
    const p03_hw_adapter *hw,
    p07_b2_route *routes,size_t route_capacity,
    uint16_t *comps,size_t comp_capacity){
    uint32_t i,route_count=0u,input_count=0u,total=0u;
    uint32_t unique=0u,prior_pix=UINT32_MAX,prior_core=UINT32_MAX;
    p07_b2_route prior={0};
    p07_b4m_frozen_binding candidate={0};
    if(!out||!outimage||!inimage||!hw||!routes||!comps||
       route_capacity!=P07_B2_MAX_ROUTE_BINDINGS||
       comp_capacity!=27u||hw->last_error!=P03_HW_OK)
        return P07_B4M_ROUTE_INVALID;
    if(checked_image(outimage,outbytes,"B4MROUT1",
                     P07_B4M_ROUTE_OUT_BYTES,8u,&route_count)||
       checked_image(inimage,inbytes,"B4MING01",
                     P07_B4M_ROUTE_IN_BYTES,6u,&input_count))
        return P07_B4M_ROUTE_SHA;
    if(input_count<784u)return P07_B4M_ROUTE_TOPOLOGY;
    for(i=0u;i<27u;i++){
        uint32_t n=le16(outimage+P07_B4M_ROUTE_HEAD+i*2u);
        if(!hw->configured[i]||!n||n>1024u||
           n!=(uint32_t)((hw->metadata[i]>>7u)&UINT64_C(0x7ff)))
            return P07_B4M_ROUTE_TOPOLOGY;
        total+=n;
    }
    for(i=P07_B4M_ROUTE_HEAD+27u*2u;
        i<P07_B4M_ROUTE_HEAD+P07_B4M_ROUTE_COMP_BYTES;i++)
        if(outimage[i]!=0u)return P07_B4M_ROUTE_TOPOLOGY;
    if(total!=1010u||le16(outimage+P07_B4M_ROUTE_HEAD+26u*2u)!=10u)
        return P07_B4M_ROUTE_TOPOLOGY;
    /* Strict source/core/compartment route order, registered target
     * axon, and independently original 27-config P03 metadata.
     */
    for(i=0u;i<route_count;i++){
        p07_b2_route r=read_route(outimage+
            P07_B4M_ROUTE_HEAD+P07_B4M_ROUTE_COMP_BYTES+(size_t)i*8u);
        if(r.source_core>=27u||r.destination_core>=27u||
           r.source_compartment>=le16(outimage+P07_B4M_ROUTE_HEAD+
                 (size_t)r.source_core*2u)||
           r.destination_axon>=4096u||
           !(hw->valid_axons[r.destination_core][r.destination_axon>>3u]&
               (uint8_t)(1u<<(r.destination_axon&7u)))||
           (i&&route_cmp(prior,r)>=0))
            return P07_B4M_ROUTE_TOPOLOGY;
        prior=r;unique|=(uint32_t)1u<<r.destination_core;
    }
    for(i=0u;i<input_count;i++){
        const uint8_t *r=inimage+P07_B4M_ROUTE_HEAD+(size_t)i*6u;
        uint32_t pix=le16(r),core=le16(r+2u),axon=le16(r+4u);
        if(pix>=784u||core>=27u||axon>=4096u||
           !(hw->valid_axons[core][axon>>3u]&
              (uint8_t)(1u<<(axon&7u)))||
           (i&&((pix<prior_pix)||
                 (pix==prior_pix&&core<=prior_core)||
                 (pix>prior_pix+1u))))
            return P07_B4M_ROUTE_TOPOLOGY;
        if(i==0u&&pix!=0u)return P07_B4M_ROUTE_TOPOLOGY;
        prior_pix=pix;prior_core=core;
    }
    if(prior_pix!=783u)return P07_B4M_ROUTE_TOPOLOGY;
    /* Commit caller-owned decoded route array only after the complete
     * immutable original P03 registration and SHA preflight.
     */
    for(i=0u;i<27u;i++)comps[i]=le16(outimage+P07_B4M_ROUTE_HEAD+i*2u);
    for(i=0u;i<route_count;i++)
        routes[i]=read_route(outimage+P07_B4M_ROUTE_HEAD+
                            P07_B4M_ROUTE_COMP_BYTES+(size_t)i*8u);
    candidate.packets.core_count=27u;
    candidate.packets.route_count=route_count;
    candidate.packets.routes=routes;
    candidate.packets.compartments_per_core=comps;
    memcpy(candidate.packets.compiled_sha256,compiled_sha,32u);
    memcpy(candidate.packets.capacity_sha256,cap_sha,32u);
    candidate.inputs.core_count=27u;
    candidate.inputs.route_count=input_count;
    candidate.inputs.trusted_routes=inimage+P07_B4M_ROUTE_HEAD;
    candidate.inputs.trusted_routes_bytes=(size_t)input_count*6u;
    memcpy(candidate.inputs.compiled_sha256,compiled_sha,32u);
    memcpy(candidate.inputs.capacity_sha256,cap_sha,32u);
    candidate.emitted_route_count=route_count;
    candidate.input_route_count=input_count;
    candidate.unique_registered_destinations=unique;
    *out=candidate;
    return P07_B4M_ROUTE_OK;
}
