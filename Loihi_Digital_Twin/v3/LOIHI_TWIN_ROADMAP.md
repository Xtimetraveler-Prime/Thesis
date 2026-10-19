# Loihi Digital Twin v3 Development Roadmap

## Purpose

FPGA-v3 is the next research/development line for the Loihi-1 architectural digital twin.

v3 begins from the final accepted FPGA-v2 state at:

```text
a9329caa064fee3876d69fbbe6c626ac035e67b5
Close P08 and complete FPGA-v2 roadmap
```

The v2 tree remains the frozen accepted record. v3 may reuse and modify v2 implementation code, but new v3 results must not retroactively change or weaken the accepted v2 evidence.

The central v3 goal is to move from a host-assisted FPGA execution model to a substantially board-local KV260/K26 execution model while increasing physical test coverage and improving benchmark comparability.

The inherited Loihi-1 architecture contract is initially:

```text
docs/LOIHI1_TARGET_SPEC.md
```

P01 will decide whether v3 needs a separate amendment/addendum for board-local execution and any new modeled Loihi features. Architectural fidelity claims remain distinct from FPGA implementation choices.

## v3 research goals

### 1. Board-local execution

Move algorithmic execution ownership onto the KV260/K26 as far as practical.

The target execution hierarchy is:

```text
PC / development host
  -> provisioning, launch, optional debug, result collection only

KV260 Processing System (PS)
  -> deployment/runtime control
  -> logical-core scheduling
  -> routing/barrier ownership where appropriate
  -> DDR-backed logical-context management

KV260 Programmable Logic (PL)
  -> Loihi-like core execution
  -> resident-context datapath
  -> packet/event datapath
  -> high-throughput DDR movement where justified

K26 DDR4
  -> non-resident logical-core backing contexts
  -> deployment/runtime buffers
  -> test/input/output data as required
```

The external PC must not be required in the algorithmic timestep loop for the final v3 runtime.

### 2. More physical validation

v2 proved the architecture with strong Python/compiled-software validation plus representative physical K26 dispatches. v3 should move substantially more of the regression and application validation onto the board itself.

The target is not to eliminate the Python golden model. The target is to use it to generate/freeze expectations while the KV260 executes most accepted regression/application runs end-to-end.

### 3. Better published benchmark

Select a published MNIST SNN whose architecture is reproducible enough to avoid the ambiguity encountered with the NxTF reconstruction.

The selected benchmark should preferably publish or provide:

- exact input preprocessing/encoding;
- exact layer dimensions;
- exact neuron counts;
- exact connection/synapse structure;
- neuron equations and parameters;
- inference timestep/phase schedule;
- readout rule;
- training procedure;
- source code and preferably reproducible weights/checkpoints;
- accuracy;
- neuromorphic-hardware mapping details where available;
- latency/power/energy methodology where available.

A benchmark is not accepted merely because its headline neuron or parameter count is known.

Initial candidate for source audit, **not yet selected**:

- Alpha Renner et al., "The backpropagation algorithm implemented on spiking neuromorphic hardware," Nature Communications (2024), DOI 10.1038/s41467-024-53827-9.
- The paper describes a cropped-MNIST feed-forward inference module with 400 input neurons, 400 hidden neurons, and 10 output neurons, explicit Loihi CUBA parameters, a four-timestep reduced inference path, published Loihi inference measurements, and public implementation code.
- P06 must independently audit the paper/code before this project treats it as the v3 benchmark.

### 4. Latency, throughput, power, and energy characterization

v3 should measure real board-local inference rather than extrapolating a single core dispatch into sample latency.

Measurements must keep distinct:

- algorithmic timesteps/phases;
- PL clock cycles;
- logical-core dispatch time;
- context page-in/page-out time;
- PS scheduling/routing time;
- complete timestep time;
- complete sample latency;
- steady-state throughput;
- idle/static board power;
- active board power;
- dynamic power when explicitly defined;
- energy per inference.

The KV260 SOM power telemetry may be used for reproducible board-level measurements, with an external meter retained as an optional validation path.

### 5. Multiple physical HLS execution engines — deferred

Multi-engine execution remains a valid v3 optimization direction, but it is
**deferred from the current critical path** until the single-engine DDR-backed
board-local architecture is implemented and characterized.

The reason is not primarily HLS arithmetic cost. Accepted routed evidence
suggests the compute engine itself is modest relative to K26 logic/DSP capacity.
The limiting issue is the resident-context memory architecture:

- the accepted three-context fabric uses true-dual-port URAM banks;
- one port currently services the HLS compute path and the other services
  host/integration/maintenance access;
- a two-engine design could potentially repurpose both ports for compute during
  a parallel wave, but page movement and packet/event maintenance would then
  need explicit arbitration or serialization;
- three or more simultaneous engines would require a deeper memory redesign,
  such as per-slot banking, selective replication, or moving some storage
  classes out of URAM.

Because v3's primary research goal is first to eliminate PC-owned paging and
control, introducing that memory redesign now would mix two independent
questions: **board autonomy** and **compute parallelism**.

The deferred optimization should be reconsidered after P02/P03/P08 measure the
single-engine system and show whether HLS compute serialization is actually a
dominant end-to-end latency term.


---

## Development/acceptance rules

Status meanings:

- **Complete** — deliverables are implemented, reproduced independently, and accepted.
- **In progress** — active work exists but acceptance is pending.
- **Planned** — agreed work not yet started.
- **Blocked** — waiting on a dependency/decision.
- **Deferred** — intentionally outside the current critical path.

For every major sub-milestone:

1. implement on a dedicated branch;
2. run the relevant automated/software/hardware gates;
3. provide exact reproduction commands;
4. stop for independent verification before merge;
5. record acceptance evidence only after independent verification succeeds;
6. merge only after explicit approval.

A passing developer-side test does not by itself close a hardware/software milestone.

---

## Phase summary

| ID | Phase | Status |
|---|---|---|
| P00 | Establish v3 baseline, directory, and roadmap | Complete |
| P01 | Define board-local architecture, ownership, and v3 contract | Complete |
| P02 | Move non-resident logical contexts into K26 DDR | Complete |
| P03 | Build autonomous PS-resident scheduling/routing/barrier runtime | Complete |
| P04 | Add multi-engine parallel logical-core execution | Deferred |
| P05 | Build board-local regression, observability, and data-path hardening | In progress (P05.2; P05.1 accepted) |
| P06 | Audit and freeze an exact published MNIST benchmark | In progress (Track A accepted; Track B gated by P08-A) |
| P07 | Execute the frozen benchmark end-to-end primarily on KV260 | In progress (A1/A2 accepted; A3 validation pending) |
| P08 | Characterize latency, throughput, power, and energy | Planned |
| P09 | Final source-backed comparison and v3 closure | Planned |

---

# P00 — Establish v3 baseline, directory, and roadmap

**Status:** Complete  
**Accepted:** 2026-10-05

## Goal

Create an isolated v3 development tree from the final accepted v2 implementation without changing the v2 record.

## Deliverables

- copy the accepted `Loihi_Digital_Twin/v2/` tree into `Loihi_Digital_Twin/v3/`;
- preserve the existing v2 source/HLS/RTL/Vivado/test functionality as the initial v3 baseline;
- add this v3 roadmap;
- replace the copied v2 README with a v3 baseline README;
- update the parent `Loihi_Digital_Twin/README.md` to identify v2 as the accepted baseline and v3 as active follow-on development;
- record that inherited package/module names may still contain `v2` until a later deliberate compatibility migration.

## Acceptance

P00 was accepted after independent verification confirmed:

- the copied implementation matches the accepted v2 baseline except for intentional v3 documentation changes;
- all inherited `docs`, `examples`, `hardware`, `hls`, `rtl`, `scripts`, `src`, `tests`, and `vivado` Git subtrees are identical to v2;
- `pyproject.toml` and `.gitignore` are identical to v2;
- no accepted v2 files were modified;
- the inherited v3 regression suite completed at 100% with 67 passing test indicators and no reported failures/errors.

Primary acceptance record: `docs/P00_ACCEPTANCE.md`.

---

# P01 — Board-local architecture, ownership, and v3 contract

**Status:** Complete  
**Accepted:** 2026-10-05

## Research question

What is the cleanest PS/PL/DDR partition that removes the PC from the algorithmic execution loop while preserving v2 architectural semantics?

## Proposed default ownership

Unless measurements justify a different split:

- **PS/A53:** control plane, deployment loading, logical-core scheduling, global barrier, cross-page routing bookkeeping, run control, result collection;
- **PL:** Loihi-like core arithmetic, resident-context memories, packet/event datapath, performance counters, and bulk memory movement support;
- **DDR4:** backing images for non-resident logical cores and runtime buffers;
- **PC:** build/deploy, initial provisioning, optional debugging, and post-run collection only.

This is a project implementation partition, not a claim about Loihi's physical microarchitecture.

## Resolution

