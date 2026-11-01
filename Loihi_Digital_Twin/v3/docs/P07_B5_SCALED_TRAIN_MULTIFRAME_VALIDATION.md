# P07-B.5 — Scaled 27-core trained physical validation

**STATUS AS OF 2026-11-01: B5.1/B5.2 PASS (four original frozen TRAIN
27-core V3 physical fingerprint-parity runs), B5.3 SELECTED ORIGINAL
TRAIN0 PHYSICAL RAW NEURON BYTEWISE PARITY PASS (840,320B / 26,260 records).
B5.4 independent closeout and operator reboot/final acceptance PENDING.
P07-B.6/P08-B gated; PRs #49/#50 unmerged.**

The user independently verified four genuine distinct physical sessions
in the order original frozen TRAIN ordinals **0,1,2,0**, each with
**702 real HLS dispatches, 26 barriers and independent exact
26-tick software-scalar FNV64/input/spike/packet/readout agreement**.
All three pre-registered TRAIN images were correctly classified, and the
independent TRAIN0 repeat exactly reproduced the original 256B physical
mailbox SHA256, all counters and FNV64. The original model and accepted V3
ELF were unchanged; the official MNIST TEST was not accessed.

- Original independent TRAIN0 / TRAIN1 / TRAIN2 reference and full
  physical verification PASS.
- Genuine TRAIN0 repeat physical evidence:
  `/home/dna/Thesis_Evidence/p07_b5_train0_reboot_repeat_real_20261101T193922Z`;
  PC audit:
  `/home/dna/Thesis_Evidence/p07_b5_verify_train0_repeat_20261101T194457Z.json`.
- Genuine four-run consolidation report:
  `/home/dna/Thesis_Evidence/p07_b5_fourrun_original_train_20261101T194900Z.json`.
- The [bounded four-run acceptance ledger](P07_B5_2_2026_11_01_REAL_FOUR_SESSION_FINGERPRINT_ACCEPTANCE.json)
  preserves each raw 256B mailbox SHA256, source evidence paths and
  the explicit remaining validation requirements.

**B5.3 real physical direct raw neuron gate: OPERATOR-VERIFIED PASS.**
New original TRAIN0 evidence:
`/home/dna/Thesis_Evidence/p07_b5_raw_train0_real_20261101T213638Z`.
The signed new B5 ELF/map, physical 256B terminal mailbox and exact
840,320B raw PS/PL debug-bank-7 neuron-state readback were independently
checked using `scripts/p07_b5_raw_physical_verify.py`.
Every one of **26,260** raw neuron records (26 ticks × 1,010
compartments × 32B) was equal to the original frozen scalar reference:
both SHA256 `7fd6d5cbfa44cc1f69745b492c7b60649a49ec5b69c42821ba6619e503554f7d`.
Original 26-tick FNV64 `0xB59CA8594D6E64AD`; 702 dispatches,
26 barriers; all seven independent scalar/physical numerical checks
were true; original same-session 27-core DDR sources/routes/readbacks
verified. [Signed bounded physical B5.3 raw PASS ledger](P07_B5_3_2026_11_01_REAL_ORIGINAL_TRAIN0_840320B_PHYSICAL_RAW_NEURON_PASS.json).
Underlying board binaries remain on the operator PC; the repository
contains provenance ledgers, not falsely manufactured physical bytes.

**Do not claim P07-B.5 fully closed.** Existing B5.2 report still states
`cold_reboot_between_runs_independently_proven=false`; the new B5
raw physical report still states
`user_power_cycle_independently_attested=false` and
`physical_DDR_ownership_independently_proven=false`.
Operator signoff/actual fresh cold reboot and recovery attestations
must be separately obtained and reviewed in **B5.4**. Board-specific
firmware/Linux/other DMA exclusive ownership remains unproven.
Every routed *packet word* is not individually checked by the new
raw neuron recorder; original packet/NEXT **counts** are exact.
The original B4m structural field
`independent_full_neuron_numerical_parity=false` embedded within
B5's reused mailbox decoder only characterizes the older structural
receipt; B5's separately authenticated
`raw_neuron_original_26x1010_bytes_exactly_equal=true`
is the direct bytewise comparison.

