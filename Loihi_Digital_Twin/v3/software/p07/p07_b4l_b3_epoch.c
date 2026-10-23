#include "p07_b4l_b3_epoch.h"
#include <string.h>
_Static_assert(P07_B3_CORES==27u,"frozen B2.4 core count changed");
_Static_assert(P07_B3_SLOTS==3u,"accepted P03 physical slot count changed");
_Static_assert(P07_B3_TICKS==26u,"frozen B2 epoch count changed");
static int fault(p07_b3c2_hw_scheduler *s,p07_b4l_b3_receipt *r,uint32_t stage){
    p07_b3_op pending;
    r->first_error=stage;
    r->faulted=1u;
    r->magic=0u;
    if(s){
        s->poisoned=1u;
        if(!s->first_fault)s->first_fault=stage;
        if(s->pager&&!s->pager->failed){
            if(p07_b3_next(s->pager,&pending)==P07_B3_OK)
                (void)p07_b3_ack(s->pager,&pending,0);
            else s->pager->failed=1u;
        }
    }
    return P07_B4L_B3_FAULT;
}
static uint64_t fnv_word(uint64_t hash,uint64_t word){
    uint32_t i;
    for(i=0u;i<8u;i++){
        hash^=(uint8_t)(word>>(8u*i));
        hash*=UINT64_C(1099511628211);
    }
    return hash;
}
int p07_b4l_b3_one_epoch(p07_b3c2_hw_scheduler *s,
                         p07_b4l_b3_receipt *r){
    p07_b3_op op,next;
    uint32_t i,captured=0u,operations=0u;
    uint64_t hash=UINT64_C(14695981039346656037);
    int status;
    if(!s||!r||!s->pager||!s->hw||!s->raw_words||
       !s->temporary||s->poisoned||s->first_fault||
       s->pager->failed||s->pager->tick!=0u||
       s->pager->order_mode!=P07_B3_ORDER_ASCENDING||
       s->pager->has_pending||s->pager->cursor!=0u||
       s->pager->counters.dispatches!=0u||
       s->pager->counters.barriers!=0u||s->word_count!=0u||
       s->raw_capacity!=P07_B3C_MAX_RAW_WORDS||
       s->temporary_capacity!=P03_RT_MAX_PACKETS||
       s->hw->last_error!=P03_HW_OK)
        return P07_B4L_B3_ARGUMENT;
    memset(r,0,sizeof(*r));
    for(operations=0u;operations<4u*P07_B3_CORES+8u;operations++){
        status=p07_b3c2_step(s,&op);
        if(status==P07_B3C2_BARRIER){
            /* Actual first-tick P03 transfers and 27 dispatch ACKs happened.
             * But no B2b/3c3 verified NEXT insertion exists yet.
             * Absolutely do not ACK this barrier or proceed to tick 1.
             */
            if(op.kind!=P07_B3_BARRIER||op.tick!=0u||
               op.current_bank!=0u||op.next_bank!=1u||
               s->pager->has_pending!=1u||s->pager->tick!=0u||
               s->pager->counters.dispatches!=P07_B3_CORES||
               s->pager->counters.page_ins!=P07_B3_CORES||
               s->pager->counters.runtime_outs!=P07_B3_CORES-P07_B3_SLOTS||
               s->pager->counters.barriers!=0u||
               p07_b3_next(s->pager,&next)!=P07_B3_OK||
               memcmp(&op,&next,sizeof(op))!=0||
               p03_hw_quiescent(s->hw)!=P03_HW_OK)
                return fault(s,r,200u);
            for(i=0u;i<P07_B3_CORES;i++){
                size_t n=s->cores[i].packet_count, j;
                if(s->cores[i].source_core!=i||
                   (n>0u&&!s->cores[i].words)||
                   n>s->word_count-captured)
                    return fault(s,r,210u+i);
                hash=fnv_word(hash,(uint64_t)i);
                hash=fnv_word(hash,(uint64_t)n);
                for(j=0u;j<n;j++)
                    hash=fnv_word(hash,s->cores[i].words[j]);
                captured+=(uint32_t)n;
            }
            if(captured!=s->word_count||
               captured>s->raw_capacity||
               s->hw->last_error!=P03_HW_OK)
                return fault(s,r,250u);
            r->magic=P07_B4L_B3_ONE_TICK_MAGIC;
            r->tick=0u;
            r->unique_dispatches=P07_B3_CORES;
            r->page_ins=s->pager->counters.page_ins;
            r->dirty_page_outs=s->pager->counters.runtime_outs;
            r->pending_barrier=1u;
            r->barrier_acked=0u;
            r->physical_packets_captured=captured;
            r->source_count=P07_B3_CORES;
            r->dispatcher_next_current_bank=op.current_bank;
            r->dispatcher_next_bank=op.next_bank;
            r->captured_word_fnv1a=hash;
            r->p03_page_bytes_expected=
                (uint64_t)r->page_ins*P07_B3_FULL_IN_BYTES+
                (uint64_t)r->dirty_page_outs*P07_B3_MUTABLE_OUT_BYTES;
            return P07_B4L_B3_OK;
        }
        if(status!=P07_B3C2_OK)
            return fault(s,r,100u+operations);
        if(op.tick!=0u||s->pager->counters.barriers!=0u)
            return fault(s,r,150u+operations);
    }
    return fault(s,r,255u);
}
