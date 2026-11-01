#include "p07_b4m_epoch_bridge.h"
#include <string.h>

_Static_assert(P07_B3_CORES==27u,"original frozen 27 core topology changed");
_Static_assert(P07_B3_SLOTS==3u,"original physical slot count changed");
_Static_assert(P07_B3_TICKS==26u,"original frozen tick count changed");

static int fail(p07_b3c2_hw_scheduler *s,
                p07_b4m_barrier_receipt *out,uint32_t reason){
    p07_b3_op pending;
    if(out){memset(out,0,sizeof(*out));out->first_failure=reason;}
    if(s){
        s->poisoned=1u;
        if(!s->first_fault)s->first_fault=400u+reason;
        if(s->pager&&!s->pager->failed){
            if(p07_b3_next(s->pager,&pending)==P07_B3_OK)
                (void)p07_b3_ack(s->pager,&pending,0);
            else s->pager->failed=1u;
        }
    }
    return P07_B4M_BRIDGE_FAULT;
}
static int exact_op(const p07_b3_op *a,const p07_b3_op *b){
    return a->kind==b->kind && a->tick==b->tick &&
           a->ordinal==b->ordinal && a->core==b->core &&
           a->slot==b->slot && a->victim==b->victim &&
           a->current_bank==b->current_bank && a->next_bank==b->next_bank &&
           a->bytes==b->bytes && a->backing_address==b->backing_address;
}
static int separate(const void *left,size_t ln,const void *right,size_t rn){
    uintptr_t a=(uintptr_t)left,b=(uintptr_t)right;
    if(!left||!right||!ln||!rn||ln>UINTPTR_MAX-a||rn>UINTPTR_MAX-b)return 0;
    return (a+ln<=b || b+rn<=a);
}
int p07_b4m_commit_pending_barrier(
    p07_b3c2_hw_scheduler *s,const p07_b3_op *op,
    const p07_b2_packet_binding *binding,
    const uint16_t (*spikes)[2],size_t nspikes,
    uint32_t source_evidence_verified,
    uint8_t *scratch,size_t scratch_bytes,
    uint8_t *frame,size_t frame_capacity,
    p07_b4m_barrier_receipt *out){
    p07_b3_op real;
    p07_b3c3_plan plan={0};
    p07_b3c3_receipt physical={0};
    p07_b4m_barrier_receipt receipt={0};
    size_t frame_bytes=0u;
    uint32_t i,total=0u;
    static const uint16_t empty[1][2]={{0u,0u}};

    /* Argument rejection cannot create a fabricated positive receipt.
     * If a hardware scheduler was supplied, however, its already-pending
     * global barrier is poisoned rather than left usable after a failure.
     */
    if(!s||!out)return P07_B4M_BRIDGE_ARGUMENT;
    if(!op||!binding||!scratch||!frame||!s->pager||!s->hw||
       !s->raw_words||!s->temporary||s->poisoned||s->first_fault||
       s->pager->failed||s->hw->last_error!=P03_HW_OK||
       !s->pager->has_pending||s->pager->cursor!=P07_B3_CORES||
       s->pager->tick>=P07_B3_TICKS||op->kind!=P07_B3_BARRIER||
       op->tick!=s->pager->tick||
       op->current_bank!=(op->tick&1u)||
       op->next_bank!=(1u-(op->tick&1u))||
       p07_b3_next(s->pager,&real)!=P07_B3_OK||
       !exact_op(op,&real)||binding->core_count!=P07_B3_CORES||
       !binding->routes||!binding->compartments_per_core||
       source_evidence_verified!=1u||
       (nspikes&&!spikes)||
       nspikes>P07_B3_CORES*1024u||
       scratch_bytes<P07_B3C_MAX_FRAME_BYTES||
       frame_capacity<P07_B3C_MAX_FRAME_BYTES||
       !separate(scratch,scratch_bytes,frame,frame_capacity)||
       !separate(scratch,scratch_bytes,s->raw_words,
                  s->raw_capacity*sizeof(*s->raw_words))||
       !separate(frame,frame_capacity,s->raw_words,
                  s->raw_capacity*sizeof(*s->raw_words))||
       !separate(scratch,scratch_bytes,s,sizeof(*s))||
       !separate(frame,frame_capacity,s,sizeof(*s))||
       !separate(scratch,scratch_bytes,out,sizeof(*out))||
       !separate(frame,frame_capacity,out,sizeof(*out)))
        return fail(s,out,1u);

    for(i=0u;i<P07_B3_CORES;i++){
        if(s->cores[i].source_core!=i||
           s->cores[i].packet_count>P03_RT_MAX_PACKETS||
           (s->cores[i].packet_count&&!s->cores[i].words)||
           s->cores[i].packet_count>s->word_count-total)
            return fail(s,out,2u);
        total+=s->cores[i].packet_count;
    }
    if(total!=s->word_count || total>s->raw_capacity)
        return fail(s,out,3u);
    /* The empty pointer is a legitimate zero-spike witness ONLY after
     * a separately verified complete PL trace. B2b still validates the
     * complete fanout against the trusted frozen source routes. */
    if(p07_b3c_encode_frame(s->cores,P07_B3_CORES,op->tick,binding,
          spikes?spikes:empty,nspikes,scratch,scratch_bytes,
          frame,frame_capacity,&frame_bytes)!=P07_B3C_OK)
        return fail(s,out,4u);
    if(p07_b3c3_prepare(&plan,s->pager,s->hw,binding,frame,frame_bytes,
          spikes?spikes:empty,nspikes)!=P07_B3C3_OK)
        return fail(s,out,5u);
    if(p07_b3c3_commit(&plan,&physical)!=P07_B3C3_OK)
        return fail(s,out,6u);
    /* No ACK without genuine completed original P03 debug/DDR insertion.
     * A failed ACK poisons the run even if NEXT writes already happened.
     */
    if(physical.magic!=P07_B3C3_RECEIPT_MAGIC||
       physical.inserted_count!=total||
       physical.source_packet_count!=total||
       physical.tick!=op->tick||physical.bank!=op->next_bank)
        return fail(s,out,7u);
    if(p07_b3c2_barrier_ack(s,op,&physical)!=P07_B3C2_OK)
        return fail(s,out,8u);
    if(s->pager->tick!=op->tick+1u||
       s->pager->counters.barriers!=op->tick+1u||
       s->pager->has_pending||s->word_count||
       s->hw->last_error!=P03_HW_OK)
        return fail(s,out,9u);
    receipt.magic=P07_B4M_BRIDGE_MAGIC;
    receipt.tick=op->tick;
    receipt.physical_packet_count=total;
    receipt.source_spike_count=(uint32_t)nspikes;
    receipt.route_inserted=physical.inserted_count;
    receipt.barrier_acks=1u;
    receipt.destination_bank=op->next_bank;
    *out=receipt;
    return P07_B4M_BRIDGE_OK;
}