P01 closed on the ownership/interface architecture in
`docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

The detailed implementation contracts originally sketched as P01.2/P01.3 are
intentionally re-homed to the phases that implement them:

- **P02.1 — DDR backing-image ABI and coherency contract** will freeze DDR
  layout, context sections/stride/alignment, page-transfer commands, address
  validation, cache-maintenance/ownership rules, and serialization.
- **P03.1 — Autonomous runtime contract** will freeze exact run/barrier/error
  transitions, board-local timing/observability boundaries, and the v3
  implementation addendum to the inherited Loihi target specification.

This avoids treating implementation details as completed merely because the
high-level partition is accepted.

## Accepted deliverables

- v3 board-local architecture/ownership document;
- explicit external-host / PS / PL / DDR responsibility table;
- PS-to-PL control-plane direction;
- PL-to-DDR bulk-data-plane direction;
- first non-coherent ownership strategy;
- preservation of logical-core / resident-slot / physical-engine separation;
- preservation of CURRENT/NEXT event causality and global barrier semantics;
- decision that no existing logical Loihi-1 semantic rule needs to change;
- explicit decision to defer multi-engine execution until the memory system and
  single-engine board-local runtime are measured.

## Acceptance

P01 is accepted based on independent design review and explicit approval of the
PS/PL/DDR partition.

This acceptance freezes the architectural direction only. It does **not** claim
that DDR paging or the PS-resident runtime is implemented yet. Those are P02
and P03 respectively.

Primary record: `docs/P01_1_BOARD_LOCAL_ARCHITECTURE.md`.

---

# P02 — DDR-backed logical-core virtualization

**Status:** Complete  
**Accepted:** 2026-10-06

## Goal

Replace PC-RAM backing for non-resident cores with K26 DDR backing.

## Sub-milestones

- **P02.1 — DDR backing-image ABI and coherency contract.** **Complete; accepted 2026-10-05.** Freeze layout,
  fixed/variable section sizes, alignment, versioning, address validation,
  page-transfer commands, ownership/cache-maintenance rules, and deterministic
  serialization. Primary records: `docs/P02_1_DDR_ABI.md` and
  `docs/P02_1_VERIFICATION.md`.
- **P02.2 — Software reference and transfer-model validation.** **Complete; accepted 2026-10-05.** Model authoritative DDR records, resident-slot
  materialization, eviction/writeback, runtime metadata refresh, transfer byte
  accounting, and full-versus-mutable-only writeback equivalence. Primary
  records: `docs/P02_2_DDR_TRANSFER_MODEL.md` and
  `docs/P02_2_ACCEPTANCE.md`.
- **P02.3a — Resident-bank page walker and ownership path.** **Complete; accepted 2026-10-05.**
  Implement the deterministic PL bank walker over the accepted P05 host-side
  memory access boundary, with full/mutable-only transfer sequencing and
  directed RTL verification.
- **P02.3b — AXI DDR master/burst integration.** **Complete; accepted 2026-10-05.** Connect the
  verified bank walker to the selected PS DDR high-performance path, add burst
  buffering/range checks, and integrate into the Vivado shell.
  - **P02.3b1 — 128-bit AXI burst coalescer.** **Complete; accepted 2026-10-05.** Coalesce the
    scalar-correct walker transactions into 256-byte / 16-beat AXI4 bursts
    without changing the accepted DDR address stream.
  - **P02.3b2 — HP0 Vivado integration.** **Complete; accepted 2026-10-05.** Bind the
    verified AXI master to the K26 PS `S_AXI_HP0_FPD` path through
    SmartConnect, confine paging to the fixed 64 MiB DDR backing window, and
    synthesize/route the resulting shell. Primary record:
    `docs/P02_3B2_HP0_INTEGRATION.md`; routed acceptance: `docs/P02_3B2_ROUTE_ACCEPTANCE.md`.
- **P02.4 — Physical DDR-backed paging acceptance.** **Complete; accepted 2026-10-06.** Demonstrate that
  non-resident logical contexts live in K26 DDR and are paged into the three
  resident slots without PC RAM participating in the page loop. Primary plan:
  `docs/P02_4_PHYSICAL_PAGING.md`.
  - **P02.4a — deterministic physical DDR round-trip.** **Complete; accepted 2026-10-05.** Reused the
    accepted P02.3b2 bitstream to prove byte-exact full page-in/full page-out and
    mutable-only writeback through real K26 DDR, with exact burst/byte/cycle
    evidence and per-bank fingerprints. Primary acceptance record:
    `docs/P02_4A_ACCEPTANCE.md`.
  - **P02.4b — five-over-three DDR-backed workload.** **Complete; accepted 2026-10-06.** Execute
    a directed seven-timestep / 35-dispatch five-logical-core workload through
    three resident slots and one physical engine with K26 DDR as the
    authoritative non-resident backing store. Require exact per-dispatch
    state/spike/packet agreement and byte-exact final DDR images for all five
    logical contexts. Primary record: `docs/P02_4B_FIVE_OVER_THREE.md`.

## Deliverables

- deterministic `logical_core_id -> DDR backing region` mapping;
- storage for all complete logical context images required by a deployment;
- page-in/page-out between DDR and the three proven resident context slots;
- preserved CURRENT/NEXT event-bank semantics;
- preserved logical destination IDs independent of physical residency;
- explicit dirty/writeback rules;
- context fingerprints/checksums;
- measured page transfer size, latency, and bandwidth;
- PS-copy and/or AXI/DMA implementation chosen from measured evidence rather than assumption.

## Acceptance

Accepted on 2026-10-06.

The directed five-logical-core / three-resident-context physical workload
completed with K26 DDR as the authoritative backing store:

```text
dispatches=35
barriers=7
routed_packets=30
page_ins=60
page_outs=60
evictions=57
page_hits=8
axi_read_bursts=102720
axi_write_bursts=24960
axi_bytes=32686080
result=PASS
```

All five complete final 512 KiB DDR records matched their golden images
byte-for-byte. Primary phase record: `docs/P02_ACCEPTANCE.md`; physical
five-over-three acceptance: `docs/P02_4B_ACCEPTANCE.md`.

---

# P03 — Autonomous PS-resident runtime

**Status:** Complete — independently accepted 2026-10-12
**Development branch:** `agent/v3-p03-autonomous-runtime` (merged into `main` at closeout).
**Authoritative acceptance:** `docs/P03_FINAL_ACCEPTANCE.md`.
**Detailed PS application architecture, DDR/packet/mailbox ABI,
debugging chronology and reproduction:** `docs/P03_PS_AUTONOMOUS_APPLICATION.md`.

## Goal

Move host-owned algorithmic orchestration onto the KV260 PS.

## Sub-milestones

- **P03.1 — Autonomous runtime contract.** **Complete; accepted 2026-10-06.** Freeze
  exact run/barrier/error transitions, board-local timer/counter boundaries,
  recovery behavior, external-host exclusion, cache/ownership rules, and the v3
  implementation addendum to the inherited Loihi target specification. Primary
  record: `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`.
- **P03.2 — PS-visible MMIO control/status shell.** **Complete; accepted 2026-10-11 for the physical experimental control shell.** Replace
  VIO-owned page/dispatch/resident-memory control with a PS-accessible AXI-Lite
  register block on the accepted `M_AXI_HPM0_FPD` direction while preserving
  the accepted P02 data plane and response semantics.
  - **P03.2a — AXI-Lite register contract.** **Complete; accepted 2026-10-06.**
    Freeze the 32-bit register map, sticky completion semantics, slow resident
    request handshake, Python/C software constants, and directed RTL regression.
  - **P03.2b — Routed HPM0 integration.** **Complete; accepted 2026-10-06.** Connect
    the register block through HPM0 at `0xA4000000..0xA4000FFF`, preserve the
    accepted HP0 DDR data path, retain VIO as observation/reset-only, close
    timing, and export bitstream/probes/fixed XSA.
  - **P03.2c — Physical PS-MMIO smoke.** **Complete; independently
    accepted 2026-10-11.** The KV260's physical PS HPM0 width selectors
    were measured at 128 bits while the original FPD/LPD PL designs
    expected 32 bits. The corrected FPD 128-bit AXI4 master plus
    1x1 SmartConnect 128-to-32-bit AXI4-Lite bridge preserves the
    `0xA4000000` MMIO ABI and existing HP0/DDR paging path.
    The independent A53 read-only diagnostic passed all four registers.
    Subsequently the independent **full A53 page/resident/dispatch
    smoke passed**: strict 64-byte mailbox verifier reported
    `id=0x4C543302`, `capabilities=0x0001031F`,
    `page_bytes=438272`, `config0=0x14001000`,
    `dispatches=1`, with full verifier exit `0`. The full
    verifier additionally checked VERSION, page burst counts, sticky
    done/errors, resident read-valid, dispatch/global errors and
    completion. Physical evidence directory:
    `/tmp/v3_p03_2c_fullsmoke_20261012T020320Z` (user PC).
    **Accepted experimental-shell decision:** retain diagnostic ILAs
    and temporary otherwise-unmapped signature during P03.3; track
    their removal and a final release route as a separate cleanup
    gate, not as a blocking functional requirement. See
    `docs/P03_2C_ACCEPTANCE.md` and
    `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`.
- **P03.3 — Standalone Cortex-A53 runtime.** **Complete; independently accepted through P03.4/P03.5 on 2026-10-12.** Implement
  P03.1's board-local state machine, deterministic scheduling/replacement,
  packet routing, cache-maintenance ownership, timer/counter collection,
  fail-closed result records, and the fixed P02 64 MiB DDR reservation.
  - **P03.3a — Portable C runtime policy engine.** **Complete;
    independently accepted 2026-10-11.**
    Introduce `software/p03/include/p03_runtime.h`,
    `software/p03/p03_runtime.c` and a host-native hardware-mock test
    harness. Test compiled logical-core service order, initial resident
    selection, dirty-victim writeback before page-in, round-robin
    eviction, exact packet-drain accounting, no-premature-barrier
    event-bank swaps, sticky first-error, and 35 dispatches / seven
    barriers for a five-over-three plan. This does **not** prove
    packet encoding, actual MMIO control or inference equivalence.
  - **P03.3b — Physical MMIO/DDR/packet adapter.**
    **Directed P03.3b1–b3 acceptance complete 2026-10-11; resident
    destination physical coverage explicitly tracked.** Native C
    MMIO/DDR packet adapter passed, the one-core/two-step real A53
    scheduler/adapter probe passed, and the two-core/one-slot
    physical real-HLS packet/dirty-page roundtrip independently passed:
    `ps_width=128`, `first_packet=0x2000000020000581`,
    `second_packet=0x2000000040000A00`,
    `core1_ddr_event1=11`, `core0_ddr_event0=20`,
    `page_ins=3`, `page_outs=3`, `dispatches=4`,
    `barriers=2`, `routed_packets=2`,
    `P03_3B3_VERIFY_EXIT=0`.
    Accepted local evidence folder:
    `/tmp/v3_p03_3b3_fixed_20261012T034337Z`.
    This verified actual PL packets, PS-owned nonresident DDR routing
    and mutable context persistence. The one-slot probe did not
    exercise direct MMIO delivery to an already-resident destination;
    that path remains native-tested and is counted explicitly by
    the new unified P03 runner. Primary acceptance record:
    `docs/P03_3B3_ACCEPTANCE.md`.
  - **P03.3c + P03.4 + P03.5 — Consolidated implementation and
    two independent physical acceptance runs.** **Complete; combined C11/Vitis implementation and physical P03.4/P03.5 gates accepted on 2026-10-12.** To minimize extra subphases, these use one immutable
    software/ABI/hardware path. New
    `software/p03/p03_finish_run.c` links the accepted C
    scheduler, real P03.3b adapter/bridge, and A53 Xilinx BSP. A
    versioned 256-byte CRC32-checked DDR launch manifest selects
    **7 or 100 timesteps** for the **exact accepted P02.4b
    five-logical-core/three-resident-slot ring**. The A53 owns
    the formerly host-driven per-core ingress injection immediately
    before dispatch, RR page replacement, cross-core routing, global
    barrier and bank swaps, CNTVCT timing/counters, failure
    persistence, and final dirty resident flush. XSDB passively
    waits for terminal mailbox and only then retrieves five full
    final 512 KiB records. The Python verifier compares those
    records byte-exactly to the frozen P02 golden and the 256-byte
    mailbox to the scheduler/timing/status oracle. The 7-step
    profile must demonstrate **35 dispatches, 7 barriers, 30
    packets** and the accepted trace fingerprint
    `9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac`.
    The 100-step profile requires **500 dispatches, 100 barriers**,
    and the 100-step Python reference's own packet count and five
    full normalized final records; it may not borrow the 7-step
    oracle. The PS runtime uses a different packet-delivery/paging
    policy than PC-controlled P02, so its *paging counts* may differ
    without changing logical results.
    **P03.4 physical attempt 1 FAILED on 2026-10-11 at the
    `WRITE_RESULT` callback (fault=12, phase=17, result=0xDEAD000B).**
    The mailbox confirmed 35 dispatches, seven barriers and all 30
    expected packets, but reported an impossible final flush count
    `0x800023` instead of 3. The five complete DDR records were
    dumped successfully but the original verifier aborted before
    comparing them against the Python oracle. A V2 corrective
    candidate explicitly initializes application-owned counters,
    preserves every acceptance predicate while encoding the exact
    failed check in a tagged error-only mailbox overlay, and runs
    byte-exact final-DDR comparison even on a failed mailbox. The
    build/physical runner require a V2 ELF marker, not the older V1
    binary. The exact root of the counter anomaly remains
    **unconfirmed** until fresh physical evidence. See
    `docs/P03_4_PHYSICAL_ATTEMPT1.md`.
    **P03.4 ACCEPTED from independent physical KV260 seven-step V2
    verification on 2026-10-11 local / 2026-10-12 UTC.**
    The five-core/three-slot A53 autonomous run completed 35 dispatches,
    30 routed HLS packets, seven barriers, 35 page-ins and 35 page-outs,
    and all five final 512 KiB DDR records matched the frozen P02/v2
    Python oracle byte-exactly; trace fingerprint
    `9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac`.
    Measured `resident_deliveries=0`: this ring provides physical
    nonresident routing evidence, not direct-to-resident packet delivery.
    Acceptance: `docs/P03_4_ACCEPTANCE.md`.
    **P03.5 ACCEPTED on 2026-10-12 (same V2 A53 ELF and FPD128
    experimental bitstream).** The independent 100-timestep
    five-core/three-slot physical test reported terminal
    `result=0x600D600D`, **500 real HLS dispatches, 495 routed
    packets, 100 barriers, 500 page-ins, 500 page-outs**, and all
    five final 512 KiB DDR records byte-exact to the independent
    100-step P02/v2 Python oracle. Reference trace fingerprint:
    `b10387cb7930e6e4452548ff4d025c8dffe52e9eeebde2d5b43ed9c5475cfcac`.
    Launch manifest SHA-256:
    `30076c118d312e57674f716e50fe3d080e7a057ed55ba1f2ae58a9a7dba51c4b`.
    User evidence:
    `/tmp/v3_p03_finish_100_20261012T145336Z`;
    `P03_FINISH_VERIFY_EXIT=0`.
    **P03 functionally COMPLETE.** P03.4 and P03.5 both reported
    `resident_deliveries=0`; this acceptance does **not** claim
    a real FPGA direct-to-resident destination packet test.
    Preserve it as a P05 hardening/coverage item, along with
    optional release cleanup for the accepted ILA/VIO diagnostic
    shell. See `docs/P03_5_ACCEPTANCE.md`,
    `docs/P03_FINAL_ACCEPTANCE.md` and
    `docs/P03_PS_AUTONOMOUS_APPLICATION.md`.

## Deliverables

A board-resident runtime that can:

- load a compiled deployment into DDR;
- initialize resident contexts;
- ingest an input sample;
- schedule logical cores;
- page contexts;
- route local and cross-page packets;
- determine timestep quiescence;
- enforce the global barrier;
- swap CURRENT/NEXT event banks only at the barrier;
- advance the requested number of timesteps/phases;
- return final evidence/results and execution metadata.

## Acceptance

After a start command, the PC must not participate in logical-core scheduling, packet routing, page replacement, or timestep/barrier control.

The representative five-over-three 100-timestep workload must complete board-locally and match the normalized v2/Python architectural result.

---

# P04 — Multi-engine parallel logical-core execution

**Status:** Deferred

## Motivation

Replicating the P03-compatible HLS evaluation engine remains attractive because
independent logical cores in the same algorithmic timestep can, in principle,
consume frozen CURRENT state concurrently and produce NEXT-timestep traffic.
That could reduce the serialized compute portion of inference latency.

Accepted routed evidence also indicates that the compute logic itself is not the
obvious K26 bottleneck:

```text
P05 one-engine / three-full-context shell:
  LUTs       5,062
  registers  7,686
  DSPs       2
  URAM       47

