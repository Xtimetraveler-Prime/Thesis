#include "p07_b2_packet.h"
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"B2b failed line %d: %s\n",__LINE__,#x);return 1;}}while(0)
static uint8_t wire[140];
static uint32_t crc(const uint8_t *p,size_t n,int head){
    uint32_t c=0xffffffffu;size_t i;int k;
    for(i=0;i<n;i++){c^=(head&&i>=52u&&i<56u)?0:p[i];for(k=0;k<8;k++)c=(c>>1)^((c&1u)?0xedb88320u:0);}
    return ~c;
}
static void w32(unsigned off,uint32_t v){wire[off]=(uint8_t)v;wire[off+1]=(uint8_t)(v>>8);wire[off+2]=(uint8_t)(v>>16);wire[off+3]=(uint8_t)(v>>24);}
static void w16(unsigned off,uint16_t v){wire[off]=(uint8_t)v;wire[off+1]=(uint8_t)(v>>8);}
static size_t pack(uint32_t tick,int emitted){
    size_t n=128u+(emitted?12u:0u);memset(wire,0,sizeof(wire));
    memcpy(wire,"P06B13R1",8);w32(8,1);w32(12,128);w32(16,emitted?12:0);
    w32(20,tick);w32(24,emitted?1:0);w32(28,2);w32(32,12);w32(36,4096);
    memset(wire+64,0x11,32);memset(wire+96,0x22,32);
    if(emitted){w32(128,tick+1);w16(132,0);w16(134,0);w16(136,1);w16(138,7);}
    w32(48,crc(wire+128,n-128,0));w32(52,crc(wire,128,1));return n;
}
int main(void){
    const p07_b2_route routes[]={{0,0,1,7}};
    const uint16_t compartments[]={1,1};
    const uint16_t spike[][2]={{0,0}};
    const uint16_t none[][2]={{0,0}};
    uint32_t external[2]={784,0};
    p07_b2_packet_binding b={0};
    p07_b2_packet_view view={0},old;
    p07_b2_epoch_state state={0}, saved;
    p07_b2_packet_receipt receipt={0}, snapshot;
    size_t n;uint32_t tick;
    b.core_count=2;b.route_count=1;b.routes=routes;b.compartments_per_core=compartments;
    memset(b.compiled_sha256,0x11,32);memset(b.capacity_sha256,0x22,32);
    n=pack(0,1);
    CHECK(p07_b2_packet_decode(wire,n,&b,0,spike,1,&view)==P07_B2_OK);
    old=view;
    wire[48]^=1u;
    CHECK(p07_b2_packet_decode(wire,n,&b,0,spike,1,&view)==P07_B2_CRC);
    CHECK(memcmp(&view,&old,sizeof(view))==0);wire[48]^=1u;
    CHECK(p07_b2_packet_decode(wire,n,&b,0,none,0,&view)==P07_B2_PACKET_INVALID);
    CHECK(p07_b2_packet_decode(wire,n,&b,0,spike,1,&view)==P07_B2_OK);
    CHECK(p07_b2_packet_commit(&view,&b,external,&state,&receipt)==P07_B2_OK);
    CHECK(state.tick==1u&&state.pending_current[1]==1u);
    CHECK(receipt.current[0]==784u&&receipt.next[1]==1u&&receipt.emitted==1u);
    saved=state;snapshot=receipt;
    external[1]=4096u;n=pack(1,0);
    CHECK(p07_b2_packet_decode(wire,n,&b,1,none,0,&view)==P07_B2_OK);
    CHECK(p07_b2_packet_commit(&view,&b,external,&state,&receipt)==P07_B2_CAPACITY);
    CHECK(memcmp(&saved,&state,sizeof(state))==0);
    CHECK(memcmp(&snapshot,&receipt,sizeof(receipt))==0);
    external[1]=4095u;
    CHECK(p07_b2_packet_commit(&view,&b,external,&state,&receipt)==P07_B2_OK);
    CHECK(receipt.current[1]==4096u&&state.tick==2u);
    external[0]=0;external[1]=0;
    for(tick=2;tick<26;tick++){
        n=pack(tick,0);
        CHECK(p07_b2_packet_decode(wire,n,&b,tick,none,0,&view)==P07_B2_OK);
        CHECK(p07_b2_packet_commit(&view,&b,external,&state,&receipt)==P07_B2_OK);
    }
    CHECK(state.tick==26u);
    n=pack(25,1);
    CHECK(p07_b2_packet_decode(wire,n,&b,25,spike,1,&view)==P07_B2_PACKET_EPOCH);
    CHECK(p07_b2_packet_decode(wire,n,&b,26,spike,1,&view)==P07_B2_TICK);
    puts("P07_B2B_NATIVE_PACKET_EPOCH_PASS=1");return 0;
}
