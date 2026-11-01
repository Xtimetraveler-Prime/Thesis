#include "p07_b3_pager.h"
#include "p03_hw_adapter.h"
#include "p05_deployment.h"
#include <string.h>
/* Native compiler binds the *actual* accepted P03/P05 headers; refuse drift. */
_Static_assert(P03_HW_BACKING_BASE==P07_B3_BACKING_BASE,"P03 DDR base drift");
_Static_assert(P03_HW_RECORD_BYTES==P07_B3_RECORD_BYTES,"P02 stride drift");
_Static_assert(P03_RT_MAX_SLOTS==P07_B3_SLOTS,"P03 physical slot-count drift");
_Static_assert(P03_HW_FULL_PAGE_BYTES==P07_B3_FULL_IN_BYTES,"P03 page-in bytes drift");
_Static_assert(P03_HW_MUTABLE_BYTES==P07_B3_MUTABLE_OUT_BYTES,"P03 mutable page-out drift");
_Static_assert(P05_DEPLOY_MAX_CORES>=P07_B3_CORES,"P05 logical ID bound drift");
/* Compile-time alignment and owner-map identity for native C11 / future A53. */
_Static_assert(P07_B3_CORES * P07_B3_RECORD_BYTES <= UINT64_C(0x43F00000) - P07_B3_BACKING_BASE,
               "27 backing records collide with future staging");
_Static_assert(P07_B3_FULL_IN_BYTES % 256u == 0u, "page-in burst misaligned");
_Static_assert(P07_B3_MUTABLE_OUT_BYTES % 256u == 0u, "page-out burst misaligned");
_Static_assert(P07_B3_FULL_IN_BYTES == 438272u, "P05 full-page bytes drift");
_Static_assert(P07_B3_MUTABLE_OUT_BYTES == 106496u, "P05 mutable-page bytes drift");

/* stage values: 0 select; 1 waiting load after acknowledged dirty save;
 * 2 awaiting next dispatch after acknowledged load.
 */
