# P03 PS application — Cortex-A53 autonomous Loihi-like execution

**Status:** Functional P03 accepted from independent KV260 physical gates on 2026-10-12.  
**Scope:** A board-local standalone A53 application controlling **one** existing HLS neuron engine, **three** physical context slots, and the frozen **five-core** P02 ring workload for **7** or **100** algorithmic timesteps.  
**Entry point:** `software/p03/p03_finish_run.c::main()`.  
**Built executable:** `p03_finish_run.elf` (the **V2** source-identification build: `P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V2`).  
**Acceptance:** `docs/P03_4_ACCEPTANCE.md`, `docs/P03_5_ACCEPTANCE.md`, `docs/P03_FINAL_ACCEPTANCE.md`.

> **Interpretation of autonomous:** The PC prepares DDR and starts the A53 once; thereafter **all algorithmic** core selection, eviction, FPGA dispatch, packet routing, quiescence checks, event-bank swaps, and timestep advancement take place on the A53. The PC/JTAG remains involved only in provisioning, the *initial* ELF launch, passive terminal-mailbox polling, and final memory retrieval. This is not an always-on Linux service, a completely untethered boot product, or concurrent execution of five cores.

## 1. Hardware and control/data-plane partition

```text
Developer PC / JTAG  [provision once, load ELF once, passive poll, final dump]
       |
       v
KV260 Zynq UltraScale+ PS — standalone application on Cortex-A53 #0
  p03_finish_run.c
    |-- versioned launch config, DDR integrity checks, input stimulus
    |-- p03_runtime.c: ordered five-core scheduler, paging decisions,
    |                  packet/barrier bookkeeping, timestep progression
    |-- p03_hw_runtime_bridge.c: runtime -> hardware callback binding
    |-- p03_hw_adapter.c: AXI-Lite commands, resident debug access,
    |                       HLS packet validation, DDR/nonresident route
    |-- p03_hw_xilinx_io.c: Xil_In32/Xil_Out32, DCache maintenance, dsb sy
    |
    | PS M_AXI_HPM0_FPD 128-bit AXI4 -> SmartConnect 128:32 conversion
    v
PL 32-bit AXI4-Lite control at 0xA4000000 [P03.2c accepted]
    |-- select resident slot, event bank, page base and logical metadata
    |-- launch/page status, completion, packet count, cycle counters
    v
PL one HLS inference engine, three URAM resident context slots
    |
    | AXI HP0 full or mutable page transfer
    v
K26 DDR authoritative context records, 5 x 512 KiB (P02 ABI)
```

The physical MMIO ID is `0x4C543302` and accepted capabilities
`0x0001031F`. These are checked, not assumed. The original physical
bring-up failed because the *booted* FPD HPM0 master width was
**128 bits** while an earlier routed design expected 32; the
accepted shell inserts a SmartConnect AXI4-to-AXI4-Lite bridge so
software still uses the unchanged **32-bit register ABI**.
`p03_hw_xilinx_fpd128_ready()` reads the PS FPD width selector
before MMIO work; mismatched boot firmware fails closed. The
accepted P02 HP0/DDR page transport is retained independently of
the CPU's AXI-Lite control path. The routed shell intentionally
retains ILA/VIO diagnostic observation during P03.

This is **sequential time multiplexing**: only one logical core
dispatches to the FPGA engine at a time. It is not five parallel
HLS engines, not a hard real-time event-driven fabric, and not a
claim about Loihi's asynchronous communication implementation.

## 2. Ownership by source file