P04 resource-scaled two-engine shell:
  LUTs       7,059
  registers  9,980
  DSPs       4
```

The two shells are not otherwise identical, so these numbers are **not** an
exact per-engine cost model. They do support the narrower conclusion that v2's
full-capacity scaling problem was dominated by retained memory rather than by
the HLS arithmetic datapath.

## Why it is deferred

The current three-full-context memory fabric is built from true-dual-port URAM
banks. In the accepted one-engine design:

- one memory side services the HLS compute path;
- the second side services host/integration functions such as packet access,
  next-event writes, and context maintenance.

A plausible two-engine design would consume both memory ports for compute during
a parallel wave:

```text
resident context A <-> port A <-> engine 0
resident context B <-> port B <-> engine 1
resident context C remains retained
```

That creates a new arbitration problem: page movement, packet draining, and
event maintenance can no longer freely use the second port while both engines
are active. The first implementation would therefore have to serialize those
operations around compute or redesign the resident-memory access fabric.

The problem becomes more fundamental at three or more engines. Three resident
slots do **not** imply three independent memory read/write ports. Supporting
3+ simultaneous engines would likely require one or more of:

- per-slot memory banking;
- selective replication of read-mostly configuration/axon/synapse/route banks;
- relocation of trace/packet/event storage to other memory classes;
- additional AXI/interconnect arbitration;
- a different resident-context organization altogether.

Those choices can increase URAM/BRAM usage and routing pressure enough to change
the physical architecture that P02/P03 are trying to stabilize.

## Why deferral is preferable

The central v3 research question is first whether the KV260 can execute the
virtualized architecture independently of PC RAM and PC-owned timestep control.

Adding multi-engine execution before that is proven would couple two separate
research problems:

1. **memory/control localization** — DDR-backed paging plus PS/PL ownership;
2. **compute parallelization** — multiple engines and a multiported/banked
   resident-memory system.

Keeping P04 deferred lets P02/P03 establish a clean single-engine baseline. P08
can then quantify how much complete-inference time is actually spent in HLS
compute versus DDR paging, packet routing, PS control, and barriers.

If compute serialization is a dominant measured term, P04 should be reactivated
with an evidence-based engine-count target.

## Preserved design rules for later reactivation

Any future multi-engine implementation must preserve:

- logical-core ID independent of engine ID;
- one engine may own at most one resident logical context at a time;
- two engines may never write the same resident context concurrently;
- CURRENT inputs remain frozen for the entire algorithmic timestep;
- generated traffic is committed only to NEXT-timestep state;
- all engines and all packet/page work must quiesce before the global barrier;
- physical engine/wave assignment is excluded from normalized logical traces;
- one-engine and multi-engine normalized results must be identical.

A future two-engine experiment should measure actual complete-inference speedup;
an assumed 2x speedup is not a valid result.

## Reactivation trigger

Reconsider P04 after the single-engine board-local implementation has accepted
measurements for:

- HLS dispatch time;
- DDR page-in/page-out time;
- packet drain/routing time;
- PS scheduling/barrier overhead;
- complete timestep latency;
- complete inference latency;
- routed resource/timing margin.

---

# P05 — Board-local regression, observability, and data-path hardening

**Status:** **COMPLETE / PHYSICALLY ACCEPTED, 2026-10-13** —
**P05.1 complete; all P05.2a–P05.2i gates physically accepted
within the documented scope.**  
**Historical development branch:** `agent/v3-p05-board-regression`;
user explicitly authorized P05 closeout and merge to `main`.
Phase acceptance: `docs/P05_FINAL_ACCEPTANCE.md`.  
**Baseline:** P03 accepted A53 scheduler, FPGA MMIO/DDR adapter, FPD128
bitstream/XSA and frozen P02/P03 reference goldens remain unchanged.

## Goal

Make KV260 the primary execution target for independent Python-oracle
regression evidence. Demonstrate correctness across different network
sizes, packet residency paths and selected intermediate checkpoints;
then harden error diagnostics, fanout, input saturation/backpressure,
paging, arithmetic, service-order variation and counter provenance.

## P05.1 — Configurable PS regression runner and test infrastructure

**Status: COMPLETE — functional acceptance from two independent user-run
KV260 gates on 2026-10-12.**

- New standalone `p05_regression_run.elf` successfully built using
  accepted routed XSA, versioned/CRC-bounded P05G descriptors,
  strictly validated complete initial DDR records, and original
  unmodified P03 scheduler and PS hardware adapter. Host
  Python↔C11 ABI/negative regressions were independently reported PASS.
- **First physical gate:** Five logical cores, three resident slots,
  seven timesteps, 35 dispatches, 30 real packet events,
  seven barriers, **35/35 independent actual-device state0
  checkpoints**, and **all five complete 512 KiB final DDR records
  byte-exact to frozen P02**. `resident_deliveries=0`;
  `P05_1_VERIFY_EXIT=0`. User evidence:
  `/tmp/v3_p05_1_probe_20261012T173751Z`.
  Acceptance: `docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md`.
- **Second physical gate:** Genuinely different three-core / three-slot
  spiking triangle, threshold=4, five timesteps,
  **15 real dispatches, 12 real packets,
  12 confirmed direct-to-resident deliveries**, five barriers,
  **15/15 model-derived actual-device checkpoints**, zero
  page replacements, and **three complete 512 KiB DDR final
  records byte-exact to its separate LogicalChip model**.
  `P05_1_TRIANGLE_VERIFY_EXIT=0`, real terminal
  `0x600D600D`. User evidence:
  `/tmp/v3_p05_1_triangle_20261012T175547Z`.
  Reference trace fingerprint:
  `c2fde59f694508003fb6b0d17f5ed2945db5f03c427a2690b13acc7bc71b717e`.
  Acceptance: `docs/P05_1_TRIANGLE_ACCEPTANCE.md`.
- Both tests used the **same P05 ELF and accepted FPGA shell**,
  with only initial deployment records/table changed. Python
  compared **actual** physically retrieved complete DDR images;
  reference trace digests are model fingerprints, not full
  physical intermediate trace captures.
- **Qualified acceptance:** Functional deployment, model-relative
  checkpoints and both residency routing paths accepted.
  Independent **physical fault-injection/first-error and
  fast-mode/no-checkpoint equivalence remain untested**. User
  explicitly accepted P05.1 functional closeout with these
  limitations carried into the P05.2 hardening scope.
  Do not imply these two additional hardware gates already passed.

### Deliverables

- New P05 test-oriented standalone Cortex-A53 executable, separate
  from the accepted fixed P03.4/P03.5 ELF, **reusing** the same
  `p03_runtime.c` scheduler and `p03_hw_adapter.c` physical callbacks;
  no per-test recompilation of the algorithmic runtime.
- Versioned bounded deployment descriptor and test-vector format
  supporting selectable logical-core count, time horizon, valid
  logical-core/slot configuration, input events per timestep/core,
  service order where legal, and deterministic observation checkpoints.
  Include checksum/integrity, range, capacity and memory-reservation
  validation on **both host and device**; failures halt before MMIO.
- Python deployment builder, test-vector/golden generation and
  independent verifier with reproducible test IDs and fingerprints;
  initial workload must reproduce an accepted P03 five-core ring
  without modifying or substituting the frozen P03 oracle.
- Device-side per-run and selected per-timestep/per-core observations:
  first-mismatch metadata (logical core, timestep, state class),
  packet/barrier/page counters, and reproducible checksums at safe
  synchronization points. Separate diagnostic and low-overhead modes.
- Retain a replayable fail-closed result format and a fresh ELF marker;
  PS runtime may not delegate paging/routing/step decisions to the PC.

### P05.1 acceptance / hold points

1. **Contract checkpoint:** deterministic host-generated deployment,
   strict portable C11 reader/validator, field-layout and corruption/
   bounds tests, P03 baseline integrity tests. Request independent
   host validation before adding the PS execution path.
2. **Runtime checkpoint:** new separately identifiable standalone A53
   program can autonomously execute at least two distinct valid
   deployment profiles using the accepted PS–PL and DDR interface,
   with byte-exact Python oracle outputs and interpretable
   telemetry. Verify staged ELF/XSA/bitstream identity.
3. **Checkpoint/diagnostic checkpoint:** selected state/event/packet
   checkpoints and first-error reporting agree with model fixtures
   without changes to neural arithmetic; production/passive
   measurements do not silently change the test workload.

**Not P05.1 acceptance yet:** A host-only schema or mocked runner,
an unbuilt ELF, or a new host-controlled per-dispatch loop. A directed
physical already-resident destination packet test may be included in
the P05.1 trial profile; broader coverage is P05.2.

## P05.2 — Directed physical regression and observability validation

**Status:** COMPLETE / PHYSICALLY ACCEPTED (2026-10-13) —
P05.2a first-fault localization,
P05.2b checkpoint-disabled equivalence,
P05.2c reordered service, P05.2d two-destination fanout
and **P05.2e composite physical evidence recheck accepted**
on real KV260 (independent user-reported results, 2026-10-12).
The first P05.2e full-DDR comparison correctly failed at
core3 packet RAM offset 0x64000 because the normalized
destination-sorted model order [0,4] differs from physical
registered output-route order [4,0].
The independent **non-destructive recheck PASS**
`P05_2E_RECHECK_EXIT=0` verifies 40/40 checkpoints, 48
packets (24 resident and 24 nonresident), 37 dirty evictions,
and all five complete real DDR images against the separate
derived physical packet-layout oracle **without modifying the
original A53/FPGA evidence or neural model**. Its acceptance
record is `docs/P05_2E_RECHECK_ACCEPTANCE.md`; the user has
not supplied a fresh native pytest summary alongside this
physical recheck. P05.2f signed arithmetic/refractory/paging and P05.2g
exact 4096 CURRENT-event-bank saturation plus CRC-valid
4097-event early device-admission rejection are independently
physically ACCEPTED. P05.2h 16-barrier mixed-residency dual-bank/packet
stress gate is independently PHYSICALLY ACCEPTED, with 318
checkpoints, 156 packets split 78 resident/78 nonresident,
77 evictions and five byte-exact DDR records (user-confirmed).
P05.2i **PHYSICALLY ACCEPTED** as the final
counter-provenance closeout gate: the same-run,
no-reboot XSDB `mrd -force` read-only capture
measured **136,960 completed read bursts,
33,280 completed write bursts and 43,581,440
successful FPGA page-engine AXI bytes** in hardware.
The independent A53 `P05R` burst counts, separate
model-derived page totals, full 318-checkpoint neural
oracle and all five 512 KiB physical DDR records
agreed; `P05_2I_VERIFY_EXIT=0`. User expressly
approved final P05 closure and merge. See
`docs/P05_2I_ACCEPTANCE.md`. Live routed NEXT-bank
overflow recovery remains explicitly unverified.

**P05.2a — Deterministic negative-checkpoint hardware diagnostic
(ACCEPTED on real KV260, 2026-10-12).** Reuse the physically accepted
three-core fully resident triangle, unchanged 3×512KiB initial
neural records, same 15 stimulus events, same 15 dispatch
metadata entries, same PS/PL binary identities. Flip **one bit
of the EXPECTED state0 CRC at checkpoint 7** (timestep 2,
logical core 1); the real A53 must intentionally
stop at barrier 2 and report `result=0xDEAD000A`, runtime fault 11,
fault phase 13, first mismatch (step=2, core=1, class=state0)
with observed CRC **equal to the independent clean model**.
Do not call some unrelated hardware ERROR a test PASS.
No final DDR equality is expected after early fault because
final dirty-slot flush never executes.

Scripts: `scripts/p05_2_fault_fixture.py`,
`scripts/p05_2_fault_verify.py`,
`scripts/run_p05_2_fault.sh`.
Host native/injected-malformed-mailbox tests:
`tests/test_p05_2_fault.py`.
Reproduction, measurement caveats and directed coverage backlog:
`docs/P05_2_DIAGNOSTIC_GATE.md`.
**Observed P05.2a PHYSICAL PASS**: user captured real A53
`0xDEAD000A` after one passive poll, with first-fault 11,
phase 13, failing step 2/core 1/state0, injected expected
CRC `0x6522DF68`, physically observed/reference-model CRC
`0x6522DF69`, 9 prior dispatches, 6 packets,
6 direct resident deliveries, 2 complete barriers and 7 passing
prior checkpoints. Strict `P05_2_FAULT_VERIFY_EXIT=0`;
physical evidence:
`/tmp/v3_p05_2_fault_20261012T181015Z`.
See `docs/P05_2A_FIRST_MISMATCH_ACCEPTANCE.md`. This
intentionally stopped before final dirty DDR flush; **no
completed golden DDR equality was claimed**.

**P05.2b — Low-overhead/fast mode versus accepted diagnostic
mode (PHYSICAL ACCEPTED on KV260, 2026-10-12).** Run the **same** accepted
three-core/three-resident, threshold-4 spiking triangle and
15 input events on the **unchanged** P05 A53 ELF and FPGA PL.
Byte-exactly preserve all three initial core images and core/
input table; only mode flag changes 1→0 and 15 checkpoints
are removed. Require 15 dispatches, 12 packets, 12 direct
resident deliveries, 5 completed barriers, no checkpoints
and **three complete final DDR records equal to both**
independent Python golden and separately accepted diagnostic
KV260 SHA-256 results. Host builder/verifier/shell:
`scripts/p05_2_fast_fixture.py`,
`scripts/p05_2_fast_verify.py`,
`scripts/run_p05_2_fast.sh`;
native tests: `tests/test_p05_2_fast.py`;
procedure: `docs/P05_2_FAST_EQUIVALENCE_GATE.md`.
**Observed P05.2b PHYSICAL PASS:** User supplied
`verify.log` with `timesteps=5`, 15 FPGA dispatches,
12 packets, 12 resident deliveries, five barriers,
`checkpoints=0`, and all three **actual full DDR
record SHA256s byte-exact to both independent Python
oracle and previously accepted diagnostic KV260 records**.
Real P05G header CRC32 `0x76E6409B`, payload CRC32
`0x1AF530B0`; physical record SHA256s remain
`5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381`
(core0),
`2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2`
(core1),
`d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f`
(core2).
`pl_dispatch_cycles=357` and `ps_inference_ticks=25994`
are raw observations, **not a calibrated performance or
power/energy benchmark**. Acceptance:
`docs/P05_2B_FAST_ACCEPTANCE.md`.

**P05.2c — Legal logical-core service-order invariance
(PHYSICAL ACCEPTED on KV260, 2026-10-12).**
Same physically accepted diagnostic three-core triangle
on the unchanged P05 ELF and accepted FPGA.
Change actual A53 service order **`[0,1,2]` →
`[2,0,1]`**, while keeping all three cores resident,
all original neuroparameters and 15 input events,
five timesteps, 12 packets and 12 resident deliveries.
Recompute an independent Python LogicalChip oracle with
the new service order and require every per-core neural
state and all three *complete* model final DDR images
equal the baseline. Then verify 15 real board checkpoints
and byte-exact physical DDR equality to **both independent
models and the pinned accepted baseline physical SHA256s**.
Scripts: `scripts/p05_2_order_fixture.py`,
`scripts/p05_2_order_verify.py`,
`scripts/run_p05_2_order.sh`, native tests
`tests/test_p05_2_order.py`,
`docs/P05_2_ORDER_INVARIANCE_GATE.md`.
**Observed P05.2c PHYSICAL PASS:** User supplied independent
`verify.log` showing real A53 service order **[2,0,1]**,
15 dispatches, 12 packets, **12 resident deliveries**,
5 barriers and 15/15 actual golden neural checkpoints.
All **three complete 512KiB final DDR records** matched
both independently simulated Python service-order variants
and the previously accepted original-order KV260 SHA256s.
P05G header CRC32 `0x22ECC007`, payload CRC32
`0xC0AFC18C`. Acceptance record:
`docs/P05_2C_ORDER_ACCEPTANCE.md`.
This establishes physical invariance for **one legal
three-resident permutation only**, not all possible
virtualization/paging schedules.

**P05.2d — Two-route physical packet fanout / convergent
NEXT-bank event aggregation (PHYSICAL ACCEPTED 2026-10-12).**
Generate a **new** independent `LogicalChip` three-core
all-to-all-except-self topology where each firing
source emits **two distinct packets**, each destination
receives two routed next-timestep spikes plus one
external spike, without violating global barriers.
With five timesteps, weight 3 and threshold 4, the
independent model is expected to produce
**15 dispatches, 24 emitted packets and 24 direct
resident deliveries**, 15 actual-device state0
checkpoints, three initial page-ins/three final
page-outs and no replacement paging.
Require all three **complete** physical DDR records
byte-exact to a fresh fanout Python oracle.
Fixture `scripts/p05_2_fanout_fixture.py`,
strict verifier `scripts/p05_2_fanout_verify.py`,
physical provisioning `vivado/p05_2_fanout_prepare.tcl`,
two-mode runner `scripts/run_p05_2_fanout.sh`,
host negative tests `tests/test_p05_2_fanout.py`,
instructions `docs/P05_2_FANOUT_GATE.md`.
**Observed P05.2d PHYSICAL PASS:** User-supplied independent
KV260 `verify.log` confirms 15 dispatches,
**24 routed packets and 24 actual resident deliveries**,
5 barriers, 15/15 model-derived hardware state0 checks,
and three complete physical 512KiB final records byte-exact
to the new fanout LogicalChip golden. P05G header CRC32
`0xD6B1D9AC`, payload CRC32 `0x20423406`.
Reference Python trace SHA256:
`931ce506074695b567f97076b0b58bc65d796dd4c468e4d320a9e02b9182a759`.
Actual final physical SHA256s:
core0 `f545f5d7fa3d896ad2792ada1515f2db9676d80b7095ec8c8c817ca1d5e95da6`,
core1 `051d61da564a0d160265c620f384c7ede18c88f2551b146a6bdb556edb428a27`,
core2 `b806caf750a820b050a73f280d3ebdf08893b4d8b66a6a2d87ccdc77630807c4`.
Acceptance: `docs/P05_2D_FANOUT_ACCEPTANCE.md`.
**Fanout with 3 incoming events/core is not 4096-entry
event-bank saturation/backpressure coverage.**

**P05.2e — Composite multifeature physical regression
(PHYSICAL RECHECK PASS, user reported 2026-10-12; native-suite
reconfirmation outstanding).**
New fully model-derived **five logical cores over three
resident slots**, eight timesteps and actual service order
**[4,1,3,0,2]**. Every source has **two outgoing fanout
destinations** (core+1/core+2 mod 5), each with normal-range
heterogeneous thresholds **4,5,6,7,8** and weight 3.
Require 40 logical A53 dispatches, 40 ingress events,
40 real-device state0 barrier checks, five complete
byte-exact physical DDR records, and **both resident and
nonresident packet deliveries**, while stressing repeated
round-robin victim replacement and dirty page flush/reload
over eight barriers.
Golden neural states, packet vectors and entire five final
DDR images come from independently generated Python
`LogicalChip`. A second standalone Python replay of the
exact accepted C victim-pointer/dirty marking policy
computes page hits, evictions, full page-ins,
mutable-outs, packet residency at actual emission and
final page-command counts; the generator fails if it does
not cover 20+ real replacements/out and both routing paths.
The gate also audits expected **programmed payload bytes**
per physical page command (full-in `0x6B000`, mutable-out
`0x1A000`), **not calibrated AXI traffic or throughput**.
No software C, existing bitstream or accepted v2 oracle
source changed.
`scripts/p05_2_composite_fixture.py`,
`scripts/p05_2_composite_verify.py`,
`scripts/run_p05_2_composite.sh`,
`vivado/p05_2_composite_prepare.tcl`,
`tests/test_p05_2_composite.py`,
`docs/P05_2_COMPOSITE_GATE.md`.
**P05.2e originally failed** on full physical packet-RAM
comparison at core3 0x64000, although the standalone A53
terminal reported `0x600D600D`. The source-informed
physical packet-layout oracle was added in
`scripts/p05_2_packet_layout.py`, without changing the
normalized Loihi model, native FPGA routing or accepted A53.
**The user independently reran the non-destructive existing-
evidence check and reported `P05_2E_RECHECK_EXIT=0`.**
All five complete physical final 512KiB DDR records
matched the separately derived route-ordered reference;
the check also confirmed the original P05G, model, mailbox
and FPGA DDR dump evidence was unchanged.
Original failed evidence is retained; the new check's PASS
does not rewrite that history. Full reproduced output and
scope: `docs/P05_2E_RECHECK_ACCEPTANCE.md`. Native pytest
regression output remains to be confirmed independently.

**P05.2f — Combined signed-24 saturation, fractional/end-point
decay, negative weights, refractory and paging regression
(PHYSICAL ACCEPTED from user's independent KV260 results 2026-10-12).**
A single six-step five-logical-core / three-slot profile combines
+/- 24-bit saturation, +/- signed weights, decay 0/1024/2048/4096,
threshold/reset/refractory, packet routing, dirty victim paging
and 30 actual-device state0 barrier checkpoints. The unchanged
P05 A53 ELF and routed FPD128 shell were reused; **no new bitstream**.
The strict verifier checked all five complete 512 KiB raw DDR
contexts, encoded signed parameters, P05R counters and frozen model
SHA/CRC. The user independently reported:

```text
PASS: P05.2f physical five-over-three signed/decay/saturation/refractory steps=6 dispatches=30 packets=8 resident_deliveries=8 nonresident_deliveries=0 barriers=6 checkpoints=30 evictions=27
PASS: P05.2f five complete 512KiB physical DDR images byte-exact to independent signed 24-bit LogicalChip reference
P05_2F_VERIFY_EXIT=0
```

**Limit:** The eight real HLS packets all reached resident destinations;
P05.2f does NOT independently exercise nonresident routing. P05.2e
already covered 24 resident + 24 nonresident deliveries.
A native pytest summary and full local binary/evidence hashes were
not included in the user's P05.2f reply; these are not invented.
Original sources: `scripts/p05_2f_arithmetic_fixture.py`,
`scripts/p05_2f_arithmetic_verify.py`,
`scripts/run_p05_2f_arithmetic.sh`,
`vivado/p05_2f_arithmetic_prepare.tcl`,
`tests/test_p05_2f_arithmetic.py`.
Procedure: `docs/P05_2F_ARITHMETIC_GATE.md`.
Physical sign-off: `docs/P05_2F_ACCEPTANCE.md`.

**P05.2g — Exactly full 4096-event CURRENT-bank and
CRC-valid 4097-event device-rejection gates
(PHYSICAL ACCEPTED; independently user-verified on real KV260
2026-10-12/13).**
Two intentionally distinct, separate booted physical runs, on one
unchanged P05 A53 ELF and accepted P03 FPGA shell:

- **Physical FULL:** One logical core, one resident slot, one
  timestep, 4,096 registered external events, one HLS dispatch,
  one barrier, three barrier checkpoints (state0/event0/event1),
  one initial page-in, one final page-out, and a complete 512 KiB
  physical DDR record compared byte-exactly to a fresh model.
  The independent model predicts current=4096/voltage=4096 with
  no outgoing spikes or packets. This demonstrates the **maximum
  accepted CURRENT-event bank depth**, not routed congestion.
- **Physical OVERFLOW:** One additional valid axon event makes
  4,097, and the payload/header remain independently CRC-valid.
  The accepted P05 A53 must fail **before any dispatch/MMIO**
  with terminal 0xDEAD0002 / error=2, zero runtime activity,
  and an unchanged initial 512 KiB physical DDR context.
  A header/checksum error or unrelated terminal cannot PASS.
  The host builder independently rejects 4,097 before creating
  such a descriptor; the deliberately invalid CRC-valid
  descriptor is produced only for the physical admission test.
- **Portable C adapter:** Compile original `p03_hw_adapter.c`
  and directed `tests/p05_2g_route_guard.c` to demonstrate that
  a NEXT bank at 4,095 allows exactly one packet append and at
  4,096 rejects any further packet before DDR store/cache clean.
  This last gate is HOST-MOCKED, not physical packet pressure.

Sources:
`scripts/p05_2g_capacity_fixture.py`,
`scripts/p05_2g_capacity_verify.py`,
`scripts/run_p05_2g_capacity.sh`,
`vivado/p05_2g_capacity_prepare.tcl`,
`tests/test_p05_2g_capacity.py`,
`tests/p05_2g_route_guard.c`.
Full acceptance/reproduction plan:
`docs/P05_2G_CAPACITY_GATE.md`.
Independent original reported physical evidence:
`docs/P05_2G_ACCEPTANCE.md`.
**Observed P05.2g PHYSICAL PASS:** User supplied TWO separate
original KV260 `verify.log` results from
`/tmp/v3_p05_2g_capacity_20261013T004149Z`.
Full profile: 4,096 CURRENT-bank input spikes, 1 real HLS
dispatch, 1 barrier, 3 actual-device post-barrier checkpoints,
and complete original physical 512 KiB DDR byte-exact to
the independent model (`P05_2G_FULL_VERIFY_EXIT=0`).
CRC-valid 4,097-event profile: real A53 rejection
`0xDEAD0002` before any MMIO/dispatch/page/barrier with
unchanged complete original 512 KiB DDR context
(`P05_2G_OVERFLOW_VERIFY_EXIT=0`).
Host native suite passed independently per user, but a
full pytest count/log was not provided.

**P05.2h — Adversarial multi-bank/boundary and routing-barrier
stress (PHYSICAL ACCEPTED; independent user-verified real KV260
2026-10-13).** The new integration test deliberately
extends service time to **16 global timesteps** on five logical
cores / three physical context slots, retains real service
order [4,1,3,0,2], uses two outgoing fanout destinations per
spike and core-specific thresholds [2,3,4,5,6].
The independent `LogicalChip` produces all complete immutable
neural core DDR records and per-step model vectors; a separate
conservative P03 victim replay computes real paging and
resident/nonresident routing counters.

An **independently replayed double-event-bank oracle** computes
every post-barrier `event0` and `event1` first-word CRC,
alongside `state0` for **all five cores at all 16 barriers**,
plus actual `packet0` whenever emitted. This means **at least
240 live physical diagnostic checkpoints**, alongside
80 physical dispatches, 80 external stimuli, repeated dirty
evictions, both routing residency modes, and entire five
512 KiB physical DDR records byte-exact to a derived
output-route-ordered packet RAM reference. Crucially, the
original destination-sorted logical Python oracle remains
unchanged. The accepted P05 ELF and P03.2c bitstream are reused;
no hardware RTL, C or FPGA shell is modified.

Implemented:
`scripts/p05_2h_barrier_fixture.py`,
`scripts/p05_2h_barrier_verify.py`,
`scripts/run_p05_2h_barrier.sh`,
`vivado/p05_2h_barrier_prepare.tcl`,
`tests/test_p05_2h_barrier.py`.
Full native-first reproduction:
`docs/P05_2H_BARRIER_GATE.md`.
User-observed original physical proof:
`docs/P05_2H_ACCEPTANCE.md`:
```text
PASS: P05.2h physical adversarial 5-over-3 bank/barrier order steps=16 dispatches=80 packets=156 resident_deliveries=78 nonresident_deliveries=78 barriers=16 checkpoints=318 evictions=77
PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier
PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden
P05_2H_VERIFY_EXIT=0
```
This satisfies P05.2h's independently checked real
double-bank/barrier, routing and full physical DDR gate;
a numeric native pytest summary was not supplied alongside
this final physical result.

**P05.2i — FINAL Phase-5 read-only AXI transfer-counter
provenance and comprehensive physical closeout
(PHYSICAL ACCEPTED; user-verified real KV260
2026-10-13; `P05_2I_VERIFY_EXIT=0`).** Reuse exactly the accepted
five-logical-core / three-slot, 16-barrier P05.2h neural
profile in **one more standalone real KV260 execution**.
After the A53 finishes, capture twice (read-only) the live
FPGA page-AXI counter MMIO words at
`0xA4000044, 0xA4000048, 0xA400004C, 0xA4000050`.
Cross-verify the physical 128-bit AXI successful read/
write burst counters and successful-byte register against
(a) the original A53 `P05R` hardware-read counters,
(b) the independent P03 victim/page replay, (c) the
256-byte/16-beat physical AXI transport geometry,
and (d) the full repeated strict P05.2h neural, 318 CRC
checkpoint, 5 complete 512 KiB DDR goldens.

Frozen P05.2h page replay: 3 initial full-ins, 77
replacement full-ins, 77 dirty runtime mutable-outs,
and 3 final mutable-outs, so 80 × 0x6B000 full-in
bytes = 35,061,760 and 80 × 0x1A000 mutable-out
bytes = 8,519,680. Required **independently measured
PL HP0 AXI page counters**:
**136,960 completed 256-byte read bursts**, **33,280
completed write bursts**, **43,581,440 successful AXI
page bytes**. These are **PL page-engine** bytes only,
not total system traffic; no synthetic counter or
host-computed page payload alone is physical acceptance.
Require nonzero PL page cycle/PS generic-timer measurements
and zero pending/error status. No changes to accepted
ELF/C runtime/HLS/bitstream.

Implemented:
`scripts/p05_2i_axi_closeout.py`,
`scripts/run_p05_2i_axi_closeout.sh`,
`vivado/p05_2i_read_axi_counters.tcl`,
`tests/test_p05_2i_axi_closeout.py`.
Native-first reproduction and failure policy:
`docs/P05_2I_AXI_CLOSEOUT_GATE.md`.

**Final independently confirmed P05.2i physical PASS (2026-10-13).**
The first P05.2i trial completed all P05.2h neural
checkpoint and 5-DDR comparisons but hit the XSDB
debugger **software** memory-map restriction on
`0xA4000044` during unforced `mrd`. That first attempt
did not satisfy P05.2i. With the KV260 **not rebooted**,
the user ran the read-only `mrd -force` recovery on
the same physical A53/DDR evidence. The new read-only
actual FPGA AXI register witness matched the independent
A53 `P05R` and software page replay exactly.
The user supplied the following actual physical verifier
outcome (the underlying raw binaries remain on the
user's machine; don't pretend they are repository files):

```text
PASS: P05.2h physical adversarial 5-over-3 bank/barrier order steps=16 dispatches=80 packets=156 resident_deliveries=78 nonresident_deliveries=78 barriers=16 checkpoints=318 evictions=77
PASS: P05.2h both event-bank first words, state0 and emitted physical packet0 checkpointed at each barrier
PASS: P05.2h all five complete physical 512KiB DDR records byte-exact to model-derived route-ordered golden
PASS: P05.2i KV260 PL HP0 AXI successful 256-byte burst counters read=136960 write=33280 and direct read-only hardware bytes=43581440 exactly equal 80 complete full page-ins + 80 mutable-only page-outs
PASS: P05.2i independent A53 P05R page counters match halted-PL MMIO burst registers and directly measured page AXI byte register
PASS: P05.2i original 16-barrier/318-checkpoint neural and all five 512KiB physical DDR oracle preserved
P05_2I_VERIFY_EXIT=0
```

Reconstructed page transfers: 3 initial full page-ins,
77 replacement full-ins, 77 dirty runtime mutable-outs,
3 final mutable-outs. Successful 256-byte read bursts:
136,960; successful write bursts: 33,280;
directly read actual PL HP0 successful-transfer bytes:
43,581,440. These are **FPGA page-engine physical
AXI transfers**, not overall PS+PL memory traffic.
User-reported P05R SHA-256
`3de43163e98d3368ee1bf52afcdbdc4737840962f449850b842f4e1ab68f4cfb`,
counter-witness SHA-256
`51ea572f1cb83902d6d853da2fc1b657bcfc28371763201fad32de41cc7d01f9`.
Whole-DDR SHA-256s, timing and preserved investigative
history: `docs/P05_2I_ACCEPTANCE.md`.

**P05 closeout disposition: COMPLETE / ACCEPTED.**
Independent physical P05.1 deployment/route tests and
P05.2a–i directed architectural tests all satisfy their
documented acceptance gates. User expressly requested
closure and merge to `main`.
Consolidated record: `docs/P05_FINAL_ACCEPTANCE.md`.

**Scope limitations carried forward (not silently closed):**

- Native C routing guard covers 4095→4096 NEXT packet append
  and reject-on-full; **the physical HLS-originating 4097th
  routed NEXT-bank packet, stall/backpressure timing, and
  successful runtime overflow recovery were NOT exercised**.
  CRC-valid 4097-**deployment** rejection is different.
- The directly observed AXI byte count covers only
  successful PL page-engine HP0 transfers, **not**
  host provisioning/PS DDR stores/cache traffic, total
  platform DDR traffic or application throughput/energy.
- P05 raw board regression timer data are **not**
  P07 MNIST inference latency nor P08 calibrated
  energy/power results. One physical HLS engine,
  not P04 deferred multi-engine parallelism, was tested.
- Several historical physical PASS excerpts did not
  include full fresh native pytest totals or original
  uploaded binary identities. Do not invent them.

The completed P05 correctness/observability scope is
accepted with these documented exclusions. P04 remains
deferred; **P06 is next**. Preserve accepted P02/P03
binary/RTL/software reference evidence unchanged.

### Deliverables

- Execute the major architectural regression corpus **physically on
  KV260**: neuron arithmetic, spike packet encoding/routing,
  **direct-to-resident delivery (unexercised in P03: measured
  `resident_deliveries=0`)**, nonresident DDR delivery, fanout,
  event saturation and backpressure, page transfers/dirty eviction,
  repeated page replacement, barriers, and legal service-order
  invariance. For every test, define independently reproducible
  Python golden outputs and target coverage before running hardware.
- Capture/checkpoint complete or selected trace/state fingerprints
  at well-defined safe observation points, with the first incorrect
  core/timestep/state class reported on mismatch.
- Audit existing PS/PL counters for dispatches, page-ins/out,
  actual transferred DDR bytes, routed packets, barrier waiting,
  hardware PL cycles and PS generic-timer intervals. Implement
  additional PL instrumentation **only where existing MMIO and
  PS software cannot supply a reliable measure**, maintaining a
  known-good accepted P03 bitstream as fallback.
- Maintain evidence provenance (ELF, XSA, bitstream, source SHA,
  manifest, output/trace digest), reproducible scripts and
  explicit failure/reboot instructions. Compare results with
  Python as oracle, not as runtime orchestration.

### P05.2 acceptance

The major frozen v3 architectural regression corpus executes on the
KV260 with zero unresolved deviations from its independently
generated software oracle. Every supported physical feature has
documented directed coverage; unexercised features remain clearly
labelled. The full evidence package identifies the first failing
core/timestep/state class when hardware diverges. A fresh hardware
route, if required, is independently revalidated before adoption.

## Relationship to later phases

P05 measures correctness and coverage; P06 freezes the exact MNIST
benchmark, P07 runs it primarily on board, and P08 measures
latency/throughput/power/energy with distinct rigor. P05 does **not**
retroactively change P03's accepted source or golden evidence.

---

# P06 — Two-track LIF MNIST model, mapping and benchmark freeze

**Direction: APPROVED — sequential compact then scaled tracks.**
**Branch:** `agent/v3-p06-lif-feasibility` (forked from the
unmerged Rao `agent/v3-p06-benchmark-audit`; accepted P05
`main` and its evidence unchanged). **No official
MNIST test-set accuracy evaluated; no trained model yet.**

**Published foundation, not an original checkpoint claim:**
Eshraghian et al. (2023), *Training Spiking Neural Networks Using Lessons
From Deep Learning* (DOI `10.1109/JPROC.2023.3308088`),
and its snnTorch MNIST examples. The tutorial's actual
784→1000→10 model uses **floating-point**, 25-step
analog image input, subtract-reset `Leaky` and same-step
forward-layer processing. Our **project models** deliberately
use deterministic spike events, P03 integer hard-reset
LIF and P05 NEXT-bank routing. Both resulting
checkpoints, accuracy results and timing measurements
will be **project-specific**; no tutorial or original
Loihi number may be attributed to them.

**Mandatory execution sequence:**

`P06-A compact reference/training/freeze → P07-A
physical 1-core MNIST → P08-A accepted baseline →
P06-B scaled mapping/training/freeze → P07-B physical
virtualized network → P08-B scaling measurements →
P09 final comparison`.

Track B's *design* is recorded here now, but **Track A physical
accuracy and a measured performance/power baseline take
priority**. Track A may proceed to P07-A when its
own P06 freeze gate passes even while P06-B remains
scheduled for later. Track B cannot retroactively
change Track A's approved checkpoint, protocol or
physical acceptance.

### Track A — Small single-core 784→32→10

- **P06-A1 — Existing compiler/hardware-image structural
  feasibility [ACCEPTED — independent user native PASS,
  2026-10-12].** Actual
  `compile_network`→`export_one_core_image`
  with **synthetic**, non-trained integer weights:
  **42 compartments, 25,408 real packed synapses,
  816 axon bindings, 32 static routes, 108,160 bytes
  v3 logical synapse cost**. Native regressions
  `test_p06_lif_compiler_probe.py` and
  `test_p06_lif_input_probe.py` PASSED after
  the source-faithful 31-spike/310-next-step-fanin
  test correction. The input-event feasibility
  and NEXT-barrier golden test passed.
  **Not trained; not a KV260 physical inference pass.**
- **P06-A2 — Integer-equivalent forward and
  input/readout protocol [CLOSED / USER-ACCEPTED 2026-10-13].**
  Independent signed-24-bit P03 LIF oracle
  covering exact decay rounding, threshold,
  saturation, signed weights, reset, refractory,
  25 event steps + 1 NEXT-bank drain, per-image
  zeroing, and 10-spike-count readout. Pin
  deterministic uint8 pixel→event encoder
  and parity against existing `LogicalChip`
  and packed P03 bank, including overflow/
  threshold/no-spike negative tests. Prove
  training-forward *inference* equivalence
  to the integer oracle, not just approximate
  float `snn.Leaky` behavior.
  A2.1 user attested native pytest PASS and supplied both 32-hidden
  and original-size compiler-probe PASS exits on 2026-10-13;
  see `docs/P06_A2_1_INTEGER_ORACLE_GATE.md`.
  The new independent event contract, complete 26-step dense SNN
  oracle and self-decoded packed-image replay are committed in
  A2.2–A2.4. Their 49-test mirrored local sanity gate passed;
  the user subsequently confirmed the A2.2–A2.4 native gate looked
  good (detailed pytest log not supplied). See
  `docs/P06_A2_2_TO_4_NATIVE_GATE.md`.
  A2.5 now provides integer-exact forward/STE surrogate gradients,
  signed24 fail-closed weight export and compiler-mapping adapter,
  with 7 PyTorch forward unit tests and 2 *native-only* export tests.
  The user explicitly confirmed verification of the A2.5 tests and
  authorized closing P06-A2 on 2026-10-13. The detailed native
  pytest counts/log were not pasted, so this is recorded as
  user-attested acceptance (not assistant-executed native testing).
  See `docs/P06_A2_5_TRAINING_FORWARD_GATE.md`. P06-A2 is
  CLOSED at the host-software numerical/training-forward boundary;
  it establishes no P07 hardware or MNIST-trained accuracy.
  No P05/HLS changes or physical MNIST.
- **P06-A3 — Train and validation-select
  a compact checkpoint [CLOSED / USER-ACCEPTED SOURCE-GO 2026-10-17;
  94.39% HELD-OUT VALIDATION / OFFICIAL TEST SEALED].**
  Canonical MNIST dataset/split/hashes,
  reproducible train/validation-only
  optimization, training seed/versions,
  source weights, legal integer weight/
  bias/decay/threshold quantization and
  a predeclared validation-only GO/NO-GO
  criterion. No sealed official MNIST
  test peeking and no borrowing paper
  accuracy/weights.
  A3.1 canonical TRAIN-only archive checksums/50k-10k seeded split,
  A3.2 exact integer-forward surrogate training and validation-only
  best-epoch selection, and A3.3 candidate checkpoint manifest and
  integrity checks are committed. The **60% validation GO/NO-GO
  floor was declared before real dataset results**. The user has now
  supplied a first 8-epoch full 50k/10k training manifest with best
  validation accuracy 0.9439, best epoch 8, GO=True, 2/10,000 silent,
  and intact split provenance. The later native A4.1 PASS necessarily
  executed the A3 load_candidate() file SHA256 check, state_dict reload,
  exported-integer-weight digest and frozen-source guard; thus the
  accepted A4.1 software run also established host checkpoint reload
  integrity (separate --validate-candidate marker not pasted).
  User on 2026-10-13 confirmed native pytest PASS and supplied
  `P06_A3_SYNTHETIC_SMOKE_PASS=1`, TRAIN-only archive MD5 and SHA256,
  `P06_A3_DATA_PREFLIGHT_PASS=1`, split seed/size and ordered-index
  hashes. Source identity and train/validation split verification:
  ACCEPTED. Synthetic smoke validation was 12/12 ALL SILENT,
  0.33333 accuracy and ln(10) cross entropy; this is computational
  success only, NOT learning evidence. A3.4 now implements a bounded
  256 TRAIN/128 validation, 2-epoch, no-checkpoint activity pilot with
  gradient, actual quantized-weight-change and output-spike diagnostics.
  The user reported native pytest PASS and supplied A3.4's canonical
  pilot output on 2026-10-15: PASS, no diagnostic reasons, 14,816 and
  320 nonzero layer gradient elements, 4,864 and 105 changed integer
  weights. Pilot baseline 128-image validation 10.16%, final 21.09%,
  but 77/128 (60.16%) final all-silent and class-0 tie bias.
  This is MECHANICAL ACTIVITY acceptance, not an accuracy guarantee.
  The user completed that predeclared eight-epoch full-data experiment:
  epoch 8 was best, train accuracy 0.9534, held-out validation 0.9439
  on 10k images, and 0.0002 silent fraction. The 60% validation
  floor is EXCEEDED by 34.39 percentage points; official test sealed.
  Saved weight-file SHA256 0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88
  and exported integer weights SHA256 1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b.
  A3 conclusion: user-attested validation GO plus native A4.1
  checkpoint-integrity prerequisite passed; A3 is CLOSED.
  Official test still SEALED; no physical accuracy claim.
  See `docs/P06_A4_FINAL_CLOSEOUT.md`.
- **P06-A4 — Freeze trained packed
  benchmark and reproducibility [CLOSED / USER-ACCEPTED 2026-10-17:
  TRAINED P03 SOFTWARE FREEZE + P02 512KiB STATIC DDR NATIVE PASS].**
  Exact real-weight compiler/exporter
  bank/resource gates, independent
  first-divergence software traces,
  model/weight SHA256 and parameter
  contract, decoder/readout/state-reset,
  26-step inference, model/data
  provenance and official-test/physical
  measurement boundaries recorded
  *before* P07-A. Explicit P06-A4
  native acceptance. This is the
  **Track A P06 exit**; P07-A may
  start without waiting for Track B.
  A4.1 now pins the accepted candidate byte hash, signed24-weight
  hash and canonical training split; compiles actual weights through
  original P06 one-core compiler and P03 word exporter; compares
  26-step PyTorch/dense/packed/LogicalChip traces on synthetic and
  fixed validation frames. Emits explicitly little-endian P03
  logical word streams plus SHA256 manifests only after parity passes.
  The user reported native P06_A4_SOFTWARE_SNAPSHOT_PASS=1 and exact
  five-frame, 26-tick, four-engine parity on the trained weights;
  that A4.1 software freeze is now ACCEPTED. All six resulting P03
  word-stream lengths and SHA256 were supplied and are pinned in
  `docs/P06_TRACK_A_SOFTWARE_BENCHMARK_FREEZE.json`.
  A4.2 audits those bytes against the user's snapshot and constructs
  the EXISTING P02.1 complete 524288-byte `LTV3CTX1` static DDR
  initial core record, checking all dense/sparse banks and header
  digest. User explicitly reported native A4.2 DDR validation PASS
  on 2026-10-17. The produced full-file SHA256 was not pasted,
  so its source-frozen metadata remains null; capture it from the
  pre-existing local artifact before P07 load, never fabricate it.
  See `docs/P06_A4_FINAL_CLOSEOUT.md` and
  `docs/P06_TRACK_A_OFFICIAL_TEST_PROTOCOL.md`.
  The P02 static record is NOT the old P05 diagnostic payload or
  a P07 A53 784-input event streamer. No board inference.

### Track B — Larger DDR-virtualized 784→1000→10

**Research target, not frozen or mapped:**
**794,000** possible dense synapses;
approximately **26 destination-partitioned
hidden logical cores plus 1 readout core** is
only a **~27-core planning hypothesis**,
not compiler acceptance or a guaranteed
optimal partition. At 27 full 512 KiB DDR
records, backing usage is **13.5 MiB**;
up to 126 logical core IDs are addressable
by the accepted P05 A53 diagnostic deployment
map, with **3 resident FPGA contexts
and 1 physical HLS compute engine**.
Important limitations are per-core 128 KiB
**logical** template/axon/synapse accounting,
32,768 physical synapse words, the input fanout
of up to 784 ports to roughly 26 destinations,
the old P05 ABI's **one valid external axon
per core**, the **896 KiB** diagnostic payload
bound, routing/buffering/barriers and DDR
page traffic. A new model/packet streaming
deployment ABI and **synapse-aware
destination partitioner** will be required.
Simply increasing `max_logical_cores`
in the present `compile_network` will
**NOT** partition by synapse pressure.

- **P06-B1 — Prove scalable packing and
  route semantics [NEXT — P08-A LATENCY-ONLY GATE SATISFIED; NOT YET IMPLEMENTED].**
  Deterministic synapse-aware partitioner;
  fail-closed axon/synapse/route/event
  budgets per logical core and exact
  512 KiB per-core images. Compare
  a partitioned integer oracle vs an
  independent monolithic reference,
  source input event replication, packet
  arrival at the correct NEXT epoch,
  scheduling invariance, page-traffic
  and estimated throughput. Model
  a worst-case all-255 timestep
  without overflowing per-core banks.
- **P06-B2 — Train, quantize and freeze
  independent larger checkpoint [PENDING
  INDEPENDENT ACCEPTANCE OF P06-B1].** Keep the same
  deterministic 25+1-step event/input,
  neuron/readout and dataset split;
  train a new project large-model
  checkpoint on train/validation ONLY.
  Freeze its own tensor SHAs, mapping,
  independent parity traces, per-core
  occupancy and a predeclared official
  test protocol. If the full 1000-hidden
  topology is infeasible, declare
  and evaluate a transparent intermediate
  model *before* accessing test results;
  do not silently relabel the model.

**Track B P06 exit:** a separately
audited, real trained *project*
checkpoint mapped with real 128 KiB/
32,768-entry bounds and independently
verified event/packet/state semantics.
No scaled KV260 claims until P07-B.
**Track A P07/P08-A latency-only acceptance gate is now satisfied.** Proceed with P06-B1 on a **new branch**, independently validating a deterministic synapse-aware partitioner before P06-B2 training. Leave all accepted Track A source/artifacts frozen.

### Archived alternate source audit

The earlier Rao et al. Loihi AHP-LSNN
investigation remains intact in
`docs/P06_1_PAPER_CANDIDATE_AUDIT.md`,
`docs/P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md`
and its exact Intel manifest. It was
**not selected**, because original paper
accuracy-to-released-checkpoint linkage
was unresolved and AHP hardware would
require a different neuron contract.
The corrected Rao original-binary
nine-file native audit remains **not
independently accepted** and is no
longer a blocker for these two LIF
tracks. NxTF remains excluded.

### P06 acceptance policy

- Distinguish **published LIF methodology**,
  **project-trained model**,
  **source-level integer oracle**,
  **compiler/HLS image structural acceptance**,
  **actual KV260 inference** and
  **measured FPGA performance**; none
  implies the next.
- Preserve P05/HLS acceptance goldens; P06
  changes require independent regressions.
- Freeze each track's model and official-test
  protocol before evaluating the sealed test
  set; model A and B have **different
  project-trained checkpoints**, so
  differences in accuracy are not pure
  hardware efficiency comparisons.
- Proceed in the A→B order stated above.
  **P06 Track A (A1–A4) is CLOSED / USER-ACCEPTED 2026-10-17.**
  A4.2 completed the static P02.1 512KiB DDR record native audit.
  Exact DDR full-file SHA256 still needs provenance capture from
  the user's existing local binary; this does not reopen the
  accepted numerical/byte-layout gate. Official test remains
  sealed. P07 physical MNIST inference and P08 physical metrics
  have not been demonstrated.

**Detailed execution/resource contract:**
`docs/P06_TWO_TRACK_LIF_PLAN.md`.
See also `docs/P06_LIF_FEASIBILITY.md`,
`docs/P06_LIF_NATIVE_GATE.md`, and
`docs/P06_LIF_CANDIDATE_PROFILE.json`.

---

# P07 — Board-local classifier evaluation: compact first, scaled second

**Status (2026-10-17): P07-A COMPLETE / USER PHYSICAL
ACCEPTED AND VERIFIED. P07-B PLANNED (P08-A gated).**
P07-A establishes the frozen compact Track A
784→32→10, 816 registered input axons, 42 compartments,
25 input + 1 drain timesteps, A53-orchestrated physical
FPGA inference and exact independent packed P03 numerical
verification. **Official canonical MNIST TEST accuracy:
9456/10000 = 94.56%; 544 incorrect; 2 all-silent
included in the denominator.** These are original-order
canonical TEST results from the **actual KV260 FPGA**,
not TRAIN validation, simulation-only parity, a competing
Intel Loihi chip or a power/throughput measurement.
Complete immutable user-submitted terminal marker
transcripts, paths, hardware identifiers and scope:
`docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.

