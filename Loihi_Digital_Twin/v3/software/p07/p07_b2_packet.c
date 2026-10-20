#include "p07_b2_packet.h"
#include <string.h>
_Static_assert(sizeof(p07_b2b_route)==8u,"trusted route layout");
_Static_assert(sizeof(p07_b2b_origin)==4u,"origin layout");
_Static_assert(sizeof(p07_b2b_packet)==12u,"decoded packet layout");
_Static_assert(P07_B2B_MAX_FRAME_PACKETS==76448u,"staging envelope drift");
static uint16_t rd16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1]<<8));
}
static uint32_t rd32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8) |
           ((uint32_t)p[2]<<16) | ((uint32_t)p[3]<<24);
}
static uint32_t crc_byte(uint32_t crc,uint8_t b) {
    uint32_t k; crc^=(uint32_t)b;
    for(k=0u;k<8u;k++) crc=(crc>>1) ^ ((crc&1u)?UINT32_C(0xEDB88320):0u);
    return crc;
}
static uint32_t crc_bytes(const uint8_t *p,size_t n,int zero_crc) {
    size_t i; uint32_t c=UINT32_C(0xFFFFFFFF);
    for(i=0u;i<n;i++) c=crc_byte(c,zero_crc && i>=52u && i<56u ? 0u:p[i]);
    return ~c;
}
static int good_sha(const uint8_t *sha) {
    unsigned i;
    for(i=0u;i<32u;i++) if(sha[i]) return 1;
    return 0;
}
static int routecmp(const p07_b2b_route *a,const p07_b2b_route *b) {
    if(a->source_core!=b->source_core) return a->source_core<b->source_core?-1:1;
    if(a->source_compartment!=b->source_compartment)
        return a->source_compartment<b->source_compartment?-1:1;
    if(a->destination_core!=b->destination_core) return a->destination_core<b->destination_core?-1:1;
    if(a->destination_axon!=b->destination_axon) return a->destination_axon<b->destination_axon?-1:1;
    return 0;
}
static p07_b2b_status valid_binding(const p07_b2b_binding *b) {
    uint32_t i,src_count[P07_B2_MAX_CORES]={0},dest_count[P07_B2_MAX_CORES]={0};
    if(!b || !b->compartments_per_core || (b->route_count && !b->routes) ||
       !b->core_count || b->core_count>P07_B2_MAX_CORES ||
       b->route_count>P07_B2B_MAX_FRAME_PACKETS ||
       !good_sha(b->compiled_sha256) || !good_sha(b->capacity_sha256))
        return P07_B2B_ARGUMENT;
    for(i=0u;i<b->core_count;i++)
        if(!b->compartments_per_core[i] || b->compartments_per_core[i]>P07_B2B_COMPARTMENTS)
            return P07_B2B_ARGUMENT;
    for(i=0u;i<b->route_count;i++) {
        const p07_b2b_route *r=&b->routes[i];
        if(r->source_core>=b->core_count ||
           r->source_compartment>=b->compartments_per_core[r->source_core] ||
           r->destination_core>=b->core_count || r->destination_axon>=4096u ||
           (i && routecmp(&b->routes[i-1u],r)>=0)) return P07_B2B_ROUTE;
        if(++src_count[r->source_core]>4096u || ++dest_count[r->destination_core]>4096u)
            return P07_B2B_CAPACITY;
    }
    return P07_B2B_OK;
}
static p07_b2b_packet read_packet(const uint8_t *p) {
    p07_b2b_packet v;
    v.target_tick=rd32(p); v.source_core=rd16(p+4u);
    v.source_compartment=rd16(p+6u); v.destination_core=rd16(p+8u);
    v.destination_axon=rd16(p+10u); return v;
}
/* SpikePacket.logical_key: target, dest_core, dest_axon, src_core, src_comp.
 * Source tick and class are fixed by the frame, so this order is exact. */