| File | Responsibility |
|---|---|
| `software/p03/p03_finish_run.c` | Standalone A53 entry point; fixed address window; launcher validation; physical record CRCs; input callback; run/diagnostic mailbox; extra dirty-slot final page-outs; PS counter timestamps; terminal PASS/ERROR. |
| `software/p03/include/p03_runtime.h` / `p03_runtime.c` | Portable C11 deterministic scheduler and phases; logical-to-resident mapping; round-robin replacement; CURRENT/NEXT swap; packet-completion and barrier invariants; sticky first fault; counters. No BSP/MMIO dependencies. |
| `software/p03/include/p03_hw_runtime_bridge.h` / `p03_hw_runtime_bridge.c` | Binds runtime callback API to page, dispatch, route, quiescence and result functions; does not choose victim/order on the PC. |
| `software/p03/include/p03_hw_adapter.h` / `p03_hw_adapter.c` | Registers core/axon metadata; issues MMIO START/polls DONE; validates packet bitfields; routes NEXT axons by logical destination; enforces allowed DDR window; per-logical-core double-bank event counts. |
| `software/p03/p03_hw_xilinx_io.c` | BSP-specific 32-bit physical MMIO/DDR stores; cache flush/invalidate; barriers; PS FPD128 boot-width assertion. |
| `software/p03/build_p03_finish.py` + `scripts/build_p03_finish.sh` | Fixed standalone A53 Vitis source set, accepted XSA/SHA/topology guards, retained ELF identifier and reserved-DDR load-segment exclusion. |
| `scripts/p03_finish_fixture.py` | Creates P02-derived 7/100 golden initial/final records and 256-byte launch manifest. |
| `scripts/run_p03_finish.sh` and `vivado/p03_finish_xsdb_{prepare,run,dump}.tcl` | Prepare/prove physical DDR write, program accepted PL, start ELF, *passively* poll, physically dump five final records. |
| `scripts/p03_finish_verify.py` | Independently validates 256-byte result and five complete physical DDR records against the unchanged Python P02.4b oracle; inspects DDR even when mailbox fails. |
| `tests/test_p03_finish_autonomy.py` | Host-native fixture, 7/100 profiles, mailbox failure injection, C syntax and source/deployment invariants. |

The reference filename/package still says `loihi_twin_v2` because
the v3 implementation intentionally inherits the accepted v2
architectural model. Both scripts explicitly prepend **this checkout's
`v3/src/`** to `sys.path` before importing it; do not replace the
reference with an unrelated installed package from `.venv-p08`.

## 3. Fixed physical DDR mapping and ABI

These are **project-reserved locations used after Linux has been
stopped**. They are not general-purpose safe addresses under running
Linux. All addresses here are *physical* PSU/APU addresses, not
A53 virtual addresses under a Linux MMU.

| Address/range | Size | Contents |
|---|---:|---|
| `0x40000000` | 512 KiB | Logical core 0 record |
| `0x40080000` | 512 KiB | Logical core 1 record |
| `0x40100000` | 512 KiB | Logical core 2 record |
| `0x40180000` | 512 KiB | Logical core 3 record |
| `0x40200000` | 512 KiB | Logical core 4 record |
| `0x43FE0000` | 256 B used | Versioned input/launch configuration |
| `0x43FF0000` | 256 B used | A53 result/error mailbox |

The adapter confines DDR operations to the accepted project window
`0x40000000` through `0x43FFFFFF`. Five records consume
`0x00280000` bytes, ending at `0x4027FFFF`. Each 512 KiB P02
record holds an initial 4 KiB header plus static and mutable banks.
The FPGA page mover transfers **438,272 bytes** (`0x6B000`) on
full page-in and **106,496 bytes** (`0x1A000`) of mutable state
on a dirty page-out. Static config, axon, synapse and route banks
are not overwritten by the normal mutable-only eviction path.

The initial record header includes `LTV3CTX1`, ABI version,
logical ID, stride and bank metadata. The A53 checks all five
initial record **CRC32s** against the launch manifest plus
specific header/config fields before running inference.
These CRCs detect accidental corruption; they are **not**
authentication or a cryptographic integrity guarantee. The P02
header's initial static digest is not automatically updated on
runtime mutable writes; the *whole final record*, including raw
stale event words, is instead compared independently with the
corresponding golden final record.

### Launch-manifest word layout (64 little-endian `uint32_t` = 256 B)

