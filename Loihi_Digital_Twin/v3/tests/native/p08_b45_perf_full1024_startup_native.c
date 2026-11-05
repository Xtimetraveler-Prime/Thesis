/* Pure C11 host-only synthetic A53 startup state, geometry, and safety. */
#include "p08_b45_perf_startup.h"
#include <stdio.h>
#include <string.h>
#include <stdint.h>
static int invalidate(void *p, uintptr_t a, size_t n){(void)p;(void)a;(void)n;return 0;}
static int idle(void *p){(void)p;return 0;}
static void fence(void *p){(void)p;}
static p08_b45_reset_state state;
static p08_b45_perf_startup_receipt receipt;
static uint8_t pins[27][32];
static int attempts=0;
#define CHECK(x) do{if(!(x)){printf("P08_B45_V2_STARTUP_NATIVE_NO_GO=%d\n",__LINE__);return 1;}}while(0)

static p08_b45_reset_config original_config(void){
    p08_b45_reset_config c={0};
    c.memory.mutable_records=(uint8_t *)(uintptr_t)UINT32_C(0x40000000);
    c.memory.immutable_backup=(const uint8_t *)(uintptr_t)UINT32_C(0x43000000);
    c.memory.original_sha256=(const uint8_t (*)[32])pins;
    c.memory.record_bytes=P08_B2_CONTEXT_TOTAL;
    c.memory.backup_bytes=P08_B2_CONTEXT_TOTAL;
    c.memory.invalidate=invalidate;
    c.memory.clean=invalidate;
    c.memory.quiescent=idle;
    c.memory.barrier=fence;
    c.memory.cookie=&attempts;
    return c;
}
int main(void){
    p08_b45_reset_config c=original_config();
    p08_b45_reset_config bad;
    state.magic=P08_B45_RESET_STATE_MAGIC;
    state.generation=1024;
    state.poisoned=1;
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&c,P08_B45_AUTHENTICATED_ONCE,&receipt)==P08_B45_START_OK);
    CHECK(receipt.prezero_magic==P08_B45_RESET_STATE_MAGIC &&
          receipt.prezero_generation==1024 && receipt.prezero_poison==1 &&
          receipt.reset_state_zeroed==1);
    CHECK(state.magic==0 && state.generation==0 && state.poisoned==0);
    puts("P08_B45_FULL1024_V2_STALE_BSS_RESET_ONLY_AFTER_VALIDATED_GEOMETRY_PASS=1");
    state.magic=P08_B45_RESET_STATE_MAGIC;
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&c,P08_B45_UNCHECKED_CONTENT,&receipt)==P08_B45_START_OK);
    CHECK(state.magic==0 && receipt.prezero_magic==P08_B45_RESET_STATE_MAGIC);
    puts("P08_B45_FULL1024_V2_BOTH_ONCE_AND_UNCHECKED_FRESH_SESSION_PASS=1");

    bad=c;bad.memory.record_bytes=7;
    state.magic=UINT32_C(0xDEADBEEF);
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,P08_B45_AUTHENTICATED_ONCE,&receipt)==P08_B45_START_BAD_SIZE);
    CHECK(state.magic==UINT32_C(0xDEADBEEF) && receipt.reset_state_zeroed==0);
    bad=c;bad.memory.original_sha256=0;
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,P08_B45_AUTHENTICATED_ONCE,&receipt)==P08_B45_START_SHA_MISSING);
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,P08_B45_UNCHECKED_CONTENT,&receipt)==P08_B45_START_OK);
    CHECK(state.magic==0);
    bad=c;bad.memory.immutable_backup=(const uint8_t *)bad.memory.mutable_records;
    state.magic=UINT32_C(0x11223344);
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,P08_B45_UNCHECKED_CONTENT,&receipt)==
          P08_B45_START_MUTABLE_BACKUP_OVERLAP);
    CHECK(state.magic==UINT32_C(0x11223344));
    bad=c;bad.memory.original_sha256=(const uint8_t (*)[32])(uintptr_t)UINT32_C(0x40000100);
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,P08_B45_AUTHENTICATED_ONCE,&receipt)==
          P08_B45_START_SHA_POINTER_OVERLAP);
    CHECK(state.magic==UINT32_C(0x11223344));
    bad=c;bad.memory.quiescent=0;
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,P08_B45_UNCHECKED_CONTENT,&receipt)==P08_B45_START_BAD_POINTER);
    CHECK(state.magic==UINT32_C(0x11223344));
    bad=c;
    CHECK(p08_b45_perf_prepare_new_session(
        &state,&bad,(p08_b45_reset_mode)3,&receipt)==P08_B45_START_BAD_MODE);
    CHECK(state.magic==UINT32_C(0x11223344));
    puts("P08_B45_FULL1024_V2_INVALID_CONFIG_NO_STATE_WRITE_AND_DIAGNOSTIC_PASS=1");
    puts("P08_B45_FULL1024_V2_NATIVE_NO_BOARD=1");
    return 0;
}
