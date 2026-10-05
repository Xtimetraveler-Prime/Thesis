# P01 — Board-Local Architecture Acceptance

**Status:** Accepted  
**Accepted:** 2026-10-05

## Decision

P01 freezes the first v3 board-local ownership/interface architecture.

The accepted partition is:

- external PC: provisioning, optional debug, and result retrieval only;
- PS / Cortex-A53: control plane, logical-core scheduling, page policy,
  cross-page routing bookkeeping, global barrier/timestep ownership, and
  board-local run control;
- PL: P03-compatible Loihi-like compute engine, three resident full-context
  slots, page-transfer datapath, packet/state observability, and hardware
  counters;
- K26 DDR: backing storage for non-resident logical cores plus deployment,
  input, result, and test buffers.

The PC is explicitly outside the algorithmic timestep loop.

## Selected data/control directions

- PS -> PL control/status: memory-mapped AXI control plane;
- PL -> DDR bulk context movement: burst access through a non-coherent
  high-performance PS/PL memory path;
- cache/coherency policy: explicit ownership handoff rather than requiring
  coherent CPU-cache behavior in the first implementation.

Exact register addresses, backing-image layout, alignment, and cache-maintenance
rules are deferred to P02.1 because they are implementation details of the DDR
memory system.

Exact runtime state/error transitions, board-local timing boundaries, and the v3
implementation addendum to the inherited Loihi target contract are deferred to
P03.1 because they belong to autonomous runtime implementation.

## Preserved logical invariants

P01 does not change the inherited Loihi-like logical architecture:

- logical core ID remains independent of resident slot and physical engine;
- CURRENT/NEXT event separation remains mandatory;
- packets retain logical destination IDs;
- a timestep may advance only after all logical work and relevant traffic
  quiesce;
- algorithmic timesteps remain distinct from PL cycles;
- physical scheduling/page choices must not change normalized results.

## Multi-engine decision

Multiple physical HLS engines remain architecturally legal but are **deferred**.

Reason:

- the accepted full-context memory fabric uses true-dual-port URAM banks;
- a two-engine wave could consume both memory ports for compute, forcing page
  transfer and packet/event maintenance to be serialized or newly arbitrated;
- three or more simultaneous engines would require a deeper resident-memory
  banking/replication redesign;
- introducing that redesign before P02/P03 would couple board-local memory/control
  migration with compute-parallelism research.

The phase should be reconsidered only after the single-engine board-local design
has measured complete-inference timing and can show whether HLS compute
serialization is a dominant bottleneck.

## Approval basis

The user explicitly approved the PS/PL/DDR ownership design and then approved
deferring multi-engine execution in light of the resident-memory constraints.

No new RTL, HLS, or PS runtime implementation is claimed by P01.

Primary architecture document:

```text
docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md
```
