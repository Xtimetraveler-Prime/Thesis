/* P07-B.4a native real P03 adapter with FAKE MMIO and fake DDR.
 * One epoch only, not an actual KV260 / actual trained B2 computation.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "p07_b4a_current_ingress.h"
#include "p03_mmio.h"
#define N P07_B4A_CORES
#define CHECK(x) do {if(!(x)){fprintf(stderr,"P07_B4A_FAIL_LINE=%u\n",(unsigned)__LINE__);return 1;}}while(0)
static p03_hw_adapter hw;
static p07_b3_pager pager;
static p07_b4a_plan plan;
static p07_b4a_receipt receipt;
static uint32_t words[P07_B4A_WORD_CAPACITY];
static uint8_t trusted[784u*2u*6u];
static uint8_t wire[128u+sizeof(trusted)+784u];
static uint8_t *ddr;
static uint32_t slots[3u][2u][4096u];
typedef struct {
    uint32_t regs[P03_MMIO_RANGE_BYTES/4u];
    uint32_t read_count,read_debug,write_debug,write_ddr,fail_store_after;
    uint32_t bad_debug,fail_read;
} bus;
static bus simulated;
static uint32_t get32(const uint8_t *p){
    return (uint32_t)p[0]|((uint32_t)p[1]<<8)|
           ((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);
}
static void put32(uint8_t *p,uint32_t v){
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
    p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);
}
static void put16(uint8_t *p,uint32_t v){
    p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);
}
static uint32_t crc(const uint8_t *p,size_t n,int hdr){
    uint32_t out=UINT32_C(0xffffffff),j;size_t i;
    for(i=0u;i<n;i++){
        out^=(hdr&&i>=52u&&i<56u)?0u:p[i];
        for(j=0u;j<8u;j++)
            out=(out>>1u)^((out&1u)?UINT32_C(0xedb88320):0u);
    }
    return ~out;
}
static uint64_t event_addr(uint32_t core,uint32_t bank,uint32_t idx){
    return P03_HW_BACKING_BASE+
        (uint64_t)core*P03_HW_RECORD_BYTES+
        (bank?P03_HW_EVENT1_OFFSET:P03_HW_EVENT0_OFFSET)+4u*idx;
}
static int read_ddr(void *context,uint64_t physical,uint32_t *out){
    bus *v=(bus *)context;
    uint64_t rel;
    if(!v||!out||v->fail_read)return -1;
    if(physical<P03_HW_BACKING_BASE ||
       physical+4u>P03_HW_BACKING_BASE+(uint64_t)N*P03_HW_RECORD_BYTES ||
       (physical&3u))return -1;
    rel=physical-P03_HW_BACKING_BASE;
    *out=get32(ddr+(size_t)rel);
    ++v->read_count;return 0;
}
static int read32(void *context,uint32_t addr,uint32_t *out){
    bus *busctx=(bus *)context;
    uint32_t cfg,slot,bank,index;
    if(!out||!busctx||addr>=P03_MMIO_RANGE_BYTES||(addr&3u))return -1;
    switch(addr){
    case P03_REG_ID:*out=P03_MMIO_ID_VALUE;return 0;
    case P03_REG_VERSION:*out=P03_MMIO_VERSION_VALUE;return 0;
    case P03_REG_CAPABILITIES:*out=UINT32_C(0x0001031F);return 0;
    case P03_REG_GLOBAL_STATUS:*out=0u;return 0;
    case P03_REG_PAGE_PENDING_BYTES:*out=0u;return 0;
    case P03_REG_DEBUG_STATUS:*out=busctx->bad_debug?0u:6u;return 0;
    case P03_REG_DEBUG_RDATA0:
      cfg=busctx->regs[P03_REG_DEBUG_CONFIG/4u];
      slot=(cfg>>P03_DEBUG_CONFIG_SLOT_SHIFT)&3u;
      bank=(cfg>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u;
      index=busctx->regs[P03_REG_DEBUG_ADDR/4u];
      if(slot>=3u||index>=4096u)return -1;
      if(bank==P03_HW_EVENT0_DEBUG_BANK)*out=slots[slot][0][index];
      else if(bank==P03_HW_EVENT1_DEBUG_BANK)*out=slots[slot][1][index];
      else return -1;
      ++busctx->read_debug;return 0;
    default:
      *out=busctx->regs[addr/4u];return 0;
    }
}
static int write32(void *context,uint32_t addr,uint32_t value){
    bus *v=(bus *)context;
    if(!v||addr>=P03_MMIO_RANGE_BYTES||(addr&3u))return -1;
    v->regs[addr/4u]=value;
    if(addr==P03_REG_DEBUG_COMMAND&&value==P03_CMD_START){
        uint32_t cfg=v->regs[P03_REG_DEBUG_CONFIG/4u];
        uint32_t slot=(cfg>>P03_DEBUG_CONFIG_SLOT_SHIFT)&3u;
        uint32_t bank=(cfg>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u;
        uint32_t idx=v->regs[P03_REG_DEBUG_ADDR/4u];
        if((cfg&P03_DEBUG_CONFIG_WRITE) && !v->bad_debug){
            if(slot>=3u||idx>=4096u)return -1;
            if(bank==P03_HW_EVENT0_DEBUG_BANK)
                slots[slot][0][idx]=v->regs[P03_REG_DEBUG_WDATA0/4u];
            else if(bank==P03_HW_EVENT1_DEBUG_BANK)
                slots[slot][1][idx]=v->regs[P03_REG_DEBUG_WDATA0/4u];
            else return -1;
            ++v->write_debug;
        }
    }
    return 0;
}
static int flush(void *c,uint64_t addr,uint32_t len){
    (void)c;(void)addr;(void)len;return 0;
}
static int store(void *ctx,uint64_t addr,uint32_t value){
    bus *v=(bus *)ctx;
    if(v->fail_store_after&&v->write_ddr>=v->fail_store_after)return -1;
    if(addr<P03_HW_BACKING_BASE ||
       addr+4u>P03_HW_BACKING_BASE+(uint64_t)N*P03_HW_RECORD_BYTES||
       (addr&3u))return -1;
    put32(ddr+(size_t)(addr-P03_HW_BACKING_BASE),value);
    ++v->write_ddr;return 0;
}
static void fence(void *cookie){(void)cookie;}
static void make_ingress(void){
    uint32_t i,j=0u;
    memset(wire,0,sizeof(wire));
    memcpy(wire,"P06B13I1",8u);
    for(i=0u;i<784u;i++){
        put16(trusted+j, i);put16(trusted+j+2u,0u);put16(trusted+j+4u,i);
        j+=6u;
        put16(trusted+j,i);put16(trusted+j+2u,1u);put16(trusted+j+4u,i);
        j+=6u;
    }
    memcpy(wire+128u,trusted,sizeof(trusted));
    memset(wire+128u+sizeof(trusted),255,784u);
    put32(wire+8u,1u);put32(wire+12u,128u);
    put32(wire+16u,sizeof(trusted)+784u);
    put32(wire+20u,1568u);put32(wire+24u,N);
    put32(wire+28u,784u);put32(wire+32u,25u);put32(wire+36u,26u);
    put32(wire+40u,6u);put32(wire+44u,784u);
    memset(wire+64u,0x11,32u);memset(wire+96u,0x22,32u);
    put32(wire+48u,crc(wire+128u,sizeof(wire)-128u,0));
    put32(wire+52u,crc(wire,128u,1));
}
static p07_b2_ingress_binding binding(void){
    p07_b2_ingress_binding b={0};
    b.core_count=N;b.route_count=1568u;
    b.trusted_routes=trusted;b.trusted_routes_bytes=sizeof(trusted);
    memset(b.compiled_sha256,0x11,32u);
    memset(b.capacity_sha256,0x22,32u);return b;
}
static int setup(void){
    uint32_t c,i;
    p03_hw_io io={read32,write32,flush,flush,store,fence};
    memset(&simulated,0,sizeof(simulated));
    memset(&hw,0,sizeof(hw));memset(&plan,0,sizeof(plan));
    memset(&receipt,0,sizeof(receipt));
    memset(slots,0,sizeof(slots));
    memset(ddr,0,(size_t)N*P03_HW_RECORD_BYTES);
    make_ingress();
    if(p03_hw_init(&hw,&io,&simulated,P03_HW_BACKING_BASE,3u)!=P03_HW_OK)return -1;
    for(c=0u;c<N;c++)
        if(p03_hw_register_core(&hw,(uint8_t)c,UINT64_C(1)<<7u|c,0u,0u)!=P03_HW_OK)return -1;
    for(c=0u;c<2u;c++)
        for(i=0u;i<784u;i++)
            if(p03_hw_register_axon(&hw,(uint8_t)c,(uint16_t)i)!=P03_HW_OK)return -1;
    for(i=100u;i<126u;i++)
        if(p03_hw_register_axon(&hw,26u,(uint16_t)i)!=P03_HW_OK)return -1;
    if(p07_b3_init(&pager,0u)!=P07_B3_OK)return -1;
    return 0;
}
static int test_empty_to_784_per_core(void){
    uint32_t i;
    p07_b2_ingress_binding b;
    CHECK(setup()==0);b=binding();
    CHECK(p07_b4a_prepare(&plan,&pager,&hw,&b,wire,sizeof(wire),words,
          P07_B4A_WORD_CAPACITY,read_ddr,&simulated)==P07_B4A_OK);
    CHECK(plan.external_total==1568u&&plan.prior_total==0u);
    CHECK(plan.final_by_core[0]==784u&&plan.final_by_core[1]==784u);
    CHECK(plan.final_by_core[26]==0u);
    CHECK(hw.event_counts[0][0]==0u&&simulated.write_ddr==0u);
    CHECK(p07_b4a_commit(&plan,&receipt)==P07_B4A_OK);
    CHECK(receipt.tick==0u&&receipt.current_total==1568u);
    CHECK(receipt.current_by_core[0]==784u&&receipt.current_by_core[1]==784u);
    CHECK(simulated.write_ddr==1568u);
    for(i=0u;i<784u;i++) {
        CHECK(get32(ddr+(size_t)(event_addr(0u,0u,i)-P03_HW_BACKING_BASE))==i);
        CHECK(get32(ddr+(size_t)(event_addr(1u,0u,i)-P03_HW_BACKING_BASE))==i);
    }
    CHECK(p07_b4a_commit(&plan,&receipt)==P07_B4A_POISONED);
    return 0;
}
static int test_resident_merge(void){
    uint32_t i; p07_b2_ingress_binding b;
    CHECK(setup()==0);b=binding();
    pager.resident[0]=0;
    hw.event_counts[0][0]=2u;
    slots[0][0][0]=7u;slots[0][0][1]=5u;
    CHECK(p07_b4a_prepare(&plan,&pager,&hw,&b,wire,sizeof(wire),words,
          P07_B4A_WORD_CAPACITY,read_ddr,&simulated)==P07_B4A_OK);
    CHECK(plan.prior_by_core[0]==2u&&plan.final_by_core[0]==786u);
    CHECK(plan.final_by_core[1]==784u);
    CHECK(plan.words[0]==0u&&plan.words[5]==5u&&plan.words[6]==5u);
    CHECK(p07_b4a_commit(&plan,&receipt)==P07_B4A_OK);
    CHECK(hw.event_counts[0][0]==786u&&pager.dirty[0]==1u);
    CHECK(simulated.write_debug==786u&&simulated.write_ddr==784u);
    for(i=1u;i<786u;i++)CHECK(slots[0][0][i]>=slots[0][0][i-1u]);
    CHECK(get32(ddr+(size_t)(event_addr(0u,0u,0u)-P03_HW_BACKING_BASE))==0u);
    return 0;
}
static int test_capacity_boundary_and_corrupt_frame(void){
    uint32_t i; p07_b2_ingress_binding b;
    CHECK(setup()==0);b=binding();
    wire[64u]^=1u;
    CHECK(p07_b4a_prepare(&plan,&pager,&hw,&b,wire,sizeof(wire),words,
          P07_B4A_WORD_CAPACITY,read_ddr,&simulated)==P07_B4A_REJECT);
    CHECK(simulated.write_ddr==0u&&hw.event_counts[0][0]==0u);
    CHECK(setup()==0);b=binding();
    hw.event_counts[0][0]=3313u;
    for(i=0u;i<3313u;i++)put32(ddr+(size_t)(event_addr(0u,0u,i)-P03_HW_BACKING_BASE),i%784u);
    CHECK(p07_b4a_prepare(&plan,&pager,&hw,&b,wire,sizeof(wire),words,
          P07_B4A_WORD_CAPACITY,read_ddr,&simulated)==P07_B4A_REJECT);
    CHECK(simulated.write_ddr==0u&&hw.event_counts[0][0]==3313u);
    CHECK(setup()==0);b=binding();
    hw.event_counts[0][0]=3312u;
    for(i=0u;i<3312u;i++)put32(ddr+(size_t)(event_addr(0u,0u,i)-P03_HW_BACKING_BASE),i%784u);
    CHECK(p07_b4a_prepare(&plan,&pager,&hw,&b,wire,sizeof(wire),words,
          P07_B4A_WORD_CAPACITY,read_ddr,&simulated)==P07_B4A_OK);
    CHECK(plan.final_by_core[0]==4096u);
    CHECK(p07_b4a_commit(&plan,&receipt)==P07_B4A_OK);
    CHECK(hw.event_counts[0][0]==4096u);
    return 0;
}
static int test_physical_write_fault_poison(void){
    p07_b2_ingress_binding b;
    CHECK(setup()==0);b=binding();
    CHECK(p07_b4a_prepare(&plan,&pager,&hw,&b,wire,sizeof(wire),words,
          P07_B4A_WORD_CAPACITY,read_ddr,&simulated)==P07_B4A_OK);
    simulated.fail_store_after=3u;
    CHECK(p07_b4a_commit(&plan,&receipt)==P07_B4A_POISONED);
    CHECK(pager.failed&&plan.poisoned&&plan.first_failure==5u);
    CHECK(simulated.write_ddr==3u&&hw.event_counts[0][0]==0u);
    CHECK(receipt.current_total==0u);
    CHECK(p07_b4a_commit(&plan,&receipt)==P07_B4A_POISONED);
    return 0;
}
int main(void){
    ddr=(uint8_t *)malloc((size_t)N*P03_HW_RECORD_BYTES);
    CHECK(ddr!=NULL);
    CHECK(test_empty_to_784_per_core()==0);
    CHECK(test_resident_merge()==0);
    CHECK(test_capacity_boundary_and_corrupt_frame()==0);
    CHECK(test_physical_write_fault_poison()==0);
    puts("P07_B4A_CURRENT_INGRESS_P03_FAKE_BUS_PASS=1");
    free(ddr);return 0;
}
