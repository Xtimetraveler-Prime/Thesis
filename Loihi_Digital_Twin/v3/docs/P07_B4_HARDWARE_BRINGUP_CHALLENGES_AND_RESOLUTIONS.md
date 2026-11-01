# P07-B.4 — Physical KV260 bring-up: engineering challenges, diagnosis, and resolutions

**Retrospective prepared 2026-11-01 after P07-B.5.1 original TRAIN validation preflight.**
This is a source- and operator-log-backed engineering history. Older handoff files were written *before* later successful runs and may retain historical "not accepted" headings; their failure observations are not to be rewritten as successes. The final accepted B4m record and user-confirmed host numerical check **supersede those historical status banners**, not the raw failure evidence.

## Purpose / scope

P07-B.4 moved from accepted P03.2c PL/PS-MMIO shell and modeled
B3 scheduler/pager to **real physical one-engine/three-resident-slot
execution of the frozen P06-B.2.4 27-core trained 784→1000→10 model on
the KV260**, with 26 global timesteps (702 HLS logical dispatches).

This was not merely a straightforward conversion of Python to RTL.
It required independently authenticated real Vitis artifacts, PS/PL
width and MMIO admission, ownership of a disposable A53 JTAG session,
byte-exact physical DDR provisioning, 27-logical-core metadata and
event-bank routing, and independent comparison to the original integer
LIF oracle.

The *original frozen trained model*, its per-core 512KiB P02 records,
accepted P03 bitstream/XSA, and B2 official TEST seal were maintained
throughout. Diagnostic V1/V2/V3 ELF variants must not be conflated.

## Chronological challenges and what resolved them

### 1. Real Vitis A53 ELF existed but the linker map did not (B4c, 2026-10-21)

**Observation.** The operator's genuine Vitis 2025.2 build compiled and
linked the standalone A53 binary. The separate physical-admission gate
rejected it because Vitis had emitted `lscript.ld` but **no GNU
`.map`**; the accepted real memory section/stack/heap mapping could
not be independently audited.

**Diagnosis.** This was a build-provenance/admission problem, **not a
C compilation or FPGA execution failure**. Heap and stack were embedded
ALLOC/NOBITS sections within one A53 ELF PT_LOAD, unlike some historical
separate-external-buffer assumptions.

**Remedy.** Set Vitis Unified
`USER_LINK_OTHER_FLAGS` with the genuine `-Wl,-Map=...` link option
*before linking*, require a real map file and validate exact ELF
ALLOC-section ranges from `readelf`; keep low-DDR ownership marked
unverified. The revised independent build/admission gates accepted
later real ELFs/maps. Never synthesize a map after the fact.

**Primary record:**
`docs/P07_B4C_REAL_A53_ATTEMPT1_LINKER_MAP_FIX.md`.

### 2. Unexpected PS FPD/LPD 64-bit widths and AXI AP timeout (B4g, 2026-10-21)

**Observation.** During early Track B admission, live PS static AXI
width registers indicated 64-bit on FPD and LPD:
`FPD_SLCR.afi_fs=0x00002560`,
`LPD_SLCR.afi_fs=0x00000512`, unlike the accepted
**128-bit/128-bit** physical configuration. An early MMIO read at
`0xA4000000` also timed out before the accepted P03 PL image had
been programmed during that boot.

**Diagnosis.** The two findings must not be collapsed into one
proven root cause. A missing P03 PL MMIO slave in the current boot is a
plausible explanation for the AP timeout. The PS width mismatch was
independently real. A successful `xmutil unloadapp` did **not**
restore PS widths. Reconciliation of 19 historical Track-A and seven
P08 logs showed earlier genuine FPD128/LPD128, including the last
recorded P08 test, but did **not prove why the later 64-bit boot state
occurred**. No audited P08 runner was shown to write the static width
registers.

**Remedy / successful operating condition.** Do not force
`mwr` changes to PS static width selectors or confuse PL bitstream
loading with PS initialization. Add a **read-only FPD/LPD width gate
before PL or DDR operations** and require the exact accepted values
`0x00000A00` (FPD) and `0x00000200` (LPD). Later dedicated
sessions physically observed both widths at 128 bits and successfully
continued. The historical 64-bit *cause remains unresolved*; the
hardware experiment can nevertheless operate under a separately
verified known-good boot/PS state.

