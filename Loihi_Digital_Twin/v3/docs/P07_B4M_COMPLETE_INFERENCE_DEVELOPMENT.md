# P07-B.4m — consolidated full 26-tick inference implementation

**Current status:** All primary software components for the new full
26-tick physical inference **candidate** have been implemented in the same
P07-B.4m milestone. They require native regression acceptance, a genuine
operator-local Vitis 2025.2 ELF build, immutable frozen TRAIN-derived image
packaging, explicit low-DDR ownership review, and real KV260 physical
acceptance. **No real B4m complete 26-tick physical inference has been run
or numerically accepted.** P07-B and P07-B.5/B.6 remain open. No additional
micro-milestones will be opened for these implementation workstreams.

## Frozen physical baseline entering this milestone

Accepted real KV260 P07-B.4l first epoch:
- immutable original 27×512 KiB trained P02 contexts physically staged
  and byte-exact readback, plus original 16 KiB binding descriptor;
- original P03 FPD/LPD128 BIT/VIO and standalone A53 first epoch;
- **27 physical P03 dispatches, 27 page-ins, 24 dirty page-outs**;
- **first global barrier pending and deliberately UNACKNOWLEDGED**;
- empty CURRENT banks, **0 physically captured spike packets**,
  no user image, no routed NEXT commit, no later tick, no numerical parity.

This evidence and the physically accepted B4l ELF remain unchanged.

## New full-inference implementation in the same milestone

| Component | New code | Scope |
| --- | --- | --- |
| Epoch routing and global barrier | `p07_b4m_epoch_bridge.c/.h` | Original B3c1/B2b canonical P06B13R1 packet decode, original B3c3 physical NEXT commit and original B3c2 real-barrier ACK, always ordered and fail-closed. |
| Independent HLS source-spike readback | `p07_b4m_spike_trace.c/.h`; optional dispatch-time hook in original B3c2 | Original HLS `trace_words` contains spike bit 192 (debug bank 7); read **every processed neuron before physical slot eviction**, cross-check 64-bit post-state against P03 state debug bank 1, sort source spike pairs canonically. A defective trace poisons B3a/B3c2 before ACK. |
| Complete A53-ready control loop | `p07_b4m_full_inference.c/.h` | Immutable signed B2.4 compiled/audit digest admission, B4a external CURRENT injection combined with prior NEXT, 27 real P03 dispatches/tick, trace proof, packet route, 26 acknowledged global barriers, 3 final dirty slots, readout neuron spike-count argmax and measured original P03 page bytes. Code path does not pretend synthetic results are physical. |
| Original B2.4 frozen route/table image | `scripts/p07_b4m_frozen_inputs.py`, `p07_b4m_frozen_routes.c/.h` | Host verifies original 33 asset frozen B2.4 snapshot; constructs immutable output+input route stage images and three fixed TRAIN-derived validation frames, with original image SHA and accepted training split. C mounts only verified SHA payload/registered P03 axon routes. **Official TEST never opened**. |
| Distinct standalone A53 candidate | `p07_b4m_full_board.c`, `build_p07_b4m_full.py`, `scripts/build_p07_b4m_full.sh` | Brand-new `P07_B4M_A53_TRAIN_26_TICK_CANDIDATE_V1` firmware. Accepted P03 XSA kept pinned; separate fresh Vitis workspace, source imports, ELF and GNU map. Existing B4l ELF and source are never rebuilt or overwritten. |
| Independent result schema | `scripts/p07_b4m_verify_full_receipt.py` | Strict 256 B A53 mailbox schema, 702 dispatches/26 barriers/702 page-ins/699 runtime dirty page-outs/3 final outs under ascending schedule; P03 page byte accounting, source spike/packet/NEXT counts, readout argmax and preserved OFFICIAL TEST seal. The structural receipt explicitly reports `independent_full_neuron_numerical_parity=false`. |
| Native fake-MMIO regression | `tests/test_p07_b4m_*py` and `tests/native/p07_b4m_*c` | C11 original P03 model: full external nonzero 784px input, 1010-compartment topology, 702 dispatches, 26 verified barriers, routing, readout, trace and final flush; bad CRC/spike provenance/stale barrier/route SHA/debug fault all fail closed. **Synthetic, not a KV260 run.** |

