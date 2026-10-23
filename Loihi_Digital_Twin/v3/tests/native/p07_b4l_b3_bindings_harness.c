#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "p07_b4l_b3_bindings.h"
#define CHECK(x) do{if(!(x)){fprintf(stderr,"B4L_BIND_FAIL_LINE=%d\n",__LINE__);return 1;}}while(0)
static int rd(void *x,uint32_t a,uint32_t *v){(void)x;(void)a;if(v)*v=0;return 0;}
static int wr(void *x,uint32_t a,uint32_t v){(void)x;(void)a;(void)v;return 0;}
static int range(void *x,uint64_t a,uint32_t b){(void)x;(void)a;(void)b;return 0;}
static int store(void *x,uint64_t a,uint32_t b){(void)x;(void)a;(void)b;return 0;}
static void barrier(void *x){(void)x;}
static p03_hw_io io={rd,wr,range,range,store,barrier};
static p03_hw_adapter hw;
static int initialize(void){return p03_hw_init(&hw,&io,&hw,P03_HW_BACKING_BASE,10u);}
int main(int argc,char **argv){
    FILE *file;uint8_t *bytes;size_t n;
    unsigned core,axb=0;
    b4l_binding_receipt r={0};
    CHECK(argc==2);
    bytes=(uint8_t *)malloc(B4L_BIND_SIZE);
    CHECK(bytes!=NULL);
    file=fopen(argv[1],"rb");CHECK(file!=NULL);
    n=fread(bytes,1,B4L_BIND_SIZE,file);
    CHECK(n==B4L_BIND_SIZE&&fgetc(file)==EOF);fclose(file);
    CHECK(initialize()==P03_HW_OK);
    CHECK(b4l_bind_frozen(&hw,bytes,n,&r)==B4L_BIND_OK);
    CHECK(r.core_count==27u&&r.registered_compartments==27u*4u);
    CHECK(r.registered_axons==27u*3u);
    for(core=0;core<27u;core++){
        uint64_t meta=hw.metadata[core];
        unsigned ax=core%4096u;
        CHECK((meta&0x7fu)==core&&((meta>>7)&0x7ffu)==4u);
        CHECK(hw.configured[core]==1u);
        CHECK((hw.valid_axons[core][ax/8u]&(1u<<(ax%8u)))!=0u);
        axb+=3u;
    }
    CHECK(axb==r.registered_axons);
    CHECK(b4l_bind_frozen(&hw,bytes,n,&r)==B4L_BIND_INVALID);
    CHECK(initialize()==P03_HW_OK);
    bytes[128u+16u]^=1u;
    CHECK(b4l_bind_frozen(&hw,bytes,n,&r)==B4L_BIND_SHA);
    for(core=0u;core<27u;core++)CHECK(hw.configured[core]==0u);
    bytes[128u+16u]^=1u;
    bytes[20u]^=0x80u;
    CHECK(b4l_bind_frozen(&hw,bytes,n,&r)==B4L_BIND_INVALID);
    bytes[20u]^=0x80u;
    bytes[32u]^=0x01u;
    CHECK(b4l_bind_frozen(&hw,bytes,n,&r)==B4L_BIND_INVALID);
    bytes[32u]^=0x01u;
    bytes[B4L_BIND_SIZE-1u]=0x01u;
    CHECK(b4l_bind_frozen(&hw,bytes,n,&r)==B4L_BIND_INVALID);
    free(bytes);
    puts("P07_B4L_B3_NATIVE_FROZEN_REGISTRATION_METADATA_AXONS_PASS=1");
    puts("P07_B4L_B3_NATIVE_FROZEN_REGISTRATION_TAMPER_FAIL_CLOSED=1");
    return 0;
}
