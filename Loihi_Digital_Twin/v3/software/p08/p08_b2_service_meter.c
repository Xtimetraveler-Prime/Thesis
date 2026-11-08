#include "p08_b2_service_meter.h"
#include <string.h>
int p08_b2_meter_start(p08_b2_meter *meter,uint32_t frame_index,
                       uint64_t observed_cntfrq,uint64_t t0){
    if(!meter || observed_cntfrq==0u || frame_index>=1024u ||
       t0==UINT64_MAX)return P08_B2_METER_INVALID;
    memset(meter,0,sizeof(*meter));
    meter->magic=P08_B2_METER_MAGIC;
    meter->frame_index=frame_index;
    meter->cntfrq_el0_hz=observed_cntfrq;
    meter->cntvct[0]=t0;
    meter->next_boundary=1u;
    return P08_B2_METER_OK;
}
int p08_b2_meter_mark(p08_b2_meter *m,p08_b2_boundary b,uint64_t t){
    if(!m || m->magic!=P08_B2_METER_MAGIC)
        return P08_B2_METER_INVALID;
    if(m->poisoned)return P08_B2_METER_POISONED;
    if((uint32_t)b!=m->next_boundary ||
       m->next_boundary>=P08_B2_METER_BOUNDARIES ||
       t==UINT64_MAX){
        m->poisoned=1u;
        return P08_B2_METER_INVALID;
    }
    if(t<m->cntvct[m->next_boundary-1u]){
        m->poisoned=1u;
        return P08_B2_METER_NONMONOTONE;
    }
    m->cntvct[m->next_boundary++]=t;
    return P08_B2_METER_OK;
}
int p08_b2_meter_finish(const p08_b2_meter *m,
                        p08_b2_image_timing *out){
    p08_b2_image_timing candidate={0};
    uint32_t i;
    if(!m || !out || m->magic!=P08_B2_METER_MAGIC ||
       m->poisoned || m->next_boundary!=P08_B2_METER_BOUNDARIES ||
       m->cntfrq_el0_hz==0u)
        return P08_B2_METER_INVALID;
    candidate.magic=P08_B2_METER_MAGIC;
    candidate.frame_index=m->frame_index;
    candidate.cntfrq_el0_hz=m->cntfrq_el0_hz;
    candidate.service_entry_cntvct=m->cntvct[0];
    candidate.service_commit_cntvct=m->cntvct[6];
    candidate.total_service_cycles=m->cntvct[6]-m->cntvct[0];
    for(i=0u;i<P08_B2_METER_PHASES;i++)
        candidate.phase_cycles[i]=m->cntvct[i+1u]-m->cntvct[i];
    *out=candidate;
    return P08_B2_METER_OK;
}
