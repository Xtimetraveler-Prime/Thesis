/* B5.3.2 actual NEW C trace hook + sidecar under synthetic P03 debug banks.
 * No KV260 / Vitis / real physical trace; source-level integration only.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "p07_b4m_spike_trace.h"
#include "p07_b5_raw_capture.h"
#include "p07_b5_trace_hook.h"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"CHECK FAIL line %d: %s\n",__LINE__,#x);return 2;}}while(0)
#define CORES 27u
static p03_hw_adapter hw;
static p07_b3_pager pager;
static p07_b3c2_hw_scheduler runner;
static p07_b4m_spike_trace trace;
static p07_b5_raw_capture capture;
static uint16_t spikes[P07_B4M_TRACE_SPIKE_CAP][2];
static uint16_t counts[CORES];
static uint32_t sidecar[P07_B5_CAPTURE_WORDS+2u];
static uint32_t actual_core,actual_tick,corrupt_reserved;
int p03_hw_quiescent(p03_hw_adapter *unused){
    return unused==&hw?P03_HW_OK:P03_HW_BAD_ARGUMENT;
}
int p03_hw_debug_word(p03_hw_adapter *arg,uint8_t slot,uint8_t bank,
    uint16_t index,int write,uint32_t data[8]){
    if(arg!=&hw||slot>=3u||write||index>=counts[actual_core]||
       runner.pager->resident[slot]!=(int32_t)actual_core)
        return P03_HW_PROTOCOL;
    memset(data,0,32u);
    if(bank==7u){
        data[0]=(actual_tick<<16u)|(actual_core<<8u)|index;
        data[6]=(actual_core==26u&&index==0u&&(actual_tick&1u)==0u)?1u:0u;
        if(corrupt_reserved)data[6]|=2u;
    } else if(bank!=1u)return P03_HW_BAD_ARGUMENT;
    return P03_HW_OK;
}
static void prepare(void){
    uint32_t c;
    memset(&hw,0,sizeof(hw));
    memset(&pager,0,sizeof(pager));
    memset(&runner,0,sizeof(runner));
    memset(&trace,0,sizeof(trace));
    memset(&capture,0,sizeof(capture));
    memset(sidecar,0xAA,sizeof(sidecar));
    sidecar[0]=0xBADC0FFE;sidecar[P07_B5_CAPTURE_WORDS+1u]=0xFEE1DEAD;
    for(c=0u;c<CORES;c++){
        counts[c]=(uint16_t)(c<25u?38u:(c==25u?50u:10u));
        hw.configured[c]=1u;
        hw.metadata[c]=((uint64_t)counts[c])<<7u;
    }
    runner.pager=&pager;runner.hw=&hw;
}
static int full_26tick(void){
    uint32_t tick,c,comp,prefix;
    p07_b4m_trace_receipt receipt;
    prepare();
    CHECK(p07_b5_capture_begin(&capture,&sidecar[1],
          P07_B5_CAPTURE_WORDS,counts)==P07_B5_CAPTURE_OK);
    CHECK(p07_b5_trace_attach(&capture)==P07_B5_CAPTURE_OK);
    CHECK(p07_b4m_trace_init(&trace,&runner,spikes,
          P07_B4M_TRACE_SPIKE_CAP)==P07_B4M_TRACE_OK);
    CHECK(trace.expected_compartments==1010u);
    for(tick=0u;tick<P07_B5_CAPTURE_TICKS;tick++){
        actual_tick=tick;pager.tick=tick;pager.cursor=0u;
        for(c=0u;c<CORES;c++){
            uint32_t slot=c%3u;
            actual_core=c;
            pager.resident[slot]=(int32_t)c;
            CHECK(p07_b4m_trace_on_dispatch(&trace,&hw,
                  (uint8_t)c,(uint8_t)slot,tick,0u)==P07_B4M_TRACE_OK);
        }
        pager.cursor=CORES;
        CHECK(p07_b4m_trace_finalize(&trace,&receipt)==P07_B4M_TRACE_OK);
        CHECK(receipt.compartments_checked==1010u);
        CHECK(receipt.spikes==((tick&1u)?0u:1u));
        CHECK(trace.read_count==CORES);
        pager.tick=tick+1u;
        pager.counters.barriers=tick+1u;
        CHECK(p07_b4m_trace_advance(&trace)==P07_B4M_TRACE_OK);
    }
    CHECK(p07_b5_capture_finalize(&capture)==P07_B5_CAPTURE_OK);
    CHECK(capture.next_record==P07_B5_CAPTURE_RECORDS);
    CHECK(capture.finished==1u);
    CHECK(sidecar[0]==0xBADC0FFE);
    CHECK(sidecar[P07_B5_CAPTURE_WORDS+1u]==0xFEE1DEAD);
    for(tick=0u;tick<P07_B5_CAPTURE_TICKS;tick++){
        prefix=0u;
        for(c=0u;c<CORES;c++){
            for(comp=0u;comp<counts[c];comp++){
                uint32_t record=(tick*1010u+prefix+comp)*8u+1u;
                CHECK(sidecar[record]==((tick<<16u)|(c<<8u)|comp));
                CHECK(sidecar[record+6u]==
                    ((c==26u&&comp==0u&&(tick&1u)==0u)?1u:0u));
                CHECK(sidecar[record+7u]==0u);
            }
            prefix+=counts[c];
        }
        CHECK(prefix==1010u);
    }
    return 0;
}
static int negative_metadata_mismatch(void){
    prepare();
    CHECK(p07_b5_capture_begin(&capture,&sidecar[1],
          P07_B5_CAPTURE_WORDS,counts)==P07_B5_CAPTURE_OK);
    CHECK(p07_b5_trace_attach(&capture)==P07_B5_CAPTURE_OK);
    hw.metadata[3]+=UINT64_C(1)<<7u;
    CHECK(p07_b4m_trace_init(&trace,&runner,spikes,
          P07_B4M_TRACE_SPIKE_CAP)==P07_B4M_TRACE_INVALID);
    CHECK(capture.next_record==0u);
    return 0;
}
static int negative_corrupted_physical_trace(void){
    prepare();
    corrupt_reserved=1u;
    CHECK(p07_b5_capture_begin(&capture,&sidecar[1],
          P07_B5_CAPTURE_WORDS,counts)==P07_B5_CAPTURE_OK);
    CHECK(p07_b5_trace_attach(&capture)==P07_B5_CAPTURE_OK);
    CHECK(p07_b4m_trace_init(&trace,&runner,spikes,
          P07_B4M_TRACE_SPIKE_CAP)==P07_B4M_TRACE_OK);
    actual_tick=0u;actual_core=0u;
    pager.resident[0]=0;
    CHECK(p07_b4m_trace_on_dispatch(&trace,&hw,0u,0u,0u,0u)
           ==P07_B4M_TRACE_FAULT);
    CHECK(trace.poisoned==1u);
    CHECK(capture.next_record==0u);
    CHECK(p07_b5_capture_finalize(&capture)==P07_B5_CAPTURE_INCOMPLETE);
    return 0;
}
int main(void){
    CHECK(full_26tick()==0);
    CHECK(negative_metadata_mismatch()==0);
    CHECK(negative_corrupted_physical_trace()==0);
    puts("P07_B5_NATIVE_26260_ORIGINAL_P03_DEBUG_WORDS_SERIALIZED_PASS=1");
    puts("P07_B5_NATIVE_TRACE_HOOK_METADATA_MISMATCH_FAIL_CLOSED=1");
    puts("P07_B5_NATIVE_CORRUPTED_TRACE_ABORTS_BEFORE_ACCEPTANCE=1");
    puts("P07_B5_PHYSICAL_BOARD_CONTACT=0");
    return 0;
}
