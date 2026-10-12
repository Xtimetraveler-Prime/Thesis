#ifndef LOIHI_TWIN_V3_P03_RUNTIME_H
#define LOIHI_TWIN_V3_P03_RUNTIME_H

/*
 * P03.3a portable Cortex-A53 runtime-control core (host-buildable C11).
 *
 * This is the algorithmic owner after p03_rt_execute(): no host PC
 * callbacks, no Python, and no external VIO dispatch loop are involved.
 * Hardware operations are injected through p03_rt_ops; their concrete MMIO
 * implementation, packet decoding and cache ownership are P03.3b.
 *
 * A successful callback means the hardware operation completed and was
 * acknowledged; merely writing a MMIO START bit is NOT completion.
 */
#include <stdint.h>

#define P03_RT_MAX_CORES 128u
#define P03_RT_MAX_SLOTS 3u
#define P03_RT_MAX_PACKETS 4096u
#define P03_RT_EMPTY_SLOT (-1)

typedef enum {
    P03_RT_RESET = 0,
    P03_RT_LOAD_DEPLOYMENT,
    P03_RT_INITIALIZE_BACKING,
    P03_RT_INITIALIZE_RESIDENT_SET,
    P03_RT_LOAD_INPUT,
    P03_RT_TIMESTEP_BEGIN,
    P03_RT_SELECT_LOGICAL_CORE,
    P03_RT_ENSURE_RESIDENT,
    P03_RT_SAVE_VICTIM,
    P03_RT_LOAD_REQUESTED,
    P03_RT_DISPATCH_CORE,
    P03_RT_DRAIN_AND_ROUTE_PACKETS,
    P03_RT_MARK_LOGICAL_CORE_COMPLETE,
    P03_RT_BARRIER_CHECK,
    P03_RT_SWAP_EVENT_BANKS,
    P03_RT_ADVANCE_TIMESTEP,
    P03_RT_FINALIZE,
    P03_RT_WRITE_RESULT,
    P03_RT_DONE,
    P03_RT_ERROR
} p03_rt_phase;

typedef enum {
    P03_RT_FAULT_NONE = 0,
    P03_RT_FAULT_INVALID_RUN_CONFIG = 1,
    P03_RT_FAULT_DEPLOYMENT_INVALID = 2,
    P03_RT_FAULT_BACKING_ABI = 3,
    P03_RT_FAULT_BACKING_RANGE = 4,
    P03_RT_FAULT_CACHE_OWNERSHIP = 5,
    P03_RT_FAULT_PAGE_ERROR = 6,
    P03_RT_FAULT_DISPATCH_ERROR = 7,
    P03_RT_FAULT_PACKET_FORMAT = 8,
    P03_RT_FAULT_EVENT_OVERFLOW = 9,
    P03_RT_FAULT_RESOURCE_OVERFLOW = 10,
    P03_RT_FAULT_BARRIER_INCOMPLETE = 11,
    P03_RT_FAULT_CONTROL_PROTOCOL = 12,
    P03_RT_FAULT_TIMEOUT = 13
} p03_rt_fault;

typedef struct {
    uint32_t logical_dispatches;
    uint32_t routed_packets;
    uint32_t barriers;
    uint32_t timesteps_completed;
    uint32_t initial_page_ins;
    uint32_t page_ins;
    uint32_t page_outs;
    uint32_t evictions;
    uint32_t page_hits;
    uint64_t pl_dispatch_cycles;
    uint64_t pl_page_cycles;
    uint64_t ps_route_ticks;
    uint64_t ps_barrier_ticks;
    uint64_t ps_inference_ticks;
    uint64_t ps_control_ticks;
} p03_rt_counters;

typedef struct {
    uint8_t logical_ids[P03_RT_MAX_CORES];
    uint16_t core_count;
    uint8_t slot_count;
    uint32_t requested_timesteps;
    uint32_t current_timestep;
    uint8_t current_event_bank;
    uint8_t next_victim_slot;
    int16_t resident[P03_RT_MAX_SLOTS];
    uint8_t dirty[P03_RT_MAX_SLOTS];
    uint8_t completed[P03_RT_MAX_CORES];
    uint16_t completed_count;
    uint32_t pending_packets;
    uint8_t external_control_locked;
    p03_rt_phase phase;
    p03_rt_phase fault_phase;
    p03_rt_fault first_fault;
    p03_rt_counters counters;
} p03_rt;

/* Callbacks must return zero ONLY after the stated operation is complete.
 * page_out saves the mutable image before overwrite; page_in materializes the
 * requested logical record; both implement the P02 cache/DDR ownership rules.
 * drain_route commits EXACTLY emitted packets to NEXT (never CURRENT), and
 * returns that acknowledged count; it may NOT page-in a destination solely to
 * deliver a packet. barrier_ready verifies no hardware/pending work remains.
 * Neither callback may delegate algorithmic decisions to the external PC.
 */
typedef struct {
    int (*load_deployment)(void *ctx);
    int (*initialize_backing)(void *ctx);
    int (*page_in)(void *ctx, uint8_t logical_id, uint8_t slot, uint64_t *pl_cycles);
    int (*page_out)(void *ctx, uint8_t logical_id, uint8_t slot,
                    uint64_t *pl_cycles);
    int (*load_input)(void *ctx);
    int (*dispatch)(void *ctx, uint8_t logical_id, uint8_t slot,
                    uint32_t timestep, uint8_t current_bank,
                    uint32_t *emitted, uint64_t *pl_cycles);
    int (*drain_route)(void *ctx, uint8_t source_logical_id,
                       uint32_t emitted, uint32_t timestep,
                       uint8_t next_bank, uint32_t *committed);
    int (*barrier_ready)(void *ctx, uint32_t timestep, uint8_t next_bank);
    int (*write_result)(void *ctx, const p03_rt *runtime);
    uint64_t (*read_ticks)(void *ctx); /* optional, monotonically increasing */
    void (*on_error)(void *ctx, const p03_rt *runtime); /* optional */
} p03_rt_ops;

/* Initialization allocates no heap and does not perform hardware work.
 * Validates logical IDs, slot count, duplicate entries and timesteps.
 * On invalid input, reports fail-closed INVALID_RUN_CONFIG when possible.
 */
int p03_rt_init(p03_rt *rt, const uint8_t *logical_ids, uint16_t core_count,
                uint8_t slot_count, uint32_t timesteps);

/* Runs the entire requested workload board-locally. Must be invoked once.
 * P03.3a is host-testable; P03.3b will provide physical MMIO callbacks.
 * Returns 0 on DONE, -1 on ERROR. First fault and fault_phase are sticky.
 */
int p03_rt_execute(p03_rt *rt, const p03_rt_ops *ops, void *ctx);

#endif
