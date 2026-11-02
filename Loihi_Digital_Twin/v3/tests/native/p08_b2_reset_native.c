/* P08-B2.2 native fake-DDR: real 27*512KiB copies/hashes; NO FPGA. */
#include "p08_b2_context_reset.h"
#include "p08_b2_service_meter.h"
#include "p07_a2_sha256.h"
#include <stdlib.h>
#include <string.h>
#include <stdio.h>

typedef struct {
    uintptr_t source,destination;
    int fail_clean,quiescent,clean_calls,invalidations;
    unsigned barriers;
} fake_bus;
static uint8_t *source,*destination;
static uint8_t digests[27][32];
static int inv(void *opaque,uintptr_t address,size_t size){
    fake_bus *ctx=(fake_bus *)opaque;
    if(size!=P08_B2_CONTEXT_STRIDE)return -1;
    if(!((address>=ctx->source &&
          address+size<=ctx->source+P08_B2_CONTEXT_TOTAL) ||
         (address>=ctx->destination &&
          address+size<=ctx->destination+P08_B2_CONTEXT_TOTAL)))return -1;
    ++ctx->invalidations;
    return 0;
}
static int clean(void *opaque,uintptr_t address,size_t size){
    fake_bus *ctx=(fake_bus *)opaque;
    if(size!=P08_B2_CONTEXT_STRIDE ||
       address<ctx->destination ||
       address+size>ctx->destination+P08_B2_CONTEXT_TOTAL)return -1;
    ++ctx->clean_calls;
    if(ctx->fail_clean)return -1;
    return 0;
}
static int quiescent(void *opaque){
    return ((fake_bus *)opaque)->quiescent ? -1:0;
}
static void fence(void *opaque){++((fake_bus *)opaque)->barriers;}
static void put32(uint8_t *p,uint32_t x){
    p[0]=(uint8_t)x;p[1]=(uint8_t)(x>>8u);
    p[2]=(uint8_t)(x>>16u);p[3]=(uint8_t)(x>>24u);
}
static int init_source(void){
    uint32_t i;
    source=(uint8_t *)malloc(P08_B2_CONTEXT_TOTAL);
    destination=(uint8_t *)malloc(P08_B2_CONTEXT_TOTAL);
    if(!source||!destination)return -1;
    memset(source,0,P08_B2_CONTEXT_TOTAL);
    memset(destination,0xA5,P08_B2_CONTEXT_TOTAL);
    for(i=0u;i<27u;i++){
        uint8_t *p=source+(size_t)i*P08_B2_CONTEXT_STRIDE;
        memcpy(p,"LTV3CTX1",8);
        put32(p+8,1);put32(p+12,4096);
        put32(p+16,P08_B2_CONTEXT_STRIDE);
        put32(p+20,i);
        put32(p+32,i==26u?10u: (i<12u?39u:38u));
        put32(p+36,1u);put32(p+40,0u);
        p[0x1000u]=(uint8_t)(i+1u);
        p[P08_B2_CONTEXT_STRIDE-1u]=(uint8_t)(i^0xAAu);
        p07_a2_sha256(p,P08_B2_CONTEXT_STRIDE,digests[i]);
    }
    return 0;
}
static int reset_positive(void){
    p08_b2_reset_state state={0};
    p08_b2_reset_receipt receipt={0};
    fake_bus bus={0};
    p08_b2_reset_config cfg={0};
    uint8_t old;
    int rc;
    bus.source=(uintptr_t)source;
    bus.destination=(uintptr_t)destination;
    cfg.mutable_records=destination;
    cfg.immutable_backup=source;
    cfg.original_sha256=(const uint8_t (*)[32])digests;
    cfg.record_bytes=P08_B2_CONTEXT_TOTAL;
    cfg.backup_bytes=P08_B2_CONTEXT_TOTAL;
    cfg.invalidate=inv;cfg.clean=clean;
    cfg.quiescent=quiescent;cfg.barrier=fence;cfg.cookie=&bus;
    rc=p08_b2_reset_bind(&state,&cfg);
    if(rc!=P08_B2_RESET_OK)return 10;
    if(p08_b2_reset_image(&state,&receipt)!=P08_B2_RESET_OK ||
       receipt.generation!=1u ||
       receipt.verified_records!=27u ||
       receipt.verified_after_copy!=27u ||
       receipt.copied_bytes!=P08_B2_CONTEXT_TOTAL ||
       memcmp(destination,source,P08_B2_CONTEXT_TOTAL)!=0)return 11;
    /* Image #1 starts from entirely new immutable original neuron state,
     * not from image #0's mutated backing context.
     */
    memset(destination+P08_B2_CONTEXT_STRIDE*9u+0x5000u,0x55,8192u);
    if(p08_b2_reset_image(&state,&receipt)!=P08_B2_RESET_OK ||
       receipt.generation!=2u ||
       memcmp(destination,source,P08_B2_CONTEXT_TOTAL)!=0)return 12;

    /* Failure in LAST SOURCE RECORD is preflighted before ANY restore write.
     * All original expected hashes remain pinned: no dynamic reauthorization.
     */
    old=source[P08_B2_CONTEXT_TOTAL-1u];
    source[P08_B2_CONTEXT_TOTAL-1u]^=0x01u;
    destination[0]^=0x33u;
    {
        uint8_t unchanged=destination[0];
        rc=p08_b2_reset_image(&state,&receipt);
        if(rc!=P08_B2_RESET_SHA || !state.poisoned ||
           destination[0]!=unchanged || state.first_fault!=4u ||
           p08_b2_reset_image(&state,&receipt)!=P08_B2_RESET_POISONED)
            return 13;
    }
    source[P08_B2_CONTEXT_TOTAL-1u]=old;
    if(bus.clean_calls!=54 || bus.invalidations<135)return 14;

    /* New session with authenticated source; injected PS clean failure is
     * permanent even though 27-source precheck already succeeded.
     */
    if(p08_b2_reset_bind(&state,&cfg)!=P08_B2_RESET_OK)return 15;
    bus.fail_clean=1;
    if(p08_b2_reset_image(&state,&receipt)!=P08_B2_RESET_IO ||
       !state.poisoned || state.first_fault!=5u ||
       p08_b2_reset_image(&state,&receipt)!=P08_B2_RESET_POISONED)
        return 16;
    bus.fail_clean=0;

    /* Quiescence failure must block restore entirely. */
    if(p08_b2_reset_bind(&state,&cfg)!=P08_B2_RESET_OK)return 17;
    bus.quiescent=1;
    if(p08_b2_reset_image(&state,&receipt)!=P08_B2_RESET_IO ||
       state.first_fault!=2u || state.generation!=0u)
        return 18;
    return 0;
}
static int meter_tests(void){
    p08_b2_meter meter={0};
    p08_b2_image_timing timing={0};
    uint64_t times[]={1100u,1120u,1130u,1145u,1800u,1810u};
    uint32_t i;
    if(p08_b2_meter_start(&meter,1023u,99999001u,1000u)!=P08_B2_METER_OK)
        return 21;
    for(i=0u;i<6u;i++)
        if(p08_b2_meter_mark(&meter,(p08_b2_boundary)(i+1u),
                             times[i])!=P08_B2_METER_OK)
            return 22;
    if(p08_b2_meter_finish(&meter,&timing)!=P08_B2_METER_OK ||
       timing.total_service_cycles!=810u ||
       timing.cntfrq_el0_hz!=99999001u ||
       timing.phase_cycles[0]!=100u ||
       timing.phase_cycles[3]!=655u)
        return 23;
    if(p08_b2_meter_mark(&meter,P08_B2_AFTER_JOURNAL_COMMIT,1900u)!=
       P08_B2_METER_INVALID || !meter.poisoned)
        return 24;
    if(p08_b2_meter_start(&meter,0u,1u,100u)!=P08_B2_METER_OK ||
       p08_b2_meter_mark(&meter,P08_B2_AFTER_STATE_RESTORE,99u)!=
       P08_B2_METER_NONMONOTONE ||
       p08_b2_meter_finish(&meter,&timing)==P08_B2_METER_OK)
        return 25;
    if(p08_b2_meter_start(&meter,1024u,1u,100u)==P08_B2_METER_OK ||
       p08_b2_meter_start(&meter,0u,0u,100u)==P08_B2_METER_OK)
        return 26;
    return 0;
}
int main(void){
    int rc;
    if(init_source()!=0)return 2;
    rc=reset_positive();
    if(rc!=0){
        fprintf(stderr,"P08_B2_2_NATIVE_RESET_NO_GO=%d\n",rc);
        return rc;
    }
    rc=meter_tests();
    if(rc!=0){
        fprintf(stderr,"P08_B2_2_NATIVE_METER_NO_GO=%d\n",rc);
        return rc;
    }
    puts("P08_B2_2_NATIVE_27_RECORD_RESET_TWICE=PASS");
    puts("P08_B2_2_NATIVE_LAST_RECORD_SHA_PRESERVE_ALL=PASS");
    puts("P08_B2_2_NATIVE_CACHE_FAULT_POISON=PASS");
    puts("P08_B2_2_NATIVE_A53_TIMER_BOUNDARIES=PASS");
    puts("P08_B2_2_PHYSICAL_DDR_OWNER_VERIFIED=0");
    puts("P08_B2_2_KV260_EXECUTED=0");
    free(source);free(destination);
    return 0;
}
