#include "include/p07_a1_ingress.h"

#include <string.h>

/* Decode untrusted bytes, never use native struct layout or alignment. */
static uint32_t le32(const uint8_t *p)
{
    return (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
}
static uint16_t le16(const uint8_t *p)
{
    return (uint16_t)((uint16_t)p[0] | ((uint16_t)p[1] << 8));
}
static uint32_t crc32_ieee(const uint8_t *p, size_t n, int zero_header_crc)
{
    size_t i;
    uint32_t crc = UINT32_C(0xFFFFFFFF);
    for (i = 0; i < n; ++i) {
        uint32_t x = (zero_header_crc && i >= 60u && i < 64u) ? 0u : p[i];
        uint32_t bit;
        crc ^= x;
        for (bit = 0; bit < 8u; ++bit)
            crc = (crc >> 1) ^ ((crc & 1u) ? UINT32_C(0xEDB88320) : 0u);
    }
    return ~crc;
}
static int nonzero_digest(const uint8_t *p)
{
    unsigned i;
    for (i = 0; i < 32u; ++i)
        if (p[i] != 0u) return 1;
    return 0;
}
int p07_a1_validate(const uint8_t *record, size_t record_bytes,
                    p07_a1_info *out)
{
    static const uint8_t magic[8] = { 'P','0','7','A','1','I','N','1' };
    uint8_t seen[P07_A1_AXON_CAPACITY / 8u] = {0};
    uint32_t i;
    const uint8_t *map;
    if (!out) return P07_A1_BAD_ARGUMENT;
    memset(out, 0, sizeof(*out));
    if (!record) return P07_A1_BAD_ARGUMENT;
    if (record_bytes != P07_A1_RECORD_BYTES) return P07_A1_BAD_LAYOUT;
    if (memcmp(record, magic, sizeof(magic)) != 0 ||
        le32(record + 8u) != P07_A1_VERSION ||
        le32(record + 12u) != P07_A1_HEADER_BYTES ||
        le32(record + 16u) != P07_A1_MAP_BYTES + P07_A1_IMAGE_BYTES ||
        le32(record + 20u) != P07_A1_MAP_BYTES ||
        le32(record + 24u) != P07_A1_IMAGE_BYTES ||
        le32(record + 28u) != P07_A1_PIXEL_COUNT ||
        le32(record + 32u) != P07_A1_INPUT_TICKS ||
        le32(record + 36u) != P07_A1_TOTAL_TICKS ||
        le32(record + 40u) != 0u ||
        le32(record + 44u) != P07_A1_PIXEL_COUNT ||
        le32(record + 48u) != P07_A1_AXON_CAPACITY ||
        le32(record + 52u) != 0u)
        return P07_A1_BAD_LAYOUT;
    if (crc32_ieee(record, P07_A1_HEADER_BYTES, 1) != le32(record + 60u) ||
        crc32_ieee(record + P07_A1_HEADER_BYTES,
                   P07_A1_MAP_BYTES + P07_A1_IMAGE_BYTES, 0) !=
                   le32(record + 56u))
        return P07_A1_BAD_CRC;
    if (!nonzero_digest(record + 64u) ||
        !nonzero_digest(record + 96u))
        return P07_A1_BAD_LAYOUT;

    map = record + P07_A1_HEADER_BYTES;
    for (i = 0; i < P07_A1_PIXEL_COUNT; ++i) {
        uint32_t axon = le16(map + (size_t)i * 2u);
        uint8_t mask;
        if (axon >= P07_A1_AXON_CAPACITY)
            return P07_A1_BAD_MAPPING;
        mask = (uint8_t)(1u << (axon & 7u));
        if ((seen[axon >> 3] & mask) != 0u)
            return P07_A1_BAD_MAPPING;
        seen[axon >> 3] |= mask;
    }
    out->core_id = 0u;
    out->map_count = P07_A1_PIXEL_COUNT;
    out->payload_crc32 = le32(record + 56u);
    memcpy(out->ddr_sha256, record + 64u, 32u);
    memcpy(out->deployment_fingerprint, record + 96u, 32u);
    return P07_A1_OK;
}

int p07_a1_tick_events(const uint8_t *record, size_t record_bytes,
                       uint32_t tick, uint16_t *out_axons,
                       size_t out_capacity, size_t *out_count)
{
    p07_a1_info info;
    const uint8_t *map, *pixels;
    uint32_t index, n = 0u;
    int rc;
    if (!out_count) return P07_A1_BAD_ARGUMENT;
    *out_count = 0u;
    if (tick >= P07_A1_TOTAL_TICKS) return P07_A1_BAD_TICK;
    rc = p07_a1_validate(record, record_bytes, &info);
    if (rc != P07_A1_OK) return rc;
    if (tick == P07_A1_INPUT_TICKS) return P07_A1_OK;

    map = record + P07_A1_HEADER_BYTES;
    pixels = map + P07_A1_MAP_BYTES;
    /* Two-pass capacity check prevents partial output writes. */
    for (index = 0; index < P07_A1_PIXEL_COUNT; ++index) {
        uint32_t phase = (tick + 17u * index) % P07_A1_INPUT_TICKS;
        uint32_t pixel = pixels[index];
        if (((phase + 1u) * pixel) / 255u > (phase * pixel) / 255u)
            ++n;
    }
    if (n > out_capacity || (n != 0u && !out_axons))
        return P07_A1_BAD_CAPACITY;
    n = 0u;
    for (index = 0; index < P07_A1_PIXEL_COUNT; ++index) {
        uint32_t phase = (tick + 17u * index) % P07_A1_INPUT_TICKS;
        uint32_t pixel = pixels[index];
        if (((phase + 1u) * pixel) / 255u > (phase * pixel) / 255u)
            out_axons[n++] = le16(map + (size_t)index * 2u);
    }
    *out_count = n;
    return P07_A1_OK;
}
