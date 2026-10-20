/* P07-B.2b independent large per-source / NEXT bank envelope boundary.
 * Synthetic C-only frame; never touches trained weights, DDR or FPGA.
 */
#include "p07_b2_packet.h"
#include <stdio.h>
#include <string.h>
#define CHECK(expr) do { if(!(expr)) {fprintf(stderr,"CAPACITY_FAIL:%d\n",__LINE__);return 1;} } while(0)
static p07_b2b_route routes[4097];
static uint8_t wire[128u + 4096u*12u];
static void wr16(uint8_t *p,unsigned v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
}
static void wr32(uint8_t *p,uint32_t v) {
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
    p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);
}
static uint32_t crc(const uint8_t *p,size_t n,int hdr) {
    uint32_t x=UINT32_C(0xffffffff);size_t i;unsigned k;
    for(i=0;i<n;i++) {
        x^=(hdr && i>=52u && i<56u)?0u:p[i];
        for(k=0u;k<8u;k++) x=(x>>1)^((x&1u)?UINT32_C(0xEDB88320):0u);
    }
    return ~x;
}
int main(void) {
    uint16_t comps[3]={1,1,1};p07_b2b_origin spike[2]={{0,0},{1,0}};
    p07_b2b_binding b={0};p07_b2b_frame_view accepted={0},saved={0};
    uint32_t i;
    memset(wire,0,sizeof(wire));memcpy(wire,"P06B13R1",8);
    wr32(wire+8,1u);wr32(wire+12,128u);
    wr32(wire+16,4096u*12u);wr32(wire+20,0u);
    wr32(wire+24,4096u);wr32(wire+28,3u);
    wr32(wire+32,12u);wr32(wire+36,4096u);
    memset(wire+64,0x11,32);memset(wire+96,0x22,32);
    b.core_count=3;b.route_count=4096u;b.routes=routes;
    b.compartments_per_core=comps;
    memset(b.compiled_sha256,0x11,32);memset(b.capacity_sha256,0x22,32);
    for(i=0u;i<4096u;i++) {
        uint8_t *p=wire+128u+(size_t)i*12u;
        routes[i]=(p07_b2b_route){0,0,2,(uint16_t)i};
        wr32(p,1u);wr16(p+4,0u);wr16(p+6,0u);
        wr16(p+8,2u);wr16(p+10,i);
    }
    wr32(wire+48,crc(wire+128u,4096u*12u,0));
    wr32(wire+52,crc(wire,128u,1));
    CHECK(p07_b2b_decode(wire,sizeof(wire),&b,0u,spike,1u,&accepted)==P07_B2B_OK);
    CHECK(accepted.source_counts[0]==4096u && accepted.destination_counts[2]==4096u);
    saved=accepted;
    routes[4096]=(p07_b2b_route){0,0,2,4095};
    /* Per-source 4097 is illegal even if another core takes extra route. */
    routes[4096]=(p07_b2b_route){0,0,2,0};
    /* Shift the 4096 legal routes to destination core 1, then append core 2. */
    for(i=0u;i<4096u;i++) routes[i].destination_core=1;
    routes[4096]=(p07_b2b_route){0,0,2,0};
    b.route_count=4097u;
    CHECK(p07_b2b_decode(wire,sizeof(wire),&b,0u,spike,1u,&accepted)==P07_B2B_CAPACITY);
    CHECK(memcmp(&saved,&accepted,sizeof(accepted))==0);
    /* Per-destination NEXT bank 4097, split over two emitting cores. */
    for(i=0u;i<4096u;i++) routes[i].destination_core=2;
    routes[4096]=(p07_b2b_route){1,0,2,0};
    CHECK(p07_b2b_decode(wire,sizeof(wire),&b,0u,spike,2u,&accepted)==P07_B2B_CAPACITY);
    CHECK(memcmp(&saved,&accepted,sizeof(accepted))==0);
    puts("P07_B2B_NATIVE_PACKET_CAPACITY_PASS=1");return 0;
}
