#include "p07_b2b_transaction.h"
#include <string.h>
_Static_assert(sizeof(p07_b2_input_event)==4u, "event tuple layout drift");
static uint16_t b2_le16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0]|((uint16_t)p[1]<<8));
}
static uint32_t b2_crc_byte(uint32_t crc,uint8_t b) {
    unsigned k;crc ^= (uint32_t)b;
    for(k=0u;k<8u;k++) crc=(crc>>1u)^((crc&1u)?UINT32_C(0xedb88320):0u);
    return crc;
}
static uint32_t b2_crc_bytes(const uint8_t *p,size_t n) {
    uint32_t crc=UINT32_C(0xffffffff);size_t i;
    for(i=0u;i<n;i++) crc=b2_crc_byte(crc,p[i]);
    return ~crc;
}
static int b2_spikes(const uint8_t *pixels,uint32_t pix,uint32_t tick) {
    uint32_t phase,value;
    if(tick==P07_B2_INPUT_TICKS) return 0;
    phase=(tick+17u*pix)%P07_B2_INPUT_TICKS;
    value=(uint32_t)pixels[pix];
    return ((phase+1u)*value)/255u > (phase*value)/255u;
}
/* uintptr_t overlap guard: disallow pending being a view into incoming
 * immutable ingress/route/frame bytes. All range arithmetic checked. */
