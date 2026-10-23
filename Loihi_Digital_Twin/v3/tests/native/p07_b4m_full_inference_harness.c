/* B4m 26-tick full CURRENT->HLS->trace->NEXT native fake bus.
 * Reuse unchanged accepted P03 MMIO fake simulator in the trace harness.
 * Synthetic routes/pixels; never a physical trained FPGA parity claim.
 */
#define main p07_b4m_trace_fixture_main
#include "p07_b4m_real_trace_integration_harness.c"
#undef main
#include "p07_b4m_full_inference.h"

#define INPUT_ROUTES 784u
#define INPUT_FRAME_BYTES (128u+INPUT_ROUTES*6u+784u)
static uint8_t encoded[INPUT_FRAME_BYTES];
static uint8_t routes_wire[INPUT_ROUTES*6u];
static uint32_t merged_words[P07_B4A_WORD_CAPACITY];
static p07_b4m_full_workspace ws;
static p07_b2_ingress_binding ingress;
static const uint8_t frozen_compiled_sha[32]={
  0x02,0xa6,0xb6,0x8a,0x2e,0xda,0x45,0x87,
  0xbb,0xdf,0x07,0xe3,0xaf,0x4a,0xa6,0x3b,
  0xdd,0x72,0x14,0x22,0x3e,0x85,0x3b,0x08,
  0xd8,0xf6,0x46,0x38,0x96,0x36,0x4f,0x5a};
static const uint8_t frozen_capacity_sha[32]={
  0x82,0xe9,0xe6,0xc1,0x12,0x64,0xc6,0x09,
  0x2d,0xbe,0x94,0xf1,0x74,0x96,0x33,0x2f,
  0xae,0x30,0x3a,0xc9,0xef,0x7d,0xfa,0xa0,
  0x1d,0x0e,0xc4,0x41,0x86,0x9a,0x94,0x98};