| Word(s) | Meaning |
|---|---|
| 0–1 | Magic `0x50334346` (`P3CF`), ABI version 1 |
| 2–9 | Timesteps **7 or 100**; five logical cores; three resident slots; base axon 10; DDR base `0x40000000`; stride `0x80000`; result-mailbox address; one physical engine |
| 10–19 | Five packed 64-bit logical-core dispatch metadata values (low/high halves) |
| 20–24 | Five low 32-bit expected initial `config[0]` words |
| 25–29 | Initial CURRENT/NEXT event counts (all zero in frozen ring) |
| 30–34 | External injected axon IDs `10,11,12,13,14` |
| 35–39 | Logical core IDs `0,1,2,3,4` |
| 40–44 | Per-core CRC32 of each full 512 KiB initial record |
| 45–48 | Expected total emitted/routed packets, total dispatches, barriers/timesteps, final NEXT bank parity |
| 49–62 | Reserved, zero |
| 63 | CRC32 of preceding 252 manifest bytes |

The physical ELF is **not** rebuilt for 7 vs 100 timesteps. Only
this manifest and corresponding source/golden DDR fixture change.
The Vitis `p03_finish_run.elf` must contain retained identity
`P03_AUTONOMOUS_P02_GOLDEN_7_OR_100_V2`; the build script
and board runner inspect the **actual ELF**, not merely its source,
and the runner compares staged C files to current repository files.

## 4. What runs after the one launch

The runtime deliberately models a synchronous **algorithmic global
timestep** over local spiking neuron evaluations, rather than
freely interleaving unbounded asynchronous events.

1. **Boot/admission.** XSDB accesses physical memory via PSU/APU
   after halting the A53 Linux contexts; `dow -data` provisions
   five initial DDR images and the two 256-byte blocks; `mrd -bin`
   reads them back byte-exactly. Vivado programs the accepted
   FPD128 PL bitstream, then XSDB `dow`/`con` starts the ELF.
2. **A53 setup.** `main()` explicitly zeros application counters
   and the output mailbox, checks the PS FPD128 selector, CRC32 of
   launch config, record CRCs/header/config words, adapter
   registration, axon IDs and runtime configuration.
3. **Initial residency.** `p03_rt_execute()` fully page-ins
   logical cores 0, 1 and 2 into physical slots 0, 1 and 2.
   A resident debug readback verifies their initial config words.
4. **Each timestep.** Reset logical completion and pending-packet
   bookkeeping. `current_event_bank` selects CURRENT; NEXT is
   `1-CURRENT`.
5. **Each logical core (ordered 0,1,2,3,4).** Find its resident
   slot or use the deterministic rotating `next_victim_slot`.
   If the victim is dirty, complete its mutable-only page-out
   *before* overwriting that slot; then complete requested
   full page-in. Mark/update slot mapping and paging counters.
6. **External stimulus.** The A53's wrapper
   `inject_external_and_dispatch()` appends exactly one
   external axon `10+logical_core_id` into that core's CURRENT
   bank immediately before dispatch, at the current per-core
   event-count index. This reproduces the accepted P02 ring's
   input timing; it is not host-supplied loop-level intervention.
7. **One real FPGA dispatch.** The bridge invokes
   `p03_hw_dispatch()`, writes slot, bank, logical metadata,
   event count and timestep over the PS MMIO interface,
   commands START, polls completion, validates active selection,
   core status and packet count, then clears the consumed
   CURRENT event count. The FPGA HLS core updates resident
   neural state/trace/packet banks. The scheduler marks the
   dispatched slot dirty.
8. **Packet collection/delivery.** For each emitted 64-bit
   packet, the A53 reads the actual PL packet bank and
   validates its logical destination (7 bits), axon (12 bits),
   source compartment, target timestep `t+1`, validity bit
   and configured destination axon. It commits exactly one
   destination axon to NEXT, *never CURRENT*:
   - If destination **resident**: MMIO debug write into its
     resident NEXT event bank.
   - If destination **nonresident**: A53 32-bit store directly
     into its authoritative DDR NEXT event bank, DCache clean,
     and memory barrier. **No destination page-in is required
     solely for routing.**
   Per-core event counts and committed-packet acknowledgments
   are updated by the A53. The bridge is hardware-only; it
   does not forward packet decisions to Python or the PC.
