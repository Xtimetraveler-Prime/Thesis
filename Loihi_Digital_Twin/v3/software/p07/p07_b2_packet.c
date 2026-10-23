#include "p07_b2_packet.h"
#include <string.h>
static uint16_t u16(const uint8_t *p){return (uint16_t)(p[0]|((uint16_t)p[1]<<8));}
static uint32_t u32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static uint32_t crc(const uint8_t *p,size_t n,int header){
    uint32_t v=UINT32_C(0xffffffff);size_t i;uint32_t k;
    for(i=0;i<n;i++){v^=(header && i>=52u && i<56u)?0u:p[i];for(k=0;k<8u;k++)v=(v>>1)^((v&1u)?UINT32_C(0xedb88320):0u);}
    return ~v;
}
static int route_order(const p07_b2_route *a,const p07_b2_route *b){
    if(a->source_core!=b->source_core)return a->source_core<b->source_core?-1:1;
    if(a->source_compartment!=b->source_compartment)return a->source_compartment<b->source_compartment?-1:1;
    if(a->destination_core!=b->destination_core)return a->destination_core<b->destination_core?-1:1;
    if(a->destination_axon!=b->destination_axon)return a->destination_axon<b->destination_axon?-1:1;
    return 0;
}
static p07_b2_packet read_packet(const uint8_t *p){
    p07_b2_packet k;k.target_tick=u32(p);k.source_core=u16(p+4u);
    k.source_compartment=u16(p+6u);k.destination_core=u16(p+8u);
    k.destination_axon=u16(p+10u);return k;
}
static int packet_order(const p07_b2_packet *a,const p07_b2_packet *b){
    if(a->destination_core!=b->destination_core)return a->destination_core<b->destination_core?-1:1;
    if(a->destination_axon!=b->destination_axon)return a->destination_axon<b->destination_axon?-1:1;
    if(a->source_core!=b->source_core)return a->source_core<b->source_core?-1:1;
    if(a->source_compartment!=b->source_compartment)return a->source_compartment<b->source_compartment?-1:1;
    return 0;
}
static int route_exists(const p07_b2_packet_binding *b,const p07_b2_packet *p){
    uint32_t lo=0u,hi=b->route_count;
    p07_b2_route wanted={p->source_core,p->source_compartment,p->destination_core,p->destination_axon};
    while(lo<hi){uint32_t mid=lo+(hi-lo)/2u;int cmp=route_order(&b->routes[mid],&wanted);
        if(cmp==0)return 1;
        if(cmp<0)lo=mid+1u;else hi=mid;
    }
    return 0;
}
static int valid_binding(const p07_b2_packet_binding *b){
    uint32_t i;uint8_t any_comp=0u,any_audit=0u;
    if(!b||!b->routes||!b->compartments_per_core||b->core_count==0u||
       b->core_count>P07_B2_MAX_CORES||b->route_count>P07_B2_MAX_ROUTE_BINDINGS)return 0;
    for(i=0u;i<32u;i++){any_comp|=b->compiled_sha256[i];any_audit|=b->capacity_sha256[i];}
    if(!any_comp||!any_audit)return 0;
    for(i=0u;i<b->core_count;i++)if(b->compartments_per_core[i]==0u||b->compartments_per_core[i]>1024u)return 0;
    for(i=0u;i<b->route_count;i++){
        const p07_b2_route *p=&b->routes[i];
        if(p->source_core>=b->core_count||p->destination_core>=b->core_count||
           p->source_compartment>=b->compartments_per_core[p->source_core]||
           p->destination_axon>=4096u||
           (i>0u&&route_order(&b->routes[i-1u],p)>=0))return 0;
    }
    return 1;
}
p07_b2_status p07_b2_packet_decode(const uint8_t *wire,size_t wire_bytes,
    const p07_b2_packet_binding *b,uint32_t tick,
    const uint16_t (*spikes)[2],size_t spike_count,p07_b2_packet_view *out){
    static const uint8_t magic[8]={'P','0','6','B','1','3','R','1'};
    uint32_t count,i,source_counts[P07_B2_MAX_CORES]={0},target_counts[P07_B2_MAX_CORES]={0};
    uint32_t source_seen=0u, previous_sc=UINT32_MAX,previous_sn=UINT32_MAX;
    p07_b2_packet_view candidate;
    if(!wire||!out||!valid_binding(b)||!spikes)return P07_B2_ARGUMENT;
    if(tick>=P07_B2_TOTAL_TICKS||spike_count>1024u*P07_B2_MAX_CORES)return P07_B2_TICK;
    if(wire_bytes<P07_B2_HEADER_BYTES)return P07_B2_BOUNDS;
    if(memcmp(wire,magic,8u)!=0||u32(wire+8u)!=1u||u32(wire+12u)!=128u||
       u32(wire+56u)!=0u||u32(wire+60u)!=0u)return P07_B2_HEADER;
    if(memcmp(wire+64u,b->compiled_sha256,32u)||memcmp(wire+96u,b->capacity_sha256,32u))
        return P07_B2_DIGEST;
    if(crc(wire,128u,1)!=u32(wire+52u))return P07_B2_CRC;
    count=u32(wire+24u);
    if(u32(wire+20u)!=tick||u32(wire+28u)!=b->core_count||
       u32(wire+32u)!=12u||u32(wire+36u)!=4096u||
       u32(wire+40u)!=0u||u32(wire+44u)!=0u||
       count>b->route_count||u32(wire+16u)!=(uint64_t)count*12u||
       (uint64_t)wire_bytes!=128u+(uint64_t)count*12u)return P07_B2_BOUNDS;
    if(crc(wire+128u,wire_bytes-128u,0)!=u32(wire+48u))return P07_B2_CRC;
    for(i=0u;i<spike_count;i++){
        uint32_t core=spikes[i][0], neuron=spikes[i][1];
        if(core>=b->core_count||neuron>=b->compartments_per_core[core]||
           (previous_sc!=UINT32_MAX &&
            (core<previous_sc||(core==previous_sc&&neuron<=previous_sn))))
            return P07_B2_PACKET_INVALID;
        previous_sc=core;previous_sn=neuron;
    }
    for(i=0u;i<count;i++){
        p07_b2_packet p=read_packet(wire+128u+(size_t)i*12u);
        if(p.target_tick!=tick+1u||p.source_core>=b->core_count||
           p.destination_core>=b->core_count||p.destination_axon>=4096u||
           p.source_compartment>=b->compartments_per_core[p.source_core]||
           !route_exists(b,&p))return P07_B2_PACKET_INVALID;
        if(i){p07_b2_packet prior=read_packet(wire+128u+(size_t)(i-1u)*12u);
            if(packet_order(&prior,&p)>=0)return P07_B2_PACKET_INVALID;}
        if(++source_counts[p.source_core]>4096u||++target_counts[p.destination_core]>4096u)
            return P07_B2_CAPACITY;
    }
    /* Complete fanout for every authoritative emitting source. Each routed
     * entry must occur once; match counts and explicit existence against a
     * verified source-spike set. O(routes * spikes) is B.2b bounded native
     * feasibility work, not an optimized physical firmware scheduler.
     */
    for(i=0u;i<b->route_count;i++){
        const p07_b2_route *route=&b->routes[i];size_t j;int emits=0;
        for(j=0u;j<spike_count;j++){
            if(spikes[j][0]==route->source_core&&spikes[j][1]==route->source_compartment)
                {emits=1;break;}
        }
        if(emits){
            uint32_t k;int found=0;
            for(k=0u;k<count;k++){
                p07_b2_packet p=read_packet(wire+128u+(size_t)k*12u);
                if(p.source_core==route->source_core&&
                   p.source_compartment==route->source_compartment&&
                   p.destination_core==route->destination_core&&
                   p.destination_axon==route->destination_axon){found=1;break;}
            }
            if(!found)return P07_B2_PACKET_INVALID;
            ++source_seen;
        }
    }
    if(source_seen!=count)return P07_B2_PACKET_INVALID;
    if(tick==P07_B2_TOTAL_TICKS-1u&&count!=0u)return P07_B2_PACKET_EPOCH;
    candidate.wire=wire;candidate.packets=wire+128u;
    candidate.emitted_tick=tick;candidate.packet_count=count;
    *out=candidate;return P07_B2_OK;
}
p07_b2_status p07_b2_packet_commit(const p07_b2_packet_view *frame,
    const p07_b2_packet_binding *b,const uint32_t *external,
    p07_b2_epoch_state *state,p07_b2_packet_receipt *receipt){
    p07_b2_packet_receipt next={0};p07_b2_epoch_state updated;uint32_t i;
    if(!frame||!frame->packets||!valid_binding(b)||!external||!state||!receipt)
        return P07_B2_ARGUMENT;
    if(frame->emitted_tick!=state->tick||state->tick>=P07_B2_TOTAL_TICKS||
       frame->packet_count>b->route_count)return P07_B2_PACKET_EPOCH;
    updated=*state;
    for(i=0u;i<b->core_count;i++){
        if(external[i]>4096u||state->pending_current[i]>4096u||
           external[i]+state->pending_current[i]>4096u)return P07_B2_CAPACITY;
        next.current[i]=external[i]+state->pending_current[i];
        next.consumed_routed+=state->pending_current[i];
        updated.pending_current[i]=0u;
    }
    for(i=0u;i<frame->packet_count;i++){
        p07_b2_packet p=read_packet(frame->packets+(size_t)i*12u);
        if(p.target_tick!=state->tick+1u||p.destination_core>=b->core_count||
           p.source_core>=b->core_count)return P07_B2_PACKET_EPOCH;
        if(++next.next[p.destination_core]>4096u||
           ++next.emitted_by_core[p.source_core]>4096u)return P07_B2_CAPACITY;
    }
    if(state->tick==P07_B2_TOTAL_TICKS-1u&&frame->packet_count)return P07_B2_PACKET_EPOCH;
    for(i=0u;i<b->core_count;i++)updated.pending_current[i]=next.next[i];
    updated.tick++;
    next.emitted=frame->packet_count;
    *receipt=next;*state=updated;return P07_B2_OK;
}
