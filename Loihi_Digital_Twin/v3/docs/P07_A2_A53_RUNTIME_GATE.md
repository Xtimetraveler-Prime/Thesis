# P07-A2 — Autonomous A53 frame runtime / first physical inference candidate

**Branch:** `agent/v3-p07-a-784-axon-streaming`.
**Status:** P07-A1 USER-ACCEPTED. P07-A2 **USER VITIS BUILD GATE PASSED**
on 2026-10-17, as evidenced in `P07_A2_NATIVE_BUILD_ATTESTATION.md`;
**XSDB/KV260 PHYSICAL TRACE GATE PENDING**. The first build's ELF has
been **superseded** by the mandatory live-scheduler-timestep trace fix.
The corrected source must be rebuilt to a fresh ELF before programming
the board. No merge until the user explicitly approves.


## 2026-10-17 native build outcome and corrected physical admission

The user's successful Vitis build produced the original standalone
`p07_a2_board.elf` SHA-256
`64601cc0ea491f9ae3e3ba8287cd9d52640b8c1d12273e8c8601c1f1aeac4c96`
using accepted routed XSA SHA-256
`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
It passed the Vitis build and DDR program-headers audit.

**STOP: do not execute that original ELF.** Source review uncovered the
board trace-reader using an unbound static `p03_rt` rather than the live
per-frame P03 runtime. It would record all 26 timestep samples into the
timestep-zero full-trace slot. The fix binds the actual runtime object
and has distinct firmware identity:
`P07_A2_KV260_A53_FROZEN_TRACK_A_V1_TRACE_CONTEXT_FIX`.
The build shell **and** XSDB launch both reject the stale identity.

For the first device gate, after pulling the current P07 branch and
re-running native tests, create the deterministic three-image batch in
the earlier section. Rebuild into a **new** absolute, unique
`P07_A2_BUILD_DIR`, using the known accepted XSA. Repeat the same build
command earlier but use a fresh timestamp:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
export P07_A2_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P07_A2_XSA_SHA256=52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
export P07_A2_BUILD_DIR="/tmp/v3_p07_a2_tracefix_$(date +%Y%m%dT%H%M%S)"
bash scripts/build_p07_a2.sh
```

The new ELF SHA-256 is a **new, distinct identity**, which must be
collected. Native success marker is
`P07_A2_VITIS_NATIVE_GATE_PASS=1`.

Once the corrected rebuild and batch creation pass, use the guarded
physical gate script instead of manually repeating independent XSDB
commands. This script checks the XSA/bitstream/ELF source equivalence
against the checked-out branch; validates P07 batch and immutable DDR
hashes; refuses an existing evidence directory; checks the live FPD128
bus width; stages/readbacks the exact bytes; programs the *accepted*
P03.2c bitstream; launches the A53 **once**; captures the entire 64KiB
mailbox; and runs the software first-divergence comparison.

**Requires the KV260 be freshly rebooted into the accepted JTAG-owned,
bare-metal, non-Linux DDR test environment.** These steps halt A53
processors, overwrite 0x40000000..0x43FFFFFF, and require a reboot
afterward whether they pass or fail. Never run while Linux is actively
using this DDR.

```bash
export P07_A2_BATCH_DIR="$PWD/artifacts/p07_a2_batch3_v1"
export P07_A2_RUN_DIR="/tmp/v3_p07_a2_physical_$(date +%Y%m%dT%H%M%S)"
export P07_A2_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p07_a2_physical.sh
```

If the board has not been rebooted or physically prepared with the
accepted P03.2c boot/FPD128 configuration, do not set the overwrite
confirmation flag; first restore that established board test state.
Successful physical end markers:
`P07_A2_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS`,
`P07_A2_PHYSICAL_TRACES_EXACT=1` and
`P07_A2_GATE_FULL_PHYSICAL_PASS=1`. These MUST be obtained from the
**real XSDB mailbox**, not inferred from a build log. If the first
failure occurs, stop, preserve the entire evidence directory, reboot
the KV260, and report the earliest error/trace mismatch.

## Completed engineering work, NOT a board result

- `software/p07/p07_a2_runtime.c`: P07-specific wrappers around **unchanged**
  accepted `p03_rt_execute`, exactly one core/one slot/26 barrier steps;
  inject *compiler-mapped* current events ahead of dispatch, collect the
  ten output trace bits at bit 192, route to NEXT until tick 24, **discard
  outgoing tick-25 packets** (P03 scheduler acknowledges their consumption
  but the separate `committed_routes` counter excludes boundary drops);
  count class spikes, lowest-index tie break, all-silent class 0.
