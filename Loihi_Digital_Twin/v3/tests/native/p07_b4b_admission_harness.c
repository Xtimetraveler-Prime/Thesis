/* Strict C11 read-only P03 B.4b admission with fake Xilinx BSP, not KV260. */
#include <stdint.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include "p07_b4b_board_admission.h"
#include "p07_b4b_xilinx_platform.h"
#include "p07_b4b_mutable_audit.h"
#include "p03_mmio.h"
#define CHECK(x) do {if(!(x)){fprintf(stderr,"P07_B4B_NATIVE_FAIL_LINE=%u\n",(unsigned)__LINE__);return 1;}}while(0)
typedef struct {
    uint32_t width,id,version,caps,global,pending;
    uint32_t reads,writes,cache_calls,backing_reads,fpd_reads;
    int fail_bus,fail_word;
    uint64_t corrupt_address;
} test_bus;
static test_bus bus;
static p03_hw_adapter adapter;
static p07_b4b_probe_receipt receipt;
static p07_b4b_ddr_reader reader;
static uint32_t context_cookie=1u;
static uint32_t core_for(uint64_t addr){
    return (uint32_t)((addr-P03_HW_BACKING_BASE)/P03_HW_RECORD_BYTES);
}
uint32_t p07_b4b_fake_xil_read(uintptr_t physical){
    if((uint64_t)physical==P07_B4B_FPD_REG){
        ++bus.fpd_reads;
        return bus.width;
    }
    ++bus.backing_reads;
    {
        uint32_t result=((core_for((uint64_t)physical)+1u)<<20u) |
           (uint32_t)(((uint64_t)physical-P03_HW_BACKING_BASE)%P03_HW_RECORD_BYTES);
        if(bus.corrupt_address==(uint64_t)physical)result^=1u;
        return result;
    }
}
static int read_bus(void *context,uint32_t addr,uint32_t *out){
    test_bus *b=(test_bus *)context;
    if(!b||!out||b->fail_bus)return -1;
    ++b->reads;
    switch(addr){
      case P03_REG_ID:*out=b->id;break;
      case P03_REG_VERSION:*out=b->version;break;
      case P03_REG_CAPABILITIES:*out=b->caps;break;
      case P03_REG_GLOBAL_STATUS:*out=b->global;break;
      case P03_REG_PAGE_PENDING_BYTES:*out=b->pending;break;
      default:return -1;
    }
    return 0;
}
static int fail_write(void *context,uint32_t addr,uint32_t value){
    (void)addr;(void)value;
    ++((test_bus *)context)->writes;
    return -1;
}
static int fake_cache(void *context,uint64_t addr,uint32_t bytes){
    (void)addr;(void)bytes;++((test_bus *)context)->cache_calls;return 0;
}
static int fake_store(void *context,uint64_t addr,uint32_t value){
    (void)addr;(void)value;
    ++((test_bus *)context)->writes;return -1;
}
static void fake_barrier(void *context){(void)context;}
static int reader_fault(void *context,uint64_t physical,uint32_t *out){
    test_bus *v=(test_bus *)context;
    if(v->fail_word)return -1;
    return p07_b4b_xilinx_read_phys(context,physical,out);
}
static void reset(void){
    p03_hw_io ops={read_bus,fail_write,fake_cache,fake_cache,
                   fake_store,fake_barrier};
    memset(&bus,0,sizeof(bus));memset(&adapter,0,sizeof(adapter));
    memset(&receipt,0,sizeof(receipt));memset(&reader,0,sizeof(reader));
    bus.width=UINT32_C(0xA00);
    bus.id=P03_MMIO_ID_VALUE;
    bus.version=P03_MMIO_VERSION_VALUE;
    bus.caps=UINT32_C(0x0001031F);
    if(p03_hw_init(&adapter,&ops,&bus,P03_HW_BACKING_BASE,7u)!=P03_HW_OK)
        abort();
}
static int positives(void){
    uint32_t output=UINT32_C(0x12345678),actual;
    uint64_t addr=P03_HW_BACKING_BASE+
        26u*P03_HW_RECORD_BYTES+P03_HW_EVENT1_OFFSET+4095u*4u;
    reset();
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_OK);
    CHECK(bus.reads==5u && bus.fpd_reads==1u);
    CHECK(bus.writes==0u&&bus.cache_calls==0u);
    CHECK(receipt.read_only_shell_probe_pass==1u);
    CHECK(receipt.inference_authorized==0u);
    CHECK(receipt.fpd_register==UINT32_C(0xA00));
    CHECK(p07_b4b_reader_init(&reader,&receipt,reader_fault,&bus)==P07_B4B_OK);
    CHECK(p07_b4b_current_event_read(&reader,addr,&output)==P07_B4B_OK);
    actual=(27u<<20u)|(P03_HW_EVENT1_OFFSET+4095u*4u);
    CHECK(output==actual);
    CHECK(reader.accepted_reads==1u && bus.backing_reads==1u);
    /* All original P02 event0+event1 bank edges, no access to other banks. */
    CHECK(p07_b4b_current_event_read(&reader,P03_HW_BACKING_BASE+
         P03_HW_EVENT0_OFFSET,&output)==P07_B4B_OK);
    CHECK(p07_b4b_current_event_read(&reader,P03_HW_BACKING_BASE+
         P03_HW_EVENT0_OFFSET+16380u,&output)==P07_B4B_OK);
    CHECK(p07_b4b_current_event_read(&reader,P03_HW_BACKING_BASE+
         P03_HW_EVENT1_OFFSET,&output)==P07_B4B_OK);
    CHECK(reader.accepted_reads==4u);
    CHECK(bus.writes==0u&&bus.cache_calls==0u);
    return 0;
}
static int rejects(void){
    uint32_t out=0xDEADBEEFu;uint32_t before;
    uint64_t invalid[]={
        P03_HW_BACKING_BASE-4u,
        P03_HW_BACKING_BASE,
        P03_HW_BACKING_BASE+P03_HW_EVENT0_OFFSET-4u,
        P03_HW_BACKING_BASE+P03_HW_EVENT1_OFFSET+16384u,
        P03_HW_BACKING_BASE+P03_HW_RECORD_BYTES-4u,
        P07_B4B_CORE_END,
        P07_B4B_CORE_END-3u,
        UINT64_C(0x43F00000),UINT64_C(0x43FE0000),
        UINT64_C(0x43FF0000),P07_B4B_FPD_REG,
        UINT64_C(0xA4000000),UINT64_MAX
    };
    size_t i;
    reset();
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_OK);
    CHECK(p07_b4b_reader_init(&reader,&receipt,reader_fault,&bus)==P07_B4B_OK);
    before=bus.backing_reads;
    for(i=0u;i<sizeof(invalid)/sizeof(invalid[0]);i++){
        CHECK(p07_b4b_current_event_read(&reader,invalid[i],&out)==P07_B4B_RANGE);
        CHECK(out==0xDEADBEEFu);
    }
    CHECK(bus.backing_reads==before);
    bus.fail_word=1;
    CHECK(p07_b4b_current_event_read(&reader,P03_HW_BACKING_BASE+
        P03_HW_EVENT0_OFFSET,&out)==P07_B4B_READ);
    CHECK(out==0xDEADBEEFu&&reader.failed_reads==1u);
    bus.fail_word=0;
    receipt.inference_authorized=1u;
    CHECK(p07_b4b_reader_init(&reader,&receipt,reader_fault,&bus)==P07_B4B_BAD_ARGUMENT);
    reset();
    bus.width=UINT32_C(0x800);
    before=receipt.magic;
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_BAD_WIDTH);
    CHECK(receipt.magic==before &&bus.reads==0u);
    reset();bus.id^=1u;
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_SHELL);
    CHECK(receipt.magic==0u&&adapter.last_error==P03_HW_PROTOCOL);
    reset();bus.global=1u;
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_SHELL);
    CHECK(receipt.magic==0u&&adapter.last_error==P03_HW_PROTOCOL);
    reset();bus.pending=8u;
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_SHELL);
    CHECK(receipt.magic==0u&&adapter.last_error==P03_HW_PROTOCOL);
    reset();bus.fail_bus=1;
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                       &context_cookie,&receipt)==P07_B4B_SHELL);
    CHECK(receipt.magic==0u&&adapter.last_error==P03_HW_BUS_ERROR);
    CHECK(bus.writes==0u&&bus.cache_calls==0u);
    return 0;
}

