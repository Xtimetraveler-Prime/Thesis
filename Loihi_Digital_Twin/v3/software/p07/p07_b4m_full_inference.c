#include "p07_b4m_full_inference.h"
#include <string.h>

_Static_assert(P07_B3_CORES==27u && P07_B3_TICKS==26u,
               "frozen 27-core 26-tick inference changed");
_Static_assert(P07_B4A_WORD_CAPACITY==27u*4096u,
               "accepted full-current event buffer changed");
static const uint8_t compiled_sha[32]={
  0x02,0xa6,0xb6,0x8a,0x2e,0xda,0x45,0x87,
  0xbb,0xdf,0x07,0xe3,0xaf,0x4a,0xa6,0x3b,
  0xdd,0x72,0x14,0x22,0x3e,0x85,0x3b,0x08,
  0xd8,0xf6,0x46,0x38,0x96,0x36,0x4f,0x5a};
static const uint8_t capacity_sha[32]={
  0x82,0xe9,0xe6,0xc1,0x12,0x64,0xc6,0x09,
  0x2d,0xbe,0x94,0xf1,0x74,0x96,0x33,0x2f,
  0xae,0x30,0x3a,0xc9,0xef,0x7d,0xfa,0xa0,
  0x1d,0x0e,0xc4,0x41,0x86,0x9a,0x94,0x98};
