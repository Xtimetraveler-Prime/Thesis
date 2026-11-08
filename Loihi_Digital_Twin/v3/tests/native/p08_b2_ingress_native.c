/* Native C11 B2.1 verification harness; NEVER contacts JTAG or programs PL.
 * For real 1024-stage checks compile against accepted p07_a2_sha256.c,
 * read existing immutable 896KiB routes and new external raw pool/hash list.
 */
#include "p08_b2_ingress.h"
#include <stdio.h>
#include <stdint.h>
#include <string.h>
#include <stdlib.h>
#include "p07_a2_sha256.h"

#define N_IMAGES 1024u
static uint8_t source_routes[P08_B2_ROUTE_IMAGE_BYTES];
static uint8_t raw_pool[N_IMAGES*P08_B2_RAW_IMAGE_BYTES];
static uint8_t encoded[P08_B2_WIRE_BYTES];
static uint8_t invalid_routes[P08_B2_ROUTE_IMAGE_BYTES];

static int read_exact(const char *name,uint8_t *out,size_t n){
    FILE *f=fopen(name,"rb");
    int ok;
    if(!f)return -1;
    ok=fread(out,1u,n,f)==n && fgetc(f)==EOF;
    if(fclose(f)!=0)ok=0;
    return ok?0:-1;
}
static int hex_digit(int c){
    if(c>='0'&&c<='9')return c-'0';
    if(c>='a'&&c<='f')return c-'a'+10;
    if(c>='A'&&c<='F')return c-'A'+10;
    return -1;
}
static int expected_sha(const char *s,uint8_t digest[32]){
    size_t i;
    if(strlen(s)!=65u || s[64]!='\n')return -1;
    for(i=0u;i<32u;i++){
        int a=hex_digit((unsigned char)s[2u*i]);
        int b=hex_digit((unsigned char)s[2u*i+1u]);
        if(a<0||b<0)return -1;
        digest[i]=(uint8_t)((a<<4)|b);
    }
    return 0;
}
int main(int argc,char **argv){
    p08_b2_route_binding routes={0};
    size_t n=0u,i;
    uint8_t hash[32],expected[32];
    char line[80];
    FILE *f;
    if(argc==2 && strcmp(argv[1],"--reject-zeros")==0){
        int rc=p08_b2_admit_routes(invalid_routes,sizeof(invalid_routes),&routes);
        if(rc!=P08_B2_SOURCE_SHA || routes.admitted_tag!=0u){
            fputs("P08_B2_NATIVE_NEGATIVE_FAIL\n",stderr);
            return 2;
        }
        if(p08_b2_encode_frame(&routes,raw_pool,encoded,sizeof(encoded),&n)==P08_B2_OK){
            fputs("P08_B2_NATIVE_UNAUTHENTICATED_FRAME_ACCEPTED\n",stderr);
            return 3;
        }
        puts("P08_B2_NATIVE_INVALID_ROUTES_REJECTED=1");
        return 0;
    }
    if(argc!=5 || strcmp(argv[1],"--verify")!=0){
        fputs("usage: p08_b2_ingress_native --verify original_896k_routes raw1024.bin expected1024sha.txt\n",stderr);
        return 2;
    }
    if(read_exact(argv[2],source_routes,sizeof(source_routes)) ||
       read_exact(argv[3],raw_pool,sizeof(raw_pool))){
        fputs("P08_B2_NATIVE_SOURCE_LENGTH_NO_GO\n",stderr);
        return 3;
    }
    if(p08_b2_admit_routes(source_routes,sizeof(source_routes),&routes)!=P08_B2_OK){
        fputs("P08_B2_NATIVE_ORIGINAL_896K_ROUTE_SHA_NO_GO\n",stderr);
        return 4;
    }
    f=fopen(argv[4],"rb");
    if(!f)return 5;
    for(i=0u;i<N_IMAGES;i++){
        const uint8_t *pixels=raw_pool+i*P08_B2_RAW_IMAGE_BYTES;
        if(!fgets(line,sizeof(line),f)||expected_sha(line,expected) ||
           p08_b2_encode_frame(&routes,pixels,encoded,sizeof(encoded),&n)!=P08_B2_OK ||
           n!=P08_B2_WIRE_BYTES){
            fprintf(stderr,"P08_B2_NATIVE_FRAME_FORMAT_NO_GO=%zu\n",i);
            fclose(f);
            return 6;
        }
        p07_a2_sha256(encoded,n,hash);
        if(memcmp(hash,expected,32u)){
            fprintf(stderr,"P08_B2_NATIVE_FRAME_SHA_NO_GO=%zu\n",i);
            fclose(f);
            return 7;
        }
    }
    if(fgetc(f)!=EOF || fclose(f)!=0){
        fputs("P08_B2_NATIVE_FRAME_SHA_TRAILING_NO_GO\n",stderr);
        return 8;
    }
    printf("P08_B2_NATIVE_SOURCE_AUTHENTICATED=1\n");
    printf("P08_B2_NATIVE_ENCODED_FRAMES_EXACT=%u\n",N_IMAGES);
    printf("P08_B2_NATIVE_BYTES_PER_FRAME=%u\n",(unsigned)P08_B2_WIRE_BYTES);
    puts("P08_B2_HARDWARE_EXECUTED=0");
    return 0;
}
