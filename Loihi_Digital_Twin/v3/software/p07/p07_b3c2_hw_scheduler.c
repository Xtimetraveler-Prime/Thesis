#include "p07_b3c2_hw_scheduler.h"
#include <string.h>
_Static_assert(P07_B3_CORES==27u,"frozen logical core count");
static int fail(p07_b3c2_hw_scheduler *s,uint32_t stage){
    if(!s)return P07_B3C2_INVALID;
    if(!s->poisoned)s->first_fault=stage;
    s->poisoned=1u;
    if(s->pager && !s->pager->failed){
        p07_b3_op pending;
        if(p07_b3_next(s->pager,&pending)==P07_B3_OK)
            (void)p07_b3_ack(s->pager,&pending,0);
        else s->pager->failed=1u;
    }
    return P07_B3C2_FAULTED;
}
static int no_overlap(const void *p,size_t count,const void *q,size_t bytes){
    uintptr_t a=(uintptr_t)p,b=(uintptr_t)q;
    if(!p||!q)return 0;
    if(count>UINTPTR_MAX-a||bytes>UINTPTR_MAX-b)return 0;
    return (a+count<=b || b+bytes<=a);
}
int p07_b3c2_init(p07_b3c2_hw_scheduler *s,p07_b3_pager *pager,
    p03_hw_adapter *hw,uint64_t *words,size_t word_capacity,
    uint64_t *scratch,size_t scratch_capacity){
    uint32_t core;
    if(!s||!pager||!hw||!words||!scratch||
       pager->failed||pager->tick!=0u||pager->ordinal!=0u||
       pager->has_pending||hw->last_error!=P03_HW_OK||
       hw->backing_base!=P03_HW_BACKING_BASE||
       word_capacity!=P07_B3C_MAX_RAW_WORDS||
       scratch_capacity!=P03_RT_MAX_PACKETS||
       !no_overlap(words,word_capacity*sizeof(*words),
                   scratch,scratch_capacity*sizeof(*scratch))||
       !no_overlap(s,sizeof(*s),words,word_capacity*sizeof(*words))||
       !no_overlap(s,sizeof(*s),scratch,scratch_capacity*sizeof(*scratch)))
        return P07_B3C2_INVALID;
    for(core=0u;core<P07_B3_CORES;core++)
        if(!hw->configured[core])return P07_B3C2_INVALID;
    if(p03_hw_identify(hw)!=P03_HW_OK ||
       p03_hw_quiescent(hw)!=P03_HW_OK)return P07_B3C2_INVALID;
    memset(s,0,sizeof(*s));
    s->pager=pager;s->hw=hw;s->raw_words=words;s->raw_capacity=word_capacity;
    s->temporary=scratch;s->temporary_capacity=scratch_capacity;
    for(core=0u;core<P07_B3_CORES;core++) {
        s->cores[core].source_core=(uint8_t)core;
        s->cores[core].slot=0u;
        s->cores[core].words=words; /* updated after each dispatch */
    }
    return P07_B3C2_OK;
}
int p07_b3c2_step(p07_b3c2_hw_scheduler *s,p07_b3_op *op){
    int rc;uint32_t emitted=0u,i;
    uint64_t cycles=0u;
    if(!s||!op||!s->pager||!s->hw)return P07_B3C2_INVALID;
    if(s->poisoned||s->pager->failed||s->hw->last_error!=P03_HW_OK)
        return fail(s,1u);
    rc=p07_b3_next(s->pager,op);
    if(rc==P07_B3_DONE)return P07_B3C2_DONE;
    if(rc!=P07_B3_OK)return fail(s,2u);
    if(op->kind==P07_B3_BARRIER)return P07_B3C2_BARRIER;
    if(op->core>=P07_B3_CORES||op->slot>=P07_B3_SLOTS ||
       op->current_bank!=(op->tick&1u))return fail(s,3u);
    if(p03_hw_quiescent(s->hw)!=P03_HW_OK)return fail(s,4u);
    if(op->kind==P07_B3_PAGE_IN)
        rc=p03_hw_page(s->hw,(uint8_t)op->core,(uint8_t)op->slot,0,0,&cycles);
    else if(op->kind==P07_B3_PAGE_OUT || op->kind==P07_B3_FINAL_FLUSH)
        rc=p03_hw_page(s->hw,(uint8_t)op->core,(uint8_t)op->slot,1,1,&cycles);
    else if(op->kind==P07_B3_DISPATCH){
        if(op->tick>=P07_B3_TICKS ||
           s->pager->resident[op->slot]!=(int32_t)op->core ||
           s->cores[op->core].packet_count!=0u)return fail(s,5u);
        rc=p03_hw_dispatch(s->hw,(uint8_t)op->core,(uint8_t)op->slot,
                           op->tick,(uint8_t)op->current_bank,
                           &emitted,&cycles);
        if(rc==P03_HW_OK){
            if(emitted>P03_RT_MAX_PACKETS ||
               emitted>s->raw_capacity-s->word_count)return fail(s,6u);
            /* PL packet bank only holds this source's last dispatch. Do
             * not run another dispatch before all emitted words are read. */
            if(p03_hw_quiescent(s->hw)!=P03_HW_OK)return fail(s,7u);
            for(i=0u;i<emitted;i++)
                if(p03_hw_read_packet(s->hw,(uint8_t)op->slot,(uint16_t)i,
                                      &s->temporary[i])!=P03_HW_OK)
                    return fail(s,8u);
            memcpy(&s->raw_words[s->word_count],s->temporary,
                   (size_t)emitted*sizeof(*s->temporary));
            s->cores[op->core].words=&s->raw_words[s->word_count];
            s->cores[op->core].slot=(uint8_t)op->slot;
            s->cores[op->core].packet_count=(uint16_t)emitted;
            s->word_count+=emitted;
        }
    }else return fail(s,9u);
    if(rc!=P03_HW_OK || p03_hw_quiescent(s->hw)!=P03_HW_OK)
        return fail(s,10u);
    if(p07_b3_ack(s->pager,op,1)!=P07_B3_OK)return fail(s,11u);
    return P07_B3C2_OK;
}
int p07_b3c2_barrier_ack(p07_b3c2_hw_scheduler *s,
    const p07_b3_op *op,const p07_b3c3_receipt *receipt){
    p07_b3_op pending;uint32_t core,total=0u;
    if(!s||!op||!receipt||!s->pager||!s->hw)return P07_B3C2_INVALID;
    if(s->poisoned||s->pager->failed)return P07_B3C2_FAULTED;
    if(receipt->magic!=P07_B3C3_RECEIPT_MAGIC||
       receipt->tick!=op->tick ||
       receipt->bank!=op->next_bank)return fail(s,16u);
    if(p07_b3_next(s->pager,&pending)!=P07_B3_OK||
       pending.kind!=P07_B3_BARRIER ||
       pending.tick!=op->tick||pending.ordinal!=op->ordinal||
       s->pager->cursor!=P07_B3_CORES)return fail(s,12u);
    for(core=0u;core<P07_B3_CORES;core++){
        total+=s->cores[core].packet_count;
        if(s->hw->event_counts[core][op->current_bank]!=0u)
            return fail(s,13u);
    }
    if(receipt->inserted_count!=total ||
       receipt->source_packet_count!=total ||
       p03_hw_quiescent(s->hw)!=P03_HW_OK)
        return fail(s,14u);
    /* Barrier ACK requires a separate verified and COMPLETED B3c3 hardware
     * insertion, not just validation. Caller must independently enforce it. */
    if(p07_b3_ack(s->pager,op,1)!=P07_B3_OK)return fail(s,15u);
    for(core=0u;core<P07_B3_CORES;core++)s->cores[core].packet_count=0u;
    s->word_count=0u;
    return P07_B3C2_OK;
}