**Primary records:** `docs/P07_B4G_P08_7_RUN_WIDTH_RECONCILIATION_LEDGER.json`,
`docs/P07_B4G_P08_A_PERSISTENT_WIDTH_CAUSE_AUDIT.md`,
`docs/P07_B4G_TRACK_A_XMUTIL_BOOT_RECONCILIATION.md`, and
`docs/P07_B4I_2026_10_22_PHYSICAL_TAKEOVER_WIDTH_PASS_LEDGER.json`.

### 3. A53 secondary-core power state and the strict JTAG takeover gate (B4i, 2026-10-22)

**Observation.** A physically attempted multi-core JTAG stop
reported a powered-down *secondary* A53, causing a conservative
stop-gate rejection.

**Diagnosis.** A powered-down secondary core is not the same as a
failed halt of primary CPU0. The earlier diagnostic assumed
all four cores would always respond identically; typical board
power-management states do not ensure that.

**Remedy.** Account for the actual state of every A53: CPU0 must be
positively stopped, and secondary cores may be explicitly observed
as powered down. Keep the independent PSU FPD+LPD 128-bit checks
mandatory and fail closed on unexpected debugger errors. A
subsequent genuine board test produced
`P07_B4I_A53_ALL_CORES_ACCOUNTED_AND_PSWIDTH128_GATE_PASS=1`.

**Primary records:** `docs/P07_B4I_TRACK_A_DERIVED_PHYSICAL_PILOT.md`,
`docs/P07_B4I_2026_10_22_FIRST_PHYSICAL_TAKEOVER_ATTEMPT.json`,
`docs/P07_B4I_2026_10_22_PHYSICAL_TAKEOVER_WIDTH_PASS_LEDGER.json`.

### 4. XSDB replied "Already stopped" during A53 launch (B4k, 2026-10-22)

**Observation.** After successful physical PL programming, a
standalone A53 launch attempt failed on XSDB's `Already stopped`
response rather than reaching the firmware mailbox.

**Diagnosis.** The original script treated this specific confirmed
CPU state as an unrecoverable `stop` command error. That was a
debugger-state handling problem, not a failure of the accepted
P03 bitstream or neural arithmetic.

**Remedy.** Accept **only the exact documented "Already stopped"
positive-state observation** where the gate requires a halted CPU,
without treating arbitrary Tcl errors as success or bypassing
mandatory DDR/ELF protections. Native negative paths remained
fail-closed; a separately rebooted physical retry completed the
A53 standalone mailbox/PS-MMIO admission.

**Primary records:** `docs/P07_B4K_STANDALONE_A53_PHYSICAL_ADMISSION.md`,
`docs/P07_B4K_2026_10_22_FIRST_A53_LAUNCH_FAILURE_LEDGER.json`,
`docs/P07_B4K_2026_10_22_PHYSICAL_STANDALONE_ACCEPTANCE_LEDGER.json`.

### 5. Original 27×512KiB source staging and a Python direct-script import failure (B4l, 2026-10-22/23)

**Observation.** Loading the trained 27-core model was substantially
more than successfully programming the PL. Each P02 context,
original 16KiB binding descriptor and later signed routing/TRAIN
payloads had to be provisioned into owned DDR ranges and
**physically read back byte-for-byte**. One PC-only preflight also
failed on Python's direct-script import path before reaching its
frozen-asset verification.

**Diagnosis.** The import issue was Python path resolution, not a
hardware or model fault. Physical source staging and runtime paging
also prove different things: a correct DDR image does not show a
context was loaded, processed, updated and saved.

**Remedy / physical progress.** Repair only the source import
resolution in the original B4l stage helper; retain all frozen
hash/ABI checks. Build an independent 27-record readback verifier,
then demonstrate **three-resident-slot page/dirty-save operation**
and an original 27-dispatch first scheduling epoch with genuine A53
receipts. The first epoch did not run the trained model through 26
ticks; no numerical inference was claimed.

**Primary record:** `docs/P07_B4L_CONSOLIDATED_MODEL_DEPLOYMENT.md`
and contemporaneous B4l staged/paged/epoch acceptance ledgers.

### 6. Full trained run failed at its first HLS dispatch (B4m V1/V2, 2026-10-31/11-01)

**Observation.** Real original 27-core TRAIN0 staging/readbacks and
A53 execution succeeded, but trained inference ended in **stage 9**
instead of completing the 26-tick schedule. V2's real failure-only
mailbox exposed:

