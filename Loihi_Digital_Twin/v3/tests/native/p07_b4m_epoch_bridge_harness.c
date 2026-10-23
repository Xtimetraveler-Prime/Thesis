/* P07-B.4m.1: original P03/P07 B3c2/B3c3 fake MMIO integration.
 * NO KV260 used; source provenance witness is synthetic.
 */
#define main p07_b3c23_original_fake_main
#include "p07_b3c23_hw_scheduler_harness.c"
#undef main
#include "p07_b4m_epoch_bridge.h"

static uint8_t bridge_scratch[P07_B3C_MAX_FRAME_BYTES];
static uint8_t bridge_frame[P07_B3C_MAX_FRAME_BYTES];
static uint16_t source_spikes[26][2];

static int run_complete(uint32_t mode){
    p07_b3_op op;
    p07_b4m_barrier_receipt receipt={0};
    uint32_t tick,core;
    int status;
    CHECK(setup(mode)==0);
    for(core=0u;core<26u;core++){
        source_spikes[core][0]=(uint16_t)core;
        source_spikes[core][1]=0u;
    }
    for(tick=0u;tick<26u;tick++){
        do{
            status=p07_b3c2_step(&runner,&op);
            CHECK(status==P07_B3C2_OK||status==P07_B3C2_BARRIER);
        }while(status==P07_B3C2_OK);
        CHECK(op.kind==P07_B3_BARRIER&&op.tick==tick);
        CHECK(p07_b4m_commit_pending_barrier(
            &runner,&op,&binding,
            (const uint16_t (*)[2])source_spikes,tick==25u?0u:26u,
            1u,bridge_scratch,sizeof(bridge_scratch),
            bridge_frame,sizeof(bridge_frame),&receipt)==P07_B4M_BRIDGE_OK);
        CHECK(receipt.magic==P07_B4M_BRIDGE_MAGIC);
        CHECK(receipt.tick==tick&&receipt.barrier_acks==1u);
        CHECK(receipt.physical_packet_count==(tick==25u?0u:26u));
        CHECK(receipt.source_spike_count==(tick==25u?0u:26u));
        CHECK(receipt.route_inserted==receipt.physical_packet_count);
        CHECK(receipt.destination_bank==1u-(tick&1u));
        CHECK(pager.tick==tick+1u);
        CHECK(pager.counters.dispatches==(tick+1u)*27u);
        CHECK(pager.counters.barriers==tick+1u);
        CHECK(runner.word_count==0u&&!runner.poisoned&&!pager.failed);
    }
    for(;;){
        status=p07_b3c2_step(&runner,&op);
        if(status==P07_B3C2_DONE)break;
        CHECK(status==P07_B3C2_OK&&op.kind==P07_B3_FINAL_FLUSH);
    }
    CHECK(pager.counters.dispatches==702u);
    CHECK(pager.counters.barriers==26u);
    CHECK(pager.counters.final_outs==3u);
    CHECK(sim.dispatches==702u&&sim.readout_checks==25u);
    CHECK(sim.dirty_pageouts==pager.counters.runtime_outs+3u);
    for(core=0u;core<27u;core++) {
        CHECK(get32(record(core)+0x5000u)==26u);
        CHECK(get32(record(core)+0x5C000u+25u*4u)==((25u<<8u)|core));
    }
    return 0;
}
static int begin_first_barrier(void){
    int status;p07_b3_op op;uint32_t core;
    CHECK(setup(P07_B3_ORDER_ASCENDING)==0);
    for(core=0u;core<26u;core++){
        source_spikes[core][0]=(uint16_t)core;
        source_spikes[core][1]=0u;
    }
    for(;;){
        status=p07_b3c2_step(&runner,&op);
        if(status==P07_B3C2_BARRIER)break;
        CHECK(status==P07_B3C2_OK);
    }
    CHECK(op.tick==0u&&pager.counters.dispatches==27u);
    return 0;
}
static int rejected_missing_source_proof(void){
    p07_b3_op op;
    p07_b4m_barrier_receipt receipt={0};
    CHECK(begin_first_barrier()==0);
    CHECK(p07_b3_next(&pager,&op)==P07_B3_OK);
    CHECK(p07_b4m_commit_pending_barrier(
        &runner,&op,&binding,(const uint16_t (*)[2])source_spikes,26u,
        0u,bridge_scratch,sizeof(bridge_scratch),
        bridge_frame,sizeof(bridge_frame),&receipt)==P07_B4M_BRIDGE_FAULT);
    CHECK(pager.failed&&runner.poisoned&&pager.counters.barriers==0u);
    CHECK(receipt.magic==0u&&receipt.first_failure!=0u);
    CHECK(sim.debug_writes==0u&&sim.nonresident_stores==0u);
    return 0;
}
static int rejected_wrong_spike_provenance(void){
    p07_b3_op op;
    p07_b4m_barrier_receipt receipt={0};
    CHECK(begin_first_barrier()==0);
    CHECK(p07_b3_next(&pager,&op)==P07_B3_OK);
    /* Packet bank contains 26 source cores, but allegedly only 25 emitted.
     * B2b complete-fanout checker must reject before ANY NEXT DDR/MMIO. */
    CHECK(p07_b4m_commit_pending_barrier(
        &runner,&op,&binding,(const uint16_t (*)[2])source_spikes,25u,
        1u,bridge_scratch,sizeof(bridge_scratch),
        bridge_frame,sizeof(bridge_frame),&receipt)==P07_B4M_BRIDGE_FAULT);
    CHECK(pager.failed&&runner.poisoned&&pager.counters.barriers==0u);
    CHECK(receipt.magic==0u&&receipt.first_failure==4u);
    CHECK(sim.debug_writes==0u&&sim.nonresident_stores==0u);
    return 0;
}
static int rejected_wrong_barrier(void){
    p07_b3_op op;
    p07_b4m_barrier_receipt receipt={0};
    CHECK(begin_first_barrier()==0);
    CHECK(p07_b3_next(&pager,&op)==P07_B3_OK);
    op.tick=1u; /* actual scheduler is at tick 0 */
    CHECK(p07_b4m_commit_pending_barrier(
        &runner,&op,&binding,(const uint16_t (*)[2])source_spikes,26u,
        1u,bridge_scratch,sizeof(bridge_scratch),
        bridge_frame,sizeof(bridge_frame),&receipt)==P07_B4M_BRIDGE_FAULT);
    CHECK(pager.failed&&runner.poisoned&&pager.counters.barriers==0u);
    CHECK(sim.debug_writes==0u&&sim.nonresident_stores==0u);
    return 0;
}
static int rejected_real_physical_write_failure(void){
    p07_b3_op op;
    p07_b4m_barrier_receipt receipt={0};
    CHECK(begin_first_barrier()==0);
    CHECK(p07_b3_next(&pager,&op)==P07_B3_OK);
    sim.fail_debug=1u; /* original P03 debug engine refuses NEXT */
    CHECK(p07_b4m_commit_pending_barrier(
        &runner,&op,&binding,(const uint16_t (*)[2])source_spikes,26u,
        1u,bridge_scratch,sizeof(bridge_scratch),
        bridge_frame,sizeof(bridge_frame),&receipt)==P07_B4M_BRIDGE_FAULT);
    CHECK(pager.failed&&runner.poisoned&&pager.counters.barriers==0u);
    CHECK(receipt.magic==0u&&receipt.first_failure==6u);
    CHECK(p07_b3_next(&pager,&op)==P07_B3_FAULTED);
    return 0;
}
int main(void){
    backing=(uint8_t *)malloc((size_t)N*RECORD);
    resident_memory=(uint8_t *)malloc((size_t)3u*RECORD);
    CHECK(backing!=NULL&&resident_memory!=NULL);
    CHECK(run_complete(P07_B3_ORDER_ASCENDING)==0);
    CHECK(run_complete(P07_B3_ORDER_ALTERNATING)==0);
    CHECK(rejected_missing_source_proof()==0);
    CHECK(rejected_wrong_spike_provenance()==0);
    CHECK(rejected_wrong_barrier()==0);
    CHECK(rejected_real_physical_write_failure()==0);
    free(backing);
    free(resident_memory);
    puts("P07_B4M_1_NATIVE_702_DISPATCH_26_ACK_ORIGINAL_P03_FAKE_BUS_PASS=1");
    puts("P07_B4M_1_NATIVE_SOURCE_PROVENANCE_AND_NEXT_FAULTS_FAIL_CLOSED=1");
    puts("P07_B4M_1_REAL_KV260_EXECUTED=0");
    return 0;
}