- `software/p07/p07_a2_board.c`: *unverified physical candidate* using
  the accepted P03 FPGA bridge/IO APIs, a separately versioned batch
  header and mailbox, an immutable frozen master DDR image, per-frame
  DDR full re-seed, per-frame fresh P03 adapter/valid-axon registration,
  cache maintenance and full P03 page-in. The 816 valid sparse axon IDs
  are read from the accepted DDR bank, **not guessed as 0..815**.
  A53 owns every event, core dispatch, packet route and barrier. The PC
  only stages files, downloads/starts the ELF once and reads evidence.
- `p07_a2_sha256.c`: portable SHA-256 of the **entire frozen 512KiB
  staged master**, checked on board against the user-supplied digest.
  Both the P07 ingress file's DDR digest and compiler fingerprint are
  checked against immutable accepted identifiers. The input wire CRCs
  remain integrity checks, not cryptographic signatures.
- `p07_a2_batch.c` and `src/loihi_twin_v2/p07_a2_batch.py`:
  independent Python/C11 64-byte `P07A2B01` envelope, 1..16 complete
  P07-A1 2480-byte frame records. All images must reference the SAME
  frozen compiler/context identities. A53 resets state/queues/counters
  between each of these images **autonomously**.
- `p07_a2_evidence.py`: strict full-64KiB mailbox parser and per-tick,
  per-compartment first divergence against frozen `replay_p03_image`
  and the compiled P06 learned checkpoint. Frame output spike counts,
  actual routed/dropped packet counts, and captured 26x42 x 256-bit
  HLS traces are compared independently. This is not a fabricated result.
- Vitis build scripts, isolated XSDB prepare/run scripts and native
  tests are version-controlled. CI host execution includes the REAL
  P03 C scheduler with deterministic **mock** PL callbacks, verifies
  two frame resets and negative overflow, a C11 SHA-256 implementation
  against hashlib including 512KiB data, and validates native parser
  negative fields. **Mock PL != actual neural computation**.

## Physical DDR map (P07 application ONLY, not a P05G deployment)

| Address | Size | Purpose |
|---|---:|---|
| `0x40000000` | 512 KiB | resettable core 0 P02 backing loaded by A53 |
| `0x43F00000` | 512 KiB | immutable accepted static P02 master (never PL-written) |
| `0x43F80000` | up to 39,680 B | 1..16 concatenated P07-A1 input records |
| `0x43FE0000` | 64 B | independent P07A2B01 versioned batch descriptor |
| `0x43FF0000` | 64 KiB | P07R results/first-frame-selected full trace |

All these addresses are inside the reserved P03/P05 dedicated fixture DDR
window. They must NOT be run under Linux or a different memory ownership
policy. A53 full-image context re-seeding is a deliberate initial
correctness choice, **not a P08 latency/energy-optimized path**.
A single batch is at most 16 frames: this is a physical diagnostic
deployment bound, NOT the sealed official MNIST evaluation protocol.
Expanding streaming for all 10k images will need separate P07-A4 planning
after stable device conformance and P08 measurement policy freeze.

## Batch bytes

64-byte header: ASCII `P07A2B01` [0:8], LE32 version=1 [8:12],
number of frames 1..16 [12:16], LE32 record bytes=2480 [16:20],
LE32 input base=0x43F80000 [20:24], LE32 flags=0 [24:28],
LE32 trace-frame index [28:32], CRC32 of 64-byte header with
[32:36] zeroed at [32:36], reserved bytes [36:64] all zero.
Body consists solely of contiguous already validated P07-A1 frames,
without labels. No P05 v1 reinterpretation.

Mailbox 64KiB header: 0:4 ASCII `P07R`, word 1 version=1, word 2
terminal success `0x600D600D` / failure `0xDEADxxxx`, word 3
failure code, word 4 active frame index, word 5 failure detail,
word 6 configured frame count, word 7 trace-selected frame index,
word 8 frames completed. Frame summaries begin at byte 256, 128 B
each; [word 8..17] hold ten class counts, [word 23..31] hold 26
packed tick-specific 10-bit output spike flags. Complete 26x42
256-bit compartment traces for the selected frame start at mailbox
offset 4096 and use HLS bit slices 0..63 before state, 64..127
synaptic accumulator, 128..191 after state, 192 spike flag.
The other frame outputs are still counted/tick recorded, but full
42-compartment debug traces are captured for **one selected frame
per batch only** to remain inside 64KiB.