9. **Global barrier.** Once all five dispatches complete, the
   scheduler requires zero pending packets. The bridge verifies
   all CURRENT logical event counts have been consumed and
   the hardware is quiescent with no page bytes pending.
   Only then does `current_event_bank` switch to NEXT,
   increment the global timestep and resume.
10. **Finalization and terminal output.** After seven or 100
    complete timesteps, `write_result()` **mutable-page-outs
    the last three dirty resident slots**, samples MMIO
    counters/quiescence, reads final per-core DDR state and
    NEXT-event counts, and fills the evidence mailbox.
    `p03_rt_execute()` transitions to `DONE`; only then
    does `main()` publish terminal `0x600D600D`, flush
    the mailbox cache and halt. Failures publish
    `0xDEAD0000 | error_code` and halt instead.
11. **External verification (post-execution only).** XSDB reads
    the terminal mailbox passively and then dumps the five
    complete physical DDR records via PSU/APU. Python checks
    counters/status/faults/state words/manifest identity and
    every byte of all five records against the frozen Python
    golden oracle, including event banks, packet/trace banks
    and untouched static images.

The scheduler is callback-driven, not manually unrolled by XSDB.
Its early `load_input` callback validates the initially
resident configuration; actual per-timestep external spike
injection is the **dispatch wrapper** (step 6 above). It is
important not to confuse those two similarly named operations.

### Cache ownership and memory ordering

`p03_hw_xilinx_io.c` wraps `Xil_In32` and `Xil_Out32` for
the 32-bit MMIO API, `Xil_DCacheFlushRange` (clean)
and `Xil_DCacheInvalidateRange` for physically addressed DDR
buffers, and `dsb sy` barriers. Before PL reads PS-written
context DDR, the adapter cleans and orders the range. Before
and after the PL overwrites mutable context DDR on page-out,
the adapter enforces CPU-cache ownership changes and invalidation.
For nonresident NEXT routing the PS writes the axon into DDR,
cleans that 32-bit insertion and barriers before the PL can
page-in that logical context. A physical event-bank write
does *not* itself change logical timestamp: the packet still
becomes eligible only after the next barrier swap.

These operations assume the accepted **bare-metal physical
addressing/BSP configuration** and halted Linux. They should
not be copied into a concurrently running Linux process
without a DMA/coherency/physical-memory ownership redesign.

## 5. Results, errors and timing

### 256-byte result mailbox: useful offsets

All fields are little-endian 32-bit words; adjacent LO/HI
words reconstruct specified 64-bit counters.

| Word(s) | Field |
|---|---|
| 0–3 | `P3RS` magic, schema 1, terminal result, application error code |
| 4–9 | Requested steps, current/last step, CURRENT-bank parity, sticky first runtime fault, first fault phase, current runtime phase |
| 10–13 | PL ID and capabilities, five logical cores, three resident slots |
| 14–23 | Logical dispatch/packet/barrier/timestep counts; initial and replacement page-ins; runtime page-outs; final dirty flush page-outs; evictions/hits |
| 24–35 | 64-bit PL dispatch and paging cycle counters; PS routing, barrier, inference and control generic-timer ticks |
| 36–44 | PS `CNTFRQ_EL0` nominal timer rate; physical resident-destination packet coverage; hardware page/dispatch completions, last page bytes, global/pending status, AXI read/write burst counters |
| 45–54 | Five final 64-bit compartment-state word 0 values from authoritative DDR |
| 55–59 | Five final NEXT-event counts |
| 60 | Manifest CRC32 |
| 61–62 | Normal case: last observed real PL output packet (64 bits). `WRITE_RESULT` error only: **tagged diagnostic mask** and first failing actual value |
| 63 | Frozen expected total routed packets (from launch manifest) |

