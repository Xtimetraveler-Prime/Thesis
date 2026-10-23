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


## B4m original dense 10,000-route physical-build correction and operator gate

The *actual* B1.2 trained 784→1000→10 dense mapping has up to
**1,000 hidden source compartments × 10 outgoing readout fanouts =
10,000 compiled inter-core output routes**, exceeding the accepted
B2b/B3c default 8,192 aggregate route buffer. The original 8,192
default remains unchanged for all already accepted B4l/Track A and
old C tests; the **separate fresh B4m Vitis source import** opt-in
replaces the *STAGED COPY ONLY* of the `p07_b2_packet.h` upper bound
with 10,000, expanding packet capture/frame and route buffer geometry.
The 80 KiB DDR output-route image accommodates 10,000 × 8-byte
rows plus 192-byte header/compartment table. The original
per-core 4,096 P03 routing and NEXT event limits still apply and
must fail closed if exceeded by an input pattern. Tests compile both
original and separate dense limits against the unchanged P03 fake bus.

An explicit **PC-only** `scripts/p07_b4m_offline_admission.py` command
now requires:
- the immutable 33-file B2.4 hash-pinned source;
- exactly 10,000 canonical original B1.2 output route rows and
  complete original registered destination axons;
- bit-exact reconstruction of both staged 80 KiB and 896 KiB route
  images from the frozen signed compiler, rather than trusting a
  potentially self-consistent staging manifest;
- all three original TRAIN validation input frames including exact
  raw 784-pixel SHA and identical authenticated external ingress
  routing; official TEST remains sealed;
- a **genuine separately built ELF64 AArch64 low-DDR executable**,
  distinct B4m identity and executable entry, real linker map,
  physical `PT_LOAD` and `.text/.bss/.heap/.stack` boundaries.
  The offline gate hard-rejects `PT_LOAD` memory above 16 MiB,
  a changed entry address, missing sections, or non-zero physical
  LOAD start. **A 16 MiB cap is NOT proof that even 1 MiB of low DDR
  is exclusive of boot firmware/other owners**.

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