## P07-A engineering and physical acceptance milestones

**A1 — COMPLETE:** accepted pixel-to-axon ingress
wire contract, original 784 distinct pixel axons,
26-tick event-input reconstruction and independently
checked Python/C neural transaction representation.
No change to the frozen P06 Track A checkpoint.

**A2 — COMPLETE:** accepted C11 standalone A53
FPGA inference runtime, verified against independent
packed P03 reference and physically accepted
FPD128 routed KV260 fabric. The historical
16-image JTAG-batch implementation required 625
separate launches for the originally precommitted
canonical full 10,000 TEST population.

**A3.1/A3.2/A3.3 — COMPLETE:** TRAIN-derived
validation and physical equivalence, accepted
original eight 16-image PRIMARY A53 runs and two
independent old-format repeats; **116/128 correct
(90.625%) diagnostic TRAIN-derived validation**,
zero silent. The 16-image A3.2 overlap is part of
the same 128, not additional unique validation
images. Frozen original A3.3 hardware records
were retained for the later A4 physical-to-
physical equivalence check.

**A4.1 — COMPLETE / PRECOMMITTED BEFORE UNSEAL:**
exact **10,000 canonical official TEST images**
in original IDX order, frozen compressed official
archive MD5/IDX identity, all-image 10000
denominator, trained checkpoint/encoder, numerical
policy, tie/silence rule, source validation and
whole-population scoring. No retuning, post hoc
selection or reduced denominator permitted.
See `docs/P07_A4_OFFICIAL_TEST_PROTOCOL_FREEZE.md`.