Success is `0x600D600D`; examples of application errors include
`0xDEAD0002` (manifest admission failure) and
`0xDEAD000B` (runtime error). The runtime has its own
`p03_rt_fault` enum; `fault=12` is
`P03_RT_FAULT_CONTROL_PROTOCOL` and
`fault_phase=17` is `P03_RT_WRITE_RESULT`.
The verifier checks fault, phase and physical counts separately:
the terminal error code alone does not explain the underlying cause.

The **V2 error-only** diagnostic has
`word61 = 0xDA600000 | mask` and
`word62 = first_actual`. Its named mask bits 0–18 cover
callback context, page-out failure, MMIO read failure and
individual acceptance predicates (ID, capabilities, counters,
flush, page operations, quiescence). The verifier requires
the tag before decoding; legacy packet words must not be
misread as a mask. See `docs/P03_4_PHYSICAL_ATTEMPT1.md`
for the full mask table and physical reproduction.

**Timing interpretation:** `cntvct_el0` is sampled on
the A53 and `cntfrq_el0` supplies the measured timer
frequency (accepted examples: `99,999,001 Hz`). The
`ps_inference_ticks` interval begins after initial
residency and ends before the final result callback, so
it is **not end-to-end deployment-to-DONE latency**.
Likewise PL dispatch/page `cycles` are in hardware
clock domains and must not be treated as raw PS ticks.
No measured board power or energy is claimed by P03.
Later P08/P09 should freeze timing/power methodology
before using these counters for published comparisons.

## 6. Problems found and what was changed

| Observation | Supported cause / correction | References |
|---|---|---|
| PS MMIO read/completion problems with otherwise seemingly correct RTL | Actual booted PS FPD HPM0 interface was 128-bit, incompatible with earlier 32-bit assumptions. Routed explicit 128:32 SmartConnect conversion; checked PS width and held XSA/bitstream identities. | `docs/P03_2C_PS_HPM_WIDTH_BOOT_REMEDIATION.md`, `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md` |
| XSDB record provisioning could fault through a selected A53 MMU context | Provision/read back *physical* DDR through the nonprocessor PSU target (APU fallback), not a Linux virtual address in the A53 context. Stop Linux and reboot afterward. | `docs/P02_4B_ACCEPTANCE.md`, `vivado/p03_finish_xsdb_prepare.tcl` |
| P03.3b3 premature `0xDEAD0002`, no useful packet/page activity | The startup caller inverted `validate_backing()`'s **zero-means-success** convention (`if (!validate_backing(...))`). Fixed to `!= 0`; kept an error-only raw-header overlay. Added retained ELF build identity and fail-closed stale-build checking. | `docs/P03_3B3_PACKET_PAGE_ROUNDTRIP.md`, `docs/P03_3B3_ACCEPTANCE.md` |
| New P03.4 Python regressions failed to load `loihi_twin_v2.ddr_abi` | A subprocess launched from `scripts/` resolved an older virtualenv package instead of `v3/src/`. Both CLI scripts prioritize the checkout's source directory; tests deliberately shadow the package. | `docs/P03_COMPLETION_GATE.md`, `tests/test_p03_finish_autonomy.py` |
| Mailbox negative test unexpectedly accepted state corruption | The test wrote zero to word 45 although that golden state was already zero: **no-op corruption**, not a verifier bug. Mutation now flips a baseline bit and asserts the word actually changed. | `tests/test_p03_finish_autonomy.py` |
| First P03.4 physical run `0xDEAD000B`, `fault=12` at `WRITE_RESULT`, `flush_outs=0x00800023` | The finalization callback failed while dispatch/packet/barrier counts looked correct. V2 explicitly resets application counters (volatile flush count), tags an individual-predicate error mask, and validates all five DDR records even if mailbox FAILs. **The exact underlying origin of the V1 counter anomaly was not independently isolated**, though V2 passed the physical 7/100 gates. | `docs/P03_4_PHYSICAL_ATTEMPT1.md`, `docs/P03_4_ACCEPTANCE.md` |
| Risk that XSDB observes PASS before callback/runtime finish | Terminal PASS is only published after the result callback returns and scheduler phase becomes `P03_RT_DONE`; a cache flush follows. The host poll is terminal-only. | `software/p03/p03_finish_run.c`, `tests/test_p03_finish_autonomy.py` |

