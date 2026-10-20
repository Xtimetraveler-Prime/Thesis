/* Host-only native file runner; production P07-B.2b does NO file I/O. */
#include "p07_b2_packet.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define MAX_FILE (1024u*1024u)
static uint8_t ingress_bytes[MAX_FILE],ingress_map[MAX_FILE];
static uint8_t route_bytes[MAX_FILE],compartments[MAX_FILE],frame[MAX_FILE];
static p07_b2b_route compiled_routes[P07_B2B_MAX_FRAME_PACKETS];
static uint16_t per_core[P07_B2_MAX_CORES];
static p07_b2_input_event pending[P07_B2B_MAX_FRAME_PACKETS];
static p07_b2b_origin origins[P07_B2_MAX_CORES*P07_B2B_COMPARTMENTS];
static size_t file_read(const char *path,uint8_t *buf,size_t cap) {
    FILE *f=fopen(path,"rb");size_t n;
    if(!f) return 0u;
    n=fread(buf,1u,cap,f);
    if(ferror(f) || (n==cap && fgetc(f)!=EOF) || fclose(f)) return 0u;
    return n;
}
static uint16_t u16(const uint8_t *x) {
    return (uint16_t)((uint16_t)x[0] | ((uint16_t)x[1]<<8));
}
static uint32_t u32(const uint8_t *x) {
    return (uint32_t)x[0] | ((uint32_t)x[1]<<8) | ((uint32_t)x[2]<<16) | ((uint32_t)x[3]<<24);
}
static int sha(const char *str,uint8_t bytes[32]) {
    size_t i;if(strlen(str)!=64u) return 0;
    for(i=0u;i<32u;i++) {
        unsigned x=0u;int j;
        for(j=0;j<2;j++) {
            char c=str[2u*i+(size_t)j];
            x*=16u;
            if(c>='0' && c<='9') x+=(unsigned)(c-'0');
            else if(c>='a' && c<='f') x+=(unsigned)(c-'a')+10u;
            else return 0;
        }
        bytes[i]=(uint8_t)x;
    }
    return 1;
}
static uint32_t crc_byte(uint32_t c,uint8_t b) {
    unsigned i;c^=b;
    for(i=0u;i<8u;i++) c=(c>>1)^((c&1u)?UINT32_C(0xEDB88320):0u);
    return c;
}
static uint32_t feed16(uint32_t c,uint16_t n) {
    c=crc_byte(c,(uint8_t)n);return crc_byte(c,(uint8_t)(n>>8));
}
static uint32_t feed32(uint32_t c,uint32_t n) {
    c=feed16(c,(uint16_t)n);return feed16(c,(uint16_t)(n>>16));
}
static uint32_t checksum_counts(const p07_b2b_receipt *v,uint32_t cores) {
    uint32_t i,c=UINT32_C(0xFFFFFFFF);
    for(i=0u;i<cores;i++) {
        c=feed32(c,v->current_by_core[i]);
        c=feed32(c,v->next_by_core[i]);
        c=feed32(c,v->emitted_by_core[i]);
    }
    return ~c;
}
static uint32_t checksum_pending(const p07_b2b_epoch *e) {
    uint32_t i,c=UINT32_C(0xFFFFFFFF);
    for(i=0u;i<e->pending_count;i++) {
        c=feed16(c,e->pending[i].core_id);
        c=feed16(c,e->pending[i].axon_id);
    }
    return ~c;
}
int main(int argc,char **argv) {
    size_t ingress_len,map_len,route_len,comp_len;
    unsigned long core_arg,inject=0u;char *end=0;
    FILE *stream;
    p07_b2_ingress_binding ib={0};p07_b2b_binding b={0};
    p07_b2_ingress_view iv={0};p07_b2b_epoch e={0};
    p07_b2b_receipt receipt={0};
    uint32_t total=0u,rejected=0u,step=0u;
    if(argc!=9 && argc!=10) return 40;
    core_arg=strtoul(argv[8],&end,10);
    if(*end || !core_arg || core_arg>P07_B2_MAX_CORES) return 41;
    if(argc==10) {
        inject=strtoul(argv[9],&end,10);
        if(*end || inject>4097u) return 42;
    }
    ingress_len=file_read(argv[1],ingress_bytes,MAX_FILE);
    map_len=file_read(argv[2],ingress_map,MAX_FILE);
    route_len=file_read(argv[3],route_bytes,MAX_FILE);
    comp_len=file_read(argv[4],compartments,MAX_FILE);
    if(!ingress_len || !map_len || route_len%8u ||
       comp_len!=core_arg*2u || map_len%6u ||
       route_len/8u>P07_B2B_MAX_FRAME_PACKETS) return 43;
    ib.core_count=(uint32_t)core_arg;
    ib.route_count=(uint32_t)(map_len/6u);
    ib.trusted_routes=ingress_map;ib.trusted_routes_bytes=map_len;
    if(!sha(argv[5],ib.compiled_sha256) || !sha(argv[6],ib.capacity_sha256)) return 44;
    if(p07_b2_decode_ingress(ingress_bytes,ingress_len,&ib,&iv)!=P07_B2_OK) return 45;
    b.core_count=(uint32_t)core_arg;b.route_count=(uint32_t)(route_len/8u);
    b.routes=compiled_routes;b.compartments_per_core=per_core;
    memcpy(b.compiled_sha256,ib.compiled_sha256,32u);
    memcpy(b.capacity_sha256,ib.capacity_sha256,32u);
    for(step=0u;step<b.core_count;step++)
        per_core[step]=u16(compartments+step*2u);
    for(step=0u;step<b.route_count;step++) {
        const uint8_t *p=route_bytes+8u*step;
        compiled_routes[step]=(p07_b2b_route){u16(p),u16(p+2u),u16(p+4u),u16(p+6u)};
    }
    if(p07_b2b_epoch_init(&e,&iv,&b,pending,P07_B2B_MAX_FRAME_PACKETS)!=P07_B2B_OK)
        return 46;
    if(inject) {
        for(step=0u;step<(uint32_t)inject;step++)
            pending[step]=(p07_b2_input_event){0u,0u};
        e.pending_count=(uint32_t)inject;
        e.pending_by_core[0]=(uint32_t)inject;
    }
    stream=fopen(argv[7],"rb");if(!stream) return 47;
    while(1) {
        uint8_t lengths[8];uint32_t size,spikes,i,old_tick;
        p07_b2b_epoch snapshot;p07_b2b_receipt old_receipt;
        p07_b2b_status status;
        uint8_t pending_snapshot[sizeof(pending)];
        size_t n=fread(lengths,1u,8u,stream);
        if(n==0u && feof(stream)) break;
        if(n!=8u) return 48;
        size=u32(lengths);spikes=u32(lengths+4u);
        if(size>MAX_FILE || spikes>P07_B2_MAX_CORES*P07_B2B_COMPARTMENTS) return 49;
        for(i=0u;i<spikes;i++) {
            uint8_t p[4];if(fread(p,1u,4u,stream)!=4u) return 50;
            origins[i]=(p07_b2b_origin){u16(p),u16(p+2u)};
        }
        if(fread(frame,1u,size,stream)!=size) return 51;
        snapshot=e;old_receipt=receipt;old_tick=e.tick;
        memcpy(pending_snapshot,pending,sizeof(pending));
        status=p07_b2b_step(&e,frame,size,spikes?origins:NULL,spikes,&receipt);
        ++total;
        if(status!=P07_B2B_OK) {
            if(memcmp(&snapshot,&e,sizeof(e)) ||
               memcmp(&old_receipt,&receipt,sizeof(receipt)) ||
               memcmp(pending_snapshot,pending,sizeof(pending))) return 52;
            printf("B2_REJECT %u %d\n",old_tick,(int)status);
            ++rejected;
            /* This is a host-only, unreachable pressure diagnostic. */
            if(inject) {e.pending_count=0u;e.pending_by_core[0]=0u;inject=0u;}
        } else {
            printf("B2_STEP %u %u %u %u %u %08x %08x %08x\n",
                   receipt.tick,receipt.current_bank,receipt.external_total,
                   receipt.routed_current,receipt.routed_next,receipt.packet_payload_crc32,
                   checksum_counts(&receipt,b.core_count),checksum_pending(&e));
        }
    }
    if(fclose(stream)!=0 || e.tick!=P07_B2_TOTAL_TICKS) return 53;
    { p07_b2b_epoch saved=e;p07_b2b_receipt old=receipt;
      if(p07_b2b_step(&e,frame,128u,NULL,0u,&receipt)!=P07_B2B_TICK ||
         memcmp(&e,&saved,sizeof(e)) || memcmp(&receipt,&old,sizeof(receipt)))
          return 54;
    }
    printf("P07_B2B_NATIVE_PACKET_PASS=1 steps=26 rejected=%u records=%u\n",
           rejected,total);
    return 0;
}
