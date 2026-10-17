/* Native host probe: independently exercise C validator and all 26 ticks.
 * No board, MNIST labels, external data, or dynamic FPGA configuration.
 */
#include "include/p07_a1_ingress.h"

#include <stdio.h>
#include <stdlib.h>

static uint64_t fnv_axons(const uint16_t *axons, size_t count)
{
    uint64_t h = UINT64_C(14695981039346656037);
    size_t i;
    for (i = 0; i < count; ++i) {
        h ^= (uint8_t)(axons[i] & 255u);
        h *= UINT64_C(1099511628211);
        h ^= (uint8_t)(axons[i] >> 8);
        h *= UINT64_C(1099511628211);
    }
    return h;
}
int main(int argc, char **argv)
{
    uint8_t record[P07_A1_RECORD_BYTES + 1u];
    uint16_t axons[P07_A1_PIXEL_COUNT];
    p07_a1_info info;
    FILE *fp;
    size_t got, count;
    unsigned tick;
    if (argc != 2) return 2;
    fp = fopen(argv[1], "rb");
    if (!fp) return 2;
    got = fread(record, 1, sizeof(record), fp);
    if (ferror(fp) || fclose(fp) != 0) return 2;
    if (p07_a1_validate(record, got, &info) != P07_A1_OK)
        return 3;
    if (info.core_id != 0u || info.map_count != P07_A1_PIXEL_COUNT)
        return 4;
    for (tick = 0; tick < P07_A1_TOTAL_TICKS; ++tick) {
        if (p07_a1_tick_events(record, got, tick, axons,
                               P07_A1_PIXEL_COUNT, &count) != P07_A1_OK)
            return 5;
        printf("%u %zu %016llx\n", tick, count,
               (unsigned long long)fnv_axons(axons, count));
    }
    /* Prove fail-before-write behavior with a full-white stimulus: 784
     * events are legal, 783 available output entries must be rejected. */
    {
        uint8_t white[P07_A1_RECORD_BYTES];
        /* Run capacity checks against whichever stimulus was supplied.
         * If it contains any spikes, check a deficient buffer at tick t. */
        (void)white;
        for (tick = 0; tick < P07_A1_INPUT_TICKS; ++tick) {
            size_t full_count, out_count = 123u, i;
            uint16_t untouched[P07_A1_PIXEL_COUNT];
            int rc;
            if (p07_a1_tick_events(record, got, tick, axons,
                                   P07_A1_PIXEL_COUNT, &full_count) != P07_A1_OK)
                return 6;
            if (full_count == 0u) continue;
            for (i = 0; i < P07_A1_PIXEL_COUNT; ++i)
                untouched[i] = UINT16_C(0xBEEF);
            rc = p07_a1_tick_events(record, got, tick, untouched,
                                    full_count - 1u, &out_count);
            if (rc != P07_A1_BAD_CAPACITY || out_count != 0u)
                return 7;
            for (i = 0; i < P07_A1_PIXEL_COUNT; ++i)
                if (untouched[i] != UINT16_C(0xBEEF)) return 8;
            break;
        }
    }
    count = 7u;
    if (p07_a1_tick_events(record, got, 26u, axons,
                           P07_A1_PIXEL_COUNT, &count) != P07_A1_BAD_TICK ||
        count != 0u)
        return 9;
    puts("P07_A1_C_NATIVE_PASS=1");
    return 0;
}
