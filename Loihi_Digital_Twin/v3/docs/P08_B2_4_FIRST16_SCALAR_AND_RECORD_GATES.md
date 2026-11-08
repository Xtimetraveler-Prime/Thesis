# P08-B2.4 — First16 independent original-B2.4 scalar reference and record gates

**2026-11-01 source-only development; operator's genuine original first16 scalar execution pending.** The operator reported (a) corrected P08-B2.1 original 1,024-byte C ingress SHA parity successful, (b) new P08-B2.3 real Vitis 2025.2 A53 image-only ELF built, and (c) offline ELF64/AArch64 PT_LOAD check passed, with new ELF SHA `0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1` and linker map SHA `f7ce75a736b6b093066b8df09a8b02aaa41b490fd48c36c23151b4ac22125efc`. Operator report **does not prove DDR exclusivity or authorise destructive hardware execution.** Accepted model and official MNIST TEST remain sealed/read-only.

## Purpose

Before the first 16-image destructive JTAG pilot, provide an independently computed, original frozen 27core B2.4 scalar truth set for **exactly** first 16 of the existing 1,024-image matched P08-A source. The three previous signed B2.3 original TRAIN validation frame references (ordinals 0–2) must reproduce exactly; the remaining 13 are computed fresh using **the same original frozen network**, same 25 input ticks + 1 drain tick, and original compiled neuron placement. It must detect a wrong prediction, incomplete route/spike receipt, dropped or altered 26×1,010 full-trace FNV, a malformed ingress/pixel SHA, or a non-additive/bogus A53 timer. No new training, no validation distribution change, no MNIST TEST and no energy claims.

New files: `scripts/p08_b2_4_scalar_first16.py`, `scripts/p08_b2_4_verify_untrusted_first16.py`, `tests/test_p08_b2_4_numerical.py`, `.github/workflows/p08_b2_4_first16_oracle.yml`. These scripts run entirely on PC and do not invoke JTAG tools or write DDR. The original A53 ELF is **not changed** during B2.4.

### Scalar stage (`scalar_first16.py`)

Reads and authenticates original 33-file B2.4 frozen model, original 27×512KiB P02 record list, original B4MING01 and B4MROUT1 signed route staging, original P08-A3.2 1,024 TRAIN validation source, original B2.1 matched raw pool and 1,024-line ingress hash file. Pins hashes of all original inputs, and checks each of the first 16 route+pixel encoded P06B13I1 frame hashes against the immutable B2.1 manifest. Runs original P06 scalar `pixel_schedule_independent` and `simulate_monolithic`, then the already-accepted original P07-B.5 `expected_counters` and `trace_fingerprint` on original 27core placement. Writes a NEW out-of-repo JSON containing per-image original raw/input hashes, canonical TRAIN source ID, scalar trace SHA, expected 26-tick FNV and per-tick FNV, external CURRENT events, PL source spikes, original P03 output packet count, NEXT count, trained classification and 10 readout spike counts. First 3 ordinal results have separately signed frozen P06 B2.3 reference checks.

**Important**: independent numeric 16 reference is **not** evidence of hardware execution; any measured 16 physical runs must have their own same-session signed and independently read-back verified PL/DDR/ELF/logs.

### Separate input-record verification (`verify_untrusted_first16.py`)

Accepts exactly three externally captured 256B-based binary candidate streams (16×256B neural journals, 16×256B A53 timing sidecars and 1×256B terminal mailbox) plus the independently generated scalar oracle. Rejects wrong CRC32/reserved bits/magic/version/count/index, mismatched per-image 10-class spike vector, expected core counts, source spike events, routes, packet captures, complete raw/ingress SHA, trace FNV or nonmonotonic and incorrectly additive CNTVCT six-phase timing. Requires 702 page-ins, 699 dirty runtime page-outs, three final flushes, 307,666,944 page-read bytes and 74,760,192 page-write bytes (given accepted original deterministic 27/3 core memory page schedule). Requires 16-image **terminal** mailbox PASS, not transient progress.

