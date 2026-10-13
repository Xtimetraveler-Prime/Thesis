#include "p05_deployment.h"
#include <string.h>

/* All offsets/lengths are validated before touching a payload entry. */
static uint32_t load32(const uint8_t *p)
{
    return (uint32_t)p[0] |
           ((uint32_t)p[1] << 8) |
           ((uint32_t)p[2] << 16) |
           ((uint32_t)p[3] << 24);
}

static uint32_t crc_byte(uint32_t crc, uint8_t value)
{
    unsigned b;
    crc ^= value;
    for (b = 0u; b < 8u; ++b)
        crc = (crc >> 1) ^
              ((crc & 1u) != 0u ? UINT32_C(0xEDB88320) : 0u);
    return crc;
}

static uint32_t crc32_bytes(const uint8_t *buf, size_t count,
                            int zero_header_crc_word)
{
    uint32_t crc = UINT32_C(0xFFFFFFFF);
    size_t i;
    for (i = 0; i < count; ++i) {
        uint8_t byte = (zero_header_crc_word &&
                        i >= 23u * 4u && i < 24u * 4u) ? 0u : buf[i];
        crc = crc_byte(crc, byte);
    }
    return crc ^ UINT32_C(0xFFFFFFFF);
}

int p05_deployment_validate(
    const uint8_t *header, size_t header_bytes,
    const uint8_t *payload, size_t payload_bytes,
    p05_deployment_info *out_info)
{
    uint32_t steps, cores, slots, events, checks, mode, payload_len;
    uint32_t core_off, event_off, check_off, crc_h, crc_p;
    uint8_t rank[P05_DEPLOY_MAX_CORES];
    uint16_t sole_axon[P05_DEPLOY_MAX_CORES];
    uint32_t i, prev_step, prev_rank, prev_class, seen_this_step;

    if (!header || !payload || !out_info)
        return P05_BAD_ARGUMENT;
    memset(out_info, 0, sizeof(*out_info));
    if (header_bytes != P05_DEPLOY_HEADER_BYTES)
        return P05_BAD_HEADER;
    if (load32(header) != P05_DEPLOY_MAGIC ||
        load32(header + 4u) != P05_DEPLOY_VERSION ||
        load32(header + 8u) != P05_DEPLOY_HEADER_BYTES)
        return P05_BAD_HEADER;
    mode = load32(header + 3u * 4u);
    steps = load32(header + 4u * 4u);
    cores = load32(header + 5u * 4u);
    slots = load32(header + 6u * 4u);
    if (mode > 1u || steps == 0u || steps > P05_DEPLOY_MAX_STEPS ||
        cores == 0u || cores > P05_DEPLOY_MAX_CORES ||
        slots == 0u || slots > P05_DEPLOY_MAX_SLOTS || slots > cores ||
        load32(header + 7u * 4u) != 1u ||
        load32(header + 8u * 4u) != P05_DEPLOY_BACKING_BASE ||
        load32(header + 9u * 4u) != P05_DEPLOY_RECORD_BYTES ||
        load32(header + 10u * 4u) != P05_DEPLOY_PAYLOAD_BASE ||
        load32(header + 11u * 4u) != P05_DEPLOY_PAYLOAD_CAPACITY ||
        load32(header + 19u * 4u) != P05_DEPLOY_MAILBOX_BASE ||
        load32(header + 20u * 4u) != steps * cores)
        return P05_BAD_HEADER;
    for (i = 21u; i < 64u; ++i) {
        if (i != 22u && i != 23u &&
            load32(header + (size_t)i * 4u) != 0u)
            return P05_BAD_HEADER;
    }
    crc_h = load32(header + 23u * 4u);
    if (crc32_bytes(header, header_bytes, 1) != crc_h)
        return P05_BAD_CHECKSUM;

    events = load32(header + 13u * 4u);
    checks = load32(header + 14u * 4u);
    if (load32(header + 15u * 4u) != cores)
        return P05_BAD_HEADER;
    core_off = load32(header + 16u * 4u);
    event_off = load32(header + 17u * 4u);
    check_off = load32(header + 18u * 4u);
    payload_len = load32(header + 12u * 4u);
    /* Use wider arithmetic to avoid any count multiplication overflow. */
    if (core_off != 0u ||
        (uint64_t)event_off != (uint64_t)cores * P05_DEPLOY_CORE_BYTES ||
        (uint64_t)check_off != (uint64_t)event_off +
                               (uint64_t)events * P05_DEPLOY_EVENT_BYTES ||
        (uint64_t)payload_len != (uint64_t)check_off +
                                 (uint64_t)checks * P05_DEPLOY_CHECKPOINT_BYTES ||
        payload_len > P05_DEPLOY_PAYLOAD_CAPACITY ||
        (size_t)payload_len != payload_bytes)
        return P05_BAD_BOUNDS;
    crc_p = load32(header + 22u * 4u);
    if (crc32_bytes(payload, payload_bytes, 0) != crc_p)
        return P05_BAD_CHECKSUM;

    memset(rank, 0xFF, sizeof(rank));
    memset(sole_axon, 0, sizeof(sole_axon));
    for (i = 0u; i < cores; ++i) {
        const uint8_t *row = payload + (size_t)i * P05_DEPLOY_CORE_BYTES;
        uint32_t id = load32(row);
        uint32_t lo = load32(row + 4u), hi = load32(row + 8u);
        uint64_t meta = (uint64_t)lo | ((uint64_t)hi << 32);
        uint32_t axon = load32(row + 20u);
        if (id >= P05_DEPLOY_MAX_CORES ||
            rank[id] != UINT8_C(0xFF) ||
            (meta & UINT64_C(0x7F)) != id ||
            ((meta >> 7) & UINT64_C(0x7FF)) == 0u ||
            (meta >> 60) != 0u ||
            load32(row + 16u) == 0u ||
            axon >= P05_DEPLOY_EVENT_DEPTH ||
            load32(row + 24u) != 0u || load32(row + 28u) != 0u)
            return P05_BAD_CORE;
        rank[id] = (uint8_t)i;
        sole_axon[id] = (uint16_t)axon;
    }

    prev_step = prev_rank = UINT32_MAX;
    seen_this_step = 0u;
    for (i = 0u; i < events; ++i) {
        const uint8_t *row = payload + (size_t)event_off +
                             (size_t)i * P05_DEPLOY_EVENT_BYTES;
        uint32_t step = load32(row), id = load32(row + 4u);
        uint32_t axon = load32(row + 8u), cur_rank;
        if (step >= steps || id >= P05_DEPLOY_MAX_CORES ||
            rank[id] == UINT8_C(0xFF) ||
            axon != (uint32_t)sole_axon[id] ||
            load32(row + 12u) != 0u)
            return P05_BAD_EVENT;
        cur_rank = rank[id];
        if (i != 0u &&
            (step < prev_step ||
             (step == prev_step && cur_rank < prev_rank)))
            return P05_BAD_EVENT;
        if (step != prev_step || cur_rank != prev_rank)
            seen_this_step = 0u;
        if (++seen_this_step > P05_DEPLOY_EVENT_DEPTH)
            return P05_BAD_EVENT;
        prev_step = step;
        prev_rank = cur_rank;
    }

    prev_step = prev_rank = prev_class = UINT32_MAX;
    for (i = 0u; i < checks; ++i) {
        const uint8_t *row = payload + (size_t)check_off +
                             (size_t)i * P05_DEPLOY_CHECKPOINT_BYTES;
        uint32_t step = load32(row), id = load32(row + 4u);
        uint32_t cls = load32(row + 8u), cur_rank;
        if (mode != 1u || step >= steps ||
            id >= P05_DEPLOY_MAX_CORES ||
            rank[id] == UINT8_C(0xFF) ||
            cls < P05_OBS_STATE0 || cls > P05_OBS_PACKET0)
            return P05_BAD_CHECKPOINT;
        cur_rank = rank[id];
        if (i != 0u &&
            (step < prev_step ||
             (step == prev_step && cur_rank < prev_rank) ||
             (step == prev_step && cur_rank == prev_rank &&
              cls <= prev_class)))
            return P05_BAD_CHECKPOINT;
        prev_step = step;
        prev_rank = cur_rank;
        prev_class = cls;
    }
    out_info->timesteps = steps;
    out_info->core_count = cores;
    out_info->slot_count = slots;
    out_info->diagnostic_mode = mode;
    out_info->event_count = events;
    out_info->checkpoint_count = checks;
    out_info->payload_crc32 = crc_p;
    out_info->header_crc32 = crc_h;
    out_info->dispatch_count = steps * cores;
    return P05_VALID;
}