**A4.2a/b — COMPLETE:** user-accepted persistent
DDR transport (`P07A4P01` descriptor,
up to 10000 ×784B raw images,
`P07A4R01` 1MiB CRC journal, one selected
64KiB trace), Python+C native parity,
standalone Cortex-A53 Vitis build, exact
accepted ELF SHA256
`dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb`,
XSA SHA256
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`,
and frozen immutable master DDR SHA256
`9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`.
The original accepted A53 A2 application, P03 neural
arithmetic and trained checkpoint were not rebuilt
or modified for this persistent execution.

**A4.2c — COMPLETE / PHYSICAL KV260:** accepted one
synthetic 16-image ramp pilot with exact physical
26×10 output and selected full trace; accepted
persistent TRAIN-derived 128-image PRIMARY
with byte-exact comparison to eight original A3.3
physical primary mailboxes; accepted independent
cold reboot 128-image repeat with byte-identical
full 1MiB journal and 64KiB selected frame0
26×42 trace; accepted one-launch **1024 distinct
TRAIN-derived validation images** with a full
last-image (frame1023) compartment trace,
then independent reboot repeat: **2/2 launches,
2048 physical frame executions across 1024 unique
validation images**, full journal 1MiB and
selected trace 64KiB byte-identical.
See `docs/P07_A4_2C_VAL128_RESTART_ACCEPTANCE.md`,
`docs/P07_A4_2C_VAL1024_RESTART_ACCEPTANCE.md`.

**A4.2c FINAL FAIL-CLOSED PHYSICAL GATE — ACCEPTED
2026-10-17:** original six DDR staging readbacks
exact on **synthetic ramp16 only**, then deliberately
change exactly one reserved descriptor 32-bit word at
`0x43FE0090` after provision and BEFORE A53
dispatch. The unchanged accepted ELF returned
`0xDEAD0001`, **zero completed image frames**,
**zero result body bytes and zero selected trace**;
independent original mutation/provision, journal CRC
and terminal failure evidence verifier passed.
`P07_A4_2C_PHYSICAL_FAIL_CLOSED_GATE_PASS=1`,
`P07_A4_2C_NEGATIVE_TEST_PASS=1`.
Original physical evidence:
`/tmp/v3_p07_a4_fail_closed_20261017T204554`
on user's PC. This is expected intentional rejection,
**not an inference success**.
See `docs/P07_A4_2C_FAIL_CLOSED_PROTOCOL.md`.

**A4.3 — COMPLETE / CANONICAL OFFICIAL TEST UNSEALED
AFTER A4.2c FAULT ACCEPTANCE:** the independently
accepted physical fault record and explicit
`--i-accept-unseal` +
`--i-accept-one-trace-policy` gates preceded
official t10k source staging. Canonical MNIST
TEST original full index range **0..9999**
was checked against MD5/IDX archive provenance
and host-only label ledger; data were not filtered,
sorted, sampled or retrained after test unseal.
No official TEST results were viewed during
pre-unseal native synthetic development.

**A4.4 — COMPLETE / FINAL OFFICIAL CANONICAL
KV260 FPGA FULL 10K PHYSICAL RUN ACCEPTED 2026-10-17:**
one autonomous persistent A53 ELF launch processed all
**10000/10000** raw test images in original IDX order.
The accepted independent closeout gate verified all
10000 CRC-protected physical result records, every
image's full **26×10 output spike-bit history**
(**2,600,000 output bits**), class counts,
silence, next-routing/discarded and external
input events against frozen packed P03 software
oracle, all original six DDR staging readbacks
and exactly one full last-image (IDX 9999)
**26×42 compartment** trace; all exact.
Success marker:
`P07_A4_4_FULL10000_KV260_INDEPENDENT_CLOSEOUT_PASS=1`
and physical terminal `0x600D600D`.
**9456 correct / 10000 = 94.56% accuracy;
544 incorrect; 2 silent / 10000.**
Original physical journal, selected trace
and complete host-only per-image score/provenance
JSON on user's PC:
`/tmp/v3_p07_a4_official_full10000_20261017T204944`;
report:
`p07_a4_4_official_full10000_report.json`.
Only the printed console PASS markers, not actual
raw binary/report per-class contents, were provided
to the assistant. See the separately frozen
`docs/P07_A4_3_4_FINAL_CANONICAL_TEST_PLAN.md`
and final physical acceptance
`docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.

