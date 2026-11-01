#include "p07_b3b_event_owner.h"
#include "p03_hw_adapter.h"
#include <string.h>
_Static_assert(P07_B3_CORES==27u && P07_B3_SLOTS==3u,"B3b accepted 27/3 topology changed");
_Static_assert(P07_B3B_DEPTH==P03_HW_EVENT_DEPTH,"P03 event-bank depth mismatch");
_Static_assert(P03_HW_EVENT0_OFFSET==0x54000u && P03_HW_EVENT1_OFFSET==0x58000u,
               "P02 event bank offset mismatch");
_Static_assert(P03_HW_EVENT1_OFFSET-P03_HW_EVENT0_OFFSET==P07_B3B_DEPTH*4u,
               "P02 event bank word width changed");
_Static_assert(P03_HW_EVENT1_OFFSET+P07_B3B_DEPTH*4u<=P03_HW_RECORD_BYTES,
               "P02 event banks exceed record bounds");
static uint16_t rd16(const uint8_t *p){return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));}
static int active(const p07_b3b_owner *o,uint32_t core){
    uint32_t slot;
    for(slot=0u;slot<P07_B3_SLOTS;slot++)
        if(o->pager->resident[slot]==(int32_t)core)return (int)slot;
    return -1;
}
static p07_b3b_event_slice *mutable_bank(p07_b3b_owner *o,uint32_t core){
    int s=active(o,core);
    return s>=0 ? &o->slot[(unsigned)s] : &o->backing[core];
}
static const p07_b3b_event_slice *bank(const p07_b3b_owner *o,uint32_t core){
    int s=active(o,core);
    return s>=0 ? &o->slot[(unsigned)s] : &o->backing[core];
}
static int fault(p07_b3b_owner *o,uint32_t kind){
    if(o){
        if(!o->poisoned)o->first_error=kind?kind:UINT32_MAX;
        o->poisoned=1u;
        if(o->pager && !o->pager->failed){
            p07_b3_op op;
            if(p07_b3_next(o->pager,&op)==P07_B3_OK)
                (void)p07_b3_ack(o->pager,&op,0);
            else o->pager->failed=1u;
        }
    }
    return P07_B3B_POISON;
}
static int pulse(uint8_t level,uint32_t pixel,uint32_t tick){
    uint32_t phase;
    if(tick==25u)return 0;
    phase=(tick+17u*pixel)%25u;
    return ((phase+1u)*(uint32_t)level)/255u > (phase*(uint32_t)level)/255u;
}
static void swap(uint32_t *v,uint32_t *w){uint32_t t=*v;*v=*w;*w=t;}
static void sort_axons(uint32_t *a,uint32_t n){
    /* in-place heapsort: no libc qsort, no dynamic memory/stack event arrays */
    uint32_t i,k;
    for(i=n/2u;i>0u;){
        uint32_t root=--i,end=n;
        while(root*2u+1u<end){
            uint32_t child=root*2u+1u;
            if(child+1u<end&&a[child]<a[child+1u])++child;
            if(a[root]>=a[child])break;
            swap(&a[root],&a[child]);root=child;
        }
    }
    for(k=n;k>1u;){
        uint32_t root=0u,end=--k;
        swap(&a[0],&a[end]);
        while(root*2u+1u<end){
            uint32_t child=root*2u+1u;
            if(child+1u<end&&a[child]<a[child+1u])++child;
            if(a[root]>=a[child])break;
            swap(&a[root],&a[child]);root=child;
        }
    }
}
static int begin_epoch(p07_b3b_owner *o){
    const p07_b2b_transaction *tx=o->transport;
    const p07_b2_ingress_view *ing=tx->ingress;
    uint32_t counts[P07_B3_CORES]={0u},routed[P07_B3_CORES]={0u},i,core,which,bank_id;
    if(tx->tick!=o->pager->tick||ing->core_count!=P07_B3_CORES||
       tx->binding->core_count!=P07_B3_CORES||
       tx->pending_count>tx->pending_capacity||o->pager->tick>=P07_B3_TICKS)
        return fault(o,100u);
    bank_id=tx->tick&1u;
    /* Independently cross-check B2b's global canonical pending vector against
     * the actually-owned P02 EVENT slice (resident slot OR backing). */
    for(i=0u;i<tx->pending_count;i++){
        core=tx->pending[i].core_id;
        if(core>=P07_B3_CORES||tx->pending[i].axon_id>=P07_B3B_DEPTH)
            return fault(o,101u);
        ++routed[core];
        if(routed[core]>P07_B3B_DEPTH)return fault(o,102u);
        if(bank(o,core)->count[bank_id]<routed[core]||
           bank(o,core)->axon[bank_id][routed[core]-1u]!=tx->pending[i].axon_id)
            return fault(o,103u);
    }
    for(core=0u;core<P07_B3_CORES;core++){
        if(tx->pending_by_core[core]!=routed[core]||
           bank(o,core)->count[bank_id]!=routed[core])
            return fault(o,104u);
        counts[core]=routed[core];
    }
    /* Check *all* external fanout and CURRENT per-core pressure before one
     * word or count is changed. CPU-simulated NEXT/DDR writes cannot fail.
     */
    for(i=0u;i<ing->route_count;i++){
        const uint8_t *route=ing->routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=rd16(route),axon=rd16(route+4u);
        core=rd16(route+2u);
        if(pixel>=P07_B2_IMAGE_BYTES||core>=P07_B3_CORES||axon>=P07_B3B_DEPTH)
            return fault(o,105u);
        if(pulse(ing->pixels[pixel],pixel,tx->tick)){
            if(++counts[core]>P07_B3B_DEPTH)return fault(o,106u);
        }
    }
    for(core=0u;core<P07_B3_CORES;core++){
        const p07_b3b_event_slice *v=bank(o,core);
        if(v->count[1u-bank_id]!=0u)return fault(o,107u);
    }
    /* Only after complete preflight is any owner bank mutated. */
    for(i=0u;i<ing->route_count;i++){
        const uint8_t *route=ing->routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=rd16(route);
        if(pulse(ing->pixels[pixel],pixel,tx->tick)){
            core=rd16(route+2u);
            which=rd16(route+4u);
            p07_b3b_event_slice *v=mutable_bank(o,core);
            v->axon[bank_id][v->count[bank_id]++]=which;
        }
    }
    for(core=0u;core<P07_B3_CORES;core++){
        p07_b3b_event_slice *v=mutable_bank(o,core);
        if(v->count[bank_id]!=counts[core])return fault(o,108u);
        sort_axons(v->axon[bank_id],v->count[bank_id]);
    }
    memcpy(o->current_expected,counts,sizeof(counts));
    memset(o->current_consumed,0,sizeof(o->current_consumed));
    memset(o->dispatched,0,sizeof(o->dispatched));
    o->tick_started=1u;
    return P07_B3B_OK;
}
int p07_b3b_init(p07_b3b_owner *o,p07_b3_pager *p,
    p07_b2b_transaction *t,p07_b3b_event_slice *backing,
    p07_b3b_event_slice *slots,p07_b2_input_event *scratch,size_t capacity){
    if(!o||!p||!t||!backing||!slots||!scratch||
       p->failed||p->tick!=0u||p->ordinal!=0u||p->has_pending||
       t->tick!=0u||t->pending_count!=0u||t->pending_capacity<1u||
       capacity<t->pending_capacity||capacity>P07_B2B_PENDING_MAX||
       !t->ingress||!t->binding||!t->pending||
       t->ingress->core_count!=P07_B3_CORES||
       t->binding->core_count!=P07_B3_CORES)
        return P07_B3B_REJECT;
    memset(o,0,sizeof(*o));
    o->pager=p;o->transport=t;o->backing=backing;o->slot=slots;
    o->scratch=scratch;o->scratch_capacity=capacity;
    return P07_B3B_OK;
}
int p07_b3b_next(p07_b3b_owner *o,p07_b3_op *op){
    int result;
    if(!o||!op)return P07_B3B_REJECT;
    if(o->poisoned||o->pager->failed)return P07_B3B_POISON;
    if(o->pager->tick<P07_B3_TICKS && !o->tick_started){
        result=begin_epoch(o);
        if(result!=P07_B3B_OK)return result;
    }
    result=p07_b3_next(o->pager,op);
    if(result==P07_B3_DONE)return P07_B3B_DONE;
    if(result!=P07_B3_OK)return fault(o,109u);
    return P07_B3B_OK;
}
int p07_b3b_ack(p07_b3b_owner *o,const p07_b3_op *op,int success){
    int result;uint32_t core,bank_id,slot;
    p07_b3b_event_slice *v;
    if(!o||!op)return P07_B3B_REJECT;
    if(o->poisoned||o->pager->failed)return P07_B3B_POISON;
    if(op->kind==P07_B3_BARRIER)return fault(o,110u);
    if(!o->pager->has_pending||success!=1){
        (void)p07_b3_ack(o->pager,op,0);
        return fault(o,111u);
    }
    if(op->kind==P07_B3_PAGE_OUT||op->kind==P07_B3_PAGE_IN||
       op->kind==P07_B3_DISPATCH||op->kind==P07_B3_FINAL_FLUSH){
        core=op->core;slot=op->slot;
        if(core>=P07_B3_CORES||slot>=P07_B3_SLOTS)
            return fault(o,112u);
        if(op->kind==P07_B3_DISPATCH){
            bank_id=op->current_bank;
            if(!o->tick_started||o->dispatched[core]||
               o->pager->resident[slot]!=(int32_t)core ||
               o->slot[slot].count[bank_id]!=o->current_expected[core])
                return fault(o,113u);
        }
    }else return fault(o,114u);
    result=p07_b3_ack(o->pager,op,1);
    if(result!=P07_B3_OK)return fault(o,115u);
    if(op->kind==P07_B3_PAGE_OUT||op->kind==P07_B3_FINAL_FLUSH){
        o->backing[core]=o->slot[slot]; /* mock mutable slice writeback ACK */
    }else if(op->kind==P07_B3_PAGE_IN){
        o->slot[slot]=o->backing[core]; /* mock full-page event slice load ACK */
    }else if(op->kind==P07_B3_DISPATCH){
        v=&o->slot[slot];bank_id=op->current_bank;
        o->current_consumed[core]=v->count[bank_id];
        v->count[bank_id]=0u; /* P03 HLS consumed CURRENT; next untouched */
        o->dispatched[core]=1u;
    }
    return P07_B3B_OK;
}
int p07_b3b_barrier(p07_b3b_owner *o,const p07_b3_op *op,
    const uint8_t *wire,size_t wire_bytes,const uint16_t (*spikes)[2],
    size_t spike_count,p07_b2b_tx_receipt *receipt){
    p07_b2b_transaction shadow;
    p07_b2b_tx_receipt proposed={0};
    uint32_t core,bank_id,i;
    p07_b2_status status;
    int result;
    if(!o||!op||!wire||!receipt)return P07_B3B_REJECT;
    if(o->poisoned||o->pager->failed)return P07_B3B_POISON;
    if(!o->tick_started||!o->pager->has_pending||
       op->kind!=P07_B3_BARRIER||op->tick!=o->pager->tick||
       o->pager->cursor!=P07_B3_CORES||o->pager->tick>=P07_B3_TICKS)
        return fault(o,116u);
    bank_id=1u-(op->tick&1u);
    for(core=0u;core<P07_B3_CORES;core++){
        if(!o->dispatched[core]||
           o->current_consumed[core]!=o->current_expected[core]||
           bank(o,core)->count[1u-bank_id]!=0u||
           bank(o,core)->count[bank_id]!=0u)
            return fault(o,117u);
    }
    /* Fully isolated shadow of B2b transport. Original state, pending tuple
     * bytes and original receipt remain untouched on any decode/capacity/
     * provenance failure. Caller scratch is not an authoritative bank.
     */
    shadow=*o->transport;
    shadow.pending=o->scratch;
    memcpy(o->scratch,o->transport->pending,
           o->transport->pending_capacity*sizeof(*o->scratch));
    status=p07_b2b_transaction_step(&shadow,wire,wire_bytes,
                                     spikes,spike_count,&proposed);
    if(status!=P07_B2_OK)return fault(o,118u);
    for(core=0u;core<P07_B3_CORES;core++){
        if(proposed.current_by_core[core]!=o->current_expected[core] ||
           proposed.next_by_core[core]>P07_B3B_DEPTH ||
           bank(o,core)->count[bank_id]!=0u)
            return fault(o,119u);
    }
    if(proposed.tick!=o->pager->tick ||
       proposed.current_bank!=(op->tick&1u)||
       shadow.pending_count!=proposed.routed_next||
       shadow.tick!=op->tick+1u)
        return fault(o,120u);
    result=p07_b3_ack(o->pager,op,1);
    if(result!=P07_B3_OK)return fault(o,121u);
    for(i=0u;i<shadow.pending_count;i++){
        uint32_t dest=shadow.pending[i].core_id;
        p07_b3b_event_slice *v=mutable_bank(o,dest);
        v->axon[bank_id][v->count[bank_id]++]=shadow.pending[i].axon_id;
        if(active(o,dest)>=0)++o->resident_next;
        else ++o->nonresident_next;
    }
    for(core=0u;core<P07_B3_CORES;core++){
        p07_b3b_event_slice *v=mutable_bank(o,core);
        if(v->count[bank_id]!=proposed.next_by_core[core])
            return fault(o,122u); /* should be unreachable after preflight */
    }
    memcpy(o->transport->pending,shadow.pending,
           shadow.pending_count*sizeof(*shadow.pending));
    o->transport->pending_count=shadow.pending_count;
    memcpy(o->transport->pending_by_core,shadow.pending_by_core,
           sizeof(shadow.pending_by_core));
    o->transport->tick=shadow.tick;
    *receipt=proposed;
    ++o->barriers_committed;
    o->tick_started=0u;
    return P07_B3B_OK;
}
int p07_b3b_read(const p07_b3b_owner *o,uint32_t core,uint32_t which,
    uint32_t idx,uint32_t *axon){
    const p07_b3b_event_slice *v;
    if(!o||!axon||core>=P07_B3_CORES||which>1u||o->poisoned)return P07_B3B_REJECT;
    v=bank(o,core);
    if(idx>=v->count[which])return P07_B3B_REJECT;
    *axon=v->axon[which][idx];
    return P07_B3B_OK;
}
