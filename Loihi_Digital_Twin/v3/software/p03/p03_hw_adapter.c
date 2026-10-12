#include "p03_hw_adapter.h"
#include "p03_mmio.h"
#include <stddef.h>
#include <string.h>

/* Portable transport and physical packet semantics.
 * Hardware reads/writes are injected; no attempt is made to interpret
 * stale DDR record digests during active inference (P03.1 sec. 12).
 */

static int reject(p03_hw_adapter *hw, int code)
{
    if (hw != NULL && hw->last_error == P03_HW_OK)
        hw->last_error = code;
    return code;
}

static int read_reg(p03_hw_adapter *hw, uint32_t addr, uint32_t *value)
{
    if (hw->io.read32(hw->cookie, addr, value) != 0)
        return reject(hw, P03_HW_BUS_ERROR);
    return P03_HW_OK;
}

static int write_reg(p03_hw_adapter *hw, uint32_t addr, uint32_t value)
{
    if (hw->io.write32(hw->cookie, addr, value) != 0)
        return reject(hw, P03_HW_BUS_ERROR);
    return P03_HW_OK;
}

static uint64_t record_base(const p03_hw_adapter *hw, uint8_t id)
{
    return hw->backing_base + ((uint64_t)id * P03_HW_RECORD_BYTES);
}

static int valid_id(const p03_hw_adapter *hw, uint8_t id)
{
    return id < P03_RT_MAX_CORES && hw->configured[id] != 0;
}

static int ready(p03_hw_adapter *hw)
{
    return hw != NULL && hw->last_error == P03_HW_OK &&
           hw->io.read32 != NULL && hw->io.write32 != NULL &&
           hw->io.barrier != NULL;
}

static int read_cycles(p03_hw_adapter *hw, uint32_t lo,
                       uint32_t hi, uint64_t *result)
{
    uint32_t upper1, lower, upper2;
    unsigned retries;
    if (!result)
        return P03_HW_BAD_ARGUMENT;
    /* The PL exposes a 64-bit completed-latch split across two CSRs. */
    for (retries = 0; retries < 3; ++retries) {
        if (read_reg(hw, hi, &upper1) ||
            read_reg(hw, lo, &lower) ||
            read_reg(hw, hi, &upper2))
            return hw->last_error;
        if (upper1 == upper2) {
            *result = ((uint64_t)upper1 << 32) | lower;
            return P03_HW_OK;
        }
    }
    return reject(hw, P03_HW_PROTOCOL);
}

static int wait_done(p03_hw_adapter *hw, uint32_t register_offset,
                     uint32_t error_mask, uint32_t *status)
{
    uint32_t i, s;
    for (i = 0; i < hw->poll_limit; ++i) {
        if (read_reg(hw, register_offset, &s))
            return hw->last_error;
        hw->last_status = s;
        if ((s & error_mask) != 0)
            return reject(hw, P03_HW_PROTOCOL);
        if ((s & 3u) == 2u) {
            if (status)
                *status = s;
            return P03_HW_OK;
        }
    }
    return reject(hw, P03_HW_TIMEOUT);
}

int p03_hw_init(p03_hw_adapter *hw, const p03_hw_io *io, void *cookie,
                uint64_t backing_base, uint32_t poll_limit)
{
    uint64_t end;
    if (!hw || !io || !io->read32 || !io->write32 ||
        !io->clean_range || !io->invalidate_range || !io->store_ddr32 ||
        !io->barrier || poll_limit == 0)
        return P03_HW_BAD_ARGUMENT;
    if ((backing_base & (P03_HW_RECORD_BYTES - 1u)) != 0u)
        return P03_HW_BAD_ARGUMENT;
    end = backing_base + P03_HW_BACKING_BYTES;
    if (end < backing_base || end > UINT64_C(0x100000000))
        return P03_HW_BAD_ARGUMENT;
    /* Limit production bring-up to the P02 accepted 64 MiB address.
     * Prevents accidental DDR writes to a Linux-owned/unknown region.
     */
    if (backing_base != P03_HW_BACKING_BASE)
        return P03_HW_BAD_ARGUMENT;
    memset(hw, 0, sizeof(*hw));
    hw->io = *io;
    hw->cookie = cookie;
    hw->backing_base = backing_base;
    hw->poll_limit = poll_limit;
    hw->last_error = P03_HW_OK;
    return P03_HW_OK;
}

