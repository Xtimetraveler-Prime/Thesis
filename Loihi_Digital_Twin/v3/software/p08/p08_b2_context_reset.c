#include "p08_b2_context_reset.h"
#include "p07_a2_sha256.h"
#include <string.h>

_Static_assert(P08_B2_CONTEXT_TOTAL==14155776u,"frozen B2.4 size drift");
_Static_assert(P08_B2_CONTEXT_BASE+P08_B2_CONTEXT_TOTAL==P08_B2_CONTEXT_END,
               "frozen 27-core DDR span drift");
_Static_assert(P08_B2_BACKUP_BASE+P08_B2_CONTEXT_TOTAL==P08_B2_BACKUP_END,
               "new immutable DDR 27-core backup span drift");

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
        load32(p+40u)<=4096u &&
        load32(p+44u)==0u && load32(p+48u)==0u &&
        load32(p+52u)==0u;
}
static int nonzero_sha(const uint8_t b[32]){
    uint32_t i;for(i=0u;i<32u;i++)if(b[i])return 1;
    return 0;
}
static int disjoint(uintptr_t a,size_t na,uintptr_t b,size_t nb){
    if(na>UINTPTR_MAX-a || nb>UINTPTR_MAX-b)return 0;
    return a+na<=b || b+nb<=a;
}
static int fingerprint(const p08_b2_reset_config *c,uint32_t core,
                       const uint8_t *source){
    uint8_t got[32];
    if(!valid_record(source,core) || !nonzero_sha(c->original_sha256[core]))
        return -1;
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
int p08_b2_reset_bind(p08_b2_reset_state *s,
                      const p08_b2_reset_config *c){
    uint32_t core;
    p08_b2_reset_state accepted;
    uintptr_t mutable_base,backup_base;
    /* Rebinding an already bound or poisoned state in a live session
     * would bypass the irreversible partial-copy fault contract. */
    if(s && s->magic==P08_B2_CONTEXT_MAGIC)
        return s->poisoned?P08_B2_RESET_POISONED:P08_B2_RESET_INVALID;
    if(!s||!c||!c->mutable_records||!c->immutable_backup||
       !c->original_sha256||!c->invalidate||!c->clean||
       !c->quiescent||!c->barrier||
       c->record_bytes!=P08_B2_CONTEXT_TOTAL||
       c->backup_bytes!=P08_B2_CONTEXT_TOTAL)return P08_B2_RESET_INVALID;
    mutable_base=(uintptr_t)c->mutable_records;
    backup_base=(uintptr_t)c->immutable_backup;
    if(!disjoint(mutable_base,c->record_bytes,backup_base,c->backup_bytes) ||
       !disjoint((uintptr_t)s,sizeof(*s),mutable_base,c->record_bytes) ||
       !disjoint((uintptr_t)s,sizeof(*s),backup_base,c->backup_bytes) ||
       !disjoint((uintptr_t)c->original_sha256,P08_B2_CONTEXT_CORES*32u,
                 mutable_base,c->record_bytes) ||
       !disjoint((uintptr_t)c->original_sha256,P08_B2_CONTEXT_CORES*32u,
                 backup_base,c->backup_bytes))
        return P08_B2_RESET_INVALID;
    if(c->quiescent(c->cookie)!=0)return P08_B2_RESET_IO;
    for(core=0u;core<P08_B2_CONTEXT_CORES;core++){
        const uint8_t *src=c->immutable_backup+
                          (size_t)core*P08_B2_CONTEXT_STRIDE;
        if(c->invalidate(c->cookie,(uintptr_t)src,P08_B2_CONTEXT_STRIDE)!=0)
            return P08_B2_RESET_IO;
        c->barrier(c->cookie);
        if(fingerprint(c,core,src)!=0)return P08_B2_RESET_SHA;
    }
    memset(&accepted,0,sizeof(accepted));
    accepted.magic=P08_B2_CONTEXT_MAGIC;
    accepted.config=*c;
    *s=accepted;
    return P08_B2_RESET_OK;
}
int p08_b2_reset_image(p08_b2_reset_state *s,
                       p08_b2_reset_receipt *out){
    uint32_t core;
    p08_b2_reset_receipt done={0};
    p08_b2_reset_config *c;
    if(!s||!out||s->magic!=P08_B2_CONTEXT_MAGIC)
        return P08_B2_RESET_INVALID;
    if(s->poisoned)return P08_B2_RESET_POISONED;
    c=&s->config;
    if(s->generation==UINT32_MAX)
        return fault(s,1u,P08_B2_RESET_INVALID);
    if(c->quiescent(c->cookie)!=0)
        return fault(s,2u,P08_B2_RESET_IO);
    /* Source must still match ALL 27 trusted SHA BEFORE the first
     * destructive copy. This makes later bad immutable bytes fail closed.
     */
    for(core=0u;core<P08_B2_CONTEXT_CORES;core++){
        const uint8_t *src=c->immutable_backup+
                           (size_t)core*P08_B2_CONTEXT_STRIDE;
        if(c->invalidate(c->cookie,(uintptr_t)src,P08_B2_CONTEXT_STRIDE)!=0)
            return fault(s,3u,P08_B2_RESET_IO);
        c->barrier(c->cookie);
        if(fingerprint(c,core,src)!=0)
            return fault(s,4u,P08_B2_RESET_SHA);
    }
    /* No further source mutation permitted after this check. If the
     * independent owner guarantees cannot be established, DON'T LAUNCH.
     */
    for(core=0u;core<P08_B2_CONTEXT_CORES;core++){
        const uint8_t *src=c->immutable_backup+
                           (size_t)core*P08_B2_CONTEXT_STRIDE;
        uint8_t *dest=c->mutable_records+
                      (size_t)core*P08_B2_CONTEXT_STRIDE;
        memcpy(dest,src,P08_B2_CONTEXT_STRIDE);
        if(c->clean(c->cookie,(uintptr_t)dest,P08_B2_CONTEXT_STRIDE)!=0)
            return fault(s,5u,P08_B2_RESET_IO);
        c->barrier(c->cookie);
        if(c->invalidate(c->cookie,(uintptr_t)dest,P08_B2_CONTEXT_STRIDE)!=0)
            return fault(s,6u,P08_B2_RESET_IO);
        c->barrier(c->cookie);
        if(fingerprint(c,core,dest)!=0)
            return fault(s,7u,P08_B2_RESET_SHA);
        ++done.verified_after_copy;
    }
    if(c->quiescent(c->cookie)!=0)
        return fault(s,8u,P08_B2_RESET_IO);
    done.generation=++s->generation;
    done.verified_records=P08_B2_CONTEXT_CORES;
    done.copied_bytes=P08_B2_CONTEXT_TOTAL;
    done.reset_magic=P08_B2_CONTEXT_MAGIC;
    *out=done;
    return P08_B2_RESET_OK;
}
