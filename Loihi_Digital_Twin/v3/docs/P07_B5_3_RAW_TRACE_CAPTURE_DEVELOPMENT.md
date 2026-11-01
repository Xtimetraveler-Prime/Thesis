# P07-B.5.3 — Exact physical neuron-trace capture: new firmware candidate

**Status (2026-11-01): IN DEVELOPMENT. B5.3.1 native-only C trace sidecar
writer + regression tests IMPLEMENTED / CI PASS; actual signed Vitis ELF,
sidecar physical DDR ownership, real JTAG readback, and full physical
byte-for-byte parity NOT YET VERIFIED OR APPROVED.** P07-B.5 final
milestone remains OPEN, P07-B.6 and P08-B remain gated, and original
official MNIST TEST remains sealed.

## B5.2 entry evidence / safe scope

The operator completed and independently reverified all four
**genuine physical** frozen TRAIN 27-core sessions (ordinals 0,1,2,0).
Every run reproduced all signed scalar aggregates and 26-tick
P03 bank7 trace FNV64. The original ordinal0 second attempt produced
the **same 256-byte physical mailbox SHA256** as the first:

`5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda`

Four-run report:
`/home/dna/Thesis_Evidence/p07_b5_fourrun_original_train_20261101T194900Z.json`;
[bounded B5.2 acceptance ledger](P07_B5_2_2026_11_01_REAL_FOUR_SESSION_FINGERPRINT_ACCEPTANCE.json).

**These are strong fingerprint reproducibility results but NOT direct physical
bytewise validation of every hidden/readout membrane state.** The
original V3 physical terminal mailbox contains one cumulative FNV64
over 26 x 1,010 actual 256-bit HLS trace words, not their raw bytes.
The independent host can already serialize the exact expected
26 x 1,010 x 32B original integer-scalar trace using
`scripts/p07_b5_raw_trace_reference.py`.

## Candidate B5.3 experimental RAW sidecar geometry

**Candidate memory only, not independently authorized physical ownership:**

| Item | Exact value |
| --- | --- |
| HLS debug source | P03 bank 7, original 256-bit per-compartment raw trace |
| Companion check | P03 bank 1 committed after-state; original V3 hooks enforce this |
| Logical schedule | 26 ticks, each 27 cores in ascending order |
| Core counts | frozen 1,000 hidden + 10 readout = 1,010 compartments |
| Record size | 32 bytes = 8 little-endian uint32 words |
| Total records | 26,260 |
| Total raw trace | **840,320 bytes** = **210,080 uint32 words** |
| Proposed additional DDR base | `0x42000000` |
| Proposed additional DDR end EXCLUSIVE | `0x420CD280` |
| Extra reader | dedicated new B5 physical XSDB PSU readback, NOT implemented |
| Accepted production V3 firmware | unchanged, not reused for new B5 ELF |
| Root B2.4 model / P03 PL | unchanged |
| Official B2 TEST | SEALED |

The proposed sidecar does **not** overlap the original known P02
27×512KiB model span `[0x40000000,0x40D80000)`, the original
input routes `[0x41000000,0x410E0000)`, original ingress
`[0x41100000,0x411E0000)` (maximal reserved frame), original binding
descriptor `[0x43FC0000,0x43FC4000)`, original output routes
`[0x43FC4000,0x43FD8000)`, or accepted 256B mailbox
`[0x43FF0000,0x43FF0100)`.

**Disjointness does NOT prove the physical region is free** relative
to PS boot firmware, memory protection, Linux carve-outs, system
allocators, coherent masters, hardware address decoding, or other
software. It must be reviewed independently against the actual KV260
memory map/owners BEFORE any Vitis B5.3 firmware runs or DDR
overwrites. The existing V3 A53 low DDR
`[0x00000000,0x00106B00)` exclusivity is independently UNPROVEN
as well. Neither original twelve destructive approvals nor
software-only tests prove new sidecar ownership.

## B5.3.1 native-only completed implementation (NO BOARD CONTACT)

Two new **additive-only** files:

- `software/p07/include/p07_b5_raw_capture.h`
- `software/p07/p07_b5_raw_capture.c`

The C module accepts caller-owned, exactly 210,080-word sidecar
memory, validates all original 27 per-core compartment counts
(sum **exactly 1,010**; readout core 26 must contain 10), clears
exactly the provided buffer, then serializes original 8-word
P03 bank7 values **without recomputing them**. It enforces
**exactly** each `(tick, core, compartment)` in canonical order,
rejects duplicate/skipped/late/out-of-range neurons, rejects
nonzero bits in the reserved high trace word/spike flag, refuses
overrun, and finalizes only after all 26,260 records.

This is a **bare C serializer**. It is not yet hooked into the real
A53 dispatch callback, is not included in the accepted V3 ELF
build and has not physically written any board memory. A successful
native test does **not** demonstrate on-board capture.

Native unit tests `tests/test_p07_b5_raw_capture_native.py` compile
the actual new C implementation with host GCC and use ctypes to
test all 26×1,010 correctly ordered synthetic words, exact little-endian
840,320B serialization, physical-buffer canaries,
wrong metadata/capacity/alignment, duplicate/skipped records,
malformed reserved bits, and incomplete trace poison behavior.
These tests cannot be substituted for an XSDB physical readback.

