#include "p07_b4l_page_probe.h"
#include <stdio.h>
#include <stdint.h>
#include <string.h>
typedef struct {
    uint32_t cfg[B4L_PROBE_CORES],state[B4L_PROBE_CORES];
    uint32_t slot_cfg[B4L_PROBE_SLOTS],slot_state[B4L_PROBE_SLOTS];
    int32_t resident[B4L_PROBE_SLOTS];
    uint32_t calls,failed_at,out_calls,in_calls;
} mock;
static void init(mock *m) {
    unsigned i;
    memset(m,0,sizeof(*m));
    for(i=0;i<B4L_PROBE_CORES;i++) {
        m->cfg[i]=0xB4000000u+i*17u;
        m->state[i]=0xABC10000u+i*7u;
    }
    for(i=0;i<B4L_PROBE_SLOTS;i++)m->resident[i]=-1;
}
static int mock_page(void *ctx,uint32_t core,uint32_t slot,int out,int mutable,
                     uint64_t *cycles) {
    mock *m=(mock *)ctx;
    if (core>=27u||slot>=3u||!cycles||(out&& !mutable)||(!out&&mutable))
        return -1;
    ++m->calls;
    if (m->failed_at==m->calls) return -1;
    if(out) {
        if(m->resident[slot]!=(int32_t)core)return -1;
        m->state[core]=m->slot_state[slot];
        ++m->out_calls;
    }else{
        m->resident[slot]=(int32_t)core;
        m->slot_cfg[slot]=m->cfg[core];
        m->slot_state[slot]=m->state[core];
        ++m->in_calls;
    }
    *cycles=250u;
    return 0;
}
static int mock_debug(void *ctx,uint32_t slot,uint32_t bank,int write,
                      uint32_t *value) {
    mock *m=(mock *)ctx;
    if (!value||slot>=3u||m->resident[slot]<0||bank>5u||
        (write&&bank!=1u))return -1;
    if(write)m->slot_state[slot]=*value;
    else if(bank==0u)*value=m->slot_cfg[slot];
    else if(bank==1u)*value=m->slot_state[slot];
    else *value=0x22220000u+(uint32_t)m->resident[slot]*31u+bank;
    return 0;
}
static int mock_read(void *ctx,uint64_t physical,uint32_t *value) {
    mock *m=(mock *)ctx;
    uint64_t off;
    uint32_t core;
    if(!value||physical<B4L_PROBE_BASE)return -1;
    off=physical-B4L_PROBE_BASE;
    core=(uint32_t)(off/B4L_PROBE_RECORD_BYTES);
    if(core>=27u)return -1;
    off%=B4L_PROBE_RECORD_BYTES;
    if(off==B4L_PROBE_CONFIG_OFFSET)*value=m->cfg[core];
    else if(off==B4L_PROBE_STATE_OFFSET)*value=m->state[core];
    else if(off==B4L_PROBE_AXON_OFFSET)*value=0x22220000u+core*31u+2u;
    else if(off==B4L_PROBE_SYNAPSE_OFFSET)*value=0x22220000u+core*31u+3u;
    else if(off==B4L_PROBE_ROUTE_DESCRIPTOR_OFFSET)*value=0x22220000u+core*31u+4u;
    else if(off==B4L_PROBE_ROUTE_OFFSET)*value=0x22220000u+core*31u+5u;
    else return -1;
    return 0;
}
int main(void) {
    b4l_probe_ops ops={mock_page,mock_debug,mock_read};
    b4l_probe_receipt receipt;
    mock m;
    init(&m);
    if (b4l_probe_run(&ops,&m,&receipt)!=B4L_PROBE_OK||
        receipt.done!=1u||receipt.first_error||receipt.unique_cores!=27u||
        receipt.page_ins!=28u||receipt.page_outs!=1u||
        m.in_calls!=28u||m.out_calls!=1u||
        receipt.state_ddr_saved!=receipt.state_dirty||
        receipt.state_restored!=receipt.state_dirty||
        receipt.state_before==receipt.state_dirty||
        m.state[0]!=receipt.state_dirty ||
        receipt.page_cycles!=29u*250u)return 1;
    puts("P07_B4L_NATIVE_27_CORE_3_SLOT_DIRTY_DDR_ROUNDTRIP_PASS=1");
    /* Inject physical page-out failure after core 0/1/2 initial loads.
     * No slot eviction or page-in of core 3 may happen on that failure.
     */
    init(&m);
    m.failed_at=4u;
    if (b4l_probe_run(&ops,&m,&receipt)!=B4L_PROBE_FAIL||
        receipt.done||receipt.first_error!=101u||
        m.in_calls!=3u||m.out_calls!=0u||m.resident[0]!=0)
        return 2;
    puts("P07_B4L_NATIVE_DIRTY_PAGEOUT_FAIL_CLOSED_PASS=1");
    /* Failure in the 1st page-in cannot mark a core resident. */
    init(&m);
    m.failed_at=1u;
    if(b4l_probe_run(&ops,&m,&receipt)!=B4L_PROBE_FAIL||
       receipt.done||receipt.first_error!=110u||m.in_calls)
        return 3;
    puts("P07_B4L_NATIVE_PAGEIN_FAIL_CLOSED_PASS=1");
    return 0;
}