Previous P02 arbiter held-request and stale-debug-response
investigations are recorded in `docs/P02_4B_ACCEPTANCE.md`;
the accepted P03 software reuses that existing data-plane behavior
rather than taking credit for rediscovering it.

## 7. Independent acceptance evidence and nonclaims

| Gate | Steps | Dispatches | Routed packets | Barriers | Total page-ins | Total page-outs | Final DDR |
|---|---:|---:|---:|---:|---:|---:|---|
| P03.3b3 nonresident packet/dirty-page directed probe | 2 | 4 | 2 | 2 | initial+replacement as logged | 3 mutable | PASS of directed events |
| P03.4 accepted five-over-three | 7 | 35 | 30 | 7 | 35 | 35 | All five 512 KiB exact |
| P03.5 accepted sustained five-over-three | 100 | 500 | 495 | 100 | 500 | 500 | All five 512 KiB exact |

P03.4 seven-step reference trace digest:
`9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac`.
P03.5 100-step reference trace digest:
`b10387cb7930e6e4452548ff4d025c8dffe52e9eeebde2d5b43ed9c5475cfcac`.

The final five DDR records were checked **byte for byte** against
model-generated expected raw physical images. The trace digests
shown by `verify.log` are fingerprints of **reference model
traces**, not independent physical per-timestep trace captures.
The physical equivalence claim is the final-DDR exact comparison
plus runtime counters and callback invariants, **not** byte-exact
inspection of all 500 intermediate physical neuron states.

Both P03.4 and P03.5 logged `resident_deliveries=0`:
this specific physical ring schedule did **not** exercise
direct delivery into an already-resident destination; that adapter
branch has native C regressions but no directed standalone KV260
packet acceptance. Therefore P03 functional acceptance does not
imply every packet-routing branch has physical coverage. An
additional directed already-resident destination test is a useful
P05 hardening/coverage target, not a silent assumption.

The standalone PS still needs the external PC to *provision* DDR
and start the ELF via JTAG; persistent onboard Linux control,
standalone power-on boot, support for arbitrary 128 logical-core
workloads, multi-engine physical parallelism, full MNIST autonomy,
and calibrated power/energy measurements are separate future
engineering/research claims. The retained ILA/VIO diagnostics
are part of the accepted experimental bitstream, not evidence
of host-owned algorithmic control.

The P03.5 user-supplied full terminal log:

```text
P03 board-local terminal result=0x600D600D after 5 poll(s)
PASS: P03 autonomous five-over-three P02/v2 normalized golden
     timesteps=100 dispatches=500 packets=495 resident_deliveries=0
     barriers=100 page_ins=500 page_outs=500
PASS: P03 all five final 512KiB DDR records byte-exact to frozen Python P02 oracle
P03_FINISH_VERIFY_EXIT=0
P03_FINISH_EVIDENCE_DIR=/tmp/v3_p03_finish_100_20261012T145336Z
PASS: P03 100-step independent board-autonomous physical golden gate
```

(The original log concatenated `packets=495resident_deliveries=0`
without a space in its display; these are **two separate fields**,
not a different numerical result.)

## 8. How to reproduce and independently inspect evidence

Run on the user's Ubuntu machine with the accepted tools:
Vivado/Vitis 2023.2, Xilinx XSDB, the existing
`.venv-p08`, JTAG/hw_server and KV260 boot firmware
that initialized DDR. Physical runs overwrite the project
DDR reservation and replace running Linux; **reboot the board
after every run, including after failure**.

