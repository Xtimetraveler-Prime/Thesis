#include "include/p07_a2_sha256.h"

#include <string.h>

static const uint32_t constants[64] = {
  0x428a2f98u,0x71374491u,0xb5c0fbcfu,0xe9b5dba5u,0x3956c25bu,0x59f111f1u,0x923f82a4u,0xab1c5ed5u,
  0xd807aa98u,0x12835b01u,0x243185beu,0x550c7dc3u,0x72be5d74u,0x80deb1feu,0x9bdc06a7u,0xc19bf174u,
  0xe49b69c1u,0xefbe4786u,0x0fc19dc6u,0x240ca1ccu,0x2de92c6fu,0x4a7484aau,0x5cb0a9dcu,0x76f988dau,
  0x983e5152u,0xa831c66du,0xb00327c8u,0xbf597fc7u,0xc6e00bf3u,0xd5a79147u,0x06ca6351u,0x14292967u,
  0x27b70a85u,0x2e1b2138u,0x4d2c6dfcu,0x53380d13u,0x650a7354u,0x766a0abbu,0x81c2c92eu,0x92722c85u,
  0xa2bfe8a1u,0xa81a664bu,0xc24b8b70u,0xc76c51a3u,0xd192e819u,0xd6990624u,0xf40e3585u,0x106aa070u,
  0x19a4c116u,0x1e376c08u,0x2748774cu,0x34b0bcb5u,0x391c0cb3u,0x4ed8aa4au,0x5b9cca4fu,0x682e6ff3u,
  0x748f82eeu,0x78a5636fu,0x84c87814u,0x8cc70208u,0x90befffau,0xa4506cebu,0xbef9a3f7u,0xc67178f2u
};
static uint32_t rotr(uint32_t value, uint32_t bits)
{
    return (value >> bits) | (value << (32u - bits));
}
static uint32_t get32(const uint8_t *p)
{
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | (uint32_t)p[3];
}
static void process(const uint8_t block[64], uint32_t state[8])
{
    uint32_t schedule[64],a,b,c,d,e,f,g,h,j;
    for (j=0;j<16u;++j) schedule[j]=get32(block+j*4u);
    for (j=16;j<64u;++j) {
        uint32_t a0=rotr(schedule[j-15u],7u)^rotr(schedule[j-15u],18u)^(schedule[j-15u]>>3);
        uint32_t a1=rotr(schedule[j-2u],17u)^rotr(schedule[j-2u],19u)^(schedule[j-2u]>>10);
        schedule[j]=schedule[j-16u]+a0+schedule[j-7u]+a1;
    }
    a=state[0];b=state[1];c=state[2];d=state[3];
    e=state[4];f=state[5];g=state[6];h=state[7];
    for(j=0;j<64u;++j) {
        uint32_t s1=rotr(e,6u)^rotr(e,11u)^rotr(e,25u);
        uint32_t ch=(e&f)^((~e)&g);
        uint32_t temp1=h+s1+ch+constants[j]+schedule[j];
        uint32_t s0=rotr(a,2u)^rotr(a,13u)^rotr(a,22u);
        uint32_t maj=(a&b)^(a&c)^(b&c);
        uint32_t temp2=s0+maj;
        h=g;g=f;f=e;e=d+temp1;d=c;c=b;b=a;a=temp1+temp2;
    }
    state[0]+=a;state[1]+=b;state[2]+=c;state[3]+=d;
    state[4]+=e;state[5]+=f;state[6]+=g;state[7]+=h;
}
void p07_a2_sha256(const uint8_t *bytes, size_t length, uint8_t out[32])
{
    static const uint32_t initial[8] = {
        0x6a09e667u,0xbb67ae85u,0x3c6ef372u,0xa54ff53au,
        0x510e527fu,0x9b05688cu,0x1f83d9abu,0x5be0cd19u
    };
    uint32_t state[8],i;
    uint8_t block[64];
    size_t offset=0,remaining;
    uint64_t bits=(uint64_t)length*8u;
    if (!out || (!bytes && length)) return;
    memcpy(state,initial,sizeof(state));
    while(length-offset>=64u) {
        process(bytes+offset,state);
        offset+=64u;
    }
    remaining=length-offset;
    memset(block,0,sizeof(block));
    if(remaining) memcpy(block,bytes+offset,remaining);
    block[remaining]=0x80u;
    if(remaining>=56u) {
        process(block,state);
        memset(block,0,sizeof(block));
    }
    for(i=0;i<8u;++i)
        block[56u+i]=(uint8_t)(bits>>(56u-8u*i));
    process(block,state);
    for(i=0;i<8u;++i) {
        out[i*4u]=(uint8_t)(state[i]>>24u);
        out[i*4u+1u]=(uint8_t)(state[i]>>16u);
        out[i*4u+2u]=(uint8_t)(state[i]>>8u);
        out[i*4u+3u]=(uint8_t)state[i];
    }
}
