/* Native DIFFERENTIAL original-vs-experimental context reset. No PL/JTAG.
 * Original signed P08-B2.2 production reset C is linked UNMODIFIED.
 */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "p08_b2_context_reset.h"
#include "p08_b4_4_profile_reset.h"
#include "p07_a2_sha256.h"

#define CHECK(test) do{if(!(test)){ \
    fprintf(stderr,"P08_B44_DIFFERENTIAL_NO_GO line %d: %s\n", \
            __LINE__,#test);return 1;}}while(0)

typedef struct {
    uint64_t counter;
    unsigned invalidate_calls,clean_calls,quiescent_calls,barriers;
    int fail_clean;
} witness;
static uint64_t tick(void *ctx){
    witness *w=(witness *)ctx;
    w->counter+=10000u;
    return w->counter;
}
static int invalidate(void *ctx,uintptr_t addr,size_t n){
    witness *w=(witness *)ctx;
    if(addr==0 || n!=P08_B2_CONTEXT_STRIDE)return -1;
    w->invalidate_calls++;
    return 0;
}
static int clean(void *ctx,uintptr_t addr,size_t n){
    witness *w=(witness *)ctx;
    if(addr==0 || n!=P08_B2_CONTEXT_STRIDE)return -1;
    w->clean_calls++;
    return w->fail_clean?-1:0;
}
static int idle(void *ctx){
    witness *w=(witness *)ctx;w->quiescent_calls++;return 0;
}
static void barrier(void *ctx){
    witness *w=(witness *)ctx;w->barriers++;
}
static void put32(uint8_t *base,uint32_t value){
    unsigned j;
    for(j=0;j<4u;j++)base[j]=(uint8_t)(value>>(8u*j));
}
static void configure(p08_b2_reset_config *c,uint8_t *mutable_bytes,
                      uint8_t *original_backup,
                      const uint8_t (*hashes)[32],witness *w){
    memset(c,0,sizeof(*c));
    c->mutable_records=mutable_bytes;
    c->immutable_backup=original_backup;
    c->original_sha256=hashes;
    c->record_bytes=P08_B2_CONTEXT_TOTAL;
    c->backup_bytes=P08_B2_CONTEXT_TOTAL;
    c->invalidate=invalidate;
    c->clean=clean;
    c->quiescent=idle;
    c->barrier=barrier;
    c->cookie=w;
}
static int same_receipt(const p08_b2_reset_receipt *a,
                        const p08_b2_reset_receipt *b){
    return a->generation==b->generation &&
           a->verified_records==b->verified_records &&
           a->copied_bytes==b->copied_bytes &&
           a->verified_after_copy==b->verified_after_copy &&
           a->reset_magic==b->reset_magic;
}
int main(void){
    uint8_t *backup=calloc(1,P08_B2_CONTEXT_TOTAL);
    uint8_t *original_mutable=malloc(P08_B2_CONTEXT_TOTAL);
    uint8_t *profile_mutable=malloc(P08_B2_CONTEXT_TOTAL);
    uint8_t hashes[P08_B2_CONTEXT_CORES][32];
    p08_b2_reset_config c_original,c_profile;
    p08_b2_reset_state state_original={0},state_profile={0};
    p08_b2_reset_receipt receipt_original={0},receipt_profile={0};
    p08_b44_reset_profile profile={0};
    witness original_clock={0},instrumented_clock={0};
    uint32_t core,iteration;
    CHECK(backup!=NULL && original_mutable!=NULL && profile_mutable!=NULL);
    for(core=0;core<P08_B2_CONTEXT_CORES;core++){
        uint8_t *row=backup+(size_t)core*P08_B2_CONTEXT_STRIDE;
        memcpy(row,"LTV3CTX1",8);
        put32(row+8,1);put32(row+12,4096);
        put32(row+16,P08_B2_CONTEXT_STRIDE);put32(row+20,core);
        put32(row+32,64);put32(row+36,64);
        row[64]=(uint8_t)(core+1);
        row[P08_B2_CONTEXT_STRIDE-1]=(uint8_t)(core*7+1);
        p07_a2_sha256(row,P08_B2_CONTEXT_STRIDE,hashes[core]);
    }
    memset(original_mutable,0xAC,P08_B2_CONTEXT_TOTAL);
    memset(profile_mutable,0xAC,P08_B2_CONTEXT_TOTAL);
    configure(&c_original,original_mutable,backup,
              (const uint8_t (*)[32])hashes,&original_clock);
    configure(&c_profile,profile_mutable,backup,
              (const uint8_t (*)[32])hashes,&instrumented_clock);
    CHECK(p08_b2_reset_bind(&state_original,&c_original)==P08_B2_RESET_OK);
    CHECK(p08_b2_reset_bind(&state_profile,&c_profile)==P08_B2_RESET_OK);
    for(iteration=0;iteration<2;iteration++){
        if(iteration==1){
            memset(original_mutable,0xBC,P08_B2_CONTEXT_TOTAL);
            memset(profile_mutable,0xBC,P08_B2_CONTEXT_TOTAL);
        }
        CHECK(p08_b2_reset_image(&state_original,&receipt_original)==P08_B2_RESET_OK);
        CHECK(p08_b44_profile_reset_image(&state_profile,&receipt_profile,
                                          tick,&instrumented_clock,&profile)==P08_B2_RESET_OK);
        CHECK(memcmp(original_mutable,profile_mutable,
                     P08_B2_CONTEXT_TOTAL)==0);
        CHECK(memcmp(backup,profile_mutable,P08_B2_CONTEXT_TOTAL)==0);
        CHECK(same_receipt(&receipt_original,&receipt_profile));
        CHECK(profile.magic==P08_B44_RESET_PROFILE_MAGIC);
        CHECK(profile.version==P08_B44_RESET_PROFILE_VERSION);
        CHECK(profile.source_sha_checks==27 && profile.destination_sha_checks==27);
        CHECK(profile.copied_bytes==P08_B2_CONTEXT_TOTAL);
        CHECK(profile.generation==iteration+1 && profile.verified_records==27);
        CHECK(profile.total_ticks>0);
        CHECK(profile.unattributed_ticks>0);
        CHECK(state_original.poisoned==0 && state_profile.poisoned==0);
        CHECK(original_clock.clean_calls==(iteration+1u)*27u);
        CHECK(instrumented_clock.clean_calls==(iteration+1u)*27u);
        CHECK(instrumented_clock.barriers==original_clock.barriers);
        CHECK(instrumented_clock.invalidate_calls==original_clock.invalidate_calls);
        CHECK(instrumented_clock.quiescent_calls==original_clock.quiescent_calls);
    }
    /* Source tamper is caught BEFORE any destructive copies in BOTH
     * original and profiled paths; fault stage must match original. */
    backup[P08_B2_CONTEXT_STRIDE+64]^=1u;
    memset(original_mutable,0xDA,P08_B2_CONTEXT_TOTAL);
    memset(profile_mutable,0xDA,P08_B2_CONTEXT_TOTAL);
    CHECK(p08_b2_reset_image(&state_original,&receipt_original)==P08_B2_RESET_SHA);
    CHECK(p08_b44_profile_reset_image(&state_profile,&receipt_profile,
                                      tick,&instrumented_clock,&profile)==P08_B2_RESET_SHA);
    CHECK(state_original.poisoned==1 && state_profile.poisoned==1);
    CHECK(state_original.first_fault==4 && state_profile.first_fault==4);
    CHECK(original_mutable[0]==0xDA && profile_mutable[0]==0xDA);
    CHECK(p08_b2_reset_image(&state_original,&receipt_original)==P08_B2_RESET_POISONED);
    CHECK(p08_b44_profile_reset_image(&state_profile,&receipt_profile,
                                      tick,&instrumented_clock,&profile)==P08_B2_RESET_POISONED);
    /* No publication of a fresh profile on failure. */
    CHECK(profile.generation==2u);
    free(backup);free(original_mutable);free(profile_mutable);
    puts("P08_B4_4_1_ORIGINAL_RESET_VS_PROFILED_MUTABLE_BYTE_EQUAL_PASS=1");
    puts("P08_B4_4_1_RESET_ORIGINAL_27_SHA_SOURCE_DEST_EQUIVALENCE_PASS=1");
    puts("P08_B4_4_1_ORIGINAL_POISON_FAULT_AND_NO_PARTIAL_COPY_EQUIVALENCE_PASS=1");
    puts("P08_B4_4_1_PHYSICAL_KV260_PROFILE_EXECUTED=0");
    return 0;
}