## Host-native CI and user verification (V3 root)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-a-784-axon-streaming
git pull --ff-only origin agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a1_ingress.py \
  tests/test_p07_a2_runtime.py \
  tests/test_p07_a2_sha256.py \
  tests/test_p07_a2_batch.py \
  tests/test_p07_a2_board_build.py \
  tests/test_p07_a2_evidence.py \
  tests/test_p06_a2_input_contract.py \
  tests/test_p05_1_deployment.py
```

The A53 header syntax test is **not** a real cross-compile.
A real Vitis 2025.2 standalone build is required before using XSDB.

## Generate deterministic test batch (never touch MNIST TEST)

The accepted P07-A1 `ramp` ingress record from your A1 run exists
locally. Use fresh output filenames (builders fail closed if output
exists):

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a1_ingress.py \
  --synthetic black --out artifacts/p07_a2_black_v1.bin
PYTHONPATH="$PWD/src" python scripts/p07_a1_ingress.py \
  --synthetic white --out artifacts/p07_a2_white_v1.bin

PYTHONPATH="$PWD/src" python scripts/p07_a2_batch.py \
  --record artifacts/p07_a2_black_v1.bin \
  --record artifacts/p07_a2_white_v1.bin \
  --record artifacts/p07_a1_ingress_ramp_v1.bin \
  --trace-frame 1 \
  --out artifacts/p07_a2_batch3_v1
```

Expected: `P07_A2_BATCH_HOST_PASS=1`, `P07_A2_FRAME_COUNT=3`,
`P07_A2_TEST_STATUS=SEALED`, `P07_A2_BOARD_STATUS=NOT_RUN`.
The model/DDR fingerprints are checked on every record; output is
a 64B header, 7440B input payload, 64KiB empty mailbox, manifest.
No physical result is implied.

## Vitis native gate (requires user's installed AMD toolchain)

Select the **same accepted P03.2c routed FPD128 XSA** used for your P05
physical implementation, and set its exact recorded SHA-256. Do not
substitute an unverified new Vivado design:

```bash
# With the accepted P03_DIAG_REPORTS/P03_2C_EXPECTED_XSA_SHA values
# available from your successful P05 build environment:
export P07_A2_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P07_A2_XSA_SHA256="$P03_2C_EXPECTED_XSA_SHA"
export P07_A2_BUILD_DIR="/tmp/v3_p07_a2_$(date +%Y%m%dT%H%M%S)"
bash scripts/build_p07_a2.sh
```

Expected `P07_A2_VITIS_NATIVE_GATE_PASS=1` and a validated,
nonoverlapping standalone `p07_a2_board.elf`; its digest is printed.
If any Vitis/BSP/compiler/ELF error occurs, STOP at that first failure
and preserve the build log; do NOT execute the candidate on hardware.

## Later device gate — DO NOT equate with native host verification

After a successful Vitis build, program the **accepted** P05 KV260
bitstream/XSA through your established method and confirm the A53
FPD128 read-only gate. With the board under the dedicated bare-metal
DDR ownership policy, the new scripts support:

```bash
mkdir -p /tmp/v3_p07_a2_readback
xsdb vivado/p07_a2_xsdb_prepare.tcl \
  artifacts/p06_a4_static_ddr_seed20261013/core0_initial_p02_ddr_512k.bin \
  artifacts/p07_a2_batch3_v1 \
  /tmp/v3_p07_a2_readback

xsdb vivado/p07_a2_xsdb_run.tcl \
  "$P07_A2_BUILD_DIR/vitis_workspace/p07_a2_board.elf" \
  /tmp/v3_p07_a2_mailbox.bin

PYTHONPATH="$PWD/src" python scripts/p07_a2_verify.py \
  --mailbox /tmp/v3_p07_a2_mailbox.bin \
  --batch-dir artifacts/p07_a2_batch3_v1
```

Only `P07_A2_PHYSICAL_TRACES_EXACT=1` from a genuine 64KiB
physical mailbox *after* the A53 terminal success and software
first-difference comparison could establish the device numerical
gate for the selected trace frame; other frames' class-output parity
is checked as well. This board result is **NOT PRESENT** in the
repository. If first mismatch, report its first tick/compartment/field
and preserve the raw physical evidence; never alter frozen P06
arithmetic, labels or goldens to make it pass.

## Acceptance stop

P07-A2 is **NOT CLOSED** as of this document. GitHub CI and host-native
C mock validation are a legitimate implementation checkpoint only.
The first native Vitis ELF gate passed for the original build,
but the trace-timestep fix supersedes that ELF and requires a clean
rebuild. After the corrected ELF passes, physical KV260
bringup/verification must be independently attempted and its output independently accepted. P07-A3 and official
P07-A4 sealed TEST remain pending. P08-A measurements are deferred.
