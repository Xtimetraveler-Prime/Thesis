/* P07-B.4m trace/debug integration with ORIGINAL fake P03 MMIO.
 * It models HLS trace bank 7, state bank 1, and packet bank 8 as
 * *separately observed* debug sources. It is not a KV260 observation.
 */
#define main original_p07_b3c23_main
#include "p07_b3c23_hw_scheduler_harness.c"
#undef main
#include "p07_b4m_spike_trace.h"
#include "p07_b4m_epoch_bridge.h"

static p07_b4m_spike_trace trace_owner;
static uint16_t detected_spikes[P07_B4M_TRACE_SPIKE_CAP][2];
static uint8_t route_scratch[P07_B3C_MAX_FRAME_BYTES];
static uint8_t route_frame[P07_B3C_MAX_FRAME_BYTES];
static uint32_t trace_debug_data[8];
static uint32_t trace_corrupt,read_traces;

static int trace_write(void *ctx,uint32_t addr,uint32_t value){
    bus *b=(bus *)ctx;
    uint32_t cfg,slot,bank,index,core,tick;
    if(addr==P03_REG_DEBUG_COMMAND&&value==P03_CMD_START){
        cfg=b->reg[P03_REG_DEBUG_CONFIG/4u];
        bank=(cfg>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u;
        slot=(cfg>>P03_DEBUG_CONFIG_SLOT_SHIFT)&3u;
        index=b->reg[P03_REG_DEBUG_ADDR/4u];
        if((bank==7u||bank==1u)&&!(cfg&P03_DEBUG_CONFIG_WRITE)){
            if(slot>=3u||index>=1024u)return -1;
            core=b->slot_owner[slot];
            if(core>=N||index>=compartments[core])return -1;
            tick=b->reg[P03_REG_DISPATCH_TIMESTEP/4u];
            memset(trace_debug_data,0,sizeof(trace_debug_data));
            if(bank==7u){
                trace_debug_data[6]=(core<26u&&tick<25u)?1u:0u;
                if(trace_corrupt)trace_debug_data[4]=1u;
                ++read_traces;
            }
            b->reg[addr/4u]=value;
            return 0;
        }
    }
    return bus_write(ctx,addr,value);
}
static int trace_read(void *ctx,uint32_t addr,uint32_t *out){
    bus *b=(bus *)ctx;uint32_t cfg,bank;
    if(addr>=P03_REG_DEBUG_RDATA0&&
       addr<P03_REG_DEBUG_RDATA0+32u&&addr%4u==0u){
        cfg=b->reg[P03_REG_DEBUG_CONFIG/4u];
        bank=(cfg>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u;
        if(bank==7u||bank==1u){
            *out=trace_debug_data[(addr-P03_REG_DEBUG_RDATA0)/4u];
            return 0;
        }
    }
    return bus_read(ctx,addr,out);
}
static int run_full(void){
    p07_b4m_trace_receipt trace_receipt;
    p07_b4m_barrier_receipt barrier_receipt;
    p07_b3_op op;
    uint32_t tick,core;int rc;
    CHECK(setup(P07_B3_ORDER_ASCENDING)==0);
    trace_corrupt=0u;read_traces=0u;
    hw.io.write32=trace_write;hw.io.read32=trace_read;
    CHECK(p07_b4m_trace_init(&trace_owner,&runner,detected_spikes,
                            P07_B4M_TRACE_SPIKE_CAP)==P07_B4M_TRACE_OK);
    CHECK(trace_owner.expected_compartments==27u);
    CHECK(p07_b3c2_set_trace_hook(&runner,p07_b4m_trace_on_dispatch,
                                 &trace_owner)==P07_B3C2_OK);
    for(tick=0u;tick<26u;tick++){
        do{
            rc=p07_b3c2_step(&runner,&op);
            CHECK(rc==P07_B3C2_OK||rc==P07_B3C2_BARRIER);
        }while(rc==P07_B3C2_OK);
        CHECK(trace_owner.read_count==27u);
        CHECK(p07_b4m_trace_finalize(&trace_owner,&trace_receipt)==P07_B4M_TRACE_OK);
        CHECK(trace_receipt.magic==P07_B4M_TRACE_MAGIC);
        CHECK(trace_receipt.source_count==27u);
        CHECK(trace_receipt.compartments_checked==27u);
        CHECK(trace_receipt.spikes==(tick==25u?0u:26u));
        for(core=0u;core<trace_receipt.spikes;core++){
            CHECK(detected_spikes[core][0]==core);
            CHECK(detected_spikes[core][1]==0u);
        }
        CHECK(p07_b4m_commit_pending_barrier(
          &runner,&op,&binding,(const uint16_t (*)[2])detected_spikes,
          trace_receipt.spikes,trace_owner.verified,
          route_scratch,sizeof(route_scratch),route_frame,
          sizeof(route_frame),&barrier_receipt)==P07_B4M_BRIDGE_OK);
        CHECK(barrier_receipt.barrier_acks==1u);
        CHECK(barrier_receipt.source_spike_count==trace_receipt.spikes);
        CHECK(p07_b4m_trace_advance(&trace_owner)==P07_B4M_TRACE_OK);
    }
    for(;;){
        rc=p07_b3c2_step(&runner,&op);
        if(rc==P07_B3C2_DONE)break;
        CHECK(rc==P07_B3C2_OK&&op.kind==P07_B3_FINAL_FLUSH);
    }
    CHECK(read_traces==702u);
    CHECK(pager.counters.dispatches==702u&&pager.counters.barriers==26u);
    CHECK(pager.counters.final_outs==3u);
    CHECK(sim.readout_checks==25u);
    return 0;
}
static int bad_trace_rejects_before_barrier(void){
    p07_b3_op op;int rc;
    CHECK(setup(P07_B3_ORDER_ASCENDING)==0);
    trace_corrupt=1u;read_traces=0u;
    hw.io.write32=trace_write;hw.io.read32=trace_read;
    CHECK(p07_b4m_trace_init(&trace_owner,&runner,detected_spikes,
                            P07_B4M_TRACE_SPIKE_CAP)==P07_B4M_TRACE_OK);
    CHECK(p07_b3c2_set_trace_hook(&runner,p07_b4m_trace_on_dispatch,
                                 &trace_owner)==P07_B3C2_OK);
    /* A trace/committed-state mismatch at first dispatch must abort
     * before any NEXT bank or global barrier acknowledgment.
     */
    do {rc=p07_b3c2_step(&runner,&op);}
    while(rc==P07_B3C2_OK);
    CHECK(rc==P07_B3C2_FAULTED);
    CHECK(trace_owner.poisoned&&pager.failed&&runner.poisoned);
    CHECK(pager.counters.dispatches==0u);
    CHECK(pager.counters.barriers==0u);
    CHECK(sim.debug_writes==0u&&sim.nonresident_stores==0u);
    return 0;
}
int main(void){
    backing=(uint8_t *)malloc((size_t)N*RECORD);
    resident_memory=(uint8_t *)malloc((size_t)3u*RECORD);
    CHECK(backing!=NULL&&resident_memory!=NULL);
    CHECK(run_full()==0);
    CHECK(bad_trace_rejects_before_barrier()==0);
    free(backing);free(resident_memory);
    puts("P07_B4M_TRACE_702_DISPATCH_26_BARRIER_SIMULATED_PASS=1");
    puts("P07_B4M_TRACE_REAL_DEBUG_BANK_SEMANTICS_NEGATIVE_PASS=1");
    puts("P07_B4M_TRACE_REAL_BOARD_TESTED=0");
    return 0;
}
