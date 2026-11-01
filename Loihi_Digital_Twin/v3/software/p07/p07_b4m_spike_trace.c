#include "p07_b4m_spike_trace.h"
#include <stdlib.h>
#include <string.h>

_Static_assert(P07_B3_CORES==27u,"original B2.4 sources");
_Static_assert(P07_B3_TICKS==26u,"original B2.4 epochs");
_Static_assert(P07_B4M_TRACE_SPIKE_CAP>=1010u,
               "real B2.4 compartments exceed bounded trace receipt");

static int fail(p07_b4m_spike_trace *t,uint32_t reason){
    if(t){if(!t->poisoned)t->first_fault=reason;t->poisoned=1u;t->verified=0u;}
    return P07_B4M_TRACE_FAULT;
}
static uint64_t fnv_u32(uint64_t value,uint32_t word){
    uint32_t n;
    for(n=0u;n<4u;n++){
        value^=(uint8_t)(word>>(n*8u));
        value*=UINT64_C(1099511628211);
    }
    return value;
}
static int spike_cmp(const void *a,const void *b){
    const uint16_t *x=(const uint16_t *)a,*y=(const uint16_t *)b;
    if(x[0]!=y[0])return x[0]<y[0]?-1:1;
    if(x[1]!=y[1])return x[1]<y[1]?-1:1;
    return 0;
}
int p07_b4m_trace_init(p07_b4m_spike_trace *t,
    p07_b3c2_hw_scheduler *s,uint16_t (*spikes)[2],size_t capacity){
    uint32_t c,comp,total=0u;
    if(!t||!s||!s->pager||!s->hw||!spikes||
       capacity<P07_B4M_TRACE_SPIKE_CAP||
       s->poisoned||s->pager->failed||s->hw->last_error!=P03_HW_OK||
       s->pager->tick!=0u||s->pager->cursor!=0u||s->pager->has_pending)
        return P07_B4M_TRACE_INVALID;
    for(c=0u;c<P07_B3_CORES;c++){
        if(!s->hw->configured[c])return P07_B4M_TRACE_INVALID;
        comp=(uint32_t)((s->hw->metadata[c]>>7u)&UINT64_C(0x7ff));
        if(!comp||comp>1024u||total>capacity-comp)
            return P07_B4M_TRACE_INVALID;
        total+=comp;
    }
    memset(t,0,sizeof(*t));
    t->hw=s->hw;t->scheduler=s;t->spikes=spikes;t->capacity=capacity;
    t->expected_compartments=total;
    t->fnv64=UINT64_C(14695981039346656037);
    return P07_B4M_TRACE_OK;
}
int p07_b4m_trace_on_dispatch(void *context,p03_hw_adapter *hw,
    uint8_t core,uint8_t slot,uint32_t tick,uint32_t packet_count){
    p07_b4m_spike_trace *t=(p07_b4m_spike_trace *)context;
    uint32_t comp,n,trace[8],after[8],j;
    if(!t||!hw)return P07_B4M_TRACE_INVALID;
    if(t->poisoned||t->verified||hw!=t->hw||
       !t->scheduler||t->scheduler->hw!=hw||
       t->scheduler->pager->failed||core>=P07_B3_CORES||
       slot>=P07_B3_SLOTS||tick!=t->tick||
       tick!=t->scheduler->pager->tick||t->seen[core]||
       (uint32_t)t->scheduler->pager->resident[slot]!=core||
       !hw->configured[core]||packet_count>P03_RT_MAX_PACKETS||
       hw->last_error!=P03_HW_OK||p03_hw_quiescent(hw)!=P03_HW_OK)
        return fail(t,1u);
    n=(uint32_t)((hw->metadata[core]>>7u)&UINT64_C(0x7ff));
    if(!n||n>1024u||t->observed_compartments>t->expected_compartments-n)
        return fail(t,2u);
    for(comp=0u;comp<n;comp++){
        memset(trace,0,sizeof(trace));memset(after,0,sizeof(after));
        /* HLS writes trace before it signals DISPATCH_DONE, so both
         * reads are from the identical freshly completed invocation.
         */
        if(p03_hw_debug_word(hw,slot,7u,(uint16_t)comp,0,trace)!=P03_HW_OK||
           p03_hw_debug_word(hw,slot,1u,(uint16_t)comp,0,after)!=P03_HW_OK)
            return fail(t,3u);
        /* Word 4+5 = independent after_state from trace; debug bank 1
         * is HLS's actual committed state. Trace bit192 = spike flag.
         * All trace high reserved bits must stay clear.
         */
        if(trace[4]!=after[0]||trace[5]!=after[1]||
           (trace[6]&UINT32_C(0xfffffffe))||trace[7]||
           (after[2]||after[3]||after[4]||after[5]||after[6]||after[7]))
            return fail(t,4u);
        for(j=0u;j<8u;j++)t->fnv64=fnv_u32(t->fnv64,trace[j]);
        if(trace[6]&1u){
            if(t->spike_count>=t->capacity)return fail(t,5u);
            t->spikes[t->spike_count][0]=(uint16_t)core;
            t->spikes[t->spike_count][1]=(uint16_t)comp;
            t->spike_count++;
        }
    }
    t->observed_compartments+=n;
    t->seen[core]=1u;
    ++t->read_count;
    return P07_B4M_TRACE_OK;
}
int p07_b4m_trace_finalize(p07_b4m_spike_trace *t,
    p07_b4m_trace_receipt *receipt){
    p07_b4m_trace_receipt candidate={0};uint32_t core;
    if(!t||!receipt)return P07_B4M_TRACE_INVALID;
    if(t->poisoned||t->verified||!t->scheduler||!t->scheduler->pager||
       t->scheduler->pager->failed||t->scheduler->pager->tick!=t->tick||
       t->scheduler->pager->cursor!=P07_B3_CORES||
       t->read_count!=P07_B3_CORES||
       t->observed_compartments!=t->expected_compartments)
        return fail(t,6u);
    for(core=0u;core<P07_B3_CORES;core++)
        if(t->seen[core]!=1u)return fail(t,7u);
    qsort(t->spikes,t->spike_count,sizeof(t->spikes[0]),spike_cmp);
    candidate.magic=P07_B4M_TRACE_MAGIC;
    candidate.tick=t->tick;
    candidate.source_count=t->read_count;
    candidate.compartments_checked=t->observed_compartments;
    candidate.spikes=t->spike_count;
    candidate.fnv64=t->fnv64;
    t->verified=1u;
    *receipt=candidate;
    return P07_B4M_TRACE_OK;
}
int p07_b4m_trace_advance(p07_b4m_spike_trace *t){
    uint32_t next_tick;
    if(!t||t->poisoned||!t->verified||!t->scheduler||
       !t->scheduler->pager||t->scheduler->pager->failed||
       t->scheduler->pager->has_pending||t->tick>=P07_B3_TICKS)
        return P07_B4M_TRACE_INVALID;
    next_tick=t->tick+1u;
    if(t->scheduler->pager->tick!=next_tick||
       t->scheduler->pager->counters.barriers!=next_tick)
        return fail(t,8u);
    memset(t->seen,0,sizeof(t->seen));
    t->tick=next_tick;
    t->read_count=0u;t->spike_count=0u;
    t->observed_compartments=0u;t->verified=0u;
    t->fnv64=UINT64_C(14695981039346656037);
    return P07_B4M_TRACE_OK;
}