**P07-A PUBLISHED-CLAIM BOUNDARY:** there is only
**one** selected full 26×42 compartment trace
for original official image 9999, unlike the
historical 625 A2 batch-selected traces;
all 10000 complete 26×10 *output* spike histories
and route/count summaries were preserved and
checked. Actual KV260 end-to-end timing,
PS overhead, throughput, rail/board power and
energy remain **P08-A**, and scaled multi-logical
core FPGA physical inference remains **P07-B**
after the P08-A gate. This is a single-core
Loihi-1-*inspired* digital twin, not physical
asynchronous circuitry or Intel Loihi silicon.
No claim of official 10000-image cold reboot
repeatability is made; only TRAIN-derived
128/1024 independent reboot repeatability
is established. Preserve all source/physical
evidence and stable artifact identifiers.

**Next:** P08-A compact physical baseline (required
before Track B scaling), followed by P07-B if
accepted. P07-A feature branch is to be merged
into `main` only with explicit user authorization,
which has been provided after the final hardware
experiments. Merging does not retroactively
validate P08/P07-B results.

## P07-A — One-core proof of useful physical MNIST inference

**STATUS: CLOSED / USER PHYSICALLY ACCEPTED
2026-10-17.** All A1/A2/A3/A4.1–A4.4 entry and
hardware numerical acceptance gates passed; final
full original-order canonical TEST classification
result **9456/10000 (94.56%)**, 2 all-silent.
See `docs/P07_A_FINAL_PHYSICAL_ACCEPTANCE.md`.

