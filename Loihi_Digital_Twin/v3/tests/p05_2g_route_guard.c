/* P05.2g portable actual P03 adapter boundary test.
 * 4095 NEXT routed events: legal last slot.
 * 4096 NEXT routed events: P03_HW_OVERFLOW before any 4097th store.
 * THIS IS MOCKED C TRANSPORT, NOT REAL KV260 ROUTING BACKPRESSURE.
 */
#include <stdint.h>
#include <string.h>
#include "p03_hw_adapter.h"

static uint32_t stores,cleans;
static uint64_t last_addr;
static uint32_t last_data;

static int rd(void *ctx,uint32_t off,uint32_t *out)
{(void)ctx;(void)off;*out=0;return 0;}
static int wr(void *ctx,uint32_t off,uint32_t val)
{(void)ctx;(void)off;(void)val;return 0;}
static int clean(void *ctx,uint64_t addr,uint32_t bytes)
{(void)ctx;(void)addr;if(bytes!=4)return -1;++cleans;return 0;}
static int invalidate(void *ctx,uint64_t addr,uint32_t bytes)
{(void)ctx;(void)addr;(void)bytes;return 0;}
static int store(void *ctx,uint64_t addr,uint32_t data)
{(void)ctx;++stores;last_addr=addr;last_data=data;return 0;}
static void barrier(void *ctx){(void)ctx;}

int main(void)
{
    p03_hw_adapter hw;
    p03_rt rt;
    p03_hw_io io={rd,wr,clean,invalidate,store,barrier};
    const uint64_t packet =
        UINT64_C(1) |
        (UINT64_C(11)<<7) |
        (UINT64_C(0)<<19) |
        (UINT64_C(1)<<29) |
        (UINT64_C(1)<<61);
    const uint64_t addr=P03_HW_BACKING_BASE+P03_HW_RECORD_BYTES+
         P03_HW_EVENT1_OFFSET+UINT64_C(4095)*4u;
    if(p03_hw_init(&hw,&io,0,P03_HW_BACKING_BASE,32)!=P03_HW_OK)return 10;
    memset(&rt,0,sizeof(rt));
    rt.slot_count=1;rt.resident[0]=0;hw.runtime=&rt;
    hw.configured[0]=hw.configured[1]=1;
    hw.metadata[0]=UINT64_C(1)<<7;
    hw.metadata[1]=UINT64_C(1)|(UINT64_C(1)<<7);
    hw.valid_axons[1][11>>3]|=(uint8_t)(1u<<(11&7));
    hw.event_counts[1][1]=4095;
    if(p03_hw_route_word(&hw,0,packet,0,1)!=P03_HW_OK)return 11;
    if(hw.event_counts[1][1]!=4096||stores!=1||cleans!=1||
       last_addr!=addr||last_data!=11)return 12;
    if(p03_hw_route_word(&hw,0,packet,0,1)!=P03_HW_OVERFLOW)return 13;
    if(hw.event_counts[1][1]!=4096||stores!=1||cleans!=1||
       hw.last_error!=P03_HW_OVERFLOW)return 14;
    return 0;
}
