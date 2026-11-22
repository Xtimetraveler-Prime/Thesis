/* SPDX-License-Identifier: MIT */
/*
 * Genuine host C compilation of the SAME first-party 49-bit validation
 * header included by the future Linux platform driver. PC ONLY.
 * A valid synthetic DMA descriptor is not an owned physical DMA address.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include "../../kernel/m08_m085_dma_contract.h"

static int assertions;

static void check_descriptor(uint64_t base, uint64_t bytes, uint64_t gen,
                             int expected)
{
    int got = !!m085_dma_descriptor_valid(base, bytes, gen);
    ++assertions;
    if (got != expected) {
        fprintf(stderr,
                "BAD_DESCRIPTOR base=%llu bytes=%llu gen=%llu got=%d want=%d\n",
                (unsigned long long)base, (unsigned long long)bytes,
                (unsigned long long)gen, got, expected);
        exit(2);
    }
}

static void check_hp0_route(uint64_t base, uint64_t bytes,
                            uint64_t generation, int expected)
{
    int got = !!m085_dma_candidate_hp0_low_valid(base, bytes, generation);
    ++assertions;
    if (got != expected) {
        fprintf(stderr,
                "BAD_HP0_ROUTE base=%llu bytes=%llu gen=%llu got=%d want=%d\\n",
                (unsigned long long)base, (unsigned long long)bytes,
                (unsigned long long)generation, got, expected);
        exit(2);
    }
}

static void check_slot(uint64_t slot, uint64_t tick, int expected)
{
    int got = !!m085_dma_slot_valid(slot, tick);
    ++assertions;
    if (got != expected) {
        fprintf(stderr,
                "BAD_SLOT slot=%llu tick=%llu got=%d want=%d\n",
                (unsigned long long)slot, (unsigned long long)tick,
                got, expected);
        exit(2);
    }
}

int main(void)
{
    const uint64_t limit = M085_DMA_AXI_LIMIT;
    int slot, tick;
    check_descriptor(0x1000ULL,4096ULL,1ULL,1);
    check_descriptor(0x0ULL,1792ULL,1ULL,1); /* source permits zero bus base */
    check_descriptor(0x200ULL,1792ULL,0xffffffffULL,1);
    check_descriptor(limit-8192ULL,4096ULL,1ULL,1);

    check_descriptor(0x1001ULL,4096ULL,1ULL,0);
    check_descriptor(0x1000ULL,1791ULL,1ULL,0);
    check_descriptor(0x1000ULL,4096ULL,0ULL,0);
    check_descriptor(0x1000ULL,4096ULL,0x100000000ULL,0);
    check_descriptor(0x1000ULL,0x100000000ULL,1ULL,0);
    check_descriptor(limit,4096ULL,1ULL,0);
    check_descriptor(limit+256ULL,4096ULL,1ULL,0);
    check_descriptor(limit-4096ULL,4096ULL,1ULL,0); /* end == 2^49 */
    check_descriptor(limit-4096ULL,4097ULL,1ULL,0);
    check_descriptor(UINT64_MAX-255ULL,4096ULL,1ULL,0);
    check_descriptor(UINT64_MAX,UINT64_MAX,UINT64_MAX,0);
    check_descriptor(0x1000ULL,0ULL,1ULL,0);
    check_descriptor(0x1000ULL,0xffffffffULL,1ULL,1);
    /* The 49-bit RTL contract is deliberately broader than the actual
     * candidate PS HP0 DDR_LOW interconnect decode. These 8 extra checks
     * prove the narrower candidate bus routing gate separately.
     */
    check_hp0_route(0x1000ULL,4096ULL,1ULL,1);
    check_hp0_route(0ULL,1792ULL,1ULL,1);
    check_hp0_route(0x7ffff000ULL,4096ULL,1ULL,1);
    check_hp0_route(0x7ffff000ULL,4097ULL,1ULL,0);
    check_hp0_route(0x80000000ULL,4096ULL,1ULL,0);
    check_hp0_route(0x80000100ULL,4096ULL,1ULL,0);
    check_hp0_route(limit-8192ULL,4096ULL,1ULL,0);
    check_hp0_route(0x7fffe000ULL,4096ULL,1ULL,1);

    for (slot = 0; slot < 7; ++slot)
        for (tick = 0; tick < 4; ++tick)
            check_slot((uint64_t)slot,(uint64_t)tick,
                       slot == 6 ? tick == 0 : 1);
    check_slot(7ULL,0ULL,0);
    check_slot(UINT64_MAX,UINT64_MAX,0);
    check_slot(0ULL,4ULL,0);
    check_slot(6ULL,1ULL,0);
    if (assertions != 57) {
        fprintf(stderr,"M085_C_CONTRACT_TEST_COUNT=%d != 57\n",assertions);
        return 3;
    }
    printf("M08_M085_PORTABLE_C_DMA_49BIT_HP0LOW_7SLOT_BOUNDARY_PASS checks=%d\n",
           assertions);
    return 0;
}
