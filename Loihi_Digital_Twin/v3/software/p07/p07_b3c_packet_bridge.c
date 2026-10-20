#include "p07_b3c_packet_bridge.h"
#include <stdlib.h>
#include <string.h>
_Static_assert(P07_B3C_MAX_RAW_WORDS==8192u,"B2b routing ceiling drift");
_Static_assert(P07_B3C_MAX_FRAME_BYTES==98432u,"bounded frame size drift");
static uint16_t r16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
}
static void put16(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
}
static void put32(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
    p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);
}
static uint32_t crc(const uint8_t *p,size_t n,int is_header) {
    uint32_t value=UINT32_C(0xffffffff),i;size_t pos;
    for(pos=0u;pos<n;pos++){
        value^=(is_header&&pos>=52u&&pos<56u)?0u:p[pos];
        for(i=0u;i<8u;i++)
            value=(value>>1u)^((value&1u)?UINT32_C(0xedb88320):0u);
    }
    return ~value;
}
static int overlap(const void *a,size_t an,const void *b,size_t bn) {
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    if(!a||!b||!an||!bn)return 0;
    if(an>UINTPTR_MAX-x||bn>UINTPTR_MAX-y)return 1;
    return x<y+bn && y<x+an;
}
static int record_compare(const void *lhs,const void *rhs) {
    const uint8_t *a=(const uint8_t *)lhs,*b=(const uint8_t *)rhs;
    uint16_t ao=r16(a+8u),bo=r16(b+8u),aa=r16(a+10u),ba=r16(b+10u);
    uint16_t as=r16(a+4u),bs=r16(b+4u),ac=r16(a+6u),bc=r16(b+6u);
    if(ao!=bo)return ao<bo?-1:1;
    if(aa!=ba)return aa<ba?-1:1;
    if(as!=bs)return as<bs?-1:1;
    if(ac!=bc)return ac<bc?-1:1;
    return 0;
}
int p07_b3c_p03_reader(void *ctx,uint8_t slot,uint16_t index,uint64_t *word){
    if(!ctx||!word)return P07_B3C_BAD_ARGUMENT;
    return p03_hw_read_packet((p03_hw_adapter *)ctx,slot,index,word)==P03_HW_OK ?
        P07_B3C_OK : P07_B3C_READ_ERROR;
}
int p07_b3c_capture_core(p07_b3c_capture *cap,uint32_t source_core,
    uint8_t slot,uint32_t emitted,uint64_t *workspace,
    size_t workspace_words,p07_b3c_packet_reader reader,void *ctx){
    uint32_t i;
    if(!cap||!reader||!ctx||!workspace||
       source_core>=P07_B3C_MAX_CORES||
       slot>=P03_RT_MAX_SLOTS||cap->core_count>P07_B3C_MAX_CORES||
       cap->word_count>P07_B3C_MAX_RAW_WORDS ||
       overlap(workspace,workspace_words*sizeof(*workspace),
               cap->words,sizeof(cap->words)))return P07_B3C_BAD_ARGUMENT;
    if(source_core!=cap->core_count)return P07_B3C_BAD_ARGUMENT;
    if(emitted>P03_RT_MAX_PACKETS || emitted>workspace_words ||
       emitted>P07_B3C_MAX_RAW_WORDS-cap->word_count)return P07_B3C_CAPACITY;
    /* A failed actual PL read may latch the P03 adapter error, but neither
     * the accepted raw words nor the committed capture count is modified. */
    for(i=0u;i<emitted;i++)
        if(reader(ctx,slot,(uint16_t)i,&workspace[i])!=0)
            return P07_B3C_READ_ERROR;
    memcpy(&cap->words[cap->word_count],workspace,(size_t)emitted*sizeof(*workspace));
    cap->count[source_core]=emitted;
    cap->word_count+=emitted;
    ++cap->core_count;
    return P07_B3C_OK;
}
int p07_b3c_encode_frame(const p07_b3c_core_words *cores,
    size_t core_count,uint32_t tick,const p07_b2_packet_binding *binding,
    const uint16_t (*spikes)[2],size_t spike_count,
    uint8_t *scratch,size_t scratch_capacity,
    uint8_t *frame,size_t capacity,size_t *frame_bytes) {
    static const uint8_t magic[8]={'P','0','6','B','1','3','R','1'};
    uint32_t n=0u;size_t core,j,bytes;
    uint8_t *payload; p07_b2_packet_view decoded={0};
    static const uint16_t empty[1][2]={{0u,0u}};
    if(!cores||!binding||!scratch||!frame||!frame_bytes||
       !binding->routes||!binding->compartments_per_core||
       core_count==0u||core_count>P07_B3C_MAX_CORES||
       core_count!=binding->core_count||tick>=P07_B2_TOTAL_TICKS||
       (spike_count&&!spikes))return P07_B3C_BAD_ARGUMENT;
    if(overlap(frame,capacity,scratch,scratch_capacity) ||
       overlap(frame,capacity,binding->routes,
               (size_t)binding->route_count*sizeof(*binding->routes)) ||
       overlap(scratch,scratch_capacity,binding->routes,
               (size_t)binding->route_count*sizeof(*binding->routes)))
        return P07_B3C_BAD_ARGUMENT;
    for(core=0u;core<core_count;core++){
        if(cores[core].source_core!=core||
           cores[core].slot>=P03_RT_MAX_SLOTS||
           (cores[core].packet_count&&!cores[core].words))
            return P07_B3C_BAD_ARGUMENT;
        if(cores[core].packet_count>P03_RT_MAX_PACKETS||
           cores[core].packet_count>P07_B3C_MAX_RAW_WORDS-n)
            return P07_B3C_CAPACITY;
        n+=cores[core].packet_count;
    }
    bytes=128u+(size_t)n*12u;
    if(bytes>scratch_capacity || bytes>capacity)
        return P07_B3C_CAPACITY;
    memset(scratch,0,128u);
    memcpy(scratch,magic,8u);
    put32(scratch+8u,1u);put32(scratch+12u,128u);
    put32(scratch+16u,n*12u);put32(scratch+20u,tick);
    put32(scratch+24u,n);put32(scratch+28u,(uint32_t)core_count);
    put32(scratch+32u,12u);put32(scratch+36u,4096u);
    memcpy(scratch+64u,binding->compiled_sha256,32u);
    memcpy(scratch+96u,binding->capacity_sha256,32u);
    payload=scratch+128u;n=0u;
    for(core=0u;core<core_count;core++)
        for(j=0u;j<cores[core].packet_count;j++){
            uint64_t word=cores[core].words[j];
            uint32_t target=(uint32_t)((word>>29u)&UINT64_C(0xffffffff));
            uint32_t dest=(uint32_t)(word&UINT64_C(0x7f));
            uint32_t axon=(uint32_t)((word>>7u)&UINT64_C(0xfff));
            uint32_t source=(uint32_t)((word>>19u)&UINT64_C(0x3ff));
            uint8_t *p=payload+12u*(size_t)n;
            if((word&(UINT64_C(1)<<61u))==0u||word>>62u||
               target!=tick+1u||dest>=core_count||
               axon>=4096u||source>=binding->compartments_per_core[core])
                return P07_B3C_BAD_FRAME;
            put32(p,target);put16(p+4u,(uint32_t)core);
            put16(p+6u,source);put16(p+8u,dest);put16(p+10u,axon);
            ++n;
        }
    /* B1.3 sorts by dest then axon then source core+compartment. Sorting
     * the 12-byte packed records is independent of host endianness. */
    qsort(payload,n,12u,record_compare);
    put32(scratch+48u,crc(payload,(size_t)n*12u,0));
    put32(scratch+52u,crc(scratch,128u,1));
    if(p07_b2_packet_decode(scratch,bytes,binding,tick,
                            spikes?spikes:empty,spike_count,&decoded)!=P07_B2_OK)
        return P07_B3C_B13_REJECT;
    if(decoded.packet_count!=n||decoded.emitted_tick!=tick)
        return P07_B3C_B13_REJECT;
    /* The complete frame is now accepted; no failure after these writes. */
    memcpy(frame,scratch,bytes);
    *frame_bytes=bytes;
    return P07_B3C_OK;
}