New PC-only [B5.4 final independent evidence/reboot acceptance gate](P07_B5_4_FINAL_INDEPENDENT_REVIEW.md)
must recheck all five real physical sessions and the saved reports
before the operator may explicitly close B5.4. No new board
run is required for the review; no automatic acceptance or
merge into `main`.

## Freeze and risk boundaries

- **DO NOT modify or rebuild** signed original 784→1000→10 B2.4
  27×512KiB frozen snapshot, original P03 XSA/bitstream, P07 B4l
  page/bind/DDR/route images, original V3 A53 ELF and GNU map.
- Original genuine V3 ELF SHA256
  `66d628bebed753ae9a5c61b993936b558f00dc31e63bf5748a8d9858ac15f904`.
  V3 GNU map SHA256
  `148b8720bc41253c5d06cece22ffaf59f8f70be7af3976726f5e504f2c379ede`.
- Original registered TRAIN frame ordinals **0, 1, 2**, fixed prior to
  these experiments, raw 784-image SHA256 from
  `scripts/p07_b4m_frozen_inputs.py`; originals are in the
  immutable TRAIN-derived B2.3 26-tick validation report.
- Actual boot-firmware exclusivity for low DDR ELF span
  `[0x00000000,0x00106B00)` remains **independently UNPROVEN**.
  Operator approval of destructive takeover/DDR overwrite is **not**
  evidence that the address range is safely owned by standalone firmware.
  The B5 verifier does not authorize hardware actions.
- Do not call this benchmark official MNIST TEST or measure official TEST
  accuracy before the separately precommitted B2.4 unseal protocol.
- Separate branch `agent/v3-p07-b5-scaled-multiframe-validation`
  branches FROM the preceding draft B4m branch, not merged main. Do not
  merge either draft branch without explicit user review/approval.

## Deliverables / required physical acceptance

**B5.1 — PC-only frozen 3-frame independent oracle [USER-VERIFIED PASS; original reference files rechecked]:**

- Verify entire original B2.4 freeze and 27 original logical contexts and
  20,384 input / 1,000 output routes.
- Independently regenerate original 26-tick **scalar integer** LIF states,
  synaptic accumulators, spikes, and SHA256 trace from
  `network_source.json` for TRAIN ordinals 0/1/2.
- Compare the independent SHA against exact frozen B2.3 original
  monolithic report; generate exact FNV64 used by the real P03 bank7
  trace/committed-state pipeline in original core/compartment order.
- Compute independent external CURRENT events, spike count, P03→NEXT
  packet fanout and all ten readout votes/class. No FPGA or TEST access.

**B5.2 — MULTIPLE *real* physical V3 TRAIN frames + distinct repeat
[USER-VERIFIED BOUNDED 4-RUN PASS; cold reboot proof separate]:**

- Three separate, freshly rebooted, destructive, JTAG-owned V3 executions
  of original ordinal **0, 1, 2**, plus at least **one further ordinal 0**
  independent reboot repeat. Each must use **a new evidence directory**;
  optionally reuse the accepted original B4m ordinal 0 run for one of
  these four required observations, provided its exact full staging and
  physical mailbox evidence is still present. Do not count the same
  evidence directory twice.
- Every run: all 27 signed original P02 DDR records read back, original
  bindings, 80KiB output/896KiB input routing and chosen original TRAIN
  image byte-exact, accepted V3 ELF+map identity, real A53 mailbox,
  702 dispatches, 26 barriers, 1010 traced compartments/tick,
  no failed HLS/pager/scheduler/route gate.
- Every run: 26-tick independent scalar **FNV64**, all ten class
  spike counts, class, external events, neural spikes and P03/NEXT
  packet counts must be EXACT against original software reference.
  Mismatches mean NO-GO; no checkpoint/threshold adjustment is permitted.
- Repeat must have equal full physical structural counter fields, class,
  votes, spikes, packet fanout and trace FNV64. Distinct evidence
  directories alone do not prove a cold reboot; this needs separate
  actual operator reboot attestation. The verifier explicitly preserves
  `cold_reboot_between_runs_independently_proven=false`.