int p03_hw_register_core(p03_hw_adapter *hw, uint8_t id, uint64_t metadata,
                         uint16_t event0_count, uint16_t event1_count)
{
    if (!ready(hw) || id >= P03_RT_MAX_CORES ||
        hw->configured[id] ||
        (metadata & (UINT64_C(0xF) << 60)) != 0 ||
        (metadata & UINT64_C(0x7F)) != id ||
        event0_count > P03_HW_EVENT_DEPTH ||
        event1_count > P03_HW_EVENT_DEPTH)
        return reject(hw, P03_HW_BAD_ARGUMENT);
    hw->configured[id] = 1;
    hw->metadata[id] = metadata;
    hw->event_counts[id][0] = event0_count;
    hw->event_counts[id][1] = event1_count;
    return P03_HW_OK;
}

int p03_hw_register_axon(p03_hw_adapter *hw, uint8_t id, uint16_t axon)
{
    if (!ready(hw) || !valid_id(hw, id) || axon >= 4096u)
        return reject(hw, P03_HW_BAD_ARGUMENT);
    hw->valid_axons[id][axon >> 3] |= (uint8_t)(1u << (axon & 7u));
    return P03_HW_OK;
}

int p03_hw_identify(p03_hw_adapter *hw)
{
    uint32_t id, version, caps;
    if (!ready(hw))
        return P03_HW_BAD_ARGUMENT;
    if (read_reg(hw, P03_REG_ID, &id) ||
        read_reg(hw, P03_REG_VERSION, &version) ||
        read_reg(hw, P03_REG_CAPABILITIES, &caps))
        return hw->last_error;
    if (id != P03_MMIO_ID_VALUE || version != P03_MMIO_VERSION_VALUE ||
        caps != UINT32_C(0x0001031F))
        return reject(hw, P03_HW_PROTOCOL);
    return P03_HW_OK;
}

int p03_hw_page(p03_hw_adapter *hw, uint8_t id, uint8_t slot,
                int page_out, int mutable_only, uint64_t *cycles)
{
    uint64_t base;
    uint32_t bytes, expected, pending, config;
    if (!ready(hw) || !valid_id(hw, id) ||
        slot >= P03_RT_MAX_SLOTS || !cycles ||
        (page_out != 0 && page_out != 1) ||
        (mutable_only != 0 && mutable_only != 1) ||
        (!page_out && mutable_only))
        return reject(hw, P03_HW_BAD_ARGUMENT);
    base = record_base(hw, id);
    expected = (page_out && mutable_only) ?
               P03_HW_MUTABLE_BYTES : P03_HW_FULL_PAGE_BYTES;
    /* Noncoherent ownership: complete all PS DDR stores, then ensure
     * no stale PS cache line can later overwrite the PL's page-out data.
     */
    if (hw->io.clean_range(hw->cookie, base, (uint32_t)P03_HW_RECORD_BYTES))
        return reject(hw, P03_HW_CACHE_ERROR);
    if (page_out &&
        hw->io.invalidate_range(hw->cookie, base, (uint32_t)P03_HW_RECORD_BYTES))
        return reject(hw, P03_HW_CACHE_ERROR);
    hw->io.barrier();
    config = ((uint32_t)slot << P03_PAGE_CONFIG_SLOT_SHIFT) |
             (page_out ? P03_PAGE_CONFIG_PAGE_OUT : 0u) |
             (mutable_only ? P03_PAGE_CONFIG_MUTABLE_ONLY : 0u);
    if (write_reg(hw, P03_REG_PAGE_CONFIG, config) ||
        write_reg(hw, P03_REG_PAGE_BASE_LO, (uint32_t)base) ||
        write_reg(hw, P03_REG_PAGE_BASE_HI, (uint32_t)(base >> 32)))
        return hw->last_error;
    hw->io.barrier();
    if (write_reg(hw, P03_REG_PAGE_COMMAND, P03_CMD_START) ||
        wait_done(hw, P03_REG_PAGE_STATUS, UINT32_C(0xFC), NULL))
        return hw->last_error;
    if (read_reg(hw, P03_REG_PAGE_BYTES, &bytes) ||
        read_reg(hw, P03_REG_PAGE_PENDING_BYTES, &pending))
        return hw->last_error;
    if (bytes != expected || pending != 0)
        return reject(hw, P03_HW_PROTOCOL);
    if (page_out) {
        hw->io.barrier();
        if (hw->io.invalidate_range(hw->cookie, base,
                                    (uint32_t)P03_HW_RECORD_BYTES))
            return reject(hw, P03_HW_CACHE_ERROR);
    }
    return read_cycles(hw, P03_REG_PAGE_CYCLES_LO,
                       P03_REG_PAGE_CYCLES_HI, cycles);
}