**Critical provenance distinction:** this accepts **unverified binary files only**, labels all output parity as unauthenticated, and explicitly never asserts that input files came from a genuine P03 physical session. A *separate future* signed XSDB/JTAG execution transcript + same-session readback verifier must independently bind actual hardware evidence to source, ELF, exact original 27core backup, original 16k binding, both frozen route binaries, 1024 source raw pool and 16 journal/timing/mailbox bytes. User must separately approve destructive JTAG after owner-map review.

### Next PC-only operator gate

From repo v3 root after pulling current branch:

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-b-scaled-latency
git pull --ff-only origin agent/v3-p08-b-scaled-latency
git status --short
git rev-parse HEAD
git rev-parse 'HEAD:LitReview.md'
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p08_b1_matched_source.py \
  tests/test_p08_b2_ingress.py \
  tests/test_p08_b2_2_reset.py \
  tests/test_p08_b2_3_image_only.py \
  tests/test_p08_b2_4_numerical.py

export P08_B2_4_SCALAR_REPORT="$HOME/Thesis_Evidence/p08_b2_4_original_first16_scalar_$(date -u +%Y%m%dT%H%M%SZ).json"
test ! -e "$P08_B2_4_SCALAR_REPORT"
PYTHONPATH="$PWD/src" python scripts/p08_b2_4_scalar_first16.py \
  --frozen-dir "$PWD/artifacts/p06_b24_frozen_1000" \
  --a-stage "$HOME/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z" \
  --train-data-dir "$PWD/data/mnist_raw" \
  --routes-dir "$HOME/p07_b4m_frozen_inputs_20261023T034626Z" \
  --ingress-dir "$HOME/Thesis_Evidence/p08_b2_1_original1024_20261102T003256Z" \
  --out "$P08_B2_4_SCALAR_REPORT"
sha256sum "$P08_B2_4_SCALAR_REPORT"
```

Expected markers:
`P08_B2_4_ORIGINAL_SCALAR_FIRST16_INDEPENDENT_PASS=1`,
`P08_B2_4_ORIGINAL_FIRST3_SIGNED_WITNESSES=REPRODUCED`,
`P08_B2_4_SCALAR_FRAME_COUNT=16`,
`P08_B2_4_ACTUAL_HARDWARE_PARITY=NOT_TESTED`.

**There is no real 16-image journal yet. Do not call the binary verifier against simulated data and claim physical success.** The current genuine new ELF is a **1024-frame** loop; before a pilot, build a separately identifiable 16-frame **bounded pilot ELF**, with a new Vitis hash and linker map, distinct on-device terminal marker, and a host JTAG readback runbook. That pilot must also collect signed source, raw/model/route and timing/journal evidence and get operator-specific destructive approval.

## Remaining physical blockers

- Original full `[0x43000000,0x43D80000)` 27core immutable backup physical source/readback not yet staged or separately owner-proven. Also verify `[0x40000000,0x44000000)` ownership versus boot ROM/FSBL/TF-A/Linux/RPU and PL DMA, new ELF linker and stack/heap.
- No 16-frame separately built, SHA-pinned A53 pilot ELF / source receipt. Current new 1024 ELF **MUST NOT** be used as a pilot.
- No independently authenticated same-session physical 16-image JTAG evidence, actual trace and journal readback, or numerical equality claim. Physical latency remains **NOT MEASURED**.
- No separate detailed-tick A53 ELF or full selected 1023 raw trace. Six paired accepted Track A/B cold-boot runs, P09 and original TEST are deferred.

**Original P07-B 27core and P08-A accepted results, protected root `LitReview.md`, frozen 33 B2.4 files, accepted original P07 V3/B5 ELF/trace, P03 bitstream/XSA and official MNIST TEST are not modified.**
