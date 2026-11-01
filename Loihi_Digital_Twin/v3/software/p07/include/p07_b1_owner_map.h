#ifndef LOIHI_TWIN_V3_P07_B1_OWNER_MAP_H
#define LOIHI_TWIN_V3_P07_B1_OWNER_MAP_H
/* P07-B.1 portable C11 read-only admission. NOT an A53 parser or FPGA runtime. */
#include <stdint.h>
#include "p03_hw_adapter.h"
#include "p03_mmio.h"
#include "p05_deployment.h"

#define P07_B1_CONTRACT_VERSION 1u
#define P07_B1_CORES 27u
#define P07_B1_HIDDEN_CORES 26u
#define P07_B1_SLOTS 3u
#define P07_B1_ENGINES 1u
#define P07_B1_PIXELS 784u
#define P07_B1_INPUT_TICKS 25u
#define P07_B1_TOTAL_TICKS 26u
#define P07_B1_INGRESS_ROUTES (P07_B1_PIXELS * P07_B1_HIDDEN_CORES)
#define P07_B1_INGRESS_BYTES (128u + 6u * P07_B1_INGRESS_ROUTES + P07_B1_PIXELS)
#define P07_B1_STAGING_BASE P05_DEPLOY_PAYLOAD_BASE
#define P07_B1_STAGING_BYTES P05_DEPLOY_PAYLOAD_CAPACITY
#define P07_B1_DESCRIPTOR_BASE P05_DEPLOY_HEADER_BASE
#define P07_B1_DESCRIPTOR_BYTES 256u
#define P07_B1_RESULT_BASE P05_DEPLOY_MAILBOX_BASE
#define P07_B1_RESULT_BYTES 65536u
#define P07_B1_BURST_BYTES 256u
#define P07_B1_SHELL_CAPABILITIES UINT32_C(0x0001031F)
/* Permanently B.1 NO-GO; a later version needs separate acceptance. */
#define P07_B1_SCALED_PHYSICAL_EXECUTION_GO 0u
#define P07_B1_OFFICIAL_MNIST_TEST_UNSEAL_GO 0u

_Static_assert(P03_HW_BACKING_BASE == UINT64_C(0x40000000), "P03 backing changed");
_Static_assert(P03_HW_BACKING_BYTES == UINT64_C(0x04000000), "P03 window changed");
_Static_assert(P03_HW_RECORD_BYTES == UINT64_C(0x80000), "P02 stride changed");
_Static_assert(P03_RT_MAX_SLOTS == P07_B1_SLOTS, "physical slot count changed");
_Static_assert(P05_DEPLOY_MAX_CORES >= P07_B1_CORES, "P05 addressable IDs insufficient");
_Static_assert(P03_HW_EVENT_DEPTH == P05_DEPLOY_EVENT_DEPTH, "event bank depth drift");
_Static_assert(P03_HW_FULL_PAGE_BYTES == 0x6B000u, "P05 page-in geometry changed");
_Static_assert(P03_HW_MUTABLE_BYTES == 0x1A000u, "P05 dirty page-out geometry changed");
_Static_assert(P03_HW_FULL_PAGE_BYTES % P07_B1_BURST_BYTES == 0u, "unaligned page-in");
_Static_assert(P03_HW_MUTABLE_BYTES % P07_B1_BURST_BYTES == 0u, "unaligned page-out");
_Static_assert(P07_B1_INGRESS_BYTES <= P07_B1_STAGING_BYTES, "ingress staging too small");
_Static_assert((uint64_t)P07_B1_CORES * P03_HW_RECORD_BYTES <=
                   (uint64_t)P07_B1_STAGING_BASE - P03_HW_BACKING_BASE,
               "core images overlap staging");
_Static_assert(P07_B1_STAGING_BASE + P07_B1_STAGING_BYTES == P07_B1_DESCRIPTOR_BASE,
               "staging overlaps descriptor");
_Static_assert(P07_B1_DESCRIPTOR_BASE + P07_B1_DESCRIPTOR_BYTES <= P07_B1_RESULT_BASE,
               "descriptor overlaps result");
_Static_assert((uint64_t)P07_B1_RESULT_BASE + P07_B1_RESULT_BYTES ==
                   P03_HW_BACKING_BASE + P03_HW_BACKING_BYTES,
               "result outside P02 reservation");

typedef enum {
    P07_B1_OK=0, P07_B1_BAD_ARGUMENT=-1, P07_B1_BAD_TOPOLOGY=-2,
    P07_B1_BAD_OWNER=-3, P07_B1_BAD_SHELL=-4, P07_B1_BAD_CAPACITY=-5
} p07_b1_status;
typedef struct {
    uint32_t logical_cores, slots, engines, input_ticks, total_ticks;
    uint32_t ingress_routes, ingress_bytes, current_events, emitted_packets;
    uint64_t backing_base, staging_base, descriptor_base, result_base;
    uint32_t shell_id, shell_caps, mmio_base, fpd_hpm0_width_bits;
} p07_b1_admission;

static inline uint64_t p07_b1_core_address(uint32_t core_id)
{
    return core_id < P07_B1_CORES ?
        P03_HW_BACKING_BASE + (uint64_t)core_id * P03_HW_RECORD_BYTES : UINT64_MAX;
}
/* Structural only. Does not read the real board, prove DDR exclusivity,
 * check ELF segments, parse CRC/SHA, route packets or execute inference. */
static inline p07_b1_status p07_b1_validate(const p07_b1_admission *p)
{
    if (p == 0) return P07_B1_BAD_ARGUMENT;
    if (p->logical_cores != P07_B1_CORES || p->slots != P07_B1_SLOTS ||
        p->engines != P07_B1_ENGINES || p->input_ticks != P07_B1_INPUT_TICKS ||
        p->total_ticks != P07_B1_TOTAL_TICKS ||
        p->ingress_routes != P07_B1_INGRESS_ROUTES ||
        p->ingress_bytes != P07_B1_INGRESS_BYTES)
        return P07_B1_BAD_TOPOLOGY;
    if (p->backing_base != P03_HW_BACKING_BASE ||
        p->staging_base != P07_B1_STAGING_BASE ||
        p->descriptor_base != P07_B1_DESCRIPTOR_BASE ||
        p->result_base != P07_B1_RESULT_BASE)
        return P07_B1_BAD_OWNER;
    if (p->shell_id != P03_MMIO_ID_VALUE ||
        p->shell_caps != P07_B1_SHELL_CAPABILITIES ||
        p->mmio_base != (uint32_t)P03_MMIO_BASE ||
        p->fpd_hpm0_width_bits != 128u)
        return P07_B1_BAD_SHELL;
    if (p->current_events > P03_HW_EVENT_DEPTH ||
        p->emitted_packets > P03_RT_MAX_PACKETS)
        return P07_B1_BAD_CAPACITY;
    return P07_B1_OK;
}
#endif
