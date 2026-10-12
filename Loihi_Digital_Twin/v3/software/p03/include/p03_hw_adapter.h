#ifndef LOIHI_TWIN_V3_P03_HW_ADAPTER_H
#define LOIHI_TWIN_V3_P03_HW_ADAPTER_H

#include <stdint.h>
#include "p03_runtime.h"

/* Physical P03.2c FPD128 / SmartConnect / 32-bit AXI4-Lite ABI.
 * Bus and cache primitives are injected for host-native regression and
 * are implemented with Xil_In32/Xil_Out32/Xil_DCache* on Cortex-A53.
 * No MMIO access is allowed without first verifying the live 128-bit
 * PS HPM0 configuration against the routed FPGA shell.
 */
#define P03_HW_BACKING_BASE UINT64_C(0x40000000)
#define P03_HW_BACKING_BYTES UINT64_C(0x04000000)
#define P03_HW_RECORD_BYTES UINT64_C(0x00080000)
#define P03_HW_MUTABLE_BYTES UINT32_C(0x0001A000)
#define P03_HW_FULL_PAGE_BYTES UINT32_C(0x0006B000)
#define P03_HW_EVENT_DEPTH 4096u
#define P03_HW_EVENT0_OFFSET UINT32_C(0x00054000)
#define P03_HW_EVENT1_OFFSET UINT32_C(0x00058000)
#define P03_HW_EVENT0_DEBUG_BANK 6u
#define P03_HW_EVENT1_DEBUG_BANK 9u
#define P03_HW_PACKET_DEBUG_BANK 8u
#define P03_HW_CONFIG_DEBUG_BANK 0u

enum {
    P03_HW_OK = 0,
    P03_HW_BAD_ARGUMENT = -1,
    P03_HW_BAD_ID = -2,
    P03_HW_BUS_ERROR = -3,
    P03_HW_TIMEOUT = -4,
    P03_HW_PROTOCOL = -5,
    P03_HW_OVERFLOW = -6,
    P03_HW_PACKET_INVALID = -7,
    P03_HW_CACHE_ERROR = -8
};

typedef struct {
    int (*read32)(void *cookie, uint32_t offset, uint32_t *value);
    int (*write32)(void *cookie, uint32_t offset, uint32_t value);
    int (*clean_range)(void *cookie, uint64_t ddr_address, uint32_t bytes);
    int (*invalidate_range)(void *cookie, uint64_t ddr_address, uint32_t bytes);
    /* PS uses an ordered mapping of the physical backing region.
     * Must perform a non-coherent 32-bit write to DDR using PS store.
     */
    int (*store_ddr32)(void *cookie, uint64_t physical_address, uint32_t value);
    void (*barrier)(void *cookie);
} p03_hw_io;

typedef struct {
    p03_hw_io io;
    void *cookie;
    uint32_t poll_limit;
    uint64_t backing_base;
    uint64_t metadata[P03_RT_MAX_CORES]; /* packed P03.2 dispatch metadata */
    uint16_t event_counts[P03_RT_MAX_CORES][2];
    uint8_t configured[P03_RT_MAX_CORES];
    /* Deploy-time sparse axon binding bitset: 128 cores x 4096 axons.
     * Explicit registration is required before any packet can be delivered.
     * Keep the adapter in static storage in bare-metal launch code (~65 KiB).
     */
    uint8_t valid_axons[P03_RT_MAX_CORES][P03_HW_EVENT_DEPTH / 8u];
    /* Active runtime needed for resident destination discovery. */
    const p03_rt *runtime;
    int last_error;
    uint32_t last_status;
} p03_hw_adapter;

/* Explicit init does not touch hardware. Caller provisions immutable
 * 512 KiB P02 records and verifies their ABI/digests before launch.
 */
int p03_hw_init(p03_hw_adapter *hw, const p03_hw_io *io, void *cookie,
                uint64_t backing_base, uint32_t poll_limit);
int p03_hw_register_core(p03_hw_adapter *hw, uint8_t id, uint64_t metadata,
                         uint16_t event0_count, uint16_t event1_count);
/* Deployment must register the accepted sparse input-axon bindings for
 * each configured logical core; otherwise packet delivery fails closed.
 */
int p03_hw_register_axon(p03_hw_adapter *hw, uint8_t id, uint16_t axon);
int p03_hw_identify(p03_hw_adapter *hw);
int p03_hw_page(p03_hw_adapter *hw, uint8_t id, uint8_t slot,
                int page_out, int mutable_only, uint64_t *cycles);
int p03_hw_debug_word(p03_hw_adapter *hw, uint8_t slot, uint8_t bank,
                      uint16_t index, int write, uint32_t data[8]);
int p03_hw_dispatch(p03_hw_adapter *hw, uint8_t id, uint8_t slot,
                    uint32_t timestep, uint8_t current_bank,
                    uint32_t *emitted, uint64_t *cycles);

/* Decode P03's 64-bit packet ABI, validate target timestep and ID,
 * and commit its axon index to exactly one NEXT bank:
 *   resident -> debug bank 6 (event0) or 9 (event1);
 *   nonresident -> DDR backing next-event payload + cache clean.
 * No paging is performed solely to deliver a packet.
 * A failed single-packet commit returns nonzero, so the scheduler will
 * fail closed. Multi-packet routing is wired in P03.3b2.
 */
int p03_hw_route_word(p03_hw_adapter *hw, uint8_t source_id,
                      uint64_t packet, uint32_t timestep, uint8_t next_bank);

/* Expose the already-validated debug packet bank, 64 bits per word.
 * Read is only legal when the HLS engine is idle.
 */
int p03_hw_read_packet(p03_hw_adapter *hw, uint8_t slot, uint16_t index,
                       uint64_t *packet);
int p03_hw_quiescent(p03_hw_adapter *hw);

#endif
