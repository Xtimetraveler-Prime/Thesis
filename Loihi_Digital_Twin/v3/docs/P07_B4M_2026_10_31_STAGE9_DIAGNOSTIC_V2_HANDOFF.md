# P07-B.4m physical inference handoff — bounded closeout (2026-10-31)

**Status: engineering implementation complete, physical full-inference
ACCEPTANCE BLOCKED (NOT PASSED).** Keep PR #49 draft and unmerged pending
an explicit decision to merge or separately freeze the unresolved work.
Do not start a new P07-B.4m micro-milestone.

## Immutable original trained deployment (never modify)

- Accepted B2.4 27-core 784→1000→10, 26 tick model:
  compilation SHA `02a6b68a2eda4587bbdf07e3af4aa63bdd7214223e853b08d8f6463896364f5a`.
- Original frozen DDR bundle physical stage/readback:
  SHA `3733e1c289fb5704c69be90f37b59a25e30ddedf7dd8dc305649e0be238af64e`.
- Original descriptor (16KiB) SHA:
  `2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb`.
- Original TRAIN input route image (896KiB) SHA:
  `380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8`.
- Original output route image (80KiB) SHA:
  `2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103`.
- Frozen original TRAIN ordinal-0 input (123,216B) SHA:
  `2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126`.
- Official MNIST TEST remains SEALED. All numerical parity remains UNVERIFIED.

## Accepted real hardware results

1. KV260 original 27×512KiB DDR contexts, descriptor, routing tables and
   original TRAIN frame were independently read back byte-for-byte **PASS**.
2. Genuine standalone B4m A53 ELF SHA
   `ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70`
   was downloaded and ran to terminal mailbox DONE, but **firmware FAIL**;
   702 dispatches / 26 barriers **NOT achieved**.
3. Original 256B physical failure mailbox SHA
   `4ff427fca04f75b89712c7ea81d7065710ce46de586f6eb07ec8bd1ea1105baf`:
   **stage=9, P03_HW_PROTOCOL=-5, dispatch completed register=1**.
   PS width, P03 MMIO identity, B2.4 metadata, frozen route mount,
   pager initialization and scheduler initialization all succeeded.
   No independent full-inference receipt was accepted.
4. PC-only reconstruction of original first TRAIN frame / frozen core-0
   P03 image: **51 tick-0 input events, 39 compartments, 30,576
   synapse entries, 784 registered axons, zero HLS input-semantic
   violations**. This makes original data formatting less suspect,
   but **DOES NOT prove the real PL subfault**.

## Bounded follow-up: isolate the real first-dispatch protocol subfault

The existing V1 A53 firmware only preserves high-level stage 9.
`software/p07/p07_b4m_full_board_diag.c` is a NEW isolated
`P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2` candidate, built separately
using `scripts/build_p07_b4m_diag.sh` plus
`software/p07/build_p07_b4m_diag.py`. It does NOT change the V1 ELF,
original model, PL bitstream, input routes or numerical algorithm.

When and ONLY when it ends in firmware FAIL, it captures a uniquely
tagged B4D2 payload in mailbox words 47..62:
- [47] B4D2 marker;
- [48] P03 adapter last polled raw status, [49] B3c2 scheduler first fault,
  [50] B3a pager first failure, [51] physical trace first failure;
- [52] dispatch status, [53] HLS core status, [54] active core/slot/bank,
  [55] physical packet count, [56] debug status, [57] global status;
- [58] paging status, [59] pending bytes, [60] dispatch config,
  [61] debug config, [62] debug address.

The original host-only mailbox decoder recognizes only the B4D2
marker before interpreting those values; a V1 failed mailbox remains
supported and its missing telemetry is explicitly NOT fabricated.
The strict original `p07_b4m_verify_full_receipt.py` remains unchanged.

**Important:** The V2 firmware is currently **BUILD-ONLY**. Neither the
older V1 hash-pinned XSDB runner nor the original V1 offline admission
gate will authorize it, and they MUST NOT be bypassed by swapping ELFs.
Any V2 physical experiment requires (a) genuine operator-local Vitis
ELF/map rebuild with new SHA, (b) independent ELF/memory/boot-firmware
review, (c) a separately source/SHA-pinned V2 admission+XSDB launcher,
and (d) new explicit destructive-run consent. DO NOT re-run the KV260
with either old commands or a manually substituted ELF.

