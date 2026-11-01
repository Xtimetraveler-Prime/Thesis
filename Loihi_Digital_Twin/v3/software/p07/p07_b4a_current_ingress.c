#include "p07_b4a_current_ingress.h"
#include <string.h>
_Static_assert(P07_B4A_CORES==27u,"P07 physical deployment must have exactly 27 cores");
_Static_assert(P07_B4A_DEPTH==4096u,"P03 event bank depth drift");
_Static_assert(P03_HW_EVENT0_OFFSET==0x54000u && P03_HW_EVENT1_OFFSET==0x58000u,
               "P02 event bank offsets drift");
_Static_assert(P03_HW_BACKING_BASE==UINT64_C(0x40000000),"P03 DDR owner drift");
static uint16_t get16(const uint8_t *p){
    return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
}
static uint32_t crc32(const uint8_t *p,size_t bytes){
    uint32_t value=UINT32_C(0xffffffff),bit;size_t i;
    for(i=0u;i<bytes;i++){
        value^=p[i];
        for(bit=0u;bit<8u;bit++)
            value=(value>>1u)^((value&1u)?UINT32_C(0xedb88320):0u);
    }return ~value;
}
static uint32_t words_crc(const uint32_t *words,const uint32_t *count){
    uint32_t value=UINT32_C(0xffffffff),c,j,k;
    for(c=0u;c<P07_B4A_CORES;c++)
        for(j=0u;j<count[c];j++){
            uint32_t word=words[(size_t)c*P07_B4A_DEPTH+j];
            for(k=0u;k<4u;k++){
                uint32_t b;value^=(uint8_t)(word>>(8u*k));
                for(b=0u;b<8u;b++)
                    value=(value>>1u)^((value&1u)?UINT32_C(0xedb88320):0u);
            }
        }
    return ~value;
}
static int disjoint(const void *a,size_t na,const void *b,size_t nb){
    uintptr_t x=(uintptr_t)a,y=(uintptr_t)b;
    if(!a||!b||na>UINTPTR_MAX-x||nb>UINTPTR_MAX-y)return 0;
    return x+na<=y || y+nb<=x;
}
static int resident(const p07_b3_pager *p,uint32_t core){
    uint32_t i;
    for(i=0u;i<P07_B3_SLOTS;i++)
        if(p->resident[i]==(int32_t)core)return (int)i;
    return -1;
}
static int fired(uint8_t value,uint32_t pixel,uint32_t tick){
    uint32_t phase;
    if(tick==P07_B2_INPUT_TICKS)return 0;
    phase=(tick+17u*pixel)%P07_B2_INPUT_TICKS;
    return ((phase+1u)*(uint32_t)value)/255u >
           (phase*(uint32_t)value)/255u;
}
static void swap(uint32_t *a,uint32_t *b){uint32_t t=*a;*a=*b;*b=t;}
static void sort(uint32_t *a,uint32_t n){
    uint32_t i,k;
    for(i=n/2u;i>0u;){
        uint32_t root=--i;
        while(root*2u+1u<n){
            uint32_t child=root*2u+1u;
            if(child+1u<n && a[child]<a[child+1u])++child;
            if(a[root]>=a[child])break;
            swap(&a[root],&a[child]);root=child;
        }
    }
    for(k=n;k>1u;){
        uint32_t root=0u,end=--k;
        swap(&a[0],&a[end]);
        while(root*2u+1u<end){
            uint32_t child=root*2u+1u;
            if(child+1u<end && a[child]<a[child+1u])++child;
            if(a[root]>=a[child])break;
            swap(&a[root],&a[child]);root=child;
        }
    }
}
static int poison(p07_b4a_plan *p,uint32_t stage){
    if(!p)return P07_B4A_ARGUMENT;
    if(!p->poisoned)p->first_failure=stage;
    p->poisoned=1u;p->prepared=0u;
    if(p->pager && !p->pager->failed){
        p07_b3_op op;
        if(p07_b3_next(p->pager,&op)==P07_B3_OK)
            (void)p07_b3_ack(p->pager,&op,0);
        else p->pager->failed=1u;
    }
    return P07_B4A_POISONED;
}
int p07_b4a_prepare(p07_b4a_plan *out,p07_b3_pager *pager,
    p03_hw_adapter *hw,const p07_b2_ingress_binding *binding,
    const uint8_t *wire,size_t wire_bytes,
    uint32_t *words,size_t capacity,
    p07_b4a_read_ddr32 read_ddr,void *reader){
    p07_b2_ingress_view view={0};
    p07_b4a_plan candidate={0};
    uint32_t core,i,old_counts[P07_B4A_CORES]={0};
    uint32_t merged[P07_B4A_CORES]={0},input_counts[P07_B4A_CORES]={0};
    uint32_t total_prior=0u,total_external=0u,tick,bank;
    if(!out||!pager||!hw||!binding||!wire||!words||!read_ddr||!reader||
       capacity!=P07_B4A_WORD_CAPACITY ||
       pager->failed||hw->last_error!=P03_HW_OK ||
       pager->tick>=P07_B3_TICKS || pager->cursor!=0u||
       pager->stage!=0u || pager->has_pending ||
       !disjoint(out,sizeof(*out),words,capacity*sizeof(*words))||
       !disjoint(wire,wire_bytes,words,capacity*sizeof(*words))||
       !disjoint(hw,sizeof(*hw),words,capacity*sizeof(*words))||
       !disjoint(pager,sizeof(*pager),words,capacity*sizeof(*words))||
       !disjoint(binding,sizeof(*binding),words,capacity*sizeof(*words)))
        return P07_B4A_ARGUMENT;
    if(p07_b2_decode_ingress(wire,wire_bytes,binding,&view)!=P07_B2_OK ||
       view.core_count!=P07_B4A_CORES || hw->backing_base!=P03_HW_BACKING_BASE ||
       p03_hw_quiescent(hw)!=P03_HW_OK)return P07_B4A_REJECT;
    tick=pager->tick;bank=tick&1u;
    for(core=0u;core<P07_B4A_CORES;core++){
        int slot=resident(pager,core);
        uint32_t old=hw->event_counts[core][bank],idx;
        if(!hw->configured[core]||hw->event_counts[core][1u-bank]!=0u||
           old>P07_B4A_DEPTH)return P07_B4A_REJECT;
        old_counts[core]=old;merged[core]=old;total_prior+=old;
        if(slot<0 && old>0u){
            uint64_t addr=P03_HW_BACKING_BASE+
                (uint64_t)core*P03_HW_RECORD_BYTES+
                (bank?P03_HW_EVENT1_OFFSET:P03_HW_EVENT0_OFFSET);
            if(!hw->io.invalidate_range||!hw->io.barrier||
               hw->io.invalidate_range(hw->cookie,addr,old*4u)!=0)
                return P07_B4A_REJECT;
            hw->io.barrier(hw->cookie);
        }
        for(idx=0u;idx<old;idx++){
            uint32_t axon=0u;
            if(slot>=0){
                uint32_t data[8]={0};
                if(p03_hw_debug_word(hw,(uint8_t)slot,
                   bank?P03_HW_EVENT1_DEBUG_BANK:P03_HW_EVENT0_DEBUG_BANK,
                   (uint16_t)idx,0,data)!=P03_HW_OK)
                    return P07_B4A_REJECT;
                axon=data[0];
            }else{
                uint64_t address=P03_HW_BACKING_BASE+
                    (uint64_t)core*P03_HW_RECORD_BYTES+
                    (bank?P03_HW_EVENT1_OFFSET:P03_HW_EVENT0_OFFSET)+
                    (uint64_t)idx*4u;
                if(read_ddr(reader,address,&axon)!=0)
                    return P07_B4A_REJECT;
            }
            if(axon>=P07_B4A_DEPTH ||
               !(hw->valid_axons[core][axon>>3u] &
                (uint8_t)(1u<<(axon&7u))))
                return P07_B4A_REJECT;
            words[(size_t)core*P07_B4A_DEPTH+idx]=axon;
        }
    }
    /* Full 27-core capacity and registered-axon preflight before any writes. */
    for(i=0u;i<view.route_count;i++){
        const uint8_t *p=view.routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pix=get16(p),dest=get16(p+2u),axon=get16(p+4u);
        if(pix>=784u||dest>=P07_B4A_CORES||axon>=P07_B4A_DEPTH)
            return P07_B4A_REJECT;
        if(fired(view.pixels[pix],pix,tick)){
            if(!(hw->valid_axons[dest][axon>>3u] &
                 (uint8_t)(1u<<(axon&7u)))||
               merged[dest]>=P07_B4A_DEPTH)
                return P07_B4A_REJECT;
            words[(size_t)dest*P07_B4A_DEPTH+merged[dest]++]=axon;
            ++input_counts[dest];++total_external;
        }
    }
    for(core=0u;core<P07_B4A_CORES;core++)
        sort(words+(size_t)core*P07_B4A_DEPTH,merged[core]);
    candidate.pager=pager;candidate.hw=hw;candidate.immutable_wire=wire;
    candidate.wire_bytes=wire_bytes;candidate.words=words;
    candidate.word_capacity=(uint32_t)capacity;candidate.tick=tick;
    candidate.current_bank=bank;candidate.wire_crc=crc32(wire,wire_bytes);
    candidate.merged_crc=words_crc(words,merged);
    candidate.prior_total=total_prior;candidate.external_total=total_external;
    candidate.final_total=total_prior+total_external;
    memcpy(candidate.prior_by_core,old_counts,sizeof(old_counts));
    memcpy(candidate.final_by_core,merged,sizeof(merged));
    memcpy(candidate.external_by_core,input_counts,sizeof(input_counts));
    candidate.prepared=1u;
    *out=candidate;
    return P07_B4A_OK;
}
int p07_b4a_commit(p07_b4a_plan *p,p07_b4a_receipt *out){
    uint32_t core,idx,bank;
    if(!p||!out)return P07_B4A_ARGUMENT;
    if(p->poisoned||!p->prepared||p->attempted||
       !p->pager||!p->hw||!p->words||!p->immutable_wire||
       p->pager->failed)return P07_B4A_POISONED;
    p->attempted=1u;bank=p->current_bank;
    if(p->pager->tick!=p->tick||p->pager->cursor!=0u||
       p->pager->stage!=0u||p->pager->has_pending ||
       p->hw->last_error!=P03_HW_OK ||
       crc32(p->immutable_wire,p->wire_bytes)!=p->wire_crc ||
       words_crc(p->words,p->final_by_core)!=p->merged_crc ||
       p03_hw_quiescent(p->hw)!=P03_HW_OK)
        return poison(p,1u);
    for(core=0u;core<P07_B4A_CORES;core++){
        if(!p->hw->configured[core]||
           p->hw->event_counts[core][bank]!=p->prior_by_core[core]||
           p->hw->event_counts[core][1u-bank]!=0u ||
           p->final_by_core[core]>P07_B4A_DEPTH)
            return poison(p,2u);
    }
    for(core=0u;core<P07_B4A_CORES;core++){
        int slot=resident(p->pager,core);
        uint32_t n=p->final_by_core[core];
        for(idx=0u;idx<n;idx++){
            uint32_t axon=p->words[(size_t)core*P07_B4A_DEPTH+idx];
            if(axon>=P07_B4A_DEPTH)return poison(p,3u);
            if(slot>=0){
                uint32_t data[8]={0};data[0]=axon;
                if(p03_hw_debug_word(p->hw,(uint8_t)slot,
                    bank?P03_HW_EVENT1_DEBUG_BANK:P03_HW_EVENT0_DEBUG_BANK,
                    (uint16_t)idx,1,data)!=P03_HW_OK)
                    return poison(p,4u);
                p->pager->dirty[slot]=1u;
            }else{
                uint64_t physical=P03_HW_BACKING_BASE+
                    (uint64_t)core*P03_HW_RECORD_BYTES+
                    (bank?P03_HW_EVENT1_OFFSET:P03_HW_EVENT0_OFFSET)+
                    (uint64_t)idx*4u;
                if(!p->hw->io.store_ddr32||
                   !p->hw->io.clean_range||!p->hw->io.barrier||
                   p->hw->io.store_ddr32(p->hw->cookie,physical,axon)!=0)
                    return poison(p,5u);
                if(p->hw->io.clean_range(p->hw->cookie,physical,4u)!=0)
                    return poison(p,6u);
                p->hw->io.barrier(p->hw->cookie);
            }
        }
        p->hw->event_counts[core][bank]=(uint16_t)n;
    }
    if(p03_hw_quiescent(p->hw)!=P03_HW_OK)return poison(p,7u);
    {
        p07_b4a_receipt receipt={0};
        receipt.tick=p->tick;receipt.bank=bank;
        receipt.prior_total=p->prior_total;
        receipt.external_total=p->external_total;
        receipt.current_total=p->final_total;
        receipt.merged_crc=p->merged_crc;
        memcpy(receipt.current_by_core,p->final_by_core,
               sizeof(receipt.current_by_core));
        *out=receipt;
    }
    p->prepared=0u;
    return P07_B4A_OK;
}
