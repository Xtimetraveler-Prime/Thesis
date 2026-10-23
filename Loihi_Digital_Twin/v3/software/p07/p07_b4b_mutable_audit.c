#include "p07_b4b_mutable_audit.h"
#include <string.h>
typedef struct {uint32_t start,bytes;} region;
static const region sections[P07_B4B_MUTABLE_SECTIONS]={
    {UINT32_C(0x05000),UINT32_C(0x02000)}, /* signed24 neuron state */
    {P03_HW_EVENT0_OFFSET,UINT32_C(0x04000)},
    {P03_HW_EVENT1_OFFSET,UINT32_C(0x04000)},
    {UINT32_C(0x5C000),UINT32_C(0x08000)}, /* trace words */
    {UINT32_C(0x64000),UINT32_C(0x08000)}  /* packet words */
};
_Static_assert(P03_HW_MUTABLE_BYTES==
    (0x2000u+0x4000u+0x4000u+0x8000u+0x8000u),
    "original P03 mutable byte count drift");
_Static_assert(0x64000u+0x8000u <=P03_HW_RECORD_BYTES,
               "P02 last mutable section escapes physical record");
static uint32_t byte_crc(uint32_t v,uint8_t byte){
    uint32_t bit;v^=byte;
    for(bit=0u;bit<8u;bit++)
        v=(v>>1u)^((v&1u)?UINT32_C(0xedb88320):0u);
    return v;
}
int p07_b4b_audit_mutable(const p07_b4b_expected_mutable *expected,
    p03_hw_adapter *hw,const p07_b3_pager *pager,
    p07_b4b_read_phys32 read_phys,void *ctx,
    p07_b4b_mutable_receipt *out,uint64_t *first_bad){
    p07_b4b_mutable_receipt proposed={0};
    uint32_t core,section,k,bit;
    uint32_t tuple_crc=UINT32_C(0xffffffff);
    if(!expected||!hw||!pager||!read_phys||!ctx||!out||
       hw->backing_base!=P03_HW_BACKING_BASE||
       hw->last_error!=P03_HW_OK||pager->failed||pager->tick!=0u||
       pager->cursor!=0u||pager->ordinal!=0u||pager->has_pending)
        return P07_B4B_AUDIT_ARG;
    for(core=0u;core<P07_B3_SLOTS;core++)
        if(pager->resident[core]>=0||pager->dirty[core])
            return P07_B4B_AUDIT_NOT_IDLE;
    for(core=0u;core<P07_B3_CORES;core++)
        if(!hw->configured[core] ||
           hw->event_counts[core][0]!=0u ||
           hw->event_counts[core][1]!=0u)
            return P07_B4B_AUDIT_NOT_IDLE;
    if(p03_hw_quiescent(hw)!=P03_HW_OK)return P07_B4B_AUDIT_NOT_IDLE;
    for(core=0u;core<P07_B3_CORES;core++){
        const uint64_t base=P03_HW_BACKING_BASE+
            (uint64_t)core*P03_HW_RECORD_BYTES;
        for(section=0u;section<P07_B4B_MUTABLE_SECTIONS;section++){
            uint64_t start=base+sections[section].start;
            uint32_t bytes=sections[section].bytes;
            uint32_t crc=UINT32_C(0xffffffff);
            if(!hw->io.invalidate_range||!hw->io.barrier ||
               hw->io.invalidate_range(hw->cookie,start,bytes)!=0)
                return P07_B4B_AUDIT_IO;
            hw->io.barrier(hw->cookie);
            for(k=0u;k<bytes;k+=4u){
                uint32_t word=0u;
                if(read_phys(ctx,start+k,&word)!=0){
                    if(first_bad)*first_bad=start+k;
                    return P07_B4B_AUDIT_IO;
                }
                for(bit=0u;bit<4u;bit++)
                    crc=byte_crc(crc,(uint8_t)(word>>(8u*bit)));
            }
            crc=~crc;
            if(crc!=expected->expected_crc[core][section]){
                if(first_bad)*first_bad=start;
                return P07_B4B_AUDIT_MISMATCH;
            }
            for(bit=0u;bit<4u;bit++)
                tuple_crc=byte_crc(tuple_crc,(uint8_t)(crc>>(8u*bit)));
            ++proposed.checked_regions;proposed.inspected_bytes+=bytes;
        }
        ++proposed.checked_cores;
    }
    if(p03_hw_quiescent(hw)!=P03_HW_OK)return P07_B4B_AUDIT_NOT_IDLE;
    proposed.digest_crc=~tuple_crc;
    *out=proposed;
    if(first_bad)*first_bad=0u;
    return P07_B4B_AUDIT_OK;
}
