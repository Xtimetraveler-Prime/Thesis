/* Reuse accepted B3c23 original P03 fake-bus apparatus UNCHANGED.
 * An independent main executes new B4l physical-scheduler coordinator.
 * Native fake bus is NOT a KV260 HLS execution or B2b packet provenance.
 */
#define main p07_accepted_original_b3_fake_main
#include "p07_b3c23_hw_scheduler_harness.c"
#undef main
#include "p07_b4l_b3_epoch.h"

static int one_epoch(uint32_t mode){
    p07_b4l_b3_receipt proof={0};
    p07_b3_op pending,duplicate;
    unsigned i;
    CHECK(setup(mode)==0);
    CHECK(p07_b4l_b3_one_epoch(&runner,&proof)==P07_B4L_B3_OK);
    CHECK(proof.magic==P07_B4L_B3_ONE_TICK_MAGIC);
    CHECK(proof.tick==0u&&proof.unique_dispatches==27u);
    CHECK(proof.page_ins==27u&&proof.dirty_page_outs==24u);
    CHECK(proof.pending_barrier==1u&&proof.barrier_acked==0u);
    CHECK(proof.source_count==27u);
    CHECK(proof.physical_packets_captured==26u);
    CHECK(proof.dispatcher_next_current_bank==0u);
    CHECK(proof.dispatcher_next_bank==1u);
    CHECK(proof.p03_page_bytes_expected==
        27u*P07_B3_FULL_IN_BYTES+24u*P07_B3_MUTABLE_OUT_BYTES);
    CHECK(pager.counters.barriers==0u&&pager.tick==0u);
    CHECK(pager.counters.dispatches==27u&&pager.counters.page_ins==27u);
    CHECK(pager.counters.runtime_outs==24u);
    CHECK(sim.dispatches==27u&&sim.finished_pageins==27u);
    CHECK(sim.dirty_pageouts==24u);
    CHECK(p07_b3_next(&pager,&pending)==P07_B3_OK);
    CHECK(p07_b3_next(&pager,&duplicate)==P07_B3_OK);
    CHECK(pending.kind==P07_B3_BARRIER&&duplicate.kind==P07_B3_BARRIER);
    CHECK(pending.tick==0u&&pending.ordinal==27u);
    CHECK(pager.has_pending&&pager.cursor==P07_B3_CORES);
    CHECK(!pager.failed&&!runner.poisoned);
    CHECK(runner.word_count==26u);
    for(i=0;i<27u;i++){
        CHECK(runner.cores[i].source_core==i);
        CHECK(runner.cores[i].packet_count==(i<26u?1u:0u));
    }
    /* Re-running a physical first epoch on an already pending barrier is
     * not a valid success or fresh launch. Prevent implicit 2nd tick.
     */
    CHECK(p07_b4l_b3_one_epoch(&runner,&proof)==P07_B4L_B3_ARGUMENT);
    CHECK(pager.tick==0u&&pager.counters.barriers==0u);
    return 0;
}
static int failure(void){
    p07_b4l_b3_receipt r={0};
    p07_b3_op op;
    CHECK(setup(0u)==0);
    sim.fail_page=1u; /* first dirty eviction, after 3 real fake page-ins */
    CHECK(p07_b4l_b3_one_epoch(&runner,&r)==P07_B4L_B3_FAULT);
    CHECK(r.faulted&&r.first_error!=0u&&!r.magic);
    CHECK(pager.failed&&runner.poisoned);
    CHECK(pager.counters.dispatches==3u&&pager.counters.barriers==0u);
    CHECK(sim.dispatches==3u&&sim.dirty_pageouts==0u);
    CHECK(p07_b3_next(&pager,&op)==P07_B3_FAULTED);
    CHECK(p07_b4l_b3_one_epoch(&runner,&r)==P07_B4L_B3_ARGUMENT);
    return 0;
}
int main(void) {
    backing=(uint8_t *)malloc((size_t)N*RECORD);
    resident_memory=(uint8_t *)malloc((size_t)3u*RECORD);
    CHECK(backing!=NULL&&resident_memory!=NULL);
    CHECK(one_epoch(P07_B3_ORDER_ASCENDING)==0);
    CHECK(failure()==0);
    free(backing);free(resident_memory);
    puts("P07_B4L_B3_NATIVE_ORIGINAL_P03_27_DISPATCH_BARRIER_PENDING_PASS=1");
    puts("P07_B4L_B3_NATIVE_UNVERIFIED_NEXT_NOT_ACKED=1");
    puts("P07_B4L_B3_NATIVE_DIRTY_EVICTION_FAULT_STICKY_PASS=1");
    return 0;
}
