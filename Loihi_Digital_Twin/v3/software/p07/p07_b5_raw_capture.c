#include "p07_b5_raw_capture.h"
#include <string.h>

_Static_assert(P07_B5_CAPTURE_BYTES == 840320u,
               "original 26x1010x32 trace size changed");
_Static_assert(P07_B5_CAPTURE_WORDS == 210080u,
               "original exact 32-bit sidecar word capacity changed");
_Static_assert(P07_B5_CAPTURE_RECORDS == 26260u,
               "original 26x1010 trace order changed");
_Static_assert(P07_B5_CAPTURE_DDR_CANDIDATE_END == UINT32_C(0x420CD280),
               "candidate physical DDR sidecar geometry changed");

static int poison(p07_b5_raw_capture *r,int error){
    if(r) {
        if(!r->fault)r->fault=(uint32_t)(-error);
        r->active=0u;
    }
    return error;
}

int p07_b5_capture_begin(p07_b5_raw_capture *r,
    volatile uint32_t *sidecar,size_t words,
    const uint16_t core_compartments[P07_B5_CAPTURE_CORES]){
    uint32_t i,total=0u;
    if(!r||!sidecar||!core_compartments||
       words!=P07_B5_CAPTURE_WORDS ||
       ((uintptr_t)sidecar&3u) ||
       ((uintptr_t)core_compartments&1u))
        return P07_B5_CAPTURE_INVALID;
    for(i=0u;i<P07_B5_CAPTURE_CORES;i++){
        uint32_t count=core_compartments[i];
        if(!count||count>1024u||total>P07_B5_CAPTURE_NEURONS-count)
            return P07_B5_CAPTURE_INVALID;
        total+=count;
    }
    if(total!=P07_B5_CAPTURE_NEURONS||
       core_compartments[P07_B5_CAPTURE_CORES-1u]!=10u)
        return P07_B5_CAPTURE_INVALID;
    memset(r,0,sizeof(*r));
    r->magic=P07_B5_CAPTURE_MAGIC;
    r->active=1u;
    r->word_capacity=(uint32_t)words;
    r->ddr_words=sidecar;
    total=0u;
    for(i=0u;i<P07_B5_CAPTURE_CORES;i++){
        r->core_prefix[i]=total;
        r->core_compartments[i]=core_compartments[i];
        total+=core_compartments[i];
    }
    /* A freshly cleared physical capture is mandatory; stale DDR pages
     * cannot accidentally masquerade as a complete second run.
     * There is no output outside the exact caller-authorized sidecar.
     */
    for(i=0u;i<P07_B5_CAPTURE_WORDS;i++)sidecar[i]=0u;
    return P07_B5_CAPTURE_OK;
}

int p07_b5_capture_record(p07_b5_raw_capture *r,
    uint32_t tick,uint32_t core,uint32_t compartment,
    const uint32_t trace8[P07_B5_CAPTURE_WORDS_PER_NEURON]){
    uint32_t index,word_off,i;
    if(!r||!trace8)return P07_B5_CAPTURE_INVALID;
    if(r->magic!=P07_B5_CAPTURE_MAGIC||!r->active||
       r->fault||r->finished||!r->ddr_words||
       r->word_capacity!=P07_B5_CAPTURE_WORDS)
        return poison(r,P07_B5_CAPTURE_INVALID);
    if(tick>=P07_B5_CAPTURE_TICKS||core>=P07_B5_CAPTURE_CORES||
       compartment>=r->core_compartments[core])
        return poison(r,P07_B5_CAPTURE_ORDER);
    index=tick*P07_B5_CAPTURE_NEURONS+
          r->core_prefix[core]+compartment;
    if(index>=P07_B5_CAPTURE_RECORDS||index!=r->next_record)
        return poison(r,P07_B5_CAPTURE_ORDER);
    if((trace8[6]&UINT32_C(0xFFFFFFFE))||trace8[7])
        return poison(r,P07_B5_CAPTURE_RESERVED);
    word_off=index*P07_B5_CAPTURE_WORDS_PER_NEURON;
    if(word_off>r->word_capacity-P07_B5_CAPTURE_WORDS_PER_NEURON)
        return poison(r,P07_B5_CAPTURE_ORDER);
    /* A53 little-endian: eight original debug register uint32 values
     * give the exact 32-byte HLS 256-bit trace ABI. No synthetic data,
     * no re-encoding, no reference digest manufactured by the firmware.
     */
    for(i=0u;i<P07_B5_CAPTURE_WORDS_PER_NEURON;i++)
        r->ddr_words[word_off+i]=trace8[i];
    ++r->next_record;
    return P07_B5_CAPTURE_OK;
}

int p07_b5_capture_finalize(p07_b5_raw_capture *r){
    if(!r||r->magic!=P07_B5_CAPTURE_MAGIC||
       !r->active||r->fault||r->finished)
        return P07_B5_CAPTURE_INVALID;
    if(r->next_record!=P07_B5_CAPTURE_RECORDS)
        return poison(r,P07_B5_CAPTURE_INCOMPLETE);
    r->active=0u;
    r->finished=1u;
    return P07_B5_CAPTURE_OK;
}
