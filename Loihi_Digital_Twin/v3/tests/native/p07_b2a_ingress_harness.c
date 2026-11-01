/* Portable native verification executable; reads only caller-provided synthetic bytes. */
#include "p07_b2_ingress.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#define LIMIT (1024u*1024u)
static uint8_t frame[LIMIT], map[LIMIT];
static p07_b2_input_event events[P07_B2_MAX_ROUTES];
static p07_b2_ingress_receipt receipt;
static size_t load(const char *path, uint8_t *dst) {
    FILE *f=fopen(path,"rb"); size_t n;
    if(!f) return 0u;
    n=fread(dst,1u,LIMIT,f);
    if(ferror(f) || (n==LIMIT && fgetc(f)!=EOF) || fclose(f)!=0) return 0u;
    return n;
}
static int hexbyte(char a,char b) {
    int x,y;
    if(a>='0' && a<='9') x=a-'0';
    else if(a>='a' && a<='f') x=a-'a'+10;
    else return -1;
    if(b>='0' && b<='9') y=b-'0';
    else if(b>='a' && b<='f') y=b-'a'+10;
    else return -1;
    return (x<<4)|y;
}
static int digest(const char *s,uint8_t out[32]) {
    size_t i;
    if(strlen(s)!=64u) return 0;
    for(i=0u;i<32u;i++) {
        int v=hexbyte(s[i*2u],s[i*2u+1u]);
        if(v<0) return 0;
        out[i]=(uint8_t)v;
    }
    return 1;
}
int main(int argc,char **argv) {
    p07_b2_ingress_binding bind={0};
    p07_b2_ingress_view view={0};
    size_t bytes, map_bytes;
    char *end=0;
    unsigned long cores;
    uint32_t tick;
    p07_b2_status code;
    if(argc!=6) return 40;
    bytes=load(argv[1],frame); map_bytes=load(argv[2],map);
    cores=strtoul(argv[5],&end,10);
    if(!bytes || !map_bytes || *end!='\0' || cores>P07_B2_MAX_CORES ||
       map_bytes%P07_B2_ROUTE_BYTES ||
       !digest(argv[3],bind.compiled_sha256) || !digest(argv[4],bind.capacity_sha256)) return 41;
    bind.core_count=(uint32_t)cores;
    bind.route_count=(uint32_t)(map_bytes/P07_B2_ROUTE_BYTES);
    bind.trusted_routes=map; bind.trusted_routes_bytes=map_bytes;
    code=p07_b2_decode_ingress(frame,bytes,&bind,&view);
    if(code!=P07_B2_OK) {
        printf("P07_B2A_REJECT=%d\n",(int)code);
        return 10;
    }
    /* A failed re-decode must not change an already committed envelope. */
    {
        p07_b2_ingress_view saved=view;
        frame[64u]^=1u;
        code=p07_b2_decode_ingress(frame,bytes,&bind,&view);
        frame[64u]^=1u;
        if(code!=P07_B2_DIGEST || memcmp(&saved,&view,sizeof(view))!=0) return 15;
    }
    for(tick=0u;tick<P07_B2_TOTAL_TICKS;tick++) {
        code=p07_b2_ingress_tick(&view,tick,events,P07_B2_MAX_ROUTES,&receipt);
        if(code!=P07_B2_OK) return 11;
        printf("B2_TICK %u %u %08x\n",tick,receipt.total,receipt.event_crc32);
    }
    {
        p07_b2_ingress_receipt saved=receipt;
        p07_b2_input_event saved_event=events[0];
        if(p07_b2_ingress_tick(&view,26u,events,P07_B2_MAX_ROUTES,&receipt)!=P07_B2_TICK ||
           memcmp(&saved,&receipt,sizeof(receipt))!=0 ||
           memcmp(&saved_event,events,sizeof(saved_event))!=0) return 12;
        if(p07_b2_ingress_tick(&view,0u,events,0u,&receipt)==P07_B2_CAPACITY) {
            if(memcmp(&saved,&receipt,sizeof(receipt))!=0 ||
               memcmp(&saved_event,events,sizeof(saved_event))!=0) return 16;
        }
    }
    if(view.route_count*P07_B2_ROUTE_BYTES+P07_B2_HEADER_BYTES+P07_B2_IMAGE_BYTES!=bytes)
        return 13;
    if(P07_B2_INPUT_TICKS!=25u || P07_B2_MAX_FRAME_BYTES>0xE0000u) return 14;
    puts("P07_B2A_NATIVE_INGRESS_PASS=1");
    return 0;
}
