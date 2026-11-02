/*
 * EXPERIMENTAL P08-B4.4.1 standalone instrumented clone of the frozen
 * P08-B2.2 p08_b2_reset_image path. DO NOT compile both as replacement
 * under the same symbol; original p08_b2_reset_image remains untouched.
 * This implementation uses exactly the same real SHA256, record gates,
 * DDR copy order, quiescence, cache callbacks, barriers and fault stages.
 */
#include "p08_b4_4_profile_reset.h"
#include "p07_a2_sha256.h"
#include <string.h>

_Static_assert(P08_B2_CONTEXT_TOTAL==14155776u, "original 27x512KiB unchanged");
_Static_assert(P08_B44_RESET_PROFILE_CORES==P08_B2_CONTEXT_CORES,
               "original 27 context count changed");
_Static_assert(P08_B2_CONTEXT_STRIDE==524288u, "original record stride changed");

static uint32_t load32(const uint8_t *p){
    return (uint32_t)p[0] | ((uint32_t)p[1]<<8u) |
           ((uint32_t)p[2]<<16u) | ((uint32_t)p[3]<<24u);
}
static int valid_record(const uint8_t *p,uint32_t core){
    static const uint8_t magic[8]={'L','T','V','3','C','T','X','1'};
    return memcmp(p,magic,sizeof(magic))==0 &&
        load32(p+8u)==1u && load32(p+12u)==4096u &&
        load32(p+16u)==P08_B2_CONTEXT_STRIDE &&
        load32(p+20u)==core &&
        load32(p+24u)==0u && load32(p+28u)==0u &&
        load32(p+32u)>0u && load32(p+32u)<=1024u &&
        load32(p+36u)>0u && load32(p+36u)<=32768u &&
        load32(p+40u)<=4096u && load32(p+44u)==0u &&
        load32(p+48u)==0u && load32(p+52u)==0u;
}
static int nonzero_sha(const uint8_t b[32]){
    uint32_t i;
    for(i=0u;i<32u;i++)if(b[i])return 1;
    return 0;
}
static int fingerprint(const p08_b2_reset_config *c,
                       uint32_t core,const uint8_t *source){
    uint8_t got[32];
    if(!valid_record(source,core) ||
       !nonzero_sha(c->original_sha256[core]))return -1;
    p07_a2_sha256(source,P08_B2_CONTEXT_STRIDE,got);
    return memcmp(got,c->original_sha256[core],32u)==0?0:-1;
}
static int fault(p08_b2_reset_state *s,uint32_t stage,int value){
    if(s){
        if(!s->poisoned)s->first_fault=stage;
        s->poisoned=1u;
    }
    return value;
}
static int add_interval(p08_b44_reset_profile *p,unsigned phase,
                        uint64_t start,uint64_t end){
    uint64_t delta;
    if(end<start || phase>=P08_B44_RESET_PROFILE_PHASES)return -1;
    delta=end-start;
    if(delta>UINT64_MAX-p->phase_ticks[phase])return -1;
    p->phase_ticks[phase]+=delta;
    return 0;
}
static int timed_end(p08_b2_reset_state *s,
                     p08_b44_reset_profile *profile,
                     unsigned phase,uint64_t start,
                     p08_b44_counter_now now,void *clock_cookie){
    if(add_interval(profile,phase,start,now(clock_cookie))!=0)
        return fault(s,9u,P08_B2_RESET_IO);
    return P08_B2_RESET_OK;
}
int p08_b44_profile_reset_image(
    p08_b2_reset_state *s,p08_b2_reset_receipt *out,
    p08_b44_counter_now now,void *clock_cookie,
    p08_b44_reset_profile *profile){
    uint32_t core;
    p08_b2_reset_receipt done={0};
    p08_b2_reset_config *c;
    p08_b44_reset_profile candidate={0};
    uint64_t entry,finish,t0,sum=0u;
    unsigned i;

    if(!s||!out||!now||!profile||s->magic!=P08_B2_CONTEXT_MAGIC)
        return P08_B2_RESET_INVALID;
    if(s->poisoned)return P08_B2_RESET_POISONED;
    c=&s->config;
    if(s->generation==UINT32_MAX)
        return fault(s,1u,P08_B2_RESET_INVALID);
    candidate.magic=P08_B44_RESET_PROFILE_MAGIC;
    candidate.version=P08_B44_RESET_PROFILE_VERSION;
    entry=now(clock_cookie);
    if(c->quiescent(c->cookie)!=0)
        return fault(s,2u,P08_B2_RESET_IO);
    /* Exactly the original ALL-27 immutable SHA BEFORE FIRST COPY. */
    for(core=0u;core<P08_B2_CONTEXT_CORES;core++){
        const uint8_t *src=c->immutable_backup+
                          (size_t)core*P08_B2_CONTEXT_STRIDE;
        t0=now(clock_cookie);
        if(c->invalidate(c->cookie,(uintptr_t)src,P08_B2_CONTEXT_STRIDE)!=0)
            return fault(s,3u,P08_B2_RESET_IO);
        c->barrier(c->cookie);
        if(timed_end(s,&candidate,P08_B44_SOURCE_CACHE_INVALIDATE,t0,
                     now,clock_cookie)!=P08_B2_RESET_OK)
            return P08_B2_RESET_IO;
        t0=now(clock_cookie);
        if(fingerprint(c,core,src)!=0)
            return fault(s,4u,P08_B2_RESET_SHA);
        if(timed_end(s,&candidate,P08_B44_SOURCE_SHA256,t0,
                     now,clock_cookie)!=P08_B2_RESET_OK)
            return P08_B2_RESET_IO;
        candidate.source_sha_checks++;
    }
    /* Identical 27-core mutable overwrite, cache ops and SHA readback. */
    for(core=0u;core<P08_B2_CONTEXT_CORES;core++){
        const uint8_t *src=c->immutable_backup+
                           (size_t)core*P08_B2_CONTEXT_STRIDE;
        uint8_t *dest=c->mutable_records+
                      (size_t)core*P08_B2_CONTEXT_STRIDE;
        t0=now(clock_cookie);
        memcpy(dest,src,P08_B2_CONTEXT_STRIDE);
        if(timed_end(s,&candidate,P08_B44_MUTABLE_MEMCPY,t0,
                     now,clock_cookie)!=P08_B2_RESET_OK)
            return P08_B2_RESET_IO;
        t0=now(clock_cookie);
        if(c->clean(c->cookie,(uintptr_t)dest,P08_B2_CONTEXT_STRIDE)!=0)
            return fault(s,5u,P08_B2_RESET_IO);
        c->barrier(c->cookie);
        if(c->invalidate(c->cookie,(uintptr_t)dest,P08_B2_CONTEXT_STRIDE)!=0)
            return fault(s,6u,P08_B2_RESET_IO);
        c->barrier(c->cookie);
        if(timed_end(s,&candidate,P08_B44_MUTABLE_CACHE_CLEAN_INVALIDATE,t0,
                     now,clock_cookie)!=P08_B2_RESET_OK)
            return P08_B2_RESET_IO;
        t0=now(clock_cookie);
        if(fingerprint(c,core,dest)!=0)
            return fault(s,7u,P08_B2_RESET_SHA);
        if(timed_end(s,&candidate,P08_B44_MUTABLE_SHA256,t0,
                     now,clock_cookie)!=P08_B2_RESET_OK)
            return P08_B2_RESET_IO;
        ++done.verified_after_copy;
        candidate.destination_sha_checks++;
    }
    if(c->quiescent(c->cookie)!=0)
        return fault(s,8u,P08_B2_RESET_IO);
    finish=now(clock_cookie);
    if(finish<entry)return fault(s,9u,P08_B2_RESET_IO);
    candidate.total_ticks=finish-entry;
    for(i=0u;i<P08_B44_RESET_PROFILE_PHASES;i++){
        if(candidate.phase_ticks[i]>UINT64_MAX-sum)
            return fault(s,9u,P08_B2_RESET_IO);
        sum+=candidate.phase_ticks[i];
    }
    if(sum>candidate.total_ticks)
        return fault(s,9u,P08_B2_RESET_IO);
    candidate.unattributed_ticks=candidate.total_ticks-sum;
    done.generation=++s->generation;
    done.verified_records=P08_B2_CONTEXT_CORES;
    done.copied_bytes=P08_B2_CONTEXT_TOTAL;
    done.reset_magic=P08_B2_CONTEXT_MAGIC;
    candidate.generation=done.generation;
    candidate.verified_records=done.verified_after_copy;
    candidate.copied_bytes=done.copied_bytes;
    *out=done;
    *profile=candidate;
    return P08_B2_RESET_OK;
}