- Implemented: `scripts/p07_b5_scaled_validation.py` supports
  `--mode preview`, `--mode verify` (one run) and
  `--mode consolidate` (precisely 0/1/2/0, in any order), with
  new write-once external JSON reports. `--mode consolidate` reopens
  all four genuine physical evidence directories and reruns provenance
  and numerical checks rather than trusting saved summary JSON.
  An independent V3 board pass for ordinal 0 is NOT automatically
  reinterpreted as multi-frame success.

**B5.3 — Selected **RAW** 26×1010 original neuron trace and packet
numerics [REAL PHYSICAL RAW 26×1010 NEURON BYTEWISE PASS; same-session readbacks authenticated; 2026-11-01]:**

The existing original V3 mailbox contains FNV64 of all 26×1010
256-bit HLS trace words; it does **NOT** contain the underlying
840,320 raw bytes. FNV64 is non-cryptographic: equality is strong
numerical fingerprint evidence but *not* direct byte-for-byte proof of
every state, accumulated synaptic input and emitted spike.

For full raw numerical acceptance, develop a **separately named,
SHA-pinned dedicated B5 firmware and launcher** with a physically
owned additional DDR trace sidecar. Require explicit new destructive
DDR ownership and reset/risk approvals before programming. Capture
exact 32-byte per-neuron trace words for each of 26×1010, 840,320
bytes, in **tick, logical-core, compartment** order. Read back all bytes
physically. Compare the signed-24 bit current/voltage, refractory,
64-bit synaptic accumulator, emitted-spike and before/after state
**byte for byte** to independently encoded scalar oracle on PC.
Selected input/source and routed NEXT packet trace must be verified
or explicitly excluded from claims. First mismatch must identify
`tick/core/compartment/field` with raw offsets. Do not modify
the previously accepted V3 ELF, bitstream, frozen checkpoint or
official TEST to instrument this; a separate B5 binary is mandatory.

**B5.4 — Final B5 acceptance [OPEN; do not mark P07-B.5 closed]:**

- All three TRAIN-derived physical frames have passed the complete
  original independent scalar comparison.
- A genuine independent cold-reboot repeat is reported and reviewed.
- A selected full raw hardware neural trace agrees with scalar reference
  (or any departure is explicitly reviewed as an approved narrower
  acceptance gate; do not silently relabel FNV64 as raw parity).
- Original V3 model/ELF/PS/PL identities, failure/recovery logs,
  original acceptance/TEST seal and physical source evidence recorded;
  no injected fake fixtures counted as physical proof.
- Stop for **user independent verification and explicit acceptance**;
  only then mark P07-B.5 complete, proceed to P07-B.6 freeze/handoff,
  and subsequently P08-B scaling/timing work.

## PC-only B5.1 reference regeneration

From `~/Git/Thesis/Loihi_Digital_Twin/v3`, with existing
`.venv-p08` activated and local original frozen staging intact:

```bash
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B5_EXPECTED="$HOME/Thesis_Evidence/p07_b5_three_train_reference_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
  --mode preview --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" --routes-dir "$P07_B4M_STAGE" \
  --out "$P07_B5_EXPECTED"
cat "$P07_B5_EXPECTED"
```

## B5.2 physical procedure (HISTORICAL REPRODUCTION INSTRUCTIONS; four runs passed)

All four original physical runs have now been independently checked. The
following run instructions are kept for audit/reproduction, **not** a
request to repeat destructive hardware actions. Only B5.3 new, separately
reviewed firmware remains physically outstanding.



The original TRAIN validation **ordinal 1** new physical run has now
PASSED complete same-session staging, 702 dispatches, 26 barriers,
all ten output counts, 26-tick HLS trace FNV64 and independent frozen
scalar comparison. Real readout class **2**, true TRAIN label **2**, 25
readout spikes, 1,852 source spikes, 1,827 routed NEXT packets,
71,994 external events, physical trace FNV64 **0x0EAC411F49856BF3**;
raw 256B physical mailbox SHA
**4410de8c57df98250b0184d352e8edccaeb74bd23a91610579142a44cabf0d95**.
Original genuine TRAIN1 evidence directory:
`/home/dna/Thesis_Evidence/p07_b5_train1_real_20261101T045754Z`;
independently verified read-only report:
`/home/dna/Thesis_Evidence/p07_b5_verify_train1_20261101T050334Z.json`.
The [original ordinal1 physical runbook](P07_B5_2_OPERATOR_ORDINAL1_PHYSICAL_RUNBOOK.md)
is retained as the successful reproduction procedure. The next two
separate, reboot-gated runs are described in the
[ordinal2 / TRAIN0 independent repeat + consolidation runbook](P07_B5_2_OPERATOR_REMAINING_PHYSICAL_RUNS.md).
No independent proof of a cold reboot for the previous run is asserted
from the mailbox. All strict raw-trace/TEST gates remain unchanged.