Using frozen Track A 784→32→10 weights and event input,
extend (not replace) the accepted A53 P05 diagnostic path
to support **many different external axon IDs per timestep**
instead of its current one registered valid axon/core,
image streams and autonomous per-image state/packet/
readout reset. Execute the exact 25+1-step protocol and
produce independent FPGA predictions from real 10-output
spike counts. Verify full-model compiler/runtime
fingerprints, image provenance, first-mismatch
timestep/current/voltage/packet traces and independent
golden predictions. Run the sealed official test
population only after the model/accuracy protocol
is frozen; if the full 10,000-image test isn't feasible,
predeclare the reduced test scope **before**
reviewing test predictions.

**Gate:** useful trained model actually
running inference on the **physical PL** under
autonomous A53 scheduling, not a simulated
test that only checks packed memory.

## P07-B — Scaled multi-logical-core physical inference

After P08-A, independently validate the scaled
frozen P06-B checkpoint across P05's same
one physical engine and three resident slots,
the additional DDR logical contexts, routed
input fanout, NEXT-event-bank packets and
barrier scheduling. Accept a bounded
physical multi-core trace corpus first,
then sealed official-test inference
if hardware time/storage permits.
Do not claim a 27-core demonstration
until physical independent evidence
confirms **all** cores, per-core full
DDR images, page swaps and predictions.