## Fixed DDR allocations proposed for future approved standalone sessions

The old original 27×P02 records occupy `[0x40000000,0x40D80000)`;
the physically accepted B4l descriptor occupies
`[0x43FC0000,0x43FC4000)`. New proposal (NOT staged on the KV260 yet):

| Purpose | Exclusive allocation |
| --- | --- |
| Original B2.4 output route descriptor, fixed SHA-bound 80 KiB | `[0x43FC4000,0x43FD8000)` |
| Original B2.4 input route descriptor, SHA-bound fixed 896 KiB | `[0x41000000,0x410E0000)` |
| Exactly one original TRAIN-derived P06B13I1 ingress image, up to 896 KiB | `[0x41100000,0x411E0000)` |
| Existing fixed result mailbox, 256 B | `[0x43FF0000,0x43FF0100)` |

All addresses are disjoint from the original 27×P02 contexts,
original 16 KiB descriptor, and each other; this is **not independent
proof of low-DDR firmware ownership**. The enlarged Vitis .bss buffers
include a 442,368 B full CURRENT staging array, two 98,432 B B1.3
frame buffers, a 65,536 B immutable source route array and HLS
packet buffers. Consequently the new genuine ELF's physical PT_LOAD
end may be MUCH larger than the accepted B4l `0x42D40`: **never reuse
the old low-DDR exemption/ELF SHA or call the physical execute runner
without separately reviewing the actual new ELF/map and ownership.**

## Required verification and remaining physical proof

1. **Native tests**: compile all original B3/P03 modules plus the
   new trace, full control, B4a CURRENT, and route-loader implementations.
   All native fake buses and synthetic witness receipts must pass without
   contacting any real board. CI is not physical evidence.
2. **Real host freeze**: run `scripts/p07_b4m_frozen_inputs.py` on the
   **existing original** B2.4 snapshot and authenticated original
   TRAIN-only IDX directory (never TEST). This must recover
   the accepted B2.3 validation ordinals 0, 1, 2, original raw TRAIN
   indices 37384, 27347, 20178, and original raw image SHA values.
   Its original route cardinalities must be measured and shown
   to satisfy 8192 raw packet/route bounds and physical bank limits.
3. **Vitis ELF/map**: operator builds separate genuine
   `p07_b4m_full_26tick.elf` from the accepted routed XSA, checks
   its real ELF SHA, load/bss/heap/stack extent and physical PS/DDR
   ownership. A linked executable is NOT physical acceptance.
4. **Physical staging and independently verified signed route bytes**:
   a fresh dedicated session must require CPU takeover/FPD128/LPD128,
   original accepted P03 BIT/VIO, original frozen model full 27 DDR
   readbacks, exact old B4l 16 KiB binding readback, NEW route and
   selected TRAIN ingress image readbacks, and a fresh 256 B
   result mailbox. **No full B4m destructive physical execute
   runner is admitted by the present branch.**
5. **True numeric parity**: capture independently verifiable full
   26-tick neuron state/current/voltage/spike/NEXT traces,
   terminal class/predictions, barriers and first-divergence against
   the original frozen 3-frame B2.3 source oracle. The currently
   emitted full-run receipt is a structural/traffic/classification
   witness, **not** full-neuron parity. No P07-B.5 corpus or
   official TEST gate may be opened from receipt alone.

**Offline user commands**: `git pull` the existing P07-B draft branch,
activate the current `.venv-p08`, then:

```bash
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4m_epoch_bridge.py \
  tests/test_p07_b4m_spike_trace.py \
  tests/test_p07_b4m_full_inference.py \
  tests/test_p07_b4m_frozen_inputs.py \
  tests/test_p07_b4m_frozen_routes.py \
  tests/test_p07_b4m_board_candidate.py
```

**Operator safeguards:** no modifications to accepted P03/P05/Track A,
original frozen B2.4 assets, B4l real first-epoch ELF, or the official
TEST protocol. No PuTTY commands beyond existing routine. No physical
KV260 action or new full-ELF download is implied/authorized by native
tests. Draft PR #49 remains UNMERGED.