/* RTL bank IDs 0=config, 6=event0, 8=packet, 9=event1.
 * Different from DDR bank ordering: event1 is NOT host-bank 7.
 */
static uint32_t bank_depth(uint8_t bank)
{
    switch (bank) {
        case 0: case 1: case 4: case 7: return 1024u;
        case 2: case 5: case 6: case 8: case 9: return 4096u;
        case 3: return 32768u;
        default: return 0;
    }
}

int p03_hw_debug_word(p03_hw_adapter *hw, uint8_t slot, uint8_t bank,
                      uint16_t index, int write, uint32_t data[8])
{
    uint32_t config, status;
    uint8_t i;
    if (!ready(hw) || !data || slot >= P03_RT_MAX_SLOTS ||
        bank_depth(bank) == 0 || index >= bank_depth(bank) ||
        (write != 0 && write != 1))
        return reject(hw, P03_HW_BAD_ARGUMENT);
    config = ((uint32_t)slot << P03_DEBUG_CONFIG_SLOT_SHIFT) |
             ((uint32_t)bank << P03_DEBUG_CONFIG_BANK_SHIFT) |
             (write ? P03_DEBUG_CONFIG_WRITE : 0u);
    if (write) {
        for (i = 0; i < 8; ++i)
            if (write_reg(hw, P03_REG_DEBUG_WDATA0 + (uint32_t)i * 4u,
                          data[i]))
                return hw->last_error;
    }
    if (write_reg(hw, P03_REG_DEBUG_CONFIG, config) ||
        write_reg(hw, P03_REG_DEBUG_ADDR, index))
        return hw->last_error;
    hw->io.barrier();
    if (write_reg(hw, P03_REG_DEBUG_COMMAND, P03_CMD_START) ||
        wait_done(hw, P03_REG_DEBUG_STATUS, UINT32_C(0x18), &status))
        return hw->last_error;
    if (!write) {
        if (!(status & UINT32_C(0x4)))
            return reject(hw, P03_HW_PROTOCOL);
        for (i = 0; i < 8; ++i)
            if (read_reg(hw, P03_REG_DEBUG_RDATA0 + (uint32_t)i * 4u,
                         &data[i]))
                return hw->last_error;
    }
    return P03_HW_OK;
}

int p03_hw_dispatch(p03_hw_adapter *hw, uint8_t id, uint8_t slot,
                    uint32_t timestep, uint8_t current_bank,
                    uint32_t *emitted, uint64_t *cycles)
{
    uint64_t metadata;
    uint32_t status, core_status, active;
    if (!ready(hw) || !valid_id(hw, id) ||
        slot >= P03_RT_MAX_SLOTS || current_bank > 1 ||
        !emitted || !cycles)
        return reject(hw, P03_HW_BAD_ARGUMENT);
    if (hw->event_counts[id][current_bank] > P03_HW_EVENT_DEPTH)
        return reject(hw, P03_HW_OVERFLOW);
    metadata = hw->metadata[id] & ~((UINT64_C(0x1FFF)) << 47);
    metadata |= (uint64_t)hw->event_counts[id][current_bank] << 47;
    if (write_reg(hw, P03_REG_DISPATCH_CONFIG,
                  (uint32_t)slot |
                  ((uint32_t)current_bank << P03_DISPATCH_CONFIG_BANK_SHIFT)) ||
        write_reg(hw, P03_REG_DISPATCH_META_LO, (uint32_t)metadata) ||
        write_reg(hw, P03_REG_DISPATCH_META_HI, (uint32_t)(metadata >> 32)) ||
        write_reg(hw, P03_REG_DISPATCH_TIMESTEP, timestep))
        return hw->last_error;
    hw->io.barrier();
    if (write_reg(hw, P03_REG_DISPATCH_COMMAND, P03_CMD_START) ||
        wait_done(hw, P03_REG_DISPATCH_STATUS, UINT32_C(0x7C), &status))
        return hw->last_error;
    if (read_reg(hw, P03_REG_DISPATCH_PACKET_CNT, emitted) ||
        read_reg(hw, P03_REG_DISPATCH_CORE_STATUS, &core_status) ||
        read_reg(hw, P03_REG_DISPATCH_ACTIVE, &active))
        return hw->last_error;
    /* ACTIVE reflects the selected core/slot/bank even after DONE.
     * A nonzero logical core ID is not an error.
     */
    if (*emitted > P03_RT_MAX_PACKETS || core_status != 0 ||
        (active & UINT32_C(0x007F0103)) !=
        (((uint32_t)id << 16) |
         ((uint32_t)current_bank << 8) | slot))
        return reject(hw, P03_HW_PROTOCOL);
    if (read_cycles(hw, P03_REG_DISPATCH_CYCLES_LO,
                    P03_REG_DISPATCH_CYCLES_HI, cycles))
        return hw->last_error;
    /* Core consumed only CURRENT events; NEXT remains preserved. */
    hw->event_counts[id][current_bank] = 0;
    return P03_HW_OK;
}

