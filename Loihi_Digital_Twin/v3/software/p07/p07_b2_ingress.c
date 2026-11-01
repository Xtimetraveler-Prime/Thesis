#include "p07_b2_ingress.h"
#include <string.h>
_Static_assert(sizeof(p07_b2_input_event) == 4u, "u16/u16 event ABI changed");
_Static_assert(P07_B2_MAX_FRAME_BYTES <= 0x000E0000u, "P05 staging reservation too small");
static uint16_t le16(const uint8_t *p) {
    return (uint16_t)((uint16_t)p[0] | (uint16_t)((uint16_t)p[1] << 8));
}
static uint32_t le32(const uint8_t *p) {
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint32_t crc_byte(uint32_t crc, uint8_t data) {
    uint32_t i;
    crc ^= (uint32_t)data;
    for (i=0u;i<8u;i++)
        crc = (crc >> 1) ^ ((crc & 1u) ? UINT32_C(0xEDB88320) : 0u);
    return crc;
}
static uint32_t crc_bytes(const uint8_t *p, size_t n, int zero_header_crc) {
    uint32_t crc=UINT32_C(0xFFFFFFFF);
    size_t i;
    for (i=0u;i<n;i++)
        crc=crc_byte(crc, (zero_header_crc && i>=52u && i<56u) ? 0u : p[i]);
    return ~crc;
}
static int nonzero_sha(const uint8_t *p) {
    size_t i;
    for(i=0;i<32u;i++) if (p[i]!=0u) return 1;
    return 0;
}
static int firing(uint8_t pixel, uint32_t index, uint32_t tick) {
    uint32_t phase;
    if (tick==P07_B2_INPUT_TICKS) return 0;
    phase=(tick+17u*index)%P07_B2_INPUT_TICKS;
    return ((phase+1u)*(uint32_t)pixel)/255u >
           (phase*(uint32_t)pixel)/255u;
}
p07_b2_status p07_b2_decode_ingress(const uint8_t *wire, size_t wire_bytes,
                                     const p07_b2_ingress_binding *trusted,
                                     p07_b2_ingress_view *out) {
    static const uint8_t magic[8]={'P','0','6','B','1','3','I','1'};
    uint32_t route_count, payload_bytes, core_count, i;
    uint32_t counts[P07_B2_MAX_CORES]={0};
    uint32_t expected_pixel=0u;
    uint32_t last_core=UINT32_MAX;
    size_t n_route_bytes;
    const uint8_t *routes;
    p07_b2_ingress_view candidate;
    if (!wire || !trusted || !out || !trusted->trusted_routes)
        return P07_B2_ARGUMENT;
    if (trusted->core_count==0u || trusted->core_count>P07_B2_MAX_CORES ||
        trusted->route_count<P07_B2_IMAGE_BYTES || trusted->route_count>P07_B2_MAX_ROUTES ||
        !nonzero_sha(trusted->compiled_sha256) || !nonzero_sha(trusted->capacity_sha256))
        return P07_B2_ARGUMENT;
    n_route_bytes=(size_t)trusted->route_count*P07_B2_ROUTE_BYTES;
    if(trusted->trusted_routes_bytes!=n_route_bytes) return P07_B2_ARGUMENT;
    if (wire_bytes<P07_B2_HEADER_BYTES) return P07_B2_BOUNDS;
    if (memcmp(wire,magic,8u)!=0 || le32(wire+8u)!=P07_B2_INGRESS_VERSION ||
        le32(wire+12u)!=P07_B2_HEADER_BYTES || le32(wire+56u)!=0u ||
        le32(wire+60u)!=0u)
        return P07_B2_HEADER;
    if(memcmp(wire+64u,trusted->compiled_sha256,32u)!=0 ||
       memcmp(wire+96u,trusted->capacity_sha256,32u)!=0)
        return P07_B2_DIGEST;
    if(crc_bytes(wire,P07_B2_HEADER_BYTES,1)!=le32(wire+52u)) return P07_B2_CRC;
    payload_bytes=le32(wire+16u); route_count=le32(wire+20u);
    core_count=le32(wire+24u);
    if(core_count!=trusted->core_count || route_count!=trusted->route_count ||
       le32(wire+28u)!=P07_B2_IMAGE_BYTES ||
       le32(wire+32u)!=P07_B2_INPUT_TICKS ||
       le32(wire+36u)!=P07_B2_TOTAL_TICKS ||
       le32(wire+40u)!=P07_B2_ROUTE_BYTES ||
       le32(wire+44u)!=P07_B2_IMAGE_BYTES ||
       (uint64_t)payload_bytes!=(uint64_t)n_route_bytes+P07_B2_IMAGE_BYTES ||
       (uint64_t)wire_bytes!=(uint64_t)P07_B2_HEADER_BYTES+payload_bytes ||
       wire_bytes>P07_B2_MAX_FRAME_BYTES)
        return P07_B2_BOUNDS;
    routes=wire+P07_B2_HEADER_BYTES;
    if(crc_bytes(routes,payload_bytes,0)!=le32(wire+48u)) return P07_B2_CRC;
    if(memcmp(routes,trusted->trusted_routes,n_route_bytes)!=0) return P07_B2_ROUTE;
    for(i=0u;i<route_count;i++) {
        const uint8_t *r=routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=le16(r), core=le16(r+2u), axon=le16(r+4u);
        if(pixel>=P07_B2_IMAGE_BYTES || core>=core_count || axon>=4096u)
            return P07_B2_ROUTE;
        if(i==0u) {
            if(pixel!=0u) return P07_B2_ROUTE;
        } else if(pixel!=expected_pixel) {
            if(pixel!=expected_pixel+1u) return P07_B2_ROUTE;
            last_core=UINT32_MAX;
        }
        if(last_core!=UINT32_MAX && core<=last_core) return P07_B2_ROUTE;
        last_core=core; expected_pixel=pixel;
        if(++counts[core]>P07_B2_PER_CORE_DEPTH) return P07_B2_CAPACITY;
    }
    if(expected_pixel!=P07_B2_IMAGE_BYTES-1u) return P07_B2_ROUTE;
    candidate.wire=wire; candidate.wire_bytes=wire_bytes;
    candidate.routes=routes; candidate.pixels=routes+n_route_bytes;
    candidate.route_count=route_count; candidate.core_count=core_count;
    *out=candidate;
    return P07_B2_OK;
}
p07_b2_status p07_b2_ingress_tick(const p07_b2_ingress_view *view, uint32_t tick,
                                   p07_b2_input_event *events, size_t event_capacity,
                                   p07_b2_ingress_receipt *receipt) {
    p07_b2_ingress_receipt candidate={0};
    uint32_t i, count=0u, crc=UINT32_C(0xFFFFFFFF);
    if(!view || !view->routes || !view->pixels || !receipt ||
       view->core_count==0u || view->core_count>P07_B2_MAX_CORES ||
       view->route_count>P07_B2_MAX_ROUTES)
        return P07_B2_ARGUMENT;
    if(tick>=P07_B2_TOTAL_TICKS) return P07_B2_TICK;
    for(i=0u;i<view->route_count;i++) {
        const uint8_t *r=view->routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=le16(r);
        uint32_t core=le16(r+2u);
        if(pixel>=P07_B2_IMAGE_BYTES || core>=view->core_count) return P07_B2_ROUTE;
        if(firing(view->pixels[pixel],pixel,tick)) {
            ++count;
            if(++candidate.counts[core]>P07_B2_PER_CORE_DEPTH)
                return P07_B2_CAPACITY;
        }
    }
    if((size_t)count>event_capacity || (count>0u && !events))
        return P07_B2_CAPACITY;
    count=0u;
    for(i=0u;i<view->route_count;i++) {
        const uint8_t *r=view->routes+(size_t)i*P07_B2_ROUTE_BYTES;
        uint32_t pixel=le16(r);
        uint16_t core=le16(r+2u),axon=le16(r+4u);
        if(firing(view->pixels[pixel],pixel,tick)) {
            uint8_t bytes[4];
            events[count].core_id=core; events[count].axon_id=axon;
            bytes[0]=(uint8_t)core; bytes[1]=(uint8_t)(core>>8);
            bytes[2]=(uint8_t)axon; bytes[3]=(uint8_t)(axon>>8);
            crc=crc_byte(crc,bytes[0]); crc=crc_byte(crc,bytes[1]);
            crc=crc_byte(crc,bytes[2]); crc=crc_byte(crc,bytes[3]);
            ++count;
        }
    }
    candidate.total=count; candidate.event_crc32=~crc;
    *receipt=candidate;
    return P07_B2_OK;
}