## Corrected original B2.4 routing cardinalities

The operator's original frozen B2.4 staging succeeded with **20,384 input
routes and 1,000 output routes**, totaling **21,384 registered axons**.
Our earlier requirement of 10,000 output packets was incorrect: a
hidden-to-readout connection's 10 destination weights are expressed by
readout axon synapse templates, not ten independent output packet routes.
The original trained deployment has only 1,000 output routes.

The separate full-inference ELF reserves capacity for up to 10,000
output routes, but this is an upper bound, not the original model's
actual occupancy. The previously built ELF remains the correct
artifact; do not regenerate it simply to reduce unused capacity.

The corrected offline gate requires the exact original **20,384 + 1,000**
route cardinalities, reconstructs both route images byte-for-byte from
the signed B2.4 source, and checks all three TRAIN-derived image
hashes. Genuine ELF section coverage is checked independently, while
expanded low-DDR ownership and real FPGA numerical parity remain NO-GO.

Build in a NEW directory outside the repository, after installing
the user's already verified Vitis 2025.2 environment:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
source ~/Git/Thesis/.venv-p08/bin/activate
export P07_B4L_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
export P07_B4M_BUILD_DIR="$HOME/p07_b4m_full_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p07_b4m_full.sh
```

Next, use the original TRAIN IDX dataset directory from the
accepted B2.3 validation (NOT the official TEST folder) and a
NEW staging directory, for example:

```bash
export P07_B4M_TRAIN_DIR="<your-existing-original-TRAIN-only-IDX-directory>"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_$(date -u +%Y%m%dT%H%M%SZ)"
python scripts/p07_b4m_frozen_inputs.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --train-data-dir "$P07_B4M_TRAIN_DIR" \
  --out "$P07_B4M_STAGE"
```

Once **both** genuine artifacts exist:

```bash
export P07_B4M_ELF="$P07_B4M_BUILD_DIR/vitis_workspace/p07_b4m_full_26tick.elf"
export P07_B4M_OFFLINE_REPORT="$HOME/p07_b4m_admission_$(date -u +%Y%m%dT%H%M%SZ).json"
python scripts/p07_b4m_offline_admission.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --routes-dir "$P07_B4M_STAGE" \
  --elf "$P07_B4M_ELF" \
  --out "$P07_B4M_OFFLINE_REPORT"
