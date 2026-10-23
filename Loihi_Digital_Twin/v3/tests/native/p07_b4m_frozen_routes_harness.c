/* Fake original-P03 registration + genuine C SHA stage admission.
 * Does NOT use B2 official TEST or real frozen B2.4 user-local files.
 */
#define main original_p07_b3c23_routes_fake_main
#include "p07_b3c23_hw_scheduler_harness.c"
#undef main
#include "p07_b4m_frozen_routes.h"
#include "p07_a2_sha256.h"

static uint8_t route_out[P07_B4M_ROUTE_OUT_BYTES];
static uint8_t route_in[P07_B4M_ROUTE_IN_BYTES];
static p07_b2_route copied_routes[P07_B2_MAX_ROUTE_BINDINGS];
static uint16_t copied_comps[27];
static p07_b4m_frozen_binding loaded;

static void put16(uint8_t *p,uint16_t word){
    p[0]=(uint8_t)word;p[1]=(uint8_t)(word>>8u);
}
static void write_header(uint8_t *img,uint32_t bytes,
                         uint32_t count,uint32_t entry,const char *magic){
    static const uint8_t compiled[32]={
        0x02,0xa6,0xb6,0x8a,0x2e,0xda,0x45,0x87,
        0xbb,0xdf,0x07,0xe3,0xaf,0x4a,0xa6,0x3b,
        0xdd,0x72,0x14,0x22,0x3e,0x85,0x3b,0x08,
        0xd8,0xf6,0x46,0x38,0x96,0x36,0x4f,0x5a};
    static const uint8_t cap[32]={
        0x82,0xe9,0xe6,0xc1,0x12,0x64,0xc6,0x09,
        0x2d,0xbe,0x94,0xf1,0x74,0x96,0x33,0x2f,
        0xae,0x30,0x3a,0xc9,0xef,0x7d,0xfa,0xa0,
        0x1d,0x0e,0xc4,0x41,0x86,0x9a,0x94,0x98};
    memset(img,0,bytes);
    memcpy(img,magic,8u);
    put32(img+8u,1u);put32(img+12u,bytes);put32(img+16u,27u);
    put32(img+20u,count);put32(img+24u,entry);put32(img+28u,128u);
    memcpy(img+32u,compiled,32u);memcpy(img+64u,cap,32u);
}
static void seal(uint8_t *img,uint32_t bytes){
    p07_a2_sha256(img+128u,bytes-128u,img+96u);
}
static int fixture(void){
    uint32_t c,i,n;
    CHECK(setup(P07_B3_ORDER_ASCENDING)==0);
    write_header(route_out,sizeof(route_out),26u,8u,"B4MROUT1");
    write_header(route_in,sizeof(route_in),784u,6u,"B4MING01");
    for(c=0u;c<27u;c++){
        if(c<24u)n=39u;else if(c<26u)n=32u;else n=10u;
        hw.metadata[c]=((uint64_t)n<<7u)|c;
        put16(route_out+128u+c*2u,(uint16_t)n);
    }
    for(c=0u;c<26u;c++){
        uint8_t *at=route_out+128u+64u+c*8u;
        put16(at,(uint16_t)c);put16(at+2u,0u);
        put16(at+4u,26u);put16(at+6u,(uint16_t)(100u+c));
    }
    for(i=0u;i<784u;i++){
        uint8_t *at=route_in+128u+i*6u;
        put16(at,(uint16_t)i);put16(at+2u,26u);put16(at+4u,125u);
    }
    seal(route_out,sizeof(route_out));seal(route_in,sizeof(route_in));
    return 0;
}
static int positive(void){
    CHECK(fixture()==0);
    CHECK(p07_b4m_mount_frozen_routes(
        &loaded,route_out,sizeof(route_out),
        route_in,sizeof(route_in),&hw,copied_routes,
        P07_B2_MAX_ROUTE_BINDINGS,copied_comps,27u)==P07_B4M_ROUTE_OK);
    CHECK(loaded.packets.core_count==27u&&loaded.packets.route_count==26u);
    CHECK(loaded.inputs.route_count==784u);
    CHECK(loaded.emitted_route_count==26u);
    CHECK(loaded.packets.routes==copied_routes);
    CHECK(loaded.packets.compartments_per_core==copied_comps);
    CHECK(copied_comps[26]==10u);
    CHECK(copied_routes[0].source_core==0u);
    CHECK(copied_routes[25].destination_axon==125u);
    return 0;
}
static int rejects_sha_and_topology(void){
    p07_b4m_frozen_binding before=loaded;
    CHECK(fixture()==0);
    route_out[128u+64u+7u]^=1u;
    CHECK(p07_b4m_mount_frozen_routes(
        &loaded,route_out,sizeof(route_out),
        route_in,sizeof(route_in),&hw,copied_routes,
        P07_B2_MAX_ROUTE_BINDINGS,copied_comps,27u)==P07_B4M_ROUTE_SHA);
    CHECK(memcmp(&loaded,&before,sizeof(loaded))==0);
    CHECK(fixture()==0);
    put16(route_out+128u+64u+6u,4095u); /* route invalid / unbound */
    seal(route_out,sizeof(route_out));
    CHECK(p07_b4m_mount_frozen_routes(
        &loaded,route_out,sizeof(route_out),
        route_in,sizeof(route_in),&hw,copied_routes,
        P07_B2_MAX_ROUTE_BINDINGS,copied_comps,27u)==P07_B4M_ROUTE_TOPOLOGY);
    CHECK(memcmp(&loaded,&before,sizeof(loaded))==0);
    CHECK(fixture()==0);
    route_in[32u]^=1u; /* original compiled SHA altered */
    CHECK(p07_b4m_mount_frozen_routes(
        &loaded,route_out,sizeof(route_out),
        route_in,sizeof(route_in),&hw,copied_routes,
        P07_B2_MAX_ROUTE_BINDINGS,copied_comps,27u)==P07_B4M_ROUTE_SHA);
    CHECK(memcmp(&loaded,&before,sizeof(loaded))==0);
    return 0;
}
int main(void){
    backing=(uint8_t *)malloc((size_t)N*RECORD);
    resident_memory=(uint8_t *)malloc((size_t)3u*RECORD);
    CHECK(backing&&resident_memory);
    CHECK(positive()==0);
    CHECK(rejects_sha_and_topology()==0);
    free(backing);free(resident_memory);
    puts("P07_B4M_FROZEN_ROUTES_C11_NATIVE_MOUNT_PASS=1");
    puts("P07_B4M_FROZEN_ROUTES_SHA_AND_TOPOLOGY_FAIL_CLOSED=1");
    puts("P07_B4M_FROZEN_ROUTES_REAL_BOARD_STAGED=0");
    return 0;
}