int p03_hw_read_packet(p03_hw_adapter *hw, uint8_t slot,
                       uint16_t index, uint64_t *packet)
{
    uint32_t data[8] = {0};
    if (!packet || index >= P03_RT_MAX_PACKETS)
        return reject(hw, P03_HW_BAD_ARGUMENT);
    if (p03_hw_debug_word(hw, slot, P03_HW_PACKET_DEBUG_BANK,
                          index, 0, data))
        return hw->last_error;
    *packet = (uint64_t)data[0] | ((uint64_t)data[1] << 32);
    return P03_HW_OK;
}

int p03_hw_route_word(p03_hw_adapter *hw, uint8_t source_id,
                      uint64_t packet, uint32_t timestep,
                      uint8_t next_bank)
{
    uint32_t axon, target_step, source_comp;
    uint8_t dest;
    uint16_t count;
    int slot = P03_RT_EMPTY_SLOT;
    uint8_t s;
    uint64_t ddr_addr;
    uint32_t words[8] = {0};

    if (!ready(hw) || !hw->runtime || !valid_id(hw, source_id) ||
        next_bank > 1 || next_bank == (timestep & 1u))
        return reject(hw, P03_HW_BAD_ARGUMENT);
    dest = (uint8_t)(packet & UINT64_C(0x7F));
    axon = (uint32_t)((packet >> 7) & UINT64_C(0xFFF));
    source_comp = (uint32_t)((packet >> 19) & UINT64_C(0x3FF));
    target_step = (uint32_t)((packet >> 29) & UINT64_C(0xFFFFFFFF));
    if (timestep == UINT32_MAX ||
        !(packet & (UINT64_C(1) << 61)) ||
        (packet >> 62) != 0 || target_step != timestep + 1u ||
        !valid_id(hw, dest) ||
        (hw->valid_axons[dest][axon >> 3] &
         (uint8_t)(1u << (axon & 7u))) == 0 ||
        source_comp >= ((hw->metadata[source_id] >> 7) & UINT64_C(0x7FF)))
        return reject(hw, P03_HW_PACKET_INVALID);
    count = hw->event_counts[dest][next_bank];
    if (count >= P03_HW_EVENT_DEPTH)
        return reject(hw, P03_HW_OVERFLOW);

    for (s = 0; s < hw->runtime->slot_count; ++s) {
        if (hw->runtime->resident[s] == dest) {
            slot = s;
            break;
        }
    }
    if (slot != P03_RT_EMPTY_SLOT) {
        words[0] = axon;
        if (p03_hw_debug_word(hw, (uint8_t)slot,
                next_bank ? P03_HW_EVENT1_DEBUG_BANK :
                            P03_HW_EVENT0_DEBUG_BANK,
                count, 1, words))
            return hw->last_error;
    } else {
        ddr_addr = record_base(hw, dest) +
                   (next_bank ? P03_HW_EVENT1_OFFSET :
                                P03_HW_EVENT0_OFFSET) +
                   (uint64_t)count * 4u;
        if (hw->io.store_ddr32(hw->cookie, ddr_addr, axon))
            return reject(hw, P03_HW_CACHE_ERROR);
        if (hw->io.clean_range(hw->cookie, ddr_addr, 4u))
            return reject(hw, P03_HW_CACHE_ERROR);
        hw->io.barrier();
    }
    hw->event_counts[dest][next_bank] = (uint16_t)(count + 1u);
    return P03_HW_OK;
}

int p03_hw_quiescent(p03_hw_adapter *hw)
{
    uint32_t status;
    if (!ready(hw))
        return P03_HW_BAD_ARGUMENT;
    if (read_reg(hw, P03_REG_GLOBAL_STATUS, &status))
        return hw->last_error;
    if (status != 0)
        return reject(hw, P03_HW_PROTOCOL);
    if (read_reg(hw, P03_REG_PAGE_PENDING_BYTES, &status))
        return hw->last_error;
    if (status != 0)
        return reject(hw, P03_HW_PROTOCOL);
    return P03_HW_OK;
}