static uint32_t audit_reference_crc(uint32_t core,uint32_t offset,uint32_t bytes){
    uint32_t crc=UINT32_C(0xffffffff),k,j,bit;
    for(k=0u;k<bytes;k+=4u){
        uint32_t word=((core+1u)<<20u)|(offset+k);
        for(j=0u;j<4u;j++){
            crc^=(uint8_t)(word>>(8u*j));
            for(bit=0u;bit<8u;bit++)
                crc=(crc>>1u)^((crc&1u)?UINT32_C(0xedb88320):0u);
        }
    }
    return ~crc;
}
static int audit_read(void *context,uint64_t physical,uint32_t *out){
    if(((test_bus *)context)->fail_word)return -1;
    return p07_b4b_xilinx_read_mutable(context,physical,out);
}
static int mutable_audit(void){
    static const uint32_t offsets[5]={0x5000u,0x54000u,0x58000u,0x5c000u,0x64000u};
    static const uint32_t sizes[5]={0x2000u,0x4000u,0x4000u,0x8000u,0x8000u};
    p07_b4b_expected_mutable expected={0};
    p07_b4b_mutable_receipt checked={0},unchanged;
    p07_b3_pager pager;
    uint64_t bad=UINT64_MAX;
    uint32_t core,section;
    reset();
    CHECK(p07_b4b_probe(&adapter,p07_b4b_xilinx_read_phys,
                        &context_cookie,&receipt)==P07_B4B_OK);
    CHECK(p07_b3_init(&pager,P07_B3_ORDER_ASCENDING)==P07_B3_OK);
    for(core=0u;core<P07_B3_CORES;core++){
        CHECK(p03_hw_register_core(&adapter,(uint8_t)core,
              ((uint64_t)1u<<7u)|core,0u,0u)==P03_HW_OK);
        for(section=0u;section<5u;section++)
            expected.expected_crc[core][section]=
                audit_reference_crc(core,offsets[section],sizes[section]);
    }
    CHECK(p07_b4b_audit_mutable(&expected,&adapter,&pager,
          audit_read,&bus,&checked,&bad)==P07_B4B_AUDIT_OK);
    CHECK(checked.checked_cores==27u&&checked.checked_regions==135u);
    CHECK(checked.inspected_bytes==27u*P03_HW_MUTABLE_BYTES);
    CHECK(bus.writes==0u&&bus.cache_calls==135u&&bad==0u);
    unchanged=checked;
    bus.corrupt_address=P03_HW_BACKING_BASE+
        26u*P03_HW_RECORD_BYTES+0x64000u+0x7FFCu;
    bad=0u;
    CHECK(p07_b4b_audit_mutable(&expected,&adapter,&pager,
          audit_read,&bus,&checked,&bad)==P07_B4B_AUDIT_MISMATCH);
    CHECK(bad==P03_HW_BACKING_BASE+26u*P03_HW_RECORD_BYTES+0x64000u);
    CHECK(memcmp(&checked,&unchanged,sizeof(checked))==0);
    bus.corrupt_address=0u;
    adapter.event_counts[0][1]=1u;
    CHECK(p07_b4b_audit_mutable(&expected,&adapter,&pager,
          audit_read,&bus,&checked,&bad)==P07_B4B_AUDIT_NOT_IDLE);
    adapter.event_counts[0][1]=0u;
    pager.resident[0]=0;
    CHECK(p07_b4b_audit_mutable(&expected,&adapter,&pager,
          audit_read,&bus,&checked,&bad)==P07_B4B_AUDIT_NOT_IDLE);
    pager.resident[0]=-1;
    bus.fail_word=1;
    CHECK(p07_b4b_audit_mutable(&expected,&adapter,&pager,
          audit_read,&bus,&checked,&bad)==P07_B4B_AUDIT_IO);
    CHECK(bad==P03_HW_BACKING_BASE+0x5000u);
    CHECK(memcmp(&checked,&unchanged,sizeof(checked))==0);
    CHECK(bus.writes==0u);
    return 0;
}

int main(void){
    CHECK(positives()==0);
    CHECK(rejects()==0);
    CHECK(mutable_audit()==0);
    puts("P07_B4B_READONLY_A53_ADMISSION_NATIVE_PASS=1");
    return 0;
}