cat "$P07_B4M_OFFLINE_REPORT"
```

Expected acceptance includes
`P07_B4M_FULL_ORIGINAL_FROZEN_ROUTE_AND_GENUINE_ELF_OFFLINE_PREFLIGHT_PASS=1`
and **`P07_B4M_PHYSICAL_LAUNCH_AUTHORIZED=0`**. This stage
intentionally does not perform JTAG, PL programming, destructive DDR
staging or trained numerical comparison. An operator-reviewed
next-stage physical plan needs brand-new source/ELF SHAs, expanded
low DDR ownership acknowledgment, physical byte-exact route/input
JTAG stage/readbacks, 26-tick capture and **full frozen oracle**
numerical parity. Neither a passing Vitis build nor native fake
P03 tests closes P07-B.4m physical acceptance.

## 2026-10-23 operator-accepted genuine B4m offline gate and next dedicated physical staging

The operator ran the original offline B4m admission against genuine original
B2.4 source, TRAIN-only input packages, and a new genuine A53 26-tick ELF:

```text
P07_B4M_FULL_ORIGINAL_FROZEN_ROUTE_AND_GENUINE_ELF_OFFLINE_PREFLIGHT_PASS=1
P07_B4M_LOW_DDR_BOOT_FIRMWARE_EXCLUSIVITY_INDEPENDENTLY_PROVEN=0
P07_B4M_PHYSICAL_LAUNCH_AUTHORIZED=0
```

Operator evidence report (existing on their PC):
`/home/dna/p07_b4m_admission_20261023T044340Z.json`.
It records *exactly* 20,384 original B2.4 input routes and 1,000 output
routes = 21,384 registered axons; signed original B2.4 raw TRAIN
input validation ordinals 0/1/2; A53 ELF
SHA `ccbd8c531e5571f929e81613cfee71f54abf341c36412ebcfa7d98e2313e6b70`,
GNU map SHA
`b6d34c354e34075be2e650335a34ea103b72c7927a36c526841006df59a8e8c3`;
true A53 physical PT_LOAD `[0,0x00106B00)`, filesz 106,580,
memsz 1,075,968 bytes. Accepted P03 XSA SHA remains
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
This is an operator-pasted text attestation, **not** an assistant-side
download of their original raw bytes.

The next physical experiment is intentionally divided into two
**execution gates within the existing P07-B.4m milestone**, rather
than additional sub-milestones:

1. **NOW: stage/read back original frozen physical data, NO new ELF launch.**
   `scripts/p07_b4m_physical_staging.py` defaults to read-only
   `--mode preflight` and requires the original B4l accepted 27-record
   stage, 16KiB signed binding descriptor, accepted P03 BIT/PS128,
   exact original B4m ELF/map and operator offline acceptance report.
   For explicitly approved `--mode stage`, the runner HALTS/DISCARDS
   Linux, programs accepted P03 PL, physically stages/readbacks
   original 27×512KiB immutable contexts at `0x40000000`,
   original 16KiB descriptor at `0x43FC0000`, and exactly three
   signed new DDR files via the new
   `vivado/p07_b4m_stage_original_routes_and_train.tcl`:

   | Source | Physical address | SHA256 (ordinal 0) |
   | --- | --- | --- |
   | Original 80KiB B2.4 output routing | `0x43FC4000` | `2405269110585a3921dfc64ed1b2adbf0622c520cfdce8bb6b1ac6d825f23103` |
   | Original 896KiB B2.4 input routing | `0x41000000` | `380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8` |
   | Original B2.3 TRAIN-validation ordinal 0, actual length from original source | `0x41100000` | `2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126` |

   Both TCL and the independent host verifier require byte-exact
   physical readback before producing
   `independent_staging_receipt.json` and
   `P07_B4M_ORIGINAL_27CORE_BINDINGS_ROUTES_TRAIN_STAGING_PHYSICAL_PASS_REBOOT_REQUIRED`.
   Host-native GitHub tests include mock actual XSDB/TCL PSU writes,
   negative readbacks, and each separate explicit hardware approval.
   There is **no ELF download, CPU resume, mailbox inference, or low
   DDR write** in this runner. After any physical JTAG takeover/staging
   attempt, **REBOOT the KV260** before PuTTY/Linux interaction.

2. **LATER: full 26-tick standalone A53 launch.** The separate
   original A53 candidate is compiled, but a new full-execution
   JTAG/mailbox runner is not yet accepted. Expanded physical low DDR
   `[0,0x00106B00)` and all original boot-firmware/coexistence ownership
   must be evaluated and knowingly approved separately. A passing
   physical staging receipt does not authorize an A53 ELF download,
   full inference, numerical parity, official MNIST TEST unsealing,
   or P07-B closeout.

### Operator commands (PC)

Use **existing** verified previous stage directories, never guessed or
substituted paths. The following PC-only preflight does not contact
the board:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
source ~/Git/Thesis/.venv-p08/bin/activate
python scripts/p07_b4m_physical_staging.py \
  --mode preflight \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" \
  --bindings-dir "$P07_B4L_BINDINGS" \
  --routes-dir "$P07_B4M_STAGE" \
  --offline-report "$P07_B4M_OFFLINE_REPORT" \
  --reports "$P07_B4L_REPORTS" \
  --b4i-build "$P07_B4I_BUILD_DIR" \
  --elf "$P07_B4M_ELF" \
  --validation-ordinal 0
```

Required:
`P07_B4M_PREPARED_FOR_DEDICATED_PHYSICAL_STAGING_ONLY=1`,
`P07_B4M_BOARD_TOUCHED=0`,
`P07_B4M_A53_FULL_26TICK_LAUNCH_AUTHORIZED=0`.

For subsequent **user-explicitly-approved destructive staging**,
reuse the same validated arguments with `--mode stage`, a **NEW**
absolute `--evidence` destination outside the repository, and
eight distinct explicit `--... YES` flags. These are not defaults.
The accepted B4l first-epoch physical experiment is NOT a reusable
runner for full B4m 26-tick inference.