```bash
cd ~/Git/Thesis
git switch main
git pull --ff-only origin main
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# Host-native gates
python -m pytest -q \
  tests/test_p03_finish_autonomy.py \
  tests/test_p03_3b3_physical_probe.py \
  tests/test_p03_3b_hw_adapter.py \
  tests/test_p03_3a_native_runtime.py \
  tests/test_p02_4b_ring_fixture.py

# Reuse exact accepted FPD128 routed hardware XSA.
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_FINISH_BUILD_DIR="$PWD/vivado/build/p03_finish_closeout_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/build_p03_finish.sh | tee /tmp/v3_p03_finish_closeout_build.log

# Reboot KV260/initialize DDR and ensure hw_server is running.
export P03_FINISH_EVIDENCE_7="/tmp/v3_p03_finish_7_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_finish.sh 7 "$P03_FINISH_EVIDENCE_7" \
  2>&1 | tee /tmp/v3_p03_finish_7_physical.log
cat "$P03_FINISH_EVIDENCE_7/verify.log"

# Reboot KV260 before the 100-step run. Reuse the SAME ELF.
export P03_FINISH_EVIDENCE_100="/tmp/v3_p03_finish_100_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_finish.sh 100 "$P03_FINISH_EVIDENCE_100" \
  2>&1 | tee /tmp/v3_p03_finish_100_physical.log
cat "$P03_FINISH_EVIDENCE_100/verify.log"
# Reboot KV260 after.
```

Do **not** overwrite the existing accepted physical evidence
directories. Each new run must use a **new evidence directory**;
the runner rejects old directories or a stale/wrong ELF. Rebuild
only when the P03 C app or source build changes, not when selecting
7 vs 100 through the launch manifest.

To inspect the accepted final 100-step run without touching hardware:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
export E=/tmp/v3_p03_finish_100_20261012T145336Z
cat "$E/identity.txt"
cat "$E/verify.log"
PYTHONPATH="$PWD/src" python scripts/p02_4b_ring_fixture.py verify \
  --fixture-dir "$E/fixture" --dump-dir "$E/final_ddr"
```

Capture full `identity.txt` (XSA/bitstream/ELF/config SHA256s),
`p03_a53_result.bin`, both fixture manifests, `verify.log`,
and all five `final_ddr/coreN_after.bin` files when archiving
the physical evidence. The GitHub commit/acceptance record does not
itself contain those private/local binary artifacts or their unknown
measured hashes. The last local 100-step `verify.log` is independently
user reported; the assistant did not run the KV260 remotely.

## 9. Related design and troubleshooting documents

- `docs/P03_1_AUTONOMOUS_RUNTIME_CONTRACT.md`: architectural contract,
  error-state and barrier semantics.
- `docs/P03_2_PS_MMIO_CONTROL.md` and `docs/P03_2C_ACCEPTANCE.md`:
  register map, physical PS width and shell verification.
- `docs/P03_3A_C_RUNTIME_POLICY_ENGINE.md`:
  portable C scheduler policy and mock tests.
- `docs/P03_3B_PHYSICAL_ADAPTER.md`,
  `docs/P03_3B3_PACKET_PAGE_ROUNDTRIP.md`:
  actual Xilinx bridge, dirty page-out, cross-core packet evidence.
- `docs/P03_4_PHYSICAL_ATTEMPT1.md`,
  `docs/P03_COMPLETION_GATE.md`: failure timeline, source-level
  repairs and V2 tagged diagnostics.
- `docs/P03_4_ACCEPTANCE.md`,
  `docs/P03_5_ACCEPTANCE.md`,
  `docs/P03_FINAL_ACCEPTANCE.md`: the physical closeout ledger.

**Research claim preserved:** P03 proves the accepted FPGA-v3
five-logical-core / three-resident-slot digital twin's **algorithmic
control loop is board-local**, not that every optional future
architecture feature or packet-route branch is physically characterized.
