/* P07-B.3c1: real accepted P03 MMIO adapter with synthetic fake bus.
 * This executable is NOT connected to the KV260; no physical telemetry.
 */
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include "p03_hw_adapter.h"
#include "p03_mmio.h"
#include "p07_b3c_packet_bridge.h"
#define CHECK(expr) do { if(!(expr)){fprintf(stderr,"P07_B3C1_FAULT:%u\n",(unsigned)__LINE__);return 1;} } while(0)
typedef struct {
    uint32_t global_status, pending_bytes, debug_status;
    uint32_t debug_config, debug_index, page_reads;
    uint64_t packet;
} bus;
static int read32(void *cookie,uint32_t address,uint32_t *out){
    bus *b=(bus *)cookie;
    if(!b || !out)return -1;
    switch(address){
        case P03_REG_ID:*out=P03_MMIO_ID_VALUE;break;
        case P03_REG_VERSION:*out=P03_MMIO_VERSION_VALUE;break;
        case P03_REG_CAPABILITIES:*out=UINT32_C(0x0001031F);break;
        case P03_REG_GLOBAL_STATUS:*out=b->global_status;break;
        case P03_REG_PAGE_PENDING_BYTES:*out=b->pending_bytes;++b->page_reads;break;
        case P03_REG_DEBUG_STATUS:*out=b->debug_status;break;
        case P03_REG_DEBUG_RDATA0:*out=(uint32_t)b->packet;break;
        case P03_REG_DEBUG_RDATA0+4u:*out=(uint32_t)(b->packet>>32);break;
        default:*out=0u;break;
    }
    return 0;
}
static int write32(void *cookie,uint32_t address,uint32_t value){
    bus *b=(bus *)cookie;if(!b)return -1;
    if(address==P03_REG_DEBUG_CONFIG)b->debug_config=value;
    if(address==P03_REG_DEBUG_ADDR)b->debug_index=value;
    return 0;
}
static int cache(void *cookie,uint64_t address,uint32_t bytes){
    (void)cookie;(void)address;(void)bytes;return 0;
}
static int store(void *cookie,uint64_t address,uint32_t value){
    (void)cookie;(void)address;(void)value;return 0;
}
static void barrier(void *cookie){(void)cookie;}
static int create(p03_hw_adapter *hw,bus *b){
    p03_hw_io io={read32,write32,cache,cache,store,barrier};
    if(p03_hw_init(hw,&io,b,P03_HW_BACKING_BASE,3u))return -1;
    if(p03_hw_identify(hw))return -1;
    if(p03_hw_register_core(hw,0u,UINT64_C(1)<<7u,0u,0u))return -1;
    return 0;
}
int main(void){
    static p03_hw_adapter hw;
    static p07_b3c_capture cap;
    uint64_t temporary[P03_RT_MAX_PACKETS]={0};
    bus b={0};uint32_t before;
    b.debug_status=6u;
    b.packet=UINT64_C(1)<<61u | UINT64_C(1)<<29u | UINT64_C(4)<<7u;
    CHECK(create(&hw,&b)==0);
    CHECK(p07_b3c_capture_p03_core(&hw,&cap,0u,2u,1u,
          temporary,P03_RT_MAX_PACKETS)==P07_B3C_OK);
    CHECK(cap.core_count==1u&&cap.word_count==1u&&cap.words[0]==b.packet);
    CHECK(b.debug_index==0u);
    CHECK(((b.debug_config>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u)==P03_HW_PACKET_DEBUG_BANK);
    CHECK(((b.debug_config>>P03_DEBUG_CONFIG_SLOT_SHIFT)&3u)==2u);
    CHECK(b.page_reads!=0u);
    before=cap.core_count;
    b.global_status=1u;
    CHECK(create(&hw,&b)==0);
    CHECK(p07_b3c_capture_p03_core(&hw,&cap,1u,2u,1u,
          temporary,P03_RT_MAX_PACKETS)==P07_B3C_BAD_ARGUMENT);
    CHECK(cap.core_count==before);
    /* An actual registered source, with busy engine, must fail in quiescence. */
    CHECK(p03_hw_register_core(&hw,1u,UINT64_C(1)<<7u|1u,0u,0u)==P03_HW_OK);
    CHECK(p07_b3c_capture_p03_core(&hw,&cap,1u,2u,1u,
          temporary,P03_RT_MAX_PACKETS)==P07_B3C_READ_ERROR);
    CHECK(hw.last_error==P03_HW_PROTOCOL);
    CHECK(cap.core_count==before&&cap.word_count==1u);
    b.global_status=0u;b.pending_bytes=3u;
    CHECK(create(&hw,&b)==0);
    CHECK(p03_hw_register_core(&hw,1u,UINT64_C(1)<<7u|1u,0u,0u)==P03_HW_OK);
    CHECK(p07_b3c_capture_p03_core(&hw,&cap,1u,2u,1u,
          temporary,P03_RT_MAX_PACKETS)==P07_B3C_READ_ERROR);
    CHECK(hw.last_error==P03_HW_PROTOCOL);
    CHECK(cap.core_count==before);
    b.pending_bytes=0u;b.debug_status=0u;
    CHECK(create(&hw,&b)==0);
    CHECK(p03_hw_register_core(&hw,1u,UINT64_C(1)<<7u|1u,0u,0u)==P03_HW_OK);
    CHECK(p07_b3c_capture_p03_core(&hw,&cap,1u,2u,1u,
          temporary,P03_RT_MAX_PACKETS)==P07_B3C_READ_ERROR);
    CHECK(hw.last_error==P03_HW_TIMEOUT);
    CHECK(cap.core_count==before);
    puts("P07_B3C1_REAL_P03_FAKE_BUS_READBACK_PASS=1");
    return 0;
}