```text
P03_DISPATCH_STATUS=0x22
P03_DISPATCH_CORE_STATUS=0x4   # HLS STATUS_SYNAPSE_ROW_BOUNDS
P03_DISPATCH_COMPLETED=1
p03_hw_adapter error=-5
```

The PC first-dispatch source audit had found **39 compartments,
30,576 valid source synapses and 51 input events** on the original
first core with no intrinsic source-level row violation. It could
not establish the physical subfault before the V2 mailbox was read.

**Diagnosis.** The original B4l 16KiB descriptor registered each
core using only `core_id | (compartments << 7)`. The P08
dispatch controller passed metadata bits `[33:18]` as
`synapse_count` and `[46:34]` as `route_count` to the HLS
core; those fields had remained **zero** in the registered
metadata. Thus valid original synapse rows appeared out of
bounds to the hardware. This explains the observed `0x4`
without changing or shrinking the trained model.

**Remedy.** Isolate the correction in **diagnostic V3 firmware**:
read original signed P02 core headers at `+0x20` compartments,
`+0x24` synapses, `+0x28` output routes, validate all 27
headers/capacity/identity against the descriptor and then populate
those runtime count fields before dispatch. Keep original frozen
27-core weights, original 16KiB binding, P03/P08 RTL, fixed
routing tables and original V1/V2 evidence unchanged.
Distinct V3 firmware identity, SHA-pinned real ELF/map, offline
admission and failure-only B4D3 telemetry prevent accidentally
promoting old failed firmware to a success.

**Physical confirmation:** the later genuine V3 run **completed all
702 dispatches and 26 barriers without HLS bounds errors**.
This strongly confirms the omitted metadata as the
*operational reason* the previous physical run failed. The
before/after experiments changed the diagnostic firmware path,
so avoid claiming a formal isolated single-variable causal trial.

**Primary record:** `docs/P07_B4M_2026_10_31_STAGE9_DIAGNOSTIC_V2_HANDOFF.md`;
V2 failed physical mailbox SHA256
`79c20f53664afabd3d349b3dccc0f3fc0f1824706863cb5d1409cb9ce493077d`.

### 7. Real XSDB CPU0 "power down" wording defeated the fallback recognizer (B4m V3 initial attempt, 2026-11-01)

**Observation.** On the **first attempted V3 physical run**, host
signed-model/ELF gates passed, but XSDB refused the very first CPU0
stop operation with:

```text
Cannot halt processor core: power down
```

No PL programming, DDR staging, ELF launch, mailbox or inference
occurred in that attempt.

**Diagnosis.** The existing bounded power-down/recovery gate
recognized only the exact XSDB text
`The core is powered down`; it rejected the other real version
before entering the guarded retries/PS-width checks. This
was a takeover-controller message-contract bug. The processor's
actual down-state/root cause was not independently determined.

**Remedy.** Recognize only the two **exact** bounded XSDB
power-down messages; retain 128-bit checks, guarded reset, positive
CPU0 halt and fail-closed unexpected errors. Test the actual new
message with native mocked XSDB responses. **Reboot** after the
failed attempt. In a subsequent standalone CPU0 gate, CPU0
stopped immediately, secondary CPU2 was accounted for as
powered down, FPD+LPD both read 128-bit, and the final takeover
marker passed; the guarded CPU0 reset fallback was **not
physically exercised** in that successful retry. The full V3
experiment then proceeded on a fresh boot.

**Primary record:** same B4m handoff, external
`p07_b4m_diag_v3_real_20261101T040103Z/ps_width.log`.

### 8. A numerical verifier's synthetic fixture concealed the wrong frozen input-route API (B4m post-run, 2026-11-01)

**Observation.** Real V3 physical structural results were already
accepted, but the first independent PC scalar comparison crashed:

```text
AttributeError: 'IngressRoute' object has no attribute 'source_input'
```

**Diagnosis.** Frozen B1.2's actual
`IngressRoute(input_population, input_index, destination_core,
destination_axon)` was mistakenly treated as
`(source_input, source_index, ...)`; the original synthetic
test repeated the incorrect invented field names, so CI had
missed the real-data failure. This was a **host verification bug**,
not a rerun of or fault in the FPGA.

**Remedy.** Use the real frozen `IngressRoute` fields,
add validation of physical core/axon bounds, and construct the
actual `IngressRoute` class in regression fixtures rather than
relying only on ad-hoc `SimpleNamespace`. The existing real
V3 mailbox was preserved and reused. The operator reran
the scalar reference check and reported:

```text
P07_B4M_V3_ORACLE_VS_PHYSICAL_ALL_CHECKS_MATCH=1
P07_B4M_DIRECT_FULL_RAW_NEURON_PARITY_VERIFIED=0
```

Report:
`/home/dna/Thesis_Evidence/p07_b4m_v3_scalar_parity_20261101T043214Z.json`.
This independently compared the original frozen 26-tick
scalar state/spike trace **FNV64 fingerprint** and
the available input/spike/packet/readout counters to the
real 256-byte physical V3 mailbox. FNV64 equality is
not a literal direct comparison of all underlying raw neuron
states and is not a test-set accuracy claim.

## Final observed P07-B.4m results and boundaries

After physical V3 firmware repair and fresh original-model staging,
the operator's accepted KV260 run
`p07_b4m_diag_v3_real_20261101T041302Z` produced:

| Metric | Genuine hardware result |
| --- | ---: |
| Original logical cores | 27 |
| Resident contexts / physical HLS engines | 3 / 1 |
| Algorithmic ticks | 26 |
| Real HLS dispatches | 702 |
| Global barriers | 26 |
| Page-ins | 702 |
| Dirty runtime outs / final outs | 699 / 3 |
| External CURRENT events | 31,512 |
| HLS bank7 source spikes | 1,514 |
| P03 egress packets captured / NEXT inserted | 1,489 / 1,489 |
| Compartments traced per tick | 1,010 |
| Readout class | 1 |
| Original TRAIN0 readout counts | `[0,25,0,0,0,0,0,0,0,0]` |
| Physical 26-tick trace fingerprint | `0xB59CA8594D6E64AD` |

Actual 256-byte physical mailbox SHA256:
`5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`.
Exact V3 A53 ELF SHA256:
`66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`.
Independent host check: operator-reported PASS above.
B5.1 subsequently **independently regenerated all three original
TRAIN scalar reference witnesses** and B5.2 **host-reverified
original physical ordinal0** using the stricter new verifier:

```text
P07_B5_THREE_FROZEN_TRAIN_SCALAR_REFERENCE_PASS=1
P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1
P07_B5_FULL_RAW_NEURON_PARITY_VERIFIED=0
```

The B5 verifier's PASS above applies to the **one supplied ordinal0
physical run**, not three physically observed validation frames.
The remainder of P07-B.5 requires physical original TRAIN1/2 and
an independent TRAIN0 restart/repeat plus, for strict raw
neuron parity, a separately captured 840,320-byte authenticated
full original 26×1010 per-neuron trace. No official B2 MNIST
TEST has been unsealed.

### What the engineering work established

- **Correctness and provenance are separate:** byte-exact frozen DDR
  reads, actual HLS dispatches, successful A53 mailbox and
  independent numerical agreement are individually necessary checks;
  neither substitutes for another.
- **Toolchain and debugger state matter:** Vitis map creation, CPU
  halt/powered-down semantics, PS AXI width and PL MMIO identity
  need independent run-time gates rather than trusting historical
  successful builds or source code.
- **The mapping ABI crosses software/RTL/HLS boundaries:** complete
  source-level data may be present yet unusable if physical controller
  metadata (synapse/route cardinalities) is missing.
- **Use real domain classes in regression tests:** mocks that recreate
  mistaken APIs can validate the wrong contract.
- **Preserve failed attempts:** distinct genuine ELF IDs, SHA hashes,
  B4D2/B4D3 failure telemetry and external evidence directories
  made it possible to diagnose the actual V2 hardware error
  without fabricating a full-inference result.
- **Respect unresolved conditions:** the transient PS64 boot state's
  root cause, standalone A53 low-DDR boot-firmware exclusivity,
  full raw-neuron physical trace parity, performance/power, and
  official TEST accuracy were **not** established by B4m.

## Forward acceptance path

P07-B.4m's original single TRAIN0 physical inference and
**independent scalar/FNV64 fingerprint comparison** passed.
Proceed on draft PR #50 with P07-B.5 frozen
TRAIN0/1/2 multi-image plus cold-reboot repeat validation;
then separate raw physical state trace verification, explicit
user acceptance, P07-B.6 evidence freeze, and P08-B
performance/traffic measurement. PR #49 remains draft and
unmerged until the operator explicitly authorizes merge.