PC only, user-buildable diagnostic candidate:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4M_DIAG_BUILD_DIR="$HOME/p07_b4m_diag_v2_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4m_diag.sh
```

Expected on a genuine operator-local build:
`P07_B4M_DIAG_V2_A53_ELF_AND_MAP_BUILT=1`,
`P07_B4M_REAL_BOARD_RUN_AUTHORIZED=0`,
`P07_B4M_EXPANDED_LOW_DDR_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0`.
Record the new ELF and GNU map SHA and actual `readelf_layout.txt`;
none are known until the user builds them.

## Handoff to next work

**Stop condition for B4m:** physical data placement passed; one full
trained inference attempt failed at P03 protocol after the first PL
dispatch; original model is untouched; preserved original signed
failure evidence and PC-only source audit. Never mark B4m fully accepted,
never merge PR #49 solely because the diagnostic candidate compiles,
and never unseal official TEST.

**Next-milestone work that can proceed independently:** documenting the
hardware/software control interface, repeatable tooling and measurement
methodology; host-native verification, benchmarking infrastructure and
non-destructive analysis; literature/digital-twin architecture write-up.
Tasks requiring 26-tick physical outputs, real inference accuracy,
per-neuron numerical parity or energy/latency benchmarks of successfully
completed inference remain gated.

A single narrowly scoped future board run with new telemetry may be
justified if it decisively identifies the P03 dispatch/debug subfault.
If time budget is exhausted, retain the unresolved failure as a precisely
measured research limitation and proceed to independent next milestones.

## Continuation decision: diagnose until true physical acceptance, then fallback if needed

The previous bounded handoff does **not** represent an acceptable final
result for Track B as a working inference engine. The operator explicitly
requires continued debugging to physically validate subsequent Track B.
No complete 26-tick inference acceptance is claimed.

V2 diagnostic has its own PC-only original-source/real-ELF admission:
`scripts/p07_b4m_diag_v2_offline_admission.py`. It requires a V2
source tree byte-identical to the committed C/header inputs (apart from
the two already-accepted Vitis include/route-cap transformations),
original frozen B2.4 source and TRAIN route data, accepted P03 XSA,
real AArch64 ELF + linker-map PT_LOAD section boundaries, and the
DIAGNOSTIC_V2 identity. It **never contacts hardware** and explicitly
outputs `diagnostic_v2_physical_launch_authorized=false`.

The next operator step is the already documented local V2 Vitis build,
then:

```bash
export P07_B4M_DIAG_OFFLINE_REPORT="$HOME/Thesis_Evidence/p07_b4m_diag_v2_offline_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b4m_diag_v2_offline_admission.py \
    --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
    --routes-dir "$P07_B4M_STAGE" \
    --build-dir "$P07_B4M_DIAG_BUILD_DIR" \
    --reports "$P07_B4L_REPORTS" \
    --out "$P07_B4M_DIAG_OFFLINE_REPORT"
