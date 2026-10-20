/* P07-B.2b native 4096/4097 source and NEXT core limit.
 * Exactly real prior B2b decoder API; synthetic frame only.
 */
#include "p07_b2_packet.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do { if(!(x)){fprintf(stderr,"B2B_CAPACITY_FAIL:%u\n",(unsigned)__LINE__);return 1;} } while(0)
#define MAX_PACKET 4097u
static p07_b2_route routes[MAX_PACKET];
static uint8_t wire[128u+MAX_PACKET*12u];
static const uint16_t neurons[3]={1u,1u,1u};
static const uint16_t spikes[2][2]={{0u,0u},{1u,0u}};
static void u16(uint8_t *p,uint32_t x){p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8);}
static void u32(uint8_t *p,uint32_t x){
    p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8);
    p[2]=(uint8_t)(x>>16);p[3]=(uint8_t)(x>>24);
}
static uint32_t checksum(const uint8_t *p,size_t n,int head){
    uint32_t crc=UINT32_C(0xffffffff),j;size_t i;
    for(i=0u;i<n;i++){
        crc^=head&&i>=52u&&i<56u?0u:p[i];
        for(j=0u;j<8u;j++)crc=(crc>>1u)^((crc&1u)?UINT32_C(0xedb88320):0u);
    }return ~crc;
}
static void emit(uint32_t index,uint32_t src,uint32_t dst,uint32_t axon){
    uint8_t *p=wire+128u+(size_t)index*12u;
    u32(p,1u);u16(p+4u,src);u16(p+6u,0u);
    u16(p+8u,dst);u16(p+10u,axon);
}
static void seal(uint32_t count){
    memset(wire,0,128u);memcpy(wire,"P06B13R1",8u);
    u32(wire+8u,1u);u32(wire+12u,128u);u32(wire+16u,count*12u);
    u32(wire+20u,0u);u32(wire+24u,count);u32(wire+28u,3u);
    u32(wire+32u,12u);u32(wire+36u,4096u);
    memset(wire+64u,0x11,32u);memset(wire+96u,0x22,32u);
    u32(wire+48u,checksum(wire+128u,(size_t)count*12u,0));
    u32(wire+52u,checksum(wire,128u,1));
}
int main(void){
    uint32_t i;
    p07_b2_packet_binding b={0};
    p07_b2_packet_view v={0},accepted;
    b.core_count=3u;b.routes=routes;b.compartments_per_core=neurons;
    memset(b.compiled_sha256,0x11,32u);
    memset(b.capacity_sha256,0x22,32u);
    for(i=0u;i<4096u;i++){
        routes[i]=(p07_b2_route){0u,0u,2u,(uint16_t)i};
        emit(i,0u,2u,i);
    }
    b.route_count=4096u;seal(4096u);
    CHECK(p07_b2_packet_decode(wire,128u+4096u*12u,&b,0u,spikes,1u,&v)==P07_B2_OK);
    CHECK(v.packet_count==4096u);
    accepted=v;
    /* One source emits 4097 valid, unique routes, split across two destinations.
     * Both targets can individually fit, but source packet bank must reject. */
    for(i=0u;i<4096u;i++){
        routes[i].destination_core=1u;
        emit(i,0u,1u,i);
    }
    routes[4096]=(p07_b2_route){0u,0u,2u,0u};
    emit(4096u,0u,2u,0u);
    b.route_count=4097u;seal(4097u);
    CHECK(p07_b2_packet_decode(wire,128u+4097u*12u,&b,0u,spikes,1u,&v)==P07_B2_CAPACITY);
    CHECK(memcmp(&v,&accepted,sizeof(v))==0);
    /* 4097 packets to one destination, 4096 from source0 + one from
     * source1. Payload is globally sorted by destination axon then source. */
    for(i=0u;i<4096u;i++) routes[i].destination_core=2u;
    routes[4096]=(p07_b2_route){1u,0u,2u,0u};
    emit(0u,0u,2u,0u);
    emit(1u,1u,2u,0u);
    for(i=1u;i<4096u;i++)emit(i+1u,0u,2u,i);
    seal(4097u);
    CHECK(p07_b2_packet_decode(wire,128u+4097u*12u,&b,0u,spikes,2u,&v)==P07_B2_CAPACITY);
    CHECK(memcmp(&v,&accepted,sizeof(v))==0);
    puts("P07_B2B_NATIVE_PACKET_CAPACITY_PASS=1");
    return 0;
}