static uint32_t crc_bytes(const uint8_t *buf,size_t bytes,int header){
    uint32_t crc=UINT32_C(0xffffffff),j,k;size_t i;
    for(i=0u;i<bytes;i++){
        crc^=(header&&i>=52u&&i<56u)?0u:buf[i];
        for(k=0u;k<8u;k++)
            crc=(crc>>1u)^((crc&1u)?UINT32_C(0xedb88320):0u);
    }
    j=~crc;return j;
}
static void put16(uint8_t *at,uint16_t v){
    at[0]=(uint8_t)v;at[1]=(uint8_t)(v>>8u);
}
static int fake_read_ddr(void *cookie,uint64_t address,uint32_t *value){
    bus *b=(bus *)cookie;
    uint64_t rel;uint32_t core,offset;
    if(!b||!value||address<P03_HW_BACKING_BASE||
       address>=P03_HW_BACKING_BASE+(uint64_t)N*RECORD)return -1;
    rel=address-P03_HW_BACKING_BASE;
    core=(uint32_t)(rel/RECORD);
    offset=(uint32_t)(rel%RECORD);
    if(offset+4u>RECORD)return -1;
    *value=get32(record(core)+offset);
    return 0;
}
static int full_trace_write(void *ctx,uint32_t addr,uint32_t value){
    int rc=trace_write(ctx,addr,value);
    if(rc==0&&addr==P03_REG_DEBUG_COMMAND&&value==P03_CMD_START){
        bus *b=(bus *)ctx;
        uint32_t cfg=b->reg[P03_REG_DEBUG_CONFIG/4u];
        uint32_t bank=(cfg>>P03_DEBUG_CONFIG_BANK_SHIFT)&15u;
        if(bank==7u){
            uint32_t idx=b->reg[P03_REG_DEBUG_ADDR/4u];
            if(idx>0u)trace_debug_data[6]=0u;
        }
    }
    return rc;
}
static int prepare(void){
    uint32_t core,i,n;
    CHECK(setup(P07_B3_ORDER_ASCENDING)==0);
    memset(&ws,0,sizeof(ws));
    memset(&ingress,0,sizeof(ingress));
    /* Fake testing apparatus has 26 synthetic one-compartment sources.
     * Grow its modeled compartment geometry to the accepted full
     * 1000 hidden + 10 readout topology while using fake HLS state.
     */
    for(core=0u;core<27u;core++){
        if(core<24u)n=39u;
        else if(core<26u)n=32u;
        else n=10u;
        compartments[core]=(uint16_t)n;
        hw.metadata[core]=((uint64_t)n<<7u)|core;
    }
    memcpy(binding.compiled_sha256,frozen_compiled_sha,32u);
    memcpy(binding.capacity_sha256,frozen_capacity_sha,32u);
    binding.compiled_sha256[0]=0x02u;
    memset(encoded,0,sizeof(encoded));
    memcpy(encoded,"P06B13I1",8u);
    put32(encoded+8u,1u);
    put32(encoded+12u,128u);
    put32(encoded+16u,INPUT_ROUTES*6u+784u);
    put32(encoded+20u,INPUT_ROUTES);
    put32(encoded+24u,27u);
    put32(encoded+28u,784u);
    put32(encoded+32u,25u);
    put32(encoded+36u,26u);
    put32(encoded+40u,6u);
    put32(encoded+44u,784u);
    for(i=0u;i<INPUT_ROUTES;i++){
        uint8_t *r=routes_wire+i*6u;
        put16(r,(uint16_t)i);put16(r+2u,26u);put16(r+4u,125u);
    }
    memcpy(encoded+128u,routes_wire,sizeof(routes_wire));
    memset(encoded+128u+sizeof(routes_wire),255,784u);
    memcpy(encoded+64u,frozen_compiled_sha,32u);
    memcpy(encoded+96u,frozen_capacity_sha,32u);
    put32(encoded+48u,crc_bytes(encoded+128u,
                                INPUT_ROUTES*6u+784u,0));
    put32(encoded+52u,crc_bytes(encoded,128u,1));
    ingress.core_count=27u;ingress.route_count=INPUT_ROUTES;
    ingress.trusted_routes=routes_wire;
    ingress.trusted_routes_bytes=sizeof(routes_wire);
    memcpy(ingress.compiled_sha256,frozen_compiled_sha,32u);
    memcpy(ingress.capacity_sha256,frozen_capacity_sha,32u);
    ws.merged_current_words=merged_words;
    ws.merged_capacity=P07_B4A_WORD_CAPACITY;
    ws.source_spikes=detected_spikes;
    ws.source_capacity=P07_B4M_TRACE_SPIKE_CAP;
    ws.frame_scratch=route_scratch;
    ws.scratch_capacity=sizeof(route_scratch);
    ws.packet_frame=route_frame;
    ws.frame_capacity=sizeof(route_frame);
    trace_corrupt=0u;read_traces=0u;
    hw.io.write32=full_trace_write;hw.io.read32=trace_read;
    return 0;
}
static int success(void){
    p07_b4m_full_receipt receipt={0};
    CHECK(prepare()==0);
    CHECK(p07_b4m_full_run(&runner,&ingress,&binding,
         encoded,sizeof(encoded),fake_read_ddr,&sim,&ws,&receipt)
         ==P07_B4M_FULL_OK);
    CHECK(receipt.magic==P07_B4M_FULL_MAGIC);
    CHECK(receipt.dispatches==702u&&receipt.barriers==26u);
    CHECK(receipt.final_outs==3u);
    CHECK(receipt.trace_compartment_count==1010u);
    CHECK(receipt.external_current==25u*784u);
    CHECK(receipt.source_spikes==25u*26u);
    CHECK(receipt.captured_packets==25u*26u);
    CHECK(receipt.inserted_next==25u*26u);
    CHECK(receipt.classification==0u);
    CHECK(receipt.page_ins==pager.counters.page_ins);
    CHECK(receipt.page_outs==pager.counters.runtime_outs);
    CHECK(receipt.read_bytes==pager.counters.read_bytes);
    CHECK(receipt.write_bytes==pager.counters.write_bytes);
    CHECK(sim.dispatches==702u&&sim.readout_checks==25u);
    CHECK(read_traces==26u*1010u);
    return 0;
}
static int no_provenance(void){
    p07_b4m_full_receipt receipt={0};
    CHECK(prepare()==0);
    trace_corrupt=1u; /* trace after_state differs from actual state */
    CHECK(p07_b4m_full_run(&runner,&ingress,&binding,
         encoded,sizeof(encoded),fake_read_ddr,&sim,&ws,&receipt)
         ==P07_B4M_FULL_FAULT);
    CHECK(receipt.magic==0u&&receipt.first_fault==9u);
    CHECK(pager.failed&&runner.poisoned);
    CHECK(pager.counters.barriers==0u);
    CHECK(sim.debug_writes==0u&&sim.nonresident_stores>0u);
    return 0;
}
static int invalid_ingress(void){
    p07_b4m_full_receipt receipt={0};
    CHECK(prepare()==0);
    encoded[128u]^=1u; /* real B2a CRC must reject before writes */
    CHECK(p07_b4m_full_run(&runner,&ingress,&binding,
         encoded,sizeof(encoded),fake_read_ddr,&sim,&ws,&receipt)
         ==P07_B4M_FULL_FAULT);
    CHECK(receipt.magic==0u&&receipt.first_fault==1u);
    CHECK(pager.failed&&runner.poisoned);
    CHECK(sim.dispatches==0u&&sim.nonresident_stores==0u);
    return 0;
}
int main(void){
    backing=(uint8_t *)malloc((size_t)N*RECORD);
    resident_memory=(uint8_t *)malloc((size_t)3u*RECORD);
    CHECK(backing!=NULL&&resident_memory!=NULL);
    CHECK(success()==0);
    CHECK(no_provenance()==0);
    CHECK(invalid_ingress()==0);
    free(backing);free(resident_memory);
    puts("P07_B4M_FULL_26_TICK_A53_CONTROL_FAKE_P03_PASS=1");
    puts("P07_B4M_FULL_REAL_CURRENT_TRACE_NEXT_702_SIMULATED=1");
    puts("P07_B4M_FULL_REAL_KV260_INFERENCE_VERIFIED=0");
    return 0;
}
