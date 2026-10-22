#include "p07_b4l_page_probe.h"
#include <string.h>

static int fail(b4l_probe_receipt *r, uint32_t step) {
    if (r->first_error==0u) r->first_error=step;
    r->done=0u;
    return B4L_PROBE_FAIL;
}
static uint64_t base(unsigned core) {
    return B4L_PROBE_BASE+(uint64_t)core*B4L_PROBE_RECORD_BYTES;
}
static int page(const b4l_probe_ops *ops,void *ctx,b4l_probe_receipt *r,
                uint32_t core,uint32_t slot,int out,int dirty,uint32_t step) {
    uint64_t cycles=0;
    if (ops->page(ctx,core,slot,out,dirty,&cycles)!=0) return fail(r,step);
    r->page_cycles+=cycles;
    if (out) ++r->page_outs;
    else ++r->page_ins;
    return B4L_PROBE_OK;
}
int b4l_probe_run(const b4l_probe_ops *ops, void *ctx,b4l_probe_receipt *r) {
    uint32_t core,slot,expected,actual,changed,saved;
    if (!ops||!r||!ops->page||!ops->debug||!ops->ddr_read)
        return B4L_PROBE_FAIL;
    memset(r,0,sizeof(*r));
    for (core=0u;core<B4L_PROBE_CORES;core++) {
        slot=core%B4L_PROBE_SLOTS;
        /* Slot zero still contains modified core #0. Persist its dirty
         * state to DDR BEFORE replacing its ownership with core #3.
         * Never use a debug readback as proof of a DDR dirty save.
         */
        if (core==3u) {
            if (page(ops,ctx,r,0u,0u,1,1,101u)) return B4L_PROBE_FAIL;
            saved=0;
            if (ops->ddr_read(ctx,base(0u)+B4L_PROBE_STATE_OFFSET,&saved))
                return fail(r,102u);
            if (saved!=r->state_dirty) return fail(r,103u);
            r->state_ddr_saved=saved;
        }
        if (page(ops,ctx,r,core,slot,0,0,110u+core))
            return B4L_PROBE_FAIL;
        expected=0;
        actual=0;
        if (ops->ddr_read(ctx,base(core)+B4L_PROBE_CONFIG_OFFSET,&expected)
                || ops->debug(ctx,slot,0,0,&actual))
            return fail(r,140u+core);
        if (actual!=expected) return fail(r,170u+core);
        r->last_core=core;r->last_slot=slot;
        ++r->unique_cores;
        if (core==0u) {
            /* Use a single 32-bit state field in 64-bit bank 1. Debug
             * transport retains the upper half. No HLS dispatch occurs.
             */
            if (ops->ddr_read(ctx,base(0u)+B4L_PROBE_STATE_OFFSET,&expected)
                    || ops->debug(ctx,0u,1u,0,&actual))
                return fail(r,200u);
            if (actual!=expected) return fail(r,201u);
            r->state_before=actual;
            changed=actual ^ B4L_PROBE_DIRTY_MASK;
            if (ops->debug(ctx,0u,1u,1,&changed)) return fail(r,202u);
            actual=0;
            if (ops->debug(ctx,0u,1u,0,&actual) || actual!=changed)
                return fail(r,203u);
            r->state_dirty=changed;
        }
    }
    /* A new page-in of evicted #0 verifies physical DDR dirty save can
     * refill a slot, not merely that the original word was still in URAM.
     */
    if (page(ops,ctx,r,0u,0u,0,0,250u)) return B4L_PROBE_FAIL;
    actual=0;
    if (ops->debug(ctx,0u,1u,0,&actual) || actual!=r->state_dirty)
        return fail(r,251u);
    r->state_restored=actual;
    r->last_core=0u;
    r->last_slot=0u;
    if (r->unique_cores!=B4L_PROBE_CORES || r->page_ins!=B4L_PROBE_PAGE_INS
            || r->page_outs!=B4L_PROBE_PAGE_OUTS
            || r->state_dirty==r->state_before
            || r->state_ddr_saved!=r->state_dirty)
        return fail(r,252u);
    r->done=1u;
    return B4L_PROBE_OK;
}