static int b2_overlap(const void *a,size_t a_bytes,const void *b,size_t b_bytes) {
    uintptr_t begin_a=(uintptr_t)a,begin_b=(uintptr_t)b;
    if(!a||!b||a_bytes==0u||b_bytes==0u) return 0;
    if(a_bytes>UINTPTR_MAX-begin_a||b_bytes>UINTPTR_MAX-begin_b) return 1;
    return begin_a<begin_b+b_bytes && begin_b<begin_a+a_bytes;
}
p07_b2_status p07_b2b_transaction_init(p07_b2b_transaction *state,
    const p07_b2_ingress_view *ingress,const p07_b2_packet_binding *binding,
    p07_b2_input_event *pending,size_t pending_capacity) {
    p07_b2b_transaction next={0};
    if(!state||!ingress||!ingress->routes||!ingress->pixels||
       !binding||!binding->routes||!binding->compartments_per_core||!pending||
       binding->core_count==0u||binding->core_count>P07_B2_MAX_CORES||
       binding->core_count!=ingress->core_count||
       pending_capacity==0u||pending_capacity>P07_B2B_PENDING_MAX||
       ingress->route_count>P07_B2_MAX_ROUTES) return P07_B2_ARGUMENT;
    if(b2_overlap(pending,pending_capacity*sizeof(*pending),
                  ingress->wire,ingress->wire_bytes) ||
       b2_overlap(pending,pending_capacity*sizeof(*pending),
                  binding->routes,(size_t)binding->route_count*sizeof(*binding->routes)))
        return P07_B2_ARGUMENT;
    next.ingress=ingress;next.binding=binding;next.pending=pending;
    next.pending_capacity=pending_capacity;
    *state=next;return P07_B2_OK;
}
p07_b2_status p07_b2b_transaction_step(p07_b2b_transaction *state,
    const uint8_t *wire,size_t wire_bytes,
    const uint16_t (*source_spikes)[2],size_t spike_count,
    p07_b2b_tx_receipt *receipt) {
    static const uint16_t dummy[1][2]={{0u,0u}};
    p07_b2_packet_view frame={0};
    p07_b2b_tx_receipt next={0};
    uint32_t counts[P07_B2_MAX_CORES]={0},i;
    uint32_t crc=UINT32_C(0xffffffff);
    p07_b2_status code;
    if(!state||!receipt||!state->ingress||!state->binding||!state->pending||
       !wire||(spike_count>0u&&!source_spikes)) return P07_B2_ARGUMENT;
    if(state->tick>=P07_B2_TOTAL_TICKS) return P07_B2_TICK;
    if(state->pending_capacity==0u||state->pending_capacity>P07_B2B_PENDING_MAX||
       state->pending_count>state->pending_capacity) return P07_B2_CAPACITY;
    if(b2_overlap(state->pending,state->pending_capacity*sizeof(*state->pending),
                  wire,wire_bytes) ||
       b2_overlap(state->pending,state->pending_capacity*sizeof(*state->pending),
                  state->ingress->wire,state->ingress->wire_bytes) ||
       b2_overlap(state->pending,state->pending_capacity*sizeof(*state->pending),
                  state->binding->routes,(size_t)state->binding->route_count*
                  sizeof(*state->binding->routes))) return P07_B2_ARGUMENT;
    code=p07_b2_packet_decode(wire,wire_bytes,state->binding,state->tick,
                               source_spikes?source_spikes:dummy,spike_count,&frame);
    if(code!=P07_B2_OK) return code;
    if(frame.packet_count>state->pending_capacity) return P07_B2_CAPACITY;
    /* Untrusted staged counts must match the entire staged vector before
     * CURRENT accounting; otherwise stale/corrupt bank state is rejected. */
    for(i=0u;i<state->pending_count;i++) {
        uint32_t core=state->pending[i].core_id,axon=state->pending[i].axon_id;
        if(core>=state->binding->core_count||axon>=4096u) return P07_B2_PACKET_INVALID;
        if(++counts[core]>4096u) return P07_B2_CAPACITY;
    }
    for(i=0u;i<state->binding->core_count;i++)
        if(counts[i]!=state->pending_by_core[i]) return P07_B2_PACKET_INVALID;
    next.tick=state->tick;next.current_bank=state->tick%2u;
    next.routed_current=state->pending_count;
    for(i=0u;i<state->ingress->route_count;i++) {
        const uint8_t *r=state->ingress->routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=b2_le16(r),core=b2_le16(r+2u),axon=b2_le16(r+4u);
        if(pixel>=P07_B2_IMAGE_BYTES||core>=state->binding->core_count||axon>=4096u)
            return P07_B2_PACKET_INVALID;
        if(b2_spikes(state->ingress->pixels,pixel,state->tick)) {
            ++next.external_events;
            if(++counts[core]>4096u) return P07_B2_CAPACITY;
        }
    }
    for(i=0u;i<state->binding->core_count;i++) next.current_by_core[i]=counts[i];
    next.routed_next=frame.packet_count;
    next.packet_payload_crc32=b2_crc_bytes(frame.packets,(size_t)frame.packet_count*12u);
    /* Preflight entire vector, including packet target/core/axon and origin.
     * The independent decoder has already proved canonical order and fanout.
     * Nothing has modified caller state or memory at this point. */
    for(i=0u;i<frame.packet_count;i++) {
        const uint8_t *p=frame.packets+(size_t)i*12u;
        uint32_t core=b2_le16(p+8u),axon=b2_le16(p+10u),src=b2_le16(p+4u);
        if(core>=state->binding->core_count||src>=state->binding->core_count||
           axon>=4096u) return P07_B2_PACKET_INVALID;
        if(++next.next_by_core[core]>4096u ||
           ++next.emitted_by_core[src]>4096u) return P07_B2_CAPACITY;
        crc=b2_crc_byte(crc,(uint8_t)core);
        crc=b2_crc_byte(crc,(uint8_t)(core>>8));
        crc=b2_crc_byte(crc,(uint8_t)axon);
        crc=b2_crc_byte(crc,(uint8_t)(axon>>8));
    }
    next.ordered_next_crc32=~crc;
    /* No rejection may occur after this write. Caller owns physical delivery
     * from the staged complete vector in the following B.3 scheduler. */
    for(i=0u;i<frame.packet_count;i++) {
        const uint8_t *p=frame.packets+(size_t)i*12u;
        state->pending[i].core_id=b2_le16(p+8u);
        state->pending[i].axon_id=b2_le16(p+10u);
    }
    memset(state->pending_by_core,0,sizeof(state->pending_by_core));
    memcpy(state->pending_by_core,next.next_by_core,sizeof(next.next_by_core));
    state->pending_count=frame.packet_count;
    ++state->tick;
    *receipt=next;
    return P07_B2_OK;
}