```

**After PC admission:** record the new V2 real ELF/map SHA and exact low
DDR LOAD end, then implement an independently source/SHA-pinned V2
same-session stage/run wrapper with separate firmware-owner approval.
Never swap diagnostic V2 into V1 launcher, and NEVER assume past staging
remains in DDR after a reboot.

First live V2 failure interpretation:
- `scheduler.first_fault==17`: per-compartment trace hook failed.
  Its `trace.first_fault==3` means physical debug read protocol;
  `==4` means trace-vs-state discrepancy. Check actual debug status,
  config, address and dispatch-status MMIO in the V2 mailbox.
- `scheduler.first_fault==10`: hardware dispatch/paging operation or
  post-operation quiescence failed; correlate raw P03 dispatch status,
  core status and active core/bank with the first adapter status.
- `scheduler.first_fault==8`: packet debug read failed.
  Confirm packet count and P03 debug bank status.
- Other subfault codes must be investigated directly from the frozen
  `p07_b3c2_hw_scheduler.c` source, not guessed.

**Contingency if V2 shows the real full frozen model remains blocked:**
develop a SEPARATELY IDENTIFIED tiny on-FPGA differential workload
under the *same accepted P03 engine and MMIO shell*. Start with a
single logical LIF compartment and no events, then one registered axon
and one event, then gradually add its synapse row, trace bank7 readback,
packet output and next-bank event; finally increase to the actual
source core0's first-tick 51 events (39 compartments, 30,576 unique
synapse entries). Preserve synthetic model and receipts in new
out-of-freeze artifacts, and validate exact software-versus-physical
trace/digest at every step. **Do not train a smaller network to hide
an MMIO protocol fault.** Only when the physical interface is proved
reliable should a smaller *trained* 784→small-hidden→10 network be
considered as an explicitly documented reduced-scope Track B
evaluation, with new capacity/resource and parity baselines. The
original 784→1000→10 result must remain clearly NOT physically verified.

No official TEST evaluation or hardware benchmarking is authorized
until the relevant model has completed a real accepted inference and
the applicable parity protocol.

## 2026-10-31 continuation — genuine V2 build + isolated physical diagnostic launcher

Operator-reported **GENUINE local Vitis DIAGNOSTIC_V2 build PASS**, followed by
strict offline original source/ELF/route admission PASS. This is **not** a
KV260 run. Accepted local build and admission sources are:

- Build: `/home/dna/p07_b4m_diag_v2_build_20261101T031054Z`
- Offline report: `/home/dna/Thesis_Evidence/p07_b4m_diag_v2_offline_20261101T031054Z.json`
- ELF identity: `P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V2`
- V2 ELF SHA256: `952393251a6910c5ca87b817ffdb2d08c0d5239f0f60b350908a78f375936a45`
- V2 .map SHA256: `864624c6511aa5eba204a89fc2f1e3b8a3a46a434a18baa88753282ef5b131da`
- Original accepted XSA SHA256: `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`
- Exact V2 ELF physical PT_LOAD: `[0x00000000,0x00106B00)`,
  filesz 106580, memsz 1075968, same bounds as genuine V1 but different
  ELF bytes. Verified .text `[0,0x11BAC)`, .bss
  `[0x1A080,0x101B00)`, .heap `[0x101B00,0x103B00)`,
  .stack `[0x103B00,0x106B00)`.
- Original route cardinality remains 20,384 + 1,000 = 21,384.
  Original trained model and TRAIN frames unchanged; official TEST sealed.

New isolated `scripts/p07_b4m_diag_v2_physical_run.py` and
`vivado/p07_b4m_diag_v2_xsdb_run.tcl` now pin the exact **V2** ELF SHA,
linker map, firmware identity, source/route offline report, original
accepted shell and identical low-DDR layout. They reuse the historical
independent SAME-SESSION 27-core/descriptor/route/TRAIN staging and
physical readbacks. The V1 runner remains unchanged and refuses the
diagnostic V2 ELF. Distinct V2 mailbox names and B4D2 failure decoding
preserve all failures without creating false full-inference receipts.
The V2 native synthetic launcher tests live in
`tests/test_p07_b4m_diag_v2_physical_run.py`.

The operator explicitly authorized destructive diagnostic KV260 runs
during the continuation chat, including the known unproven low-DDR
boot-firmware coexistence risk. Per-run CLI risk flags remain necessary
to record this accepted risk, NOT to claim firmware ownership proved.
The board must be rebooted after ANY actual takeover/attempt, including
failures; never resume the interrupted Linux. These source additions
and native CI success do not establish a genuine V2 board result.
**P07-B.4m full trained 26-tick physical inference and numerical parity
remain OPEN until independently demonstrated.**

## P07-B.4m original TRAIN physical V2 result and root-cause candidate

User executed the complete genuine V2 JTAG session on KV260 with accepted
original 27×512KiB model context readback, 16KiB binding descriptor
readback, 80KiB output routes, 896KiB input routes, and 123216-byte
TRAIN ordinal 0 ingress readback. V2 A53 ELF physically downloaded,
executed and wrote a terminal 256-byte B4D2 failure mailbox.
The full original-trained inference **FAILED** at stage 9 before the
first logical dispatch was accepted; P03 completed-dispatch register=1.
The failure is real hardware evidence, NOT a completed inference receipt.

- Preserved external evidence: `/home/dna/Thesis_Evidence/p07_b4m_diag_v2_real_20261101T032559Z`
- Real V2 failure mailbox SHA256:
  `79c20f53664afabd3d349b3dccc0f3fc0f1824706863cb5d1409cb9ce493077d`
- Firmware status FAIL `0xDEAD0000`, first_fault=9, adapter=-5.
- B4D2 marker `0x42344432`; scheduler.first_fault=10;
  pager.first_failure_kind=3 (dispatch); trace.first_fault=0.
- `P03_DISPATCH_STATUS=0x22` (DONE + error_core_status),
  `P03_DISPATCH_CORE_STATUS=0x4` (HLS STATUS_SYNAPSE_ROW_BOUNDS),
  `P03_DISPATCH_COMPLETED=1`, packet_count=0.
- Current-read source audit of original TRAIN frame/first core had
  51 events, 39 compartments, 30576 valid source synapses, with no
  source-level HLS synapse-bounds violation.
- User confirmed locally that accepted B4l source-bound descriptor
  metadata has **zero upper count fields**. The accepted descriptor
  `p07_b4l_frozen_bindings.py` constructs metadata solely as
  `core_id | (compartment_count << 7)`.
- **Source-verified exact hardware cause candidate:** the accepted
  `rtl/p08_paged_dispatch_controller.v` maps bits [33:18] directly
  into HLS `synapse_count`, [46:34] into HLS `route_count`, while
  the unchanged P03 adapter appends CURRENT events in [59:47].
  Thus the old registered metadata delivers `synapse_count=0` and
  `route_count=0`, consistent with the observed HLS `0x4`.
  Real physical confirmation that fixing these fields makes HLS
  dispatch succeed is still PENDING.

## Diagnostic V3: isolated firmware-only metadata repair (PC candidate)

New `software/p07/p07_b4m_dispatch_metadata.c/.h` reads the signed
P02 v1 per-core header at offsets +0x20/+0x24/+0x28 to extract
compartments/synapses/output routes. It checks all **27** cores
against the accepted B4l sparse-registration metadata, 512KiB
record ABI, zero initial event banks, and P08 capacity limits
**before any adapter metadata mutation**. Then it adds synapse/route
counts to the existing runtime `hw.metadata[]`. It does NOT change
original B2.4 model context bytes, the 16KiB descriptor, original
P03 adapter code, P08 RTL, or the accepted PL shell.

The distinct `p07_b4m_full_board_diag_v3.c` calls this helper
after accepted B4l descriptor binding and before route mount/paging.
Any mapping discrepancy is a fail-closed stop. On V3 failure-only
B4D3 mailbox `0x42344433`, word 62 carries metadata-repair status
instead of the V2 debug address. The PC mailbox diagnostic can
decode both V2 and V3 without treating a failure as success.

New `scripts/build_p07_b4m_diag_v3.sh` and
`software/p07/build_p07_b4m_diag_v3.py` provide a fresh
independent Vitis 2025.2 A53 ELF build; V3 offline strict source,
XSA, route/ELF/map preflight is
`scripts/p07_b4m_diag_v3_offline_admission.py`.
The operator subsequently built the genuine V3 A53 ELF/map and passed
strict current-source offline admission. The ELF is now SHA-pinned in a
**separate** V3 same-session physical diagnostic launcher. No KV260 V3
execution or numerical parity is yet accepted. Continue SAME P07-B.4m
milestone, draft PR #49.


## V3 operator build accepted for distinct SHA-pinned physical diagnostic experiment

Observed on operator PC (genuine Vitis 2025.2 build / original frozen B2.4
strict offline report; the experiment has NOT yet run on KV260):

- Build: `/home/dna/p07_b4m_diag_v3_build_20261101T034702Z`
- Strict offline report: `/home/dna/Thesis_Evidence/p07_b4m_diag_v3_offline_20261101T034702Z.json`
- V3 app identity: `P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3`
- V3 ELF SHA256: `66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`
- V3 real linker map SHA256: `148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede`
- P03 XSA: `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`
- V3 PT_LOAD `[0x00000000,0x00106B00)`, filesz=106580,
  memsz=1075968. This is the SAME low-DDR physical range as V2
  but with DIFFERENT executable bytes. .text `[0,0x11F2C)`,
  .bss `[0x1A080,0x101B00)`, .heap `[0x101B00,0x103B00)`,
  .stack `[0x103B00,0x106B00)`.
- V3 offline source SHA for metadata helper
  `f73e4d7c0c23b8ceec1e2bc5912a7495241408a548d7fef9e6d7f2feceb89b76`.
  V3 board entry `9349d21f10ea4c09e6491610e365bd13c607a784065eb392f59a8a96a7dcc928`.
- Original registered axons=21384, source routes=20384, output routes=1000,
  model untouched, original MNIST TEST SEALED.
- Firmware low-DDR boot-firmware exclusivity remains independently
  UNPROVEN, regardless of matching previous V1/V2 bounds.

New `scripts/p07_b4m_diag_v3_physical_run.py` pins EXACT V3 ELF/map,
re-derives original source/route/offline report/ELF memory admission,
retains stage-only eight per-run flags plus four V3 A53/low-DDR risk
flags. It uses the unchanged accepted SAME-SESSION 27x512KiB contexts +
original 16KiB descriptor + 80KiB/896KiB routes + signed TRAIN 0
physical staging/readback, *then* calls separate
`vivado/p07_b4m_diag_v3_xsdb_run.tcl` to download V3 and capture 256B
mailbox. The V1/V2 launchers and previous evidence remain untouched.
The native simulated physical launcher tests are in
`tests/test_p07_b4m_diag_v3_physical_run.py`; no physical claim
follows from these mocks.

On V3 failed terminal mailbox, B4D3 failure-only word47 and metadata
fix code at word62 are decoded by the independent diagnostic parser.
Failures cannot be accepted as valid trained physical inference.
On a verified structural success, do NOT claim independent full-neuron
numerical parity from the structural receipt alone. Reboot KV260 after
ANY actual destructive board takeover/attempt, even on failure.

## Diagnostic V3: 2026-11-01 first KV260 takeover failure (pre-PL)

Operator ran V3 `scripts/p07_b4m_diag_v3_physical_run.py --mode execute`
with exact registered model, TRAIN 0, genuine hash-pinned ELF/map, and
destructive approvals. Read-only PC host gates completed:

- `P07_B4M_DIAG_V3_ALL_27_ORIGINAL_P02_METADATA_COUNTS_HOST_VERIFIED=1`
- `P07_B4M_SIGNED_MODEL_TRAIN_GENUINE_ELF_HOST_GATE_PASS=1`

The very FIRST physical action, the historical P07-B.4i CPU stop/FPD width
gate, failed before PL programming, before all DDR staging, and before
ELF download or inference:

```text
P07_B4I_STOP_WIDTH_GATE_FAIL_REBOOT_REQUIRED=1
P07-B.4i stop failed for Cortex-A53 #0: Cannot halt processor core: power down
```

- Original external evidence: `/home/dna/Thesis_Evidence/p07_b4m_diag_v3_real_20261101T040103Z/ps_width.log`
- No B4D3 failure mailbox was produced. No physical V3 HLS count fix
  verification, no dispatch, no numerical parity.
- Precise software mismatch discovered: historical
  `vivado/p07_b4i_stop_and_width_gate.tcl` handled exact XSDB string
  `The core is powered down`, but operator XSDB actually returned
  `Cannot halt processor core: power down`. It rejected this before
  the existing bounded retries, PS-width checks, or guarded processor reset.
- The gate now treats ONLY those two complete error strings as the same
  observed power-down state. It still checks both FPD and LPD PS-width
  raw registers before trying a guarded Track-A processor reset; it still
  **requires a subsequently confirmed A53 #0 stop**, does not waive a
  processor halt and does not program PL or transfer DDR if this fails.
  Secondary down-state remains only an observation, never a CPU0 pass.
- Additional native Tcl simulations exercise the operator's exact XSDB
  wording, successful guarded recovery, unavailable reset, wrong PS width,
  ambiguous multi-line errors, and secondary-core handling.
- After ANY actual XSDB takeover failure, reboot/power-cycle KV260;
  never resume the potentially disrupted Linux process. Use a NEW external
  evidence directory on retry, preserve this one unchanged.

This is a takeover-controller defect / environmental CPU state problem,
NOT evidence that the original trained HLS fault is resolved or that the
metadata fix failed. P07-B.4m remains OPEN, PR #49 draft.

## 2026-11-01 — genuine original TRAIN0 26-tick V3 physical STRUCTURAL PASS

Operator reran the exact admitted V3 experiment on KV260 after successful
standalone A53 stop / PS FPD+LPD 128-bit verification. **Real V3 hardware
success is supported by same-session complete byte-exact DDR staging,
A53 firmware downloaded/executed, 256-byte terminal DONE mailbox captured,
and strict independent structural receipt acceptance.** This supersedes
the *V3 first-takeover-attempt* failure as the latest observed board result;
that earlier failure remains preserved separately.

- Physical evidence directory: `/home/dna/Thesis_Evidence/p07_b4m_diag_v3_real_20261101T041302Z`.
- Original 27 frozen × 512KiB P02 model physically staged/read back;
  original 16KiB binding SHA `2f0a5299a3948d7e0d4d48c265d199616fd3709d966343629596464687f611eb`;
  SHA-verified 80KiB output routes, 896KiB input routes and 123216-byte
  original TRAIN validation 0 ingress.
- V3 actual A53 ELF `66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`
  downloaded and observed terminal. Original accepted XSA preserved.
- Raw 256-byte **actual V3** physical mailbox SHA256:
  `5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`.
- Strict P07-B.4m structural receipt: **702/702 real HLS dispatches,
  26/26 barriers, 702 page-ins, 699 runtime dirty page-outs, 3 final
  page-outs, 307666944 page-read bytes, 74760192 page-write bytes**.
- Registered axons=21384, original external current=31512,
  physical bank7 source spikes=1514, real P03 packet words captured=1489,
  NEXT packets inserted=1489.
- All 1010 compartments traced per tick; physical cumulative trace
  `FNV64=0xB59CA8594D6E64AD`.
- Physical TRAIN0 readout predicted class **1** with 10-class spike
  counts `[0,25,0,0,0,0,0,0,0,0]`. The original independent B2.3 TRAIN0
  expected class/readout counts must still be compared before any
  inference-correctness claim. Label is NOT implied by this receipt.
- Firmware confirmed no P03 errors or scheduler/pager trace faults and
  structural PASS `P07_B4M_DIAG_V3_STRUCTURAL_RECEIPT_ACCEPTED=1`;
  `independent_full_neuron_numerical_parity_verified=false` remains TRUE.
- These observations strongly support the metadata omission as root cause
  of V2's immediate `STATUS_SYNAPSE_ROW_BOUNDS` failure. They do NOT
  establish bit-exact neuron-by-neuron parity against an independent host.
- Official MNIST TEST is still `SEALED_NOT_ACCESSED`.
  Boot firmware low-DDR exclusivity independently UNPROVEN, as before.

The next action is **PC-only numerical investigation of this real capture**:
new `scripts/p07_b4m_v3_train0_scalar_vs_physical.py` re-verifies
original B2.4 frozen assets and JTAG physical readback bytes, and computes
26-tick reference scalar LIF state trace from original
`network_source.json` + TRAIN0 raw pixels. It independently reconstructs
the actual P07 HLS trace/after-state FNV byte encoding, compares all six
available aggregates plus 26-tick FNV against the existing real V3 mailbox,
and verifies the scalar SHA against original frozen B2.3 monolithic
numerical witness. No new board contact or HLS changes are needed for
this check. **Only a matching aggregate/FNV can be called numerical
fingerprint agreement, not raw per-neuron bytewise numerical parity.**
No fake/synthetic mailbox is accepted as real evidence.
P07-B.4m remains open pending this parity audit and interpretation.

## 2026-11-01 read-only independent scalar checker: real frozen ABI bug

Operator's *real original V3 physical evidence* passed all source/DDR/readback
gates and B2.3 frozen scalar replay before crashing inside
`expected_counters()` on an incorrect Python API assumption:

```text
AttributeError: 'IngressRoute' object has no attribute 'source_input'
```

Frozen P06 B1.2 defines
`IngressRoute(input_population, input_index, destination_core, destination_axon)`.
The checker (and its former synthetic fixtures) mistakenly used
`source_input` and `source_index`. Both corrected and regression tests now
construct the genuine frozen compiler `IngressRoute` class to prevent
future mock-only false positives. No original model/compiled mapping,
accepted A53 ELF/map, P03 HLS, DDR physical evidence or bitstream changed.
No hardware rerun needed. **Numerical checker has NOT yet passed on real
evidence**; next action is the operator's host-only rerun and evidence
review, not an inference acceptance claim.

Milestone sequence per roadmap: if complete original TRAIN0 physical vs
independent scalar counters/FNV64 all pass, accept bounded P07-B.4m
witness conditionally, then undertake **P07-B.5 scaled TRAIN-derived
multi-frame validation / physical per-neuron parity** and **P07-B.6
acceptance/closeout**, before **P08-B scaled physical timing/traffic**
measurements. A matching FNV64 is strong fingerprint evidence, not
literal bytewise capture of all `26 * 1010` neuron updates; preserve that
evidence boundary. PR #49 remains draft, unmerged; no official TEST
unseal is authorized.