**Always distinguish Track A and Track B
accuracy and checkpoints.**

---

# P08 — Independent physical baseline and scaling measurements

**Status:** **P08-A LATENCY-ONLY ACCEPTED BY USER (POWER/ENERGY P08-A4 DEFERRED).** This satisfies the user-approved entry gate to **P06-B1 SCALED PACKING FIRST**, then P06-B2 separate checkpoint, P07-B physical virtualization and P08-B scaled measurements. **P08-B NOT YET STARTED.**

## P08-A — Compact physical KV260 latency baseline

**Status (2026-10-18 project timeline): P08-A LATENCY-ONLY COMPLETION EXPLICITLY ACCEPTED BY USER; MERGE OF PR #45 TO `main` AUTHORIZED. A3 SIX ORIGINAL KV260 PHYSICAL SESSIONS NUMERICALLY VERIFIED BY USER (A2.1 MEDIANS 35.7023 / 35.6946 / 35.6696 ms; A2.2 35.7234 / 35.7163 / 35.7220 ms; PAIR MEDIAN DELTAS +16.840 / +25.400 / +29.710 µs; MEAN +23.984 µs / SD 6.551 µs). A5 P07-PARITY-GATED CPU PRELOADED RUN MEDIANS 25.6147 / 25.6001 / 25.5735 ms, RAW784→CLASS MEDIANS 30.3930 / 30.3147 / 30.2579 ms, CPU/PHYSICAL REPORT SOURCE HASH MATCH USER VERIFIED. P08-A4 POWER/ENERGY DEFERRED/UNMEASURED. CPU/FPGA ENDPOINTS NON-EQUIVALENT; NO PURE PL SPEEDUP OR VERIFIED PL HZ. CORRECTED A5 FINAL PYTEST SUMMARY NOT POSTED; MERGE OUTCOME VERIFIED SEPARATELY FROM GITHUB.** P07-A accepted accuracy and physical numerical parity remain frozen; **do not rerun official MNIST TEST** for this experiment.

| Gate | State | Authoritative reference |
| --- | --- | --- |
| P08-A1 measurement boundary audit | User approved latency-first direction; deferred power/energy | [Measurement contract](docs/P08_A1_MEASUREMENT_CONTRACT.md) |
| P08-A2.1 per-image A53 timing source | Original frozen A2.1 ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`; **KV260 FIRST1024 PAIRED PHYSICAL RUN SUCCESS (USER ATTESTED)** | [Image timing method](docs/P08_A2_1_LATENCY_SIDECAR.md) |
| P08-A2.2 per-tick seven-boundary timing source | User reports regressions and Vitis build PASS after false-positive regression fix; **ELF SHA256 attested** `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`; **KV260 EXECUTED as A3.1 16-image pilot AND A3.2.2 first1024 paired session (USER ATTESTED)** | [Per-tick timing method and sources](docs/P08_A2_2_TIMING_METHODS.md) |
| **P08-A3.1 physical 16-image validation pilot** | **PHYSICAL FUNCTIONAL GATE PASS (USER-ATTESTED 2026-10-18)**: first 16 distinct TRAIN-derived validation images, 26×10 output flags per image and selected 26×42 full trace exact to independent oracle; A2.1 image and A2.2 per-tick timing sidecar terminal/CRC/clock/route consistency PASS. **User-supplied numerical pilot: median 35.4432 ms (31.2682–41.2175 ms), CNTFRQ_EL0 99,999,001 Hz; 1,024-frame repeated baseline NOT RUN.** [Exact pilot numbers](docs/P08_A3_1_PHYSICAL_LATENCY_RESULTS.md) and [physical acceptance](docs/P08_A3_1_PHYSICAL_ACCEPTANCE.md) | [Pilot protocol](docs/P08_A3_1_PHYSICAL_PILOT_PROTOCOL.md) |
| **P08-A3.2 repeated latency characterization** | **USER-ATTESTED PHYSICAL THREE-PAIR COMPLETE:** paired median A2.2−A2.1 full A53 image service +16.840, +25.400, +29.710 µs (mean +23.984 µs, n=3 run pairs); within-image median delta range 24.730 µs, p95 range 73.541 µs. P07 original packed neural oracle + tick/image timing integrity PASS on each accepted pair; original 1,024 TRAIN-derived validation sample identities unchanged; 1,023 ordinary frames analyzed each run. **Aggregate source JSON/report hash not independently file-sealed here; PL achieved Hz not independently calibrated; no pure PL speed or CI claim.** | [Complete six-run results](docs/P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md), [repeated protocol](docs/P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md) |
| P08-A4 power and energy | **DEFERRED**; no sensor selection or power measurements authorized | Future explicit user decision |
| **P08-A5 CPU software reference and final closeout** | **HOST BENCHMARK/DUAL NUMERICAL PROOF/FINAL REVIEW REPORT USER-ATTESTED PASS; LATENCY-ONLY FINAL APPROVAL PENDING.** Original frozen packed 26-tick preloaded CPU scalar per-run medians **25.6147 / 25.6001 / 25.5735 ms**; original raw784 encoder→class medians **30.3930 / 30.3147 / 30.2579 ms**; three sequential PC passes across the same 1024 canonical TRAIN validation images; original full 1024 P07 physical-neural/original-oracle and full-26-tick parity PASS. Stage descriptor/pixel/manifest SHA256 and accepted A2.1 physical run bound to six-session KV260 results PASS. Generated report, source hashes, p95/stdev and CPU environment posted and reviewed. **Not an isolated PL acceleration claim, not optimized native C, CPU/board scopes differ; achieved PL frequency uncalibrated.** Corrected A5 final native pytest summary not pasted (not falsely claimed PASS); user **EXPLICITLY ACCEPTED LATENCY-ONLY P08-A AND AUTHORIZED PR #45 MERGE**. Actual GitHub merge outcome tracked separately. | [Measured A5 CPU/FPGA results and SHA256s](docs/P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md), [P08-A FINAL ACCEPTANCE CANDIDATE — signature/merge stop gate](docs/P08_A_LATENCY_ONLY_FINAL_ACCEPTANCE_CANDIDATE.md), [A5 protocol](docs/P08_A5_CPU_REFERENCE_PROTOCOL.md) |

For the active Track A **physical latency** study, collect actual A53 per-frame (26-tick) service intervals, event encoding/bank-write/dispatch/trace/route/barrier intervals, hardware PL dispatch and page counters with **separate clock domains**, and CPU comparison endpoints. Host JTAG polls, HLS clock estimates and simulator cycles are not board latency data. Report benchmark overhead and selected full-trace perturbation explicitly.

**Entry gate to scaled Track B:** accept original P07-A frozen accuracy plus a genuine **physical, independently numerically verified P08-A latency baseline** before implementing B hardware. Power/energy are *not* an active prerequisite during this user-approved deferral; do not silently resume them or claim measured Loihi efficiency.

## P08-B — Scaled physical resource/traffic/energy study

Repeat the same measurement method for the
frozen scaled model. In addition, record
logical core count, 3 resident slots,
actual HLS dispatches, per-core paging
hits/misses/evictions, bytes moved, routed
packet fanout/barrier time, event-bank
occupancy and resource mapping across
all cores; compare these against P08-A.

Report *two different model sizes and
checkpoints*: improvements in classification
accuracy and costs from model scaling
are not pure FPGA architecture speedups.
Avoid claiming direct Intel Loihi
power/latency comparisons where workload
or scope differs. An extra physical
engine is a **deferred, optional**
optimization only after one-engine
baseline and scaled bottlenecks are measured.

---

# P09 — Thesis comparison and closure

**Status:** PLANNED.

First close the complete **Track A evidence
chain** (published-method scope, independently
trained/frozen exact checkpoint, source oracle,
P03 HLS image, board-local physical predictions,
official-test accuracy, power/energy, and
measurement provenance). **If Track B is not
successful**, this result must remain a fully
valid standalone thesis contribution.

If Track B passes P06-B/P07-B/P08-B,
add its **separate** reproducible
checkpoint, accuracy and physical data,
plus a measured compact-vs-scaled comparison:
model capacity, classification accuracy,
contexts, paging, routed event traffic,
true complete-sample latency, throughput
and total/dynamic energy.

**No hidden claim inflation:** project-trained
snnTorch-method checkpoints are not
released author pretrained weights;
static-analog input is not our
deterministic event encoder; hardware
P03 integer reset is not snnTorch
subtract-reset; a faster/smaller
model is not a pure architecture
comparison to a different model;
Loihi-1 transistor/native SRAM/NoC
or published chip-level energy
equivalence is not established.

Close only with immutable commit,
checkpoint/data/bitstream/ELF
fingerprints, independent regressions,
physical first-mismatch and board
performance evidence, and explicit
unknowns/non-comparable claims.

---

## Deferred/future directions

- multi-engine physical execution pending single-engine latency characterization;

These are intentionally not prerequisites for the initial v3 roadmap unless later evidence makes them necessary:

- full PL-owned scheduling instead of PS-owned orchestration;
- on-FPGA/on-chip learning;
- Loihi 2 architectural targeting;
- real-time sensor/event input;
- multi-board scaling;
- physically asynchronous FPGA circuitry.