static uint64_t fnv64_combine(uint64_t hash,uint64_t value){
    uint32_t i;
    for(i=0u;i<8u;i++){
        hash^=(uint8_t)(value>>(i*8u));
        hash*=UINT64_C(1099511628211);
    }
    return hash;
}
static int fault(p07_b3c2_hw_scheduler *s,
                 p07_b4m_full_receipt *r,uint32_t stage){
    p07_b3_op pending;
    if(r){memset(r,0,sizeof(*r));r->first_fault=stage;}
    if(s){
        s->poisoned=1u;
        if(!s->first_fault)s->first_fault=700u+stage;
        if(s->pager && !s->pager->failed){
            if(p07_b3_next(s->pager,&pending)==P07_B3_OK)
                (void)p07_b3_ack(s->pager,&pending,0);
            else s->pager->failed=1u;
        }
    }
    return P07_B4M_FULL_FAULT;
}
int p07_b4m_full_run(p07_b3c2_hw_scheduler *s,
    const p07_b2_ingress_binding *in,
    const p07_b2_packet_binding *routing,
    const uint8_t *wire,size_t wire_bytes,
    p07_b4a_read_ddr32 read_ddr,void *reader,
    p07_b4m_full_workspace *ws,p07_b4m_full_receipt *out){
    p07_b4m_full_receipt receipt={0};
    p07_b2_ingress_view parsed={0};
    p07_b4a_plan external_plan={0};
    p07_b4a_receipt external_receipt={0};
    p07_b4m_trace_receipt source_receipt={0};
    p07_b4m_barrier_receipt route_receipt={0};
    p07_b3_op op;
    uint32_t tick,step,i,best=0u;
    int status;

    if(!s||!out)return P07_B4M_FULL_ARGUMENT;
    /* All input artifacts MUST come from immutable B2.4 compiled mapping.
     * Do not confuse the 21,384 registered input axons with the <=8192
     * cross-core B1.2 packet routes (the latter must be counted separately).
     */
    if(!in||!routing||!wire||!ws||!read_ddr||!reader||
       !ws->merged_current_words||!ws->source_spikes||
       !ws->frame_scratch||!ws->packet_frame||
       ws->merged_capacity!=P07_B4A_WORD_CAPACITY||
       ws->source_capacity!=P07_B4M_TRACE_SPIKE_CAP||
       ws->scratch_capacity<P07_B3C_MAX_FRAME_BYTES||
       ws->frame_capacity<P07_B3C_MAX_FRAME_BYTES||
       !s->pager||!s->hw||s->poisoned||s->pager->failed||
       s->hw->last_error!=P03_HW_OK||
       s->pager->order_mode!=P07_B3_ORDER_ASCENDING||
       s->pager->tick||s->pager->cursor||s->pager->has_pending||
       s->pager->counters.dispatches||s->pager->counters.barriers||
       s->trace_hook||s->word_count||
       in->core_count!=P07_B3_CORES||
       routing->core_count!=P07_B3_CORES||
       routing->route_count>P07_B2_MAX_ROUTE_BINDINGS||
       memcmp(in->compiled_sha256,compiled_sha,32u)||
       memcmp(in->capacity_sha256,capacity_sha,32u)||
       memcmp(routing->compiled_sha256,compiled_sha,32u)||
       memcmp(routing->capacity_sha256,capacity_sha,32u)||
       p07_b2_decode_ingress(wire,wire_bytes,in,&parsed)!=P07_B2_OK)
        return fault(s,out,1u);
    if(!routing->compartments_per_core||!routing->routes||
       routing->compartments_per_core[26]!=10u)
        return fault(s,out,2u);
    if(p07_b4m_trace_init(&ws->trace,s,ws->source_spikes,
                          ws->source_capacity)!=P07_B4M_TRACE_OK ||
       ws->trace.expected_compartments!=1010u)
        return fault(s,out,3u);
    for(i=0u;i<P07_B3_CORES;i++)
        if(routing->compartments_per_core[i]!=
           (uint16_t)((s->hw->metadata[i]>>7u)&UINT64_C(0x7ff)))
            return fault(s,out,4u);
    if(p07_b3c2_set_trace_hook(s,p07_b4m_trace_on_dispatch,
                              &ws->trace)!=P07_B3C2_OK)
        return fault(s,out,5u);
    receipt.cumulative_trace_fnv64=UINT64_C(14695981039346656037);
    for(tick=0u;tick<P07_B3_TICKS;tick++){
        if(s->pager->tick!=tick||s->pager->cursor||
           s->pager->has_pending||ws->trace.tick!=tick)
            return fault(s,out,6u);
        if(p07_b4a_prepare(&external_plan,s->pager,s->hw,in,wire,wire_bytes,
                           ws->merged_current_words,ws->merged_capacity,
                           read_ddr,reader)!=P07_B4A_OK)
            return fault(s,out,7u);
        if(p07_b4a_commit(&external_plan,&external_receipt)!=P07_B4A_OK||
           external_receipt.tick!=tick||
           external_receipt.bank!=(tick&1u))
            return fault(s,out,8u);
        receipt.external_current+=external_receipt.external_total;
        /* Bound each epoch: 27 loads, 27 dispatches, <=27 dirty saves.
         * A spurious loop or early DONE never earns a success receipt.
         */
        for(step=0u;step<4u*P07_B3_CORES+8u;step++){
            status=p07_b3c2_step(s,&op);
            if(status==P07_B3C2_BARRIER)break;
            if(status!=P07_B3C2_OK||op.tick!=tick)
                return fault(s,out,9u);
        }
        if(step==4u*P07_B3_CORES+8u||
           op.kind!=P07_B3_BARRIER||op.tick!=tick)
            return fault(s,out,10u);
        if(p07_b4m_trace_finalize(&ws->trace,&source_receipt)!=P07_B4M_TRACE_OK||
           source_receipt.magic!=P07_B4M_TRACE_MAGIC||
           source_receipt.compartments_checked!=1010u)
            return fault(s,out,11u);
        receipt.cumulative_trace_fnv64=fnv64_combine(
            receipt.cumulative_trace_fnv64,source_receipt.fnv64);
        for(i=0u;i<source_receipt.spikes;i++){
            uint32_t c=ws->source_spikes[i][0],n=ws->source_spikes[i][1];
            if(c==26u){
                if(n>=10u)return fault(s,out,12u);
                ++receipt.output_spike_counts[n];
            }
        }
        if(p07_b4m_commit_pending_barrier(
               s,&op,routing,(const uint16_t (*)[2])ws->source_spikes,
               source_receipt.spikes,ws->trace.verified,
               ws->frame_scratch,ws->scratch_capacity,
               ws->packet_frame,ws->frame_capacity,&route_receipt)
               !=P07_B4M_BRIDGE_OK ||
           route_receipt.tick!=tick||route_receipt.barrier_acks!=1u||
           route_receipt.source_spike_count!=source_receipt.spikes)
            return fault(s,out,13u);
        receipt.source_spikes+=source_receipt.spikes;
        receipt.captured_packets+=route_receipt.physical_packet_count;
        receipt.inserted_next+=route_receipt.route_inserted;
        if(p07_b4m_trace_advance(&ws->trace)!=P07_B4M_TRACE_OK)
            return fault(s,out,14u);
    }
    /* Final-flush all three dirty resident slots, not just the
     * 24 runtime evictions per tick. No refreeze of source P02 files.
     */
    for(step=0u;step<=P07_B3_SLOTS;step++){
        status=p07_b3c2_step(s,&op);
        if(status==P07_B3C2_DONE)break;
        if(status!=P07_B3C2_OK||op.kind!=P07_B3_FINAL_FLUSH)
            return fault(s,out,15u);
    }
    if(status!=P07_B3C2_DONE||s->pager->tick!=P07_B3_TICKS||
       s->pager->counters.dispatches!=P07_B3_CORES*P07_B3_TICKS||
       s->pager->counters.barriers!=P07_B3_TICKS||
       s->pager->counters.final_outs!=P07_B3_SLOTS||
       s->hw->last_error!=P03_HW_OK||s->poisoned||s->pager->failed)
        return fault(s,out,16u);
    for(i=1u;i<10u;i++)
        if(receipt.output_spike_counts[i]>receipt.output_spike_counts[best])
            best=i;
    receipt.magic=P07_B4M_FULL_MAGIC;
    receipt.barriers=s->pager->counters.barriers;
    receipt.dispatches=s->pager->counters.dispatches;
    receipt.page_ins=s->pager->counters.page_ins;
    receipt.page_outs=s->pager->counters.runtime_outs;
    receipt.final_outs=s->pager->counters.final_outs;
    receipt.trace_compartment_count=1010u;
    receipt.classification=best;
    receipt.read_bytes=s->pager->counters.read_bytes;
    receipt.write_bytes=s->pager->counters.write_bytes;
    *out=receipt;
    return P07_B4M_FULL_OK;
}
