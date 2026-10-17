# P07-A4.2a native gate — persistent DDR transport prototype

**Status 2026-10-17:** Python/C11 DDR wire prototype **CLOSED /
USER NATIVE ACCEPTED**. P07-A4.2b persistent A53 source,
portable C11 tests and isolated Vitis build scripts are
implemented/CI-green; **new user Vitis ELF build PENDING**.
P07-A4.2c physical XSDB gate tools are implemented/CI-green,
but persistent KV260 inference is **NOT PHYSICALLY RUN**.
Full canonical 10k MNIST **TEST remains SEALED**.
Branch `agent/v3-p07-a-784-axon-streaming`, do not merge without
user approval.

## Summary / boundaries

The existing P07-A2 16-frame firmware, ABI and P03 Loihi arithmetic
are **unchanged**. New `P07A4P01` descriptor and portable C11
host-parity parser establish a candidate DDR layout for a future
**single A53 launch over up to 10,000 raw 784B images**, one frozen
784×uint16 pixel→axon map and a **distinct 1MiB** result journal.
The 64MiB JTAG-owned DDR map, fixed offsets, CRC fields, per-image
96-byte result record and first failure/progress contract are
specified in `P07_A4_2_PERSISTENT_DDR_DESIGN.md`.

The new C11 encoder reconstructs **byte-for-byte exact** accepted
P07-A1 records from each raw image, pins real P06-A4.2 DDR master and
compiled checkpoint SHA/fingerprint, validates unique ingress axons
and CRC, and reuses the exact 25+1 step packet semantics of the
previously accepted A53 runtime (which will become the A4.2b
standalone application). New 96-byte results retain **all 26×10
per-tick physical output spike bits**, 10 spike counts, raw-image CRC,
routes, discard, completion and independent readout checks.
The new physical A53 loop has **not** yet been built or launched,
and C tests use a synthetic fixture, not the actual PL.

## Regression gates already exercised in GitHub CI

- Portable C11 `-std=c11 -Wall -Wextra -Werror -pedantic`
  implementation compiled to a native shared test library.
- Python/C11 descriptor parity for exactly **1, 16, 128,
  10,000** raw synthetic 784-pixel samples.
- Accepted P07-A1 byte-exact ingress reconstruction for
  selected frames; CRC, magic, reserved bits, DDR base,
  frozen master, compiled source and mapping failures
  independently rejected even after descriptor CRC recomputation.
- Result word packing, 26×10 spike-bit/count/class tie/
  all-silent agreement and result CRC parity; corrupt or
  incomplete journal must NEVER count as completion.
- Initial all-zero result journal and C11 header parity;
  no data beyond declared image/result bounds.
- New independent artifact-file checker detects tampered
  staged input bytes, validates exact 1MiB initial journal,
  frozen map and A2-format reconstruction.
- All current tests use **synthetic in-memory IDX-free inputs**,
  no official MNIST TEST download/open.

## Native user reproduction (from VS Code terminal)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-a-784-axon-streaming
git pull --ff-only origin agent/v3-p07-a-784-axon-streaming
source ~/Git/Thesis/.venv-p08/bin/activate
cd Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_a4_stream.py \
  tests/test_p07_a4_protocol.py \
  tests/test_p07_a3_3_protocol.py

# Stage NEW synthetic 16-image candidate DDR files; NO FPGA access.
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --synthetic ramp --count 16 --trace-index 0 \
  --out artifacts/p07_a4_2a_ramp16_v1

PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir artifacts/p07_a4_2a_ramp16_v1

# Native preflight of accepted first 128 TRAIN-derived validation images.
# Loads only train-images/train-labels archives; DOES NOT open official t10k.
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --validation-first 128 --trace-index 0 \
  --data-dir data/mnist_raw \
  --out artifacts/p07_a4_2a_validation128_v1

PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir artifacts/p07_a4_2a_validation128_v1
```

Optional full-capacity **synthetic-only** journal/buffer
stress on the actual native PC (still no FPGA):

```bash
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_prepare.py \
  --synthetic white --count 10000 \
  --out artifacts/p07_a4_2a_synthetic10k_v1
PYTHONPATH="$PWD/src" python scripts/p07_a4_2_check.py \
  --stage-dir artifacts/p07_a4_2a_synthetic10k_v1
```

Expected markers for any prepared corpus:
```text
P07_A4_2A_STREAM_FRAMES=<16,128,10000>
P07_A4_2A_INPUT_ABI_HOST_PASS=1
P07_A4_2A_A53_FIRMWARE=NOT_YET_BUILT
P07_A4_2A_KV260_STATUS=NOT_RUN
P07_A4_OFFICIAL_TEST=SEALED
P07_A4_2A_INPUT_DESCRIPTOR_CRC_PASS=1
P07_A4_2A_1M_JOURNAL_INIT_EXACT=1
P07_A4_2A_ACCEPTED_A1_INGRESS_EQUIVALENCE=1
P07_A4_2A_STAGING_CHECK_PASS=1
```

**Destination paths are immutable/no-overwrite.** Use a new suffix
if a previous native run already created files. Never delete the
accepted A2, A3 or A4.1 artifacts. No need to reboot KV260, open
Vivado/Vitis or connect XSDB to complete A4.2a.

## After user-native acceptance

Continue **A4.2b**: build a *separate* corrected A53 standalone ELF
with persistent input pointer, full dataset validation BEFORE dispatch,
per-image frozen P07-A2 `p07_a2_run_frame` and reset, bounded append-only
CRC-protected result journal and fail-first progress status. The new
physical runner and independent numerical oracle verifier will be
implemented and tested on synthetic and already-accepted TRAIN-derived
validation fixtures for A4.2c. The accepted original 16-image A2
ELF and P03 bitstream remain regression baselines.

Only after passing A4.2c can A4.3 explicitly unseal the frozen
full 10000 canonical MNIST TEST. No official image, label
or official score has been consulted by this work.

## Recorded user-native acceptance (2026-10-17)

The user explicitly reported A4.2a was verified.
A4.2b implementation is now available; see
`P07_A4_2B_2C_PERSISTENT_GATE.md` for next native
C11/Vitis ELF and subsequent physical-gate commands.
No official TEST source files have been opened.