uint64_t p07_b3_core_address(uint32_t core) {
    return core < P07_B3_CORES ? P07_B3_BACKING_BASE + (uint64_t)core*P07_B3_RECORD_BYTES : UINT64_MAX;
}
int p07_b3_init(p07_b3_pager *p, uint32_t order_mode) {
    uint32_t i;
    if(!p || order_mode > P07_B3_ORDER_ALTERNATING) return P07_B3_ERROR;
    memset(p,0,sizeof(*p));
    p->order_mode=order_mode;
    p->selected_slot=P07_B3_NO_SLOT;
    p->selected_core=P07_B3_NO_CORE;
    p->selected_victim=P07_B3_NO_CORE;
    for(i=0;i<P07_B3_SLOTS;i++){
        p->resident[i]=-1;
        p->last_use[i]=UINT32_MAX;
    }
    return P07_B3_OK;
}
static int fail(p07_b3_pager *p,uint32_t kind) {
    p->failed=1u;
    if(!p->first_failure_kind)p->first_failure_kind=kind ? kind : UINT32_MAX;
    p->has_pending=0u;
    return P07_B3_FAULTED;
}
static uint32_t choose_slot(const p07_b3_pager *p,uint32_t core) {
    uint32_t s,best=0u;
    for(s=0u;s<P07_B3_SLOTS;s++)if(p->resident[s]==(int32_t)core)return s;
    for(s=0u;s<P07_B3_SLOTS;s++)if(p->resident[s]==-1)return s;
    for(s=1u;s<P07_B3_SLOTS;s++){
        if(p->last_use[s]<p->last_use[best])best=s;
    }
    return best;
}
static uint32_t service_core(const p07_b3_pager *p) {
    if(p->order_mode==P07_B3_ORDER_ALTERNATING && (p->tick&1u))
        return P07_B3_CORES-1u-p->cursor;
    return p->cursor;
}
static void issue(p07_b3_pager *p,p07_b3_op *out,
                  uint32_t kind,uint32_t core,uint32_t slot,uint32_t victim) {
    p07_b3_op result={0};
    result.kind=kind;result.tick=p->tick;
    result.ordinal=p->ordinal;
    result.core=core;result.slot=slot;result.victim=victim;
    result.current_bank=p->tick&1u;
    result.next_bank=1u-result.current_bank;
    if(kind==P07_B3_PAGE_IN){result.bytes=P07_B3_FULL_IN_BYTES;result.backing_address=p07_b3_core_address(core);}
    if(kind==P07_B3_PAGE_OUT || kind==P07_B3_FINAL_FLUSH){
        result.bytes=P07_B3_MUTABLE_OUT_BYTES;
        result.backing_address=p07_b3_core_address(core);
    }
    p->pending=result;p->has_pending=1u;
    *out=result;
}
int p07_b3_next(p07_b3_pager *p,p07_b3_op *out) {
    uint32_t core,slot,victim;
    if(!p||!out)return P07_B3_ERROR;
    if(p->failed)return P07_B3_FAULTED;
    if(p->has_pending){*out=p->pending;return P07_B3_OK;}
    if(p->tick>=P07_B3_TICKS){
        while(p->flush_slot<P07_B3_SLOTS){
            slot=p->flush_slot;
            if(p->resident[slot]>=0 && p->dirty[slot]){
                issue(p,out,P07_B3_FINAL_FLUSH,(uint32_t)p->resident[slot],slot,P07_B3_NO_CORE);
                return P07_B3_OK;
            }
            ++p->flush_slot;
        }
        return P07_B3_DONE;
    }
    if(p->cursor==P07_B3_CORES){
        issue(p,out,P07_B3_BARRIER,P07_B3_NO_CORE,P07_B3_NO_SLOT,P07_B3_NO_CORE);
        return P07_B3_OK;
    }
    core=service_core(p);
    if(p->stage){
        if(p->selected_core!=core || p->selected_slot>=P07_B3_SLOTS)
            return fail(p,UINT32_MAX);
        if(p->stage==1u){
            issue(p,out,P07_B3_PAGE_IN,core,p->selected_slot,p->selected_victim);
            return P07_B3_OK;
        }
        issue(p,out,P07_B3_DISPATCH,core,p->selected_slot,P07_B3_NO_CORE);
        return P07_B3_OK;
    }
    slot=choose_slot(p,core);
    victim=p->resident[slot]>=0 ? (uint32_t)p->resident[slot] : P07_B3_NO_CORE;
    p->selected_slot=slot;p->selected_core=core;p->selected_victim=victim;
    if(victim==core){
        issue(p,out,P07_B3_DISPATCH,core,slot,P07_B3_NO_CORE);
        return P07_B3_OK;
    }
    if(victim!=P07_B3_NO_CORE){
        if(!p->dirty[slot]) return fail(p,UINT32_MAX); /* dirty eviction cannot be skipped */
        issue(p,out,P07_B3_PAGE_OUT,victim,slot,P07_B3_NO_CORE);
        return P07_B3_OK;
    }
    issue(p,out,P07_B3_PAGE_IN,core,slot,P07_B3_NO_CORE);
    return P07_B3_OK;
}
static int op_equal(const p07_b3_op *a,const p07_b3_op *b) {
    return a->kind==b->kind && a->tick==b->tick &&
           a->ordinal==b->ordinal && a->core==b->core &&
           a->slot==b->slot && a->victim==b->victim &&
           a->current_bank==b->current_bank && a->next_bank==b->next_bank &&
           a->bytes==b->bytes && a->backing_address==b->backing_address;
}
int p07_b3_ack(p07_b3_pager *p,const p07_b3_op *observed,int success) {
    uint32_t kind,slot;
    if(!p||!observed)return P07_B3_ERROR;
    if(p->failed)return P07_B3_FAULTED;
    if(!p->has_pending || !op_equal(observed,&p->pending) || success!=1)
        return fail(p,p->has_pending ? p->pending.kind : UINT32_MAX);
    kind=p->pending.kind;slot=p->pending.slot;
    if(kind==P07_B3_PAGE_OUT){
        if(slot>=P07_B3_SLOTS || p->resident[slot]!=(int32_t)p->pending.core || !p->dirty[slot])
            return fail(p,kind);
        p->dirty[slot]=0u;
        p->stage=1u;
        ++p->counters.dirty_evictions;++p->counters.runtime_outs;
        p->counters.write_bytes+=P07_B3_MUTABLE_OUT_BYTES;
    }else if(kind==P07_B3_PAGE_IN){
        if(slot>=P07_B3_SLOTS || p->resident[slot]==(int32_t)p->pending.core ||
           (p->resident[slot]!=-1 && p->dirty[slot]))return fail(p,kind);
        if(p->resident[slot]==-1)++p->counters.cold_ins;
        else ++p->counters.replacements;
        p->resident[slot]=(int32_t)p->pending.core;
        p->dirty[slot]=0u;
        p->stage=2u;
        ++p->counters.page_ins;
        p->counters.read_bytes+=P07_B3_FULL_IN_BYTES;
    }else if(kind==P07_B3_DISPATCH){
        if(slot>=P07_B3_SLOTS || p->resident[slot]!=(int32_t)p->pending.core ||
           p->cursor>=P07_B3_CORES)return fail(p,kind);
        if(p->stage==0u)++p->counters.hits;
        p->dirty[slot]=1u;
        p->last_use[slot]=p->ordinal;
        ++p->ordinal;++p->cursor;++p->counters.dispatches;
        p->stage=0u;
    }else if(kind==P07_B3_BARRIER){
        if(p->cursor!=P07_B3_CORES || p->tick>=P07_B3_TICKS)return fail(p,kind);
        ++p->counters.barriers;
        ++p->tick;p->cursor=0u;p->stage=0u;
    }else if(kind==P07_B3_FINAL_FLUSH){
        if(slot>=P07_B3_SLOTS || p->resident[slot]!=(int32_t)p->pending.core ||
           !p->dirty[slot] || p->tick!=P07_B3_TICKS)return fail(p,kind);
        p->dirty[slot]=0u;
        ++p->counters.final_outs;
        p->counters.write_bytes+=P07_B3_MUTABLE_OUT_BYTES;
        ++p->flush_slot;
    }else return fail(p,kind);
    p->has_pending=0u;
    return P07_B3_OK;
}