## B5.3.2 work still needed (NEW FIRMWARE AND SHA GATES)

1. **Independent physical DDR and boot ownership review first.**
   Prove or separately accept the specific sidecar address risk
   without weakening the low-DDR risk recorded for V3.
2. Construct a separately named
   `P07_B5_A53_TRAIN_RAW_TRACE_DIAGNOSTIC_V1` standalone A53 ELF
   using an isolated **new** Vitis build and GNU linker map; NEVER
   overwrite accepted `p07_b4m_diag_v3_26tick.elf` or its map.
3. Add the new capture call **only** to a separately staged B5
   copy of the existing
   `p07_b4m_spike_trace.c` callback, immediately after the
   physical P03 bank7 and independently cross-checked bank1
   reads and **before** HLS slot eviction. This avoids doubling
   debug MMIO reads or using software-reconstructed trace bytes.
   Do not modify the repository's accepted B4m hook.
4. Add a dedicated B5 main/registration path to bind the approved
   sidecar, clear it **before** first HLS dispatch, require 26,260
   ordered updates, call `p07_b5_capture_finalize()`, flush exactly
   the new sidecar from A53 DCache, and expose an independent
   **B5-specific** terminal mailbox. A B4m V3 mailbox must not be
   repurposed or falsely stamped as a B5 trace receipt.
5. Independent PC-only source/ELF/physical range / XSA/route
   admission with distinct hashes; new physical launcher must
   refuse synthetic/mock trace artifacts and missing external
   run approvals. Source staging, Vitis build and offline checks
   cannot themselves authorize or claim a new board run.
6. In one separately authorized fresh JTAG physical session,
   stage and **physically read back** all original 27 P02 records,
   bindings/routes/one fixed original TRAIN input; run accepted
   P03 bitstream with new signed B5 ELF; capture the distinct
   B5 mailbox; physically read back **all 840,320 bytes** from
   the reserved B5 sidecar using the PSU debug target. Preserve
   readback and source hashes outside the repository.
7. Recompute original frozen scalar reference using
   `scripts/p07_b5_raw_trace_reference.py`; independently compare
   all bytes and report first
   `tick/core/compartment/population/neuron-index/field`
   mismatch. Require exact physical provenance and fresh mailbox
   before reporting `full_raw_neuron_trace_equal=true`.
   The existing `--mode compare-unverified` intentionally
   labels even an equal binary as unauthenticated; it is not a
   genuine hardware-acceptance route by itself.
8. Record a separate actual power-cycle/recovery attestation
   for P07-B.5.2 sessions (not derivable from mailboxes), and
   only after all remaining physical gates pass request explicit
   operator signoff for final P07-B.5/P07-B.6 transition.

**No B5.3 real hardware launch is implemented, claimed or authorized.**
Do not run older V3 launchers with a mismatched ELF or try to
patch accepted frozen binary/weights to bypass SHA admission.

## Operator PC-only development checks (safe today)

```bash
cd ~/Git/Thesis
git switch agent/v3-p07-b5-scaled-multiframe-validation
git pull --ff-only origin agent/v3-p07-b5-scaled-multiframe-validation
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b5_scaled_validation.py \
  tests/test_p07_b5_raw_trace_reference.py \
  tests/test_p07_b5_raw_capture_native.py
```

Regenerate the signed scalar raw transcript for the original fixed
TRAIN0 witness; this is still HOST-ONLY, no new real KV260 data:

```bash
export P07_B4L1_STAGE="$HOME/Thesis_Evidence/p07_b4l1_original27_20261022T204013Z"
export P07_B4M_STAGE="$HOME/p07_b4m_frozen_inputs_20261023T034626Z"
export P07_B5_RAW_REF="$HOME/Thesis_Evidence/p07_b5_train0_expected_raw_$(date -u +%Y%m%dT%H%M%SZ).bin"
export P07_B5_RAW_REF_JSON="$HOME/Thesis_Evidence/p07_b5_train0_expected_raw_$(date -u +%Y%m%dT%H%M%SZ).json"

PYTHONPATH="$PWD/src" python scripts/p07_b5_raw_trace_reference.py \
  --mode reference --ordinal 0 \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --staged-dir "$P07_B4L1_STAGE" --routes-dir "$P07_B4M_STAGE" \
  --expected-raw "$P07_B5_RAW_REF" --out "$P07_B5_RAW_REF_JSON"
stat -c '%n %s bytes' "$P07_B5_RAW_REF"
sha256sum "$P07_B5_RAW_REF"
cat "$P07_B5_RAW_REF_JSON"
```

Expected if the real frozen scalar oracle and raw FNV embedding agree:
`P07_B5_RAW_SCALAR_REFERENCE_REPORT=...`,
`P07_B5_FULL_RAW_PHYSICAL_TRACE_AUTHENTICATED=0`, and a real output
file of exactly 840,320 bytes. **This raw scalar success is NOT
physical B5.3 acceptance.**