1. Hard-reboot KV260 and verify a dedicated XSDB server. Never resume a
   Linux session after JTAG takeover. Make a **NEW** evidence dir for
   each run. Physical V3 runner is still
   `scripts/p07_b4m_diag_v3_physical_run.py --mode execute` with the
   **same flags/authorizations** from successful B4m run.
   Set `--validation-ordinal 1` for the second original witness,
   and `--validation-ordinal 2` for the third. Keep the same accepted
   V3 offline report/ELF/map, which cover all three frozen TRAIN frames.
   Never overwrite existing physical evidence.
2. Each physical run is destructive to A53 Linux/JTAG ownership.
   Keep the previously approved 12 explicit risk/overwrite approvals
   separately; they **do not prove** low-DDR coexistence or trace
   sidecar ownership. No new B5 trace-sidecar risk is accepted here.
3. Verify each session with:
   ```bash
   export P07_B5_ONE_REPORT="$HOME/Thesis_Evidence/p07_b5_one_$(date -u +%Y%m%dT%H%M%SZ).json"
   PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
     --mode verify --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
     --staged-dir "$P07_B4L1_STAGE" --routes-dir "$P07_B4M_STAGE" \
     --run "1:/absolute/path/to/new/ordinal1/evidence" \
     --out "$P07_B5_ONE_REPORT"
   ```
   Use `--run 2:/...` for ordinal 2. A genuine original ordinal0
   session can be supplied as `--run 0:/...`.
4. After all four **real**, distinct original TRAIN evidence folders:
   ```bash
   export P07_B5_SUMMARY="$HOME/Thesis_Evidence/p07_b5_multiframe_$(date -u +%Y%m%dT%H%M%SZ).json"
   PYTHONPATH="$PWD/src" python scripts/p07_b5_scaled_validation.py \
     --mode consolidate --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
     --staged-dir "$P07_B4L1_STAGE" --routes-dir "$P07_B4M_STAGE" \
     --run "0:/absolute/path/to/accepted/ordinal0/evidence" \
     --run "1:/absolute/path/to/new/ordinal1/evidence" \
     --run "2:/absolute/path/to/new/ordinal2/evidence" \
     --run "0:/absolute/path/to/new/repeat_ordinal0/evidence" \
     --out "$P07_B5_SUMMARY"
   cat "$P07_B5_SUMMARY"
   ```
   Success marker is
   `P07_B5_INDEPENDENT_MULTI_FRAME_FP_AND_COUNTS_PASS=1`,
   **not** a B5.3 raw numerical parity or milestone closeout.

## B5.3 PC-only raw scalar reference (NEW)

Before designing/running dedicated physical sidecar firmware, the
independent 32-byte P03 bank7 trace reference can be materialized
in an external immutable report and exactly 840,320-byte raw file:

```bash
export P07_B5_RAW_REF="$HOME/Thesis_Evidence/p07_b5_train0_raw_scalar_$(date -u +%Y%m%dT%H%M%SZ).bin"
export P07_B5_RAW_REF_JSON="$HOME/Thesis_Evidence/p07_b5_train0_raw_scalar_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p07_b5_raw_trace_reference.py \
  --mode reference --ordinal 0 \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" --routes-dir "$P07_B4M_STAGE" \
  --expected-raw "$P07_B5_RAW_REF" --out "$P07_B5_RAW_REF_JSON"
sha256sum "$P07_B5_RAW_REF"
```

`scripts/p07_b5_raw_trace_reference.py` implements field-level
first mismatch diagnosis for unverified raw binary files, but
**will not authenticate** a byte stream as a real physical capture
until the separately engineered and JTAG-read-back B5.3 sidecar exists.

No raw B5.3 sidecar has been staged on KV260. No official TEST accessed.
