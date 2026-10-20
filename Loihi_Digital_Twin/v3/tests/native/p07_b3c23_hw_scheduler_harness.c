/* P07-B.3c2/3 native full-schedule P03 fake-bus regression.
 * Real P03 adapter C links unchanged. THIS IS NOT PHYSICAL KV260 EVIDENCE.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "p07_b3c2_hw_scheduler.h"
#include "p07_b3c3_next_commit.h"
#include "p03_mmio.h"
#define N 27u
#define RECORD 0x6B000u
#define CHECK(x) do {if(!(x)){fprintf(stderr,"B3C23_FAIL_LINE=%u\n",(unsigned)__LINE__);return 1;}}while(0)
static uint8_t *backing,*resident_memory;
static p03_hw_adapter hw;
static p07_b3_pager pager;
static p07_b3c2_hw_scheduler runner;
static uint64_t raw[P07_B3C_MAX_RAW_WORDS],temp[P03_RT_MAX_PACKETS];
static p07_b2_route route[26];
static uint16_t compartments[N];
static p07_b2_packet_binding binding;
static uint8_t scratch[P07_B3C_MAX_FRAME_BYTES],frame[P07_B3C_MAX_FRAME_BYTES];
typedef struct {
    uint32_t reg[P03_MMIO_RANGE_BYTES/4u],page_bytes,reads,dispatches,debug_writes;
    uint32_t nonresident_stores,dirty_pageouts,finished_pageins,readout_checks;
    uint32_t fail_debug,fail_store,fail_page;
    uint8_t slot_owner[3];
} bus;
static bus sim;
static uint8_t *record(uint32_t core){return backing+(size_t)core*RECORD;}
static uint8_t *slotp(uint32_t s){return resident_memory+(size_t)s*RECORD;}
static uint32_t get32(const uint8_t *p){return (uint32_t)p[0]|((uint32_t)p[1]<<8)|((uint32_t)p[2]<<16)|((uint32_t)p[3]<<24);}
static void put32(uint8_t *p,uint32_t v){p[0]=(uint8_t)v;p[1]=(uint8_t)(v>>8);p[2]=(uint8_t)(v>>16);p[3]=(uint8_t)(v>>24);}
static int bus_read(void *ctx,uint32_t addr,uint32_t *out){
    bus *b=(bus *)ctx;
    uint32_t source=b->reg[P03_REG_DISPATCH_ACTIVE/4u]>>16;
    uint32_t tick=b->reg[P03_REG_DISPATCH_TIMESTEP/4u];
    uint64_t word=UINT64_C(1)<<61u | ((uint64_t)(tick+1u)<<29u) |
                  ((uint64_t)(source+100u)<<7u) | 26u;
    if(!out||addr>=P03_MMIO_RANGE_BYTES||addr%4u)return -1;
    switch(addr){
      case P03_REG_ID:*out=P03_MMIO_ID_VALUE;break;
      case P03_REG_VERSION:*out=P03_MMIO_VERSION_VALUE;break;
      case P03_REG_CAPABILITIES:*out=UINT32_C(0x0001031F);break;
      case P03_REG_GLOBAL_STATUS:*out=0u;break;
      case P03_REG_PAGE_PENDING_BYTES:*out=0u;break;
      case P03_REG_PAGE_STATUS:*out=b->reg[addr/4u];break;
      case P03_REG_PAGE_BYTES:*out=b->page_bytes;break;
      case P03_REG_DISPATCH_STATUS:*out=2u;break;
      case P03_REG_DISPATCH_CORE_STATUS:*out=0u;break;
      case P03_REG_DISPATCH_PACKET_CNT:*out=source<26u&&tick<25u?1u:0u;break;
      case P03_REG_DISPATCH_ACTIVE:*out=b->reg[addr/4u];break;
      case P03_REG_DEBUG_STATUS:*out=b->fail_debug?0u:6u;break;
      case P03_REG_DEBUG_RDATA0:*out=(uint32_t)word;break;
      case P03_REG_DEBUG_RDATA0+4u:*out=(uint32_t)(word>>32u);break;
      default:*out=b->reg[addr/4u];break;
    }
    return 0;
}
static void mutable_save(uint8_t *dst,const uint8_t *src){
    static const struct {uint32_t off,size;} parts[]={
        {0x05000u,0x02000u},{0x54000u,0x04000u},
        {0x58000u,0x04000u},{0x5C000u,0x08000u},
        {0x64000u,0x08000u}
    };
    unsigned j;uint32_t sum=0u;
    for(j=0u;j<sizeof(parts)/sizeof(parts[0]);j++){
        memcpy(dst+parts[j].off,src+parts[j].off,parts[j].size);
        sum+=parts[j].size;
    }
    if(sum!=P03_HW_MUTABLE_BYTES)abort();
}
static int bus_write(void *ctx,uint32_t addr,uint32_t value){
    bus *b=(bus *)ctx;uint32_t cfg,slot,core,kind,bank,index,tick;
    if(addr>=P03_MMIO_RANGE_BYTES||addr%4u)return -1;
    b->reg[addr/4u]=value;
    if(addr==P03_REG_PAGE_COMMAND && value==P03_CMD_START){
        cfg=b->reg[P03_REG_PAGE_CONFIG/4u];
        slot=(cfg>>P03_PAGE_CONFIG_SLOT_SHIFT)&3u;
        core=(b->reg[P03_REG_PAGE_BASE_LO/4u]-P03_HW_BACKING_BASE)/P03_HW_RECORD_BYTES;
        kind=cfg&P03_PAGE_CONFIG_PAGE_OUT;
        if(slot>=3u||core>=N)return -1;
        if(b->fail_page && kind){b->reg[P03_REG_PAGE_STATUS/4u]=0x4u;return 0;}
        if(kind){
            mutable_save(record(core),slotp(slot));
            b->page_bytes=P03_HW_MUTABLE_BYTES;
            ++b->dirty_pageouts;
        }else{
            memcpy(slotp(slot),record(core),RECORD);
            b->page_bytes=P03_HW_FULL_PAGE_BYTES;
            b->slot_owner[slot]=(uint8_t)core;
            ++b->finished_pageins;
        }
        b->reg[P03_REG_PAGE_STATUS/4u]=2u;
    }else if(addr==P03_REG_DISPATCH_COMMAND && value==P03_CMD_START){
        cfg=b->reg[P03_REG_DISPATCH_CONFIG/4u];
        slot=cfg&3u;tick=b->reg[P03_REG_DISPATCH_TIMESTEP/4u];
        core=(uint32_t)(b->reg[P03_REG_DISPATCH_META_LO/4u]&0x7fu);
        if(core>=N||slot>=3u||b->slot_owner[slot]!=core)return -1;
        b->reg[P03_REG_DISPATCH_ACTIVE/4u]=(core<<16u)|((cfg&0x100u))|slot;
        put32(slotp(slot)+0x5000u,get32(slotp(slot)+0x5000u)+1u);
        put32(slotp(slot)+0x5C000u+tick*4u,(tick<<8u)|core);
        if(core==26u&&tick>0u){
            unsigned i;uint32_t eventbank=tick&1u;
            for(i=0u;i<26u;i++)
                if(get32(slotp(slot)+(eventbank?0x58000u:0x54000u)+i*4u)!=i+100u)
                    return -1;
            ++b->readout_checks;
        }
        b->dispatches++;
    }else if(addr==P03_REG_DEBUG_COMMAND&&value==P03_CMD_START){
        cfg=b->reg[P03_REG_DEBUG_CONFIG/4u];
        bank=(cfg>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u;
        slot=(cfg>>P03_DEBUG_CONFIG_SLOT_SHIFT)&3u;
        index=b->reg[P03_REG_DEBUG_ADDR/4u];
        if(slot>=3u)return -1;
        if(cfg&P03_DEBUG_CONFIG_WRITE){
            if(bank!=P03_HW_EVENT0_DEBUG_BANK &&bank!=P03_HW_EVENT1_DEBUG_BANK)return -1;
            if(index>=4096u)return -1;
            put32(slotp(slot)+(bank==P03_HW_EVENT0_DEBUG_BANK?
                                0x54000u:0x58000u)+index*4u,
                                b->reg[P03_REG_DEBUG_WDATA0/4u]);
            ++b->debug_writes;
        }else if(bank!=P03_HW_PACKET_DEBUG_BANK)return -1;
    }
    return 0;
}
static int clean(void *ctx,uint64_t addr,uint32_t bytes){(void)ctx;(void)addr;(void)bytes;return 0;}
static int inval(void *ctx,uint64_t addr,uint32_t bytes){(void)ctx;(void)addr;(void)bytes;return 0;}
static int store(void *ctx,uint64_t address,uint32_t value){
    bus *b=(bus *)ctx;uint64_t rel;
    if(b->fail_store)return -1;
    if(address<P03_HW_BACKING_BASE ||
       address>=P03_HW_BACKING_BASE+(uint64_t)N*P03_HW_RECORD_BYTES)return -1;
    rel=address-P03_HW_BACKING_BASE;
    if((rel%P03_HW_RECORD_BYTES)+4u>RECORD)return -1;
    put32(record((uint32_t)(rel/P03_HW_RECORD_BYTES))+
          (size_t)(rel%P03_HW_RECORD_BYTES),value);
    ++b->nonresident_stores;
    return 0;
}
static void fence(void *ctx){(void)ctx;}
static int setup(uint32_t mode){
    uint32_t core,slot;
    p03_hw_io ops={bus_read,bus_write,clean,inval,store,fence};
    memset(&sim,0,sizeof(sim));
    memset(&hw,0,sizeof(hw));
    memset(raw,0,sizeof(raw));
    memset(&runner,0,sizeof(runner));
    memset(backing,0,(size_t)N*RECORD);
    memset(resident_memory,0,(size_t)3u*RECORD);
    for(core=0u;core<N;core++){
        put32(record(core)+0x1000u,core+1u);
        put32(record(core)+0x5000u,0u);
        compartments[core]=1u;
    }
    for(core=0u;core<26u;core++)
        route[core]=(p07_b2_route){(uint16_t)core,0u,26u,(uint16_t)(100u+core)};
    memset(&binding,0,sizeof(binding));
    binding.core_count=N;binding.route_count=26u;
    binding.routes=route;binding.compartments_per_core=compartments;
    memset(binding.compiled_sha256,0x11,32u);
    memset(binding.capacity_sha256,0x22,32u);
    if(p03_hw_init(&hw,&ops,&sim,P03_HW_BACKING_BASE,5u)!=P03_HW_OK)return -1;
    for(core=0u;core<N;core++){
        if(p03_hw_register_core(&hw,(uint8_t)core,((uint64_t)1u<<7u)|core,
                                 0u,0u)!=P03_HW_OK)return -1;
    }
    for(core=0u;core<26u;core++)
        if(p03_hw_register_axon(&hw,26u,(uint16_t)(100u+core))!=P03_HW_OK)return -1;
    if(p07_b3_init(&pager,mode)!=P07_B3_OK)return -1;
    if(p07_b3c2_init(&runner,&pager,&hw,raw,P07_B3C_MAX_RAW_WORDS,
                      temp,P03_RT_MAX_PACKETS)!=P07_B3C2_OK)return -1;
    for(slot=0u;slot<3u;slot++)sim.slot_owner[slot]=UINT8_MAX;
    return 0;
}
static int barrier(uint32_t tick,int bad_packet,int fail_write){
    p07_b3c3_plan plan={0};p07_b3c3_receipt receipt={0};
    p07_b3_op op;size_t bytes=0u;uint32_t src;
    uint16_t emitted[26][2];
    /* ISO C11: implicit uint16_t (*)[2] -> const uint16_t (*)[2] is
     * not permitted for nested array qualifiers before C23.
     * Keep mutable fixture initialization, then cast explicitly at the
     * read-only API boundary. No data are changed through this view. */
    const uint16_t (*readonly_emitted)[2]=(const uint16_t (*)[2])emitted;
    for(src=0u;src<26u;src++){emitted[src][0]=(uint16_t)src;emitted[src][1]=0u;}
    CHECK(p07_b3_next(&pager,&op)==P07_B3_OK&&op.kind==P07_B3_BARRIER);
    CHECK(p07_b3c_encode_frame(runner.cores,N,tick,&binding,
             readonly_emitted,tick<25u?26u:0u,
             scratch,sizeof(scratch),frame,sizeof(frame),&bytes)==P07_B3C_OK);
    if(bad_packet)frame[128u]^=1u;
    if(bad_packet){
        CHECK(p07_b3c3_prepare(&plan,&pager,&hw,&binding,frame,bytes,
              readonly_emitted,tick<25u?26u:0u)==P07_B3C3_PRECHECK);
        CHECK(!pager.failed&&pager.tick==tick);
        return 0;
    }
    CHECK(p07_b3c3_prepare(&plan,&pager,&hw,&binding,frame,bytes,
          readonly_emitted,tick<25u?26u:0u)==P07_B3C3_OK);
    if(fail_write){
        if(resident_memory)sim.fail_debug=1u;
        if(p07_b3c3_commit(&plan,&receipt)!=P07_B3C3_FAULTED)return 1;
        CHECK(pager.failed&&plan.poisoned&&receipt.magic==0u);
        return 0;
    }
    CHECK(p07_b3c3_commit(&plan,&receipt)==P07_B3C3_OK);
    CHECK(receipt.magic==P07_B3C3_RECEIPT_MAGIC);
    CHECK(receipt.inserted_count==(tick<25u?26u:0u));
    CHECK(p07_b3c2_barrier_ack(&runner,&op,&receipt)==P07_B3C2_OK);
    return 0;
}
static int end_to_end(uint32_t mode){
    uint32_t tick,core;int done;
    p07_b3_op op;
    CHECK(setup(mode)==0);
    for(tick=0u;tick<26u;tick++){
        do{
            done=p07_b3c2_step(&runner,&op);
            if(done!=P07_B3C2_OK&&done!=P07_B3C2_BARRIER)
                fprintf(stderr,"B3C23_STEP_DETAIL mode=%u tick=%u kind=%u "
                    "core=%u slot=%u rc=%d hw_error=%d hw_status=%u "
                    "pager_failed=%u pager_fault=%u runner_fault=%u "
                    "dispatches=%u page_ins=%u page_outs=%u\n",
                    mode,tick,op.kind,op.core,op.slot,done,
                    hw.last_error,hw.last_status,pager.failed,
                    pager.first_failure_kind,runner.first_fault,
                    pager.counters.dispatches,pager.counters.page_ins,
                    pager.counters.runtime_outs);
            CHECK(done==P07_B3C2_OK||done==P07_B3C2_BARRIER);
        }while(done==P07_B3C2_OK);
        CHECK(op.kind==P07_B3_BARRIER&&op.tick==tick);
        CHECK(barrier(tick,0,0)==0);
    }
    for(;;){
        done=p07_b3c2_step(&runner,&op);
        if(done==P07_B3C2_DONE)break;
        CHECK(done==P07_B3C2_OK && op.kind==P07_B3_FINAL_FLUSH);
    }
    CHECK(pager.counters.dispatches==702u&&pager.counters.barriers==26u);
    CHECK(pager.counters.final_outs==3u);
    CHECK(sim.dispatches==702u&&sim.readout_checks==25u);
    CHECK(sim.finished_pageins==pager.counters.page_ins);
    CHECK(sim.dirty_pageouts==pager.counters.runtime_outs+3u);
    CHECK(sim.nonresident_stores==(mode==0u?0u:312u));
    CHECK(sim.debug_writes==(mode==0u?650u:338u));
    for(core=0u;core<N;core++){
        CHECK(get32(record(core)+0x5000u)==26u);
        CHECK(get32(record(core)+0x1000u)==core+1u);
        CHECK(get32(record(core)+0x5C000u+25u*4u)==((25u<<8u)|core));
    }
    return 0;
}
static int failure_guards(void){
    int state;p07_b3_op op;uint32_t tick;
    p07_b3c3_plan plan={0};p07_b3c3_receipt receipt={0};
    uint16_t spikes[26][2];uint32_t i;size_t bytes=0u;
    const uint16_t (*readonly_spikes)[2]=(const uint16_t (*)[2])spikes;
    CHECK(setup(0u)==0);
    /* First incomplete page write acknowledgment must poison scheduler. */
    while(pager.counters.dispatches<3u){
        state=p07_b3c2_step(&runner,&op);
        CHECK(state==P07_B3C2_OK);
    }
    sim.fail_page=1u;
    CHECK(p07_b3c2_step(&runner,&op)==P07_B3C2_FAULTED);
    CHECK(pager.failed&&pager.counters.runtime_outs==0u);
    CHECK(setup(0u)==0);
    for(;;){
        state=p07_b3c2_step(&runner,&op);
        if(state==P07_B3C2_BARRIER)break;
        CHECK(state==P07_B3C2_OK);
    }
    /* A mutated CRC frame cannot write physical NEXT at all. */
    CHECK(barrier(0u,1,0)==0);
    CHECK(hw.event_counts[26][1]==0u&&sim.debug_writes==0u);
    for(i=0u;i<26u;i++){spikes[i][0]=(uint16_t)i;spikes[i][1]=0u;}
    /* A caller cannot advance the scheduler using a missing/fake
     * B3c3 insertion receipt after a failed preflight. */
    CHECK(p07_b3c2_barrier_ack(&runner,&op,&receipt)==P07_B3C2_FAULTED);
    CHECK(pager.failed&&pager.counters.barriers==0u);
    CHECK(setup(0u)==0);
    for(;;){
        state=p07_b3c2_step(&runner,&op);
        if(state==P07_B3C2_BARRIER)break;
        CHECK(state==P07_B3C2_OK);
    }
    CHECK(p07_b3c_encode_frame(runner.cores,N,0u,&binding,
             readonly_spikes,26u,scratch,sizeof(scratch),frame,sizeof(frame),&bytes)==P07_B3C_OK);
    /* CRC-valid but unregistered destination axon must be rejected
     * before any physical/debug NEXT bank write. */
    hw.valid_axons[26u][100u>>3u] &=
         (uint8_t)~(1u<<(100u&7u));
    CHECK(p07_b3c3_prepare(&plan,&pager,&hw,&binding,frame,bytes,
                           readonly_spikes,26u)==P07_B3C3_PRECHECK);
    CHECK(hw.event_counts[26][1]==0u&&sim.debug_writes==0u);
    hw.valid_axons[26u][100u>>3u] |= (uint8_t)(1u<<(100u&7u));
    CHECK(p07_b3c3_prepare(&plan,&pager,&hw,&binding,frame,bytes,
                           readonly_spikes,26u)==P07_B3C3_OK);
    /* Actual P03 debug failure: no success receipt, no barrier advancement. */
    sim.fail_debug=1u;
    CHECK(p07_b3c3_commit(&plan,&receipt)==P07_B3C3_FAULTED);
    CHECK(pager.failed&&plan.poisoned&&receipt.magic==0u);
    CHECK(p07_b3c3_commit(&plan,&receipt)==P07_B3C3_FAULTED);
    CHECK(setup(1u)==0);
    /* Alternate service policy -> readout nonresident after odd epoch. */
    for(tick=0u;tick<2u;tick++){
        for(;;){
            state=p07_b3c2_step(&runner,&op);
            if(state==P07_B3C2_BARRIER)break;
            CHECK(state==P07_B3C2_OK);
        }
        if(tick==0u)CHECK(barrier(tick,0,0)==0);
    }
    CHECK(pager.resident[0]!=26&&pager.resident[1]!=26&&pager.resident[2]!=26);
    CHECK(p07_b3c_encode_frame(runner.cores,N,1u,&binding,
             readonly_spikes,26u,scratch,sizeof(scratch),frame,sizeof(frame),&bytes)==P07_B3C_OK);
    CHECK(p07_b3c3_prepare(&plan,&pager,&hw,&binding,frame,bytes,
                           readonly_spikes,26u)==P07_B3C3_OK);
    sim.fail_store=1u;
    CHECK(p07_b3c3_commit(&plan,&receipt)==P07_B3C3_FAULTED);
    CHECK(pager.failed&&plan.poisoned&&receipt.magic==0u);
    return 0;
}
int main(void){
    backing=(uint8_t *)malloc((size_t)N*RECORD);
    resident_memory=(uint8_t *)malloc((size_t)3u*RECORD);
    CHECK(backing!=NULL&&resident_memory!=NULL);
    CHECK(end_to_end(0u)==0);
    CHECK(end_to_end(1u)==0);
    CHECK(failure_guards()==0);
    puts("P07_B3C23_REAL_P03_NATIVE_FAKE_BUS_PASS=1");
    free(backing);free(resident_memory);
    return 0;
}
