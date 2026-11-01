/* P07-B.3a host-native independent ACK harness; no FPGA, no B2 TEST. */
#include "p07_b3_pager.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define CHECK(x) do {if(!(x)){fprintf(stderr,"P07_B3_PAGER_ERROR_LINE=%d\n",__LINE__);return 1;}}while(0)
static int valid_addresses(const p07_b3_op *op) {
    if(op->kind==P07_B3_PAGE_IN || op->kind==P07_B3_PAGE_OUT || op->kind==P07_B3_FINAL_FLUSH) {
        uint32_t size=op->kind==P07_B3_PAGE_IN?P07_B3_FULL_IN_BYTES:P07_B3_MUTABLE_OUT_BYTES;
        return op->core<P07_B3_CORES && op->bytes==size &&
               op->slot<P07_B3_SLOTS &&
               op->backing_address==P07_B3_BACKING_BASE+(uint64_t)op->core*P07_B3_RECORD_BYTES;
    }
    return op->bytes==0u && op->backing_address==0u;
}
static int complete(uint32_t mode,int print) {
    p07_b3_pager p;
    p07_b3_op op,again;
    uint32_t count=0u;
    int status;
    CHECK(p07_b3_init(&p,mode)==P07_B3_OK);
    while((status=p07_b3_next(&p,&op))==P07_B3_OK) {
        CHECK(++count<3000u);
        CHECK(op.tick <= P07_B3_TICKS);
        CHECK(valid_addresses(&op));
        CHECK(p07_b3_next(&p,&again)==P07_B3_OK);
        CHECK(memcmp(&op,&again,sizeof(op))==0);
        if(print)printf("OP %u %u %u %u %u %u %u %u %llu %u\n",
           op.tick,op.ordinal,op.kind,op.core,op.slot,op.victim,
           op.current_bank,op.next_bank,(unsigned long long)op.backing_address,op.bytes);
        CHECK(p07_b3_ack(&p,&op,1)==P07_B3_OK);
    }
    CHECK(status==P07_B3_DONE);
    CHECK(p.counters.dispatches==702u && p.counters.barriers==26u);
    CHECK(p.ordinal==702u && p.tick==26u);
    CHECK(p.counters.runtime_outs==p.counters.dirty_evictions);
    CHECK(p.counters.page_ins==p.counters.cold_ins+p.counters.replacements);
    CHECK(p.counters.replacements==p.counters.runtime_outs);
    CHECK(p.counters.final_outs==3u);
    CHECK(p.counters.read_bytes==(uint64_t)p.counters.page_ins*P07_B3_FULL_IN_BYTES);
    CHECK(p.counters.write_bytes==(uint64_t)(p.counters.runtime_outs+3u)*P07_B3_MUTABLE_OUT_BYTES);
    if(print)printf("SUMMARY %u %u %u %u %u %u %u %u %u %llu %llu\n",
       p.counters.dispatches,p.counters.barriers,p.counters.page_ins,
       p.counters.hits,p.counters.cold_ins,p.counters.replacements,
       p.counters.runtime_outs,p.counters.final_outs,p.counters.dirty_evictions,
       (unsigned long long)p.counters.read_bytes,
       (unsigned long long)p.counters.write_bytes);
    CHECK(p07_b3_next(&p,&op)==P07_B3_DONE);
    CHECK(p07_b3_ack(&p,&op,1)==P07_B3_FAULTED);
    CHECK(p.first_failure_kind!=0u);
    CHECK(p07_b3_next(&p,&op)==P07_B3_FAULTED);
    return 0;
}
static int injected_failures(void) {
    p07_b3_pager p;
    p07_b3_op op,bad;
    int status;
    uint32_t i;
    CHECK(p07_b3_init(&p,0u)==P07_B3_OK);
    CHECK(p07_b3_next(&p,&op)==P07_B3_OK && op.kind==P07_B3_PAGE_IN);
    bad=op;bad.bytes++;
    CHECK(p07_b3_ack(&p,&bad,1)==P07_B3_FAULTED);
    CHECK(p.counters.page_ins==0u && p.resident[0]==-1);
    CHECK(p07_b3_next(&p,&op)==P07_B3_FAULTED);
    CHECK(p07_b3_init(&p,0u)==P07_B3_OK);
    CHECK(p07_b3_next(&p,&op)==P07_B3_OK && op.kind==P07_B3_PAGE_IN);
    CHECK(p07_b3_ack(&p,&op,0)==P07_B3_FAULTED);
    CHECK(p.counters.page_ins==0u && p.resident[0]==-1);
    CHECK(p07_b3_init(&p,0u)==P07_B3_OK);
    for(i=0u;i<6u;i++){
        CHECK(p07_b3_next(&p,&op)==P07_B3_OK);
        CHECK(p07_b3_ack(&p,&op,1)==P07_B3_OK);
    }
    CHECK(p.counters.dispatches==3u && p.counters.page_ins==3u);
    CHECK(p07_b3_next(&p,&op)==P07_B3_OK && op.kind==P07_B3_PAGE_OUT);
    CHECK(op.core==0u && op.slot==0u && p.dirty[0]==1u);
    CHECK(p07_b3_ack(&p,&op,0)==P07_B3_FAULTED);
    CHECK(p.dirty[0]==1u && p.resident[0]==0 && p.counters.runtime_outs==0u);
    CHECK(p07_b3_init(&p,0u)==P07_B3_OK);
    while((status=p07_b3_next(&p,&op))==P07_B3_OK) {
        if(op.kind==P07_B3_BARRIER){
            CHECK(op.tick==0u && p.counters.dispatches==27u);
            CHECK(p07_b3_ack(&p,&op,0)==P07_B3_FAULTED);
            CHECK(p.tick==0u && p.counters.barriers==0u);
            break;
        }
        CHECK(p07_b3_ack(&p,&op,1)==P07_B3_OK);
    }
    CHECK(status==P07_B3_OK && p.failed);
    CHECK(p07_b3_init(&p,0u)==P07_B3_OK);
    while((status=p07_b3_next(&p,&op))==P07_B3_OK){
        if(op.kind==P07_B3_FINAL_FLUSH){
            CHECK(p.tick==26u && p.counters.barriers==26u);
            CHECK(p07_b3_ack(&p,&op,0)==P07_B3_FAULTED);
            CHECK(p.counters.final_outs==0u && p.dirty[op.slot]);
            break;
        }
        CHECK(p07_b3_ack(&p,&op,1)==P07_B3_OK);
    }
    CHECK(status==P07_B3_OK && p.failed);
    CHECK(p07_b3_core_address(0)==UINT64_C(0x40000000));
    CHECK(p07_b3_core_address(26)==UINT64_C(0x40d00000));
    CHECK(p07_b3_core_address(27)==UINT64_MAX);
    puts("P07_B3A_NATIVE_FAULT_GATE_PASS=1");
    return 0;
}
int main(int argc,char **argv){
    int mode;
    if(argc!=2)return 20;
    mode=atoi(argv[1]);
    if(mode==2)return injected_failures();
    if(mode!=0&&mode!=1)return 21;
    return complete((uint32_t)mode,1);
}