static int packetcmp(p07_b2b_packet a,p07_b2b_packet b) {
    if(a.target_tick!=b.target_tick) return a.target_tick<b.target_tick?-1:1;
    if(a.destination_core!=b.destination_core) return a.destination_core<b.destination_core?-1:1;
    if(a.destination_axon!=b.destination_axon) return a.destination_axon<b.destination_axon?-1:1;
    if(a.source_core!=b.source_core) return a.source_core<b.source_core?-1:1;
    if(a.source_compartment!=b.source_compartment)
        return a.source_compartment<b.source_compartment?-1:1;
    return 0;
}
static int has_output_route(const p07_b2b_binding *b,p07_b2b_route query) {
    size_t l=0u,h=b->route_count;
    while(l<h) {
        size_t mid=l+(h-l)/2u; int c=routecmp(&b->routes[mid],&query);
        if(!c) return 1;
        if(c<0) l=mid+1u; else h=mid;
    }
    return 0;
}
static int has_packet(const uint8_t *payload,uint32_t count,p07_b2b_route r,uint32_t tick) {
    p07_b2b_packet expected,got;
    size_t l=0u,h=count;
    expected.target_tick=tick+1u;expected.source_core=r.source_core;
    expected.source_compartment=r.source_compartment;
    expected.destination_core=r.destination_core;expected.destination_axon=r.destination_axon;
    while(l<h) {
        size_t mid=l+(h-l)/2u;
        got=read_packet(payload+mid*P07_B2B_PACKET_BYTES);
        { int c=packetcmp(got,expected);
          if(!c) return 1;
          if(c<0) l=mid+1u; else h=mid; }
    }
    return 0;
}
static int has_origin(const p07_b2b_origin *spikes,size_t count,
                      uint16_t core,uint16_t comp) {
    size_t i;
    for(i=0u;i<count;i++)
        if(spikes[i].core==core && spikes[i].compartment==comp) return 1;
    return 0;
}
p07_b2b_status p07_b2b_decode(const uint8_t *frame,size_t frame_bytes,
        const p07_b2b_binding *trusted,uint32_t emitted_tick,
        const p07_b2b_origin *source_spikes,size_t source_count,
        p07_b2b_frame_view *out) {
    static const uint8_t magic[8]={'P','0','6','B','1','3','R','1'};
    p07_b2b_frame_view candidate;uint32_t n,payload_bytes,i,matched=0u;
    size_t j;p07_b2b_packet prior={0};p07_b2b_status status;
    if(!frame || !out || (source_count && !source_spikes)) return P07_B2B_ARGUMENT;
    status=valid_binding(trusted);
    if(status!=P07_B2B_OK) return status;
    if(source_count>(size_t)trusted->core_count*P07_B2B_COMPARTMENTS)
        return P07_B2B_PROVENANCE;
    if(emitted_tick>=P07_B2_TOTAL_TICKS) return P07_B2B_TICK;
    if(frame_bytes<P07_B2B_FRAME_HEADER) return P07_B2B_BOUNDS;
    if(memcmp(frame,magic,8u)!=0 || rd32(frame+8u)!=1u ||
       rd32(frame+12u)!=P07_B2B_FRAME_HEADER || rd32(frame+56u)!=0u ||
       rd32(frame+60u)!=0u) return P07_B2B_HEADER;
    if(memcmp(frame+64u,trusted->compiled_sha256,32u)!=0 ||
       memcmp(frame+96u,trusted->capacity_sha256,32u)!=0)
        return P07_B2B_DIGEST;
    if(crc_bytes(frame,P07_B2B_FRAME_HEADER,1)!=rd32(frame+52u))
        return P07_B2B_CRC;
    n=rd32(frame+24u);payload_bytes=rd32(frame+16u);
    if(rd32(frame+20u)!=emitted_tick || rd32(frame+28u)!=trusted->core_count ||
       rd32(frame+32u)!=P07_B2B_PACKET_BYTES || rd32(frame+36u)!=4096u ||
       rd32(frame+40u)!=0u || rd32(frame+44u)!=0u ||
       n>P07_B2B_MAX_FRAME_PACKETS ||
       (uint64_t)n>(uint64_t)trusted->core_count*4096u ||
       (uint64_t)payload_bytes!=(uint64_t)n*P07_B2B_PACKET_BYTES ||
       (uint64_t)frame_bytes!=(uint64_t)P07_B2B_FRAME_HEADER+payload_bytes ||
       frame_bytes>P07_B2B_STAGING_BYTES) return P07_B2B_BOUNDS;
    if(crc_bytes(frame+P07_B2B_FRAME_HEADER,payload_bytes,0)!=rd32(frame+48u))
        return P07_B2B_CRC;
    /* The actual HLS source-spike list must be independent of packet bytes.
     * Readout spikes with no outgoing routes are allowed. */
    for(j=0u;j<source_count;j++) {
        size_t k;
        if(source_spikes[j].core>=trusted->core_count ||
           source_spikes[j].compartment>=trusted->compartments_per_core[source_spikes[j].core])
            return P07_B2B_PROVENANCE;
        for(k=0u;k<j;k++)
            if(source_spikes[k].core==source_spikes[j].core &&
               source_spikes[k].compartment==source_spikes[j].compartment)
                return P07_B2B_PROVENANCE;
    }
    memset(&candidate,0,sizeof(candidate));
    candidate.wire=frame;candidate.wire_bytes=frame_bytes;
    candidate.emitted_tick=emitted_tick;candidate.packet_count=n;
    candidate.payload=frame+P07_B2B_FRAME_HEADER;
    for(i=0u;i<n;i++) {
        p07_b2b_packet v=read_packet(candidate.payload+(size_t)i*P07_B2B_PACKET_BYTES);
        p07_b2b_route route;
        if(v.target_tick!=emitted_tick+1u || v.source_core>=trusted->core_count ||
           v.destination_core>=trusted->core_count || v.destination_axon>=4096u ||
           v.source_compartment>=trusted->compartments_per_core[v.source_core])
            return P07_B2B_ROUTE;
        if(i && packetcmp(prior,v)>=0) return P07_B2B_ORDER;
        prior=v;
        route.source_core=v.source_core;route.source_compartment=v.source_compartment;
        route.destination_core=v.destination_core;route.destination_axon=v.destination_axon;
        if(!has_output_route(trusted,route)) return P07_B2B_ROUTE;
        if(!has_origin(source_spikes,source_count,v.source_core,v.source_compartment))
            return P07_B2B_PROVENANCE;
        if(++candidate.source_counts[v.source_core]>4096u ||
           ++candidate.destination_counts[v.destination_core]>4096u)
            return P07_B2B_CAPACITY;
    }
    /* Require all routes for every independently observed emitting origin. */
    for(i=0u;i<trusted->route_count;i++) {
        p07_b2b_route r=trusted->routes[i];
        if(has_origin(source_spikes,source_count,r.source_core,r.source_compartment)) {
            if(!has_packet(candidate.payload,n,r,emitted_tick))
                return P07_B2B_ROUTE;
            ++matched;
        }
    }
    if(matched!=n) return P07_B2B_ROUTE;
    *out=candidate;return P07_B2B_OK;
}
p07_b2b_status p07_b2b_epoch_init(p07_b2b_epoch *state,
     const p07_b2_ingress_view *ingress,const p07_b2b_binding *trusted,
     p07_b2_input_event *pending,size_t pending_capacity) {
    p07_b2b_epoch candidate;p07_b2b_status status=valid_binding(trusted);
    if(status!=P07_B2B_OK) return status;
    if(!state || !ingress || !ingress->routes || !ingress->pixels ||
       ingress->core_count!=trusted->core_count ||
       !pending || !pending_capacity || pending_capacity>P07_B2B_MAX_FRAME_PACKETS)
        return P07_B2B_ARGUMENT;
    memset(&candidate,0,sizeof(candidate));
    candidate.ingress=ingress;candidate.binding=trusted;
    candidate.pending=pending;candidate.pending_capacity=pending_capacity;
    *state=candidate;return P07_B2B_OK;
}
static int fired(uint8_t intensity,uint32_t pixel,uint32_t tick) {
    uint32_t phase;
    if(tick==P07_B2_INPUT_TICKS) return 0;
    phase=(tick+17u*pixel)%P07_B2_INPUT_TICKS;
    return ((phase+1u)*(uint32_t)intensity)/255u >
           (phase*(uint32_t)intensity)/255u;
}
p07_b2b_status p07_b2b_step(p07_b2b_epoch *state,
     const uint8_t *packet_frame,size_t frame_bytes,
     const p07_b2b_origin *source_spikes,size_t source_count,
     p07_b2b_receipt *out) {
    p07_b2b_frame_view frame;p07_b2b_receipt candidate={0};
    p07_b2b_status status;uint32_t i;
    if(!state || !out || !state->ingress || !state->binding || !state->pending)
        return P07_B2B_ARGUMENT;
    if(state->tick>=P07_B2_TOTAL_TICKS) return P07_B2B_TICK;
    /* Reject simple input/NEXT staging alias before any possible write. */
    if(packet_frame && frame_bytes &&
       (uintptr_t)state->pending < (uintptr_t)packet_frame+frame_bytes &&
       (uintptr_t)packet_frame < (uintptr_t)state->pending+
           state->pending_capacity*sizeof(*state->pending))
        return P07_B2B_ARGUMENT;
    status=p07_b2b_decode(packet_frame,frame_bytes,state->binding,state->tick,
                          source_spikes,source_count,&frame);
    if(status!=P07_B2B_OK) return status;
    if(state->pending_count>state->pending_capacity ||
       state->pending_count>P07_B2B_MAX_FRAME_PACKETS) return P07_B2B_CAPACITY;
    for(i=0u;i<state->pending_count;i++) {
        uint32_t core=state->pending[i].core_id;
        if(core>=state->binding->core_count || state->pending[i].axon_id>=4096u ||
           ++candidate.current_by_core[core]>4096u) return P07_B2B_CAPACITY;
    }
    for(i=0u;i<state->binding->core_count;i++)
        if(candidate.current_by_core[i]!=state->pending_by_core[i])
            return P07_B2B_CAPACITY;
    for(i=0u;i<state->ingress->route_count;i++) {
        const uint8_t *r=state->ingress->routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=rd16(r),core=rd16(r+2u);
        if(pixel>=P07_B2_IMAGE_BYTES || core>=state->binding->core_count ||
           rd16(r+4u)>=4096u) return P07_B2B_ROUTE;
        if(fired(state->ingress->pixels[pixel],pixel,state->tick)) {
            ++candidate.external_total;
            if(++candidate.current_by_core[core]>4096u) return P07_B2B_CAPACITY;
        }
    }
    if(frame.packet_count>state->pending_capacity) return P07_B2B_CAPACITY;
    if(state->tick==P07_B2_TOTAL_TICKS-1u && frame.packet_count)
        return P07_B2B_FINAL;
    candidate.tick=state->tick;candidate.current_bank=state->tick%2u;
    candidate.routed_current=state->pending_count;candidate.routed_next=frame.packet_count;
    candidate.packet_payload_crc32=crc_bytes(frame.payload,
                                 (size_t)frame.packet_count*P07_B2B_PACKET_BYTES,0);
    for(i=0u;i<state->binding->core_count;i++) {
        candidate.next_by_core[i]=frame.destination_counts[i];
        candidate.emitted_by_core[i]=frame.source_counts[i];
    }
    /* Atomic host commit point. No fallible operations below. */
    for(i=0u;i<frame.packet_count;i++) {
        p07_b2b_packet p=read_packet(frame.payload+(size_t)i*P07_B2B_PACKET_BYTES);
        state->pending[i].core_id=p.destination_core;
        state->pending[i].axon_id=p.destination_axon;
    }
    memcpy(state->pending_by_core,candidate.next_by_core,sizeof(state->pending_by_core));
    state->pending_count=frame.packet_count;
    ++state->tick;*out=candidate;
    return P07_B2B_OK;
}
