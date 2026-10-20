#include "p07_b3c3_next_commit.h"
#include <string.h>
_Static_assert(P07_B3_CORES==27u,"B3c3 requires exact 27 context runtime");
_Static_assert(P03_HW_EVENT0_OFFSET==UINT32_C(0x54000),"P03 event0 drift");
_Static_assert(P03_HW_EVENT1_OFFSET==UINT32_C(0x58000),"P03 event1 drift");
_Static_assert(P03_HW_EVENT_DEPTH==4096u,"P03 event bank depth drift");
_Static_assert(P03_HW_EVENT1_OFFSET+4096u*4u<=P03_HW_RECORD_BYTES,
               "P03 event1 overlaps DDR record end");
static uint16_t le16(const uint8_t *p){
    return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
}
static uint32_t crc32(const uint8_t *p,size_t n){
    uint32_t c=UINT32_C(0xffffffff),bit;size_t i;
    for(i=0u;i<n;i++){
        c^=p[i];for(bit=0u;bit<8u;bit++)
            c=(c>>1u)^((c&1u)?UINT32_C(0xedb88320):0u);
    }
    return ~c;
}
static int poison(p07_b3c3_plan *p,uint32_t stage){
    if(!p)return P07_B3C3_INVALID;
    if(!p->poisoned)p->first_fault=stage;
    p->poisoned=1u;p->admitted=0u;
    if(p->pager&&!p->pager->failed){
        p07_b3_op op;
        if(p07_b3_next(p->pager,&op)==P07_B3_OK)
            (void)p07_b3_ack(p->pager,&op,0);
        else p->pager->failed=1u;
    }
    return P07_B3C3_FAULTED;
}
static int resident(const p07_b3_pager *p,uint32_t id){
    uint32_t i;
    for(i=0u;i<P07_B3_SLOTS;i++)
        if(p->resident[i]==(int32_t)id)return (int)i;
    return -1;
}
int p07_b3c3_prepare(p07_b3c3_plan *out,p07_b3_pager *pager,
    p03_hw_adapter *hw,const p07_b2_packet_binding *binding,
    const uint8_t *frame,size_t bytes,const uint16_t (*spikes)[2],
    size_t nspikes){
    p07_b2_packet_view decoded={0};
    uint32_t destinations[P07_B3_CORES]={0},core,i;
    p07_b3_op op;
    static const uint16_t empty[1][2]={{0u,0u}};
    p07_b3c3_plan tmp={0};
    if(!out||!pager||!hw||!binding||!frame||
       (nspikes&&!spikes)||binding->core_count!=P07_B3_CORES||
       pager->failed||hw->last_error!=P03_HW_OK||
       pager->tick>=P07_B3_TICKS||!pager->has_pending||
       pager->cursor!=P07_B3_CORES ||
       p07_b3_next(pager,&op)!=P07_B3_OK||
       op.kind!=P07_B3_BARRIER||op.tick!=pager->tick)
        return P07_B3C3_INVALID;
    if(p07_b2_packet_decode(frame,bytes,binding,pager->tick,
                            spikes?spikes:empty,nspikes,&decoded)!=P07_B2_OK)
        return P07_B3C3_PRECHECK;
    if(p03_hw_quiescent(hw)!=P03_HW_OK)return P07_B3C3_PRECHECK;
    for(core=0u;core<P07_B3_CORES;core++){
        if(!hw->configured[core] ||
           hw->event_counts[core][op.current_bank]!=0u||
           hw->event_counts[core][op.next_bank]!=0u)
            return P07_B3C3_PRECHECK;
    }
    for(i=0u;i<decoded.packet_count;i++){
        const uint8_t *p=decoded.packets+(size_t)i*12u;
        uint32_t dest=le16(p+8u),axon=le16(p+10u);
        if(dest>=P07_B3_CORES||axon>=4096u||
           (hw->valid_axons[dest][axon>>3u] &
            (uint8_t)(1u<<(axon&7u)))==0u ||
           ++destinations[dest]>P03_HW_EVENT_DEPTH)
            return P07_B3C3_PRECHECK;
    }
    tmp.wire=frame;tmp.wire_bytes=bytes;
    tmp.pager=pager;tmp.hw=hw;
    tmp.tick=pager->tick;tmp.bank=op.next_bank;
    tmp.packet_count=decoded.packet_count;
    tmp.frame_crc=crc32(frame,bytes);
    memcpy(tmp.destination_count,destinations,sizeof(destinations));
    tmp.admitted=1u;
    *out=tmp;return P07_B3C3_OK;
}
int p07_b3c3_commit(p07_b3c3_plan *p,p07_b3c3_receipt *receipt){
    uint32_t i,counts[P07_B3_CORES]={0};
    p07_b3_op current;
    if(!p||!receipt)return P07_B3C3_INVALID;
    if(p->poisoned||!p->admitted||p->attempted||
       !p->pager||!p->hw||p->pager->failed||
       p->hw->last_error!=P03_HW_OK)return P07_B3C3_FAULTED;
    p->attempted=1u;
    if(p07_b3_next(p->pager,&current)!=P07_B3_OK ||
       current.kind!=P07_B3_BARRIER||current.tick!=p->tick||
       current.next_bank!=p->bank ||
       crc32(p->wire,p->wire_bytes)!=p->frame_crc ||
       p03_hw_quiescent(p->hw)!=P03_HW_OK)return poison(p,1u);
    for(i=0u;i<P07_B3_CORES;i++)
        if(p->hw->event_counts[i][current.current_bank]!=0u||
           p->hw->event_counts[i][p->bank]!=0u)
            return poison(p,2u);
    for(i=0u;i<p->packet_count;i++){
        const uint8_t *packet=p->wire+128u+(size_t)i*12u;
        uint32_t dest=le16(packet+8u),axon=le16(packet+10u);
        uint32_t cursor;
        int slot;
        if(dest>=P07_B3_CORES||axon>=4096u)return poison(p,3u);
        cursor=counts[dest]++;
        if(cursor>=p->destination_count[dest]||
           cursor!=p->hw->event_counts[dest][p->bank])
            return poison(p,4u);
        slot=resident(p->pager,dest);
        if(slot>=0){
            uint32_t word[8]={0};
            word[0]=axon;
            if(p03_hw_debug_word(p->hw,(uint8_t)slot,
                 p->bank ? P03_HW_EVENT1_DEBUG_BANK :
                           P03_HW_EVENT0_DEBUG_BANK,
                 (uint16_t)cursor,1,word)!=P03_HW_OK)
                return poison(p,5u);
            /* Resident packet event changes the victim's mutable event
             * bank, even if that core was not dispatched this epoch. */
            p->pager->dirty[slot]=1u;
        }else{
            uint64_t addr=P03_HW_BACKING_BASE+
                (uint64_t)dest*P03_HW_RECORD_BYTES+
                (p->bank ? P03_HW_EVENT1_OFFSET:P03_HW_EVENT0_OFFSET)+
                (uint64_t)cursor*4u;
            if(!p->hw->io.store_ddr32 ||
               !p->hw->io.clean_range || !p->hw->io.barrier ||
               p->hw->io.store_ddr32(p->hw->cookie,addr,axon)!=0)
                return poison(p,6u);
            if(p->hw->io.clean_range(p->hw->cookie,addr,4u)!=0)
                return poison(p,7u);
            p->hw->io.barrier(p->hw->cookie);
        }
        p->hw->event_counts[dest][p->bank]=(uint16_t)(cursor+1u);
    }
    for(i=0u;i<P07_B3_CORES;i++)
        if(counts[i]!=p->destination_count[i])
            return poison(p,8u);
    if(p03_hw_quiescent(p->hw)!=P03_HW_OK)return poison(p,9u);
    {
        p07_b3c3_receipt result={0};
        result.magic=P07_B3C3_RECEIPT_MAGIC;
        result.tick=p->tick;result.bank=p->bank;
        result.inserted_count=p->packet_count;
        result.frame_crc=p->frame_crc;
        result.source_packet_count=p->packet_count;
        *receipt=result;
    }
    p->admitted=0u;
    return P07_B3C3_OK;
}
