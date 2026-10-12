# P05.1 second physical profile — 3-core resident spiking triangle

**Status:** Hardware execution NOT YET VERIFIED. Prepared on
`agent/v3-p05-board-regression`; first 5-core/35-checkpoint P05
physical gate is accepted (`docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md`).
**Same P05 A53 ELF and same accepted P03.2c FPD128 FPGA bitstream:**
no rebuild is needed if the Vitis staged files still match this branch.

## Why this is a genuinely different neural network

The first accepted five-core network always reported
`resident_deliveries=0`. A second 100-timestep replay would
not test the coverage gap or prove general deployment.

The second P05.1 model-derived test uses:

| Parameter | Profile |
|---|---|
| Logical cores | IDs 0,1,2 (three, not five) |
| Physical resident slots | 3 (all logical cores remain resident) |
| Physical engines | 1 |
| Timesteps | 5 |
| Compartment threshold | 2 (instead of frozen ring's 5) |
| Synaptic weight | 3 |
| Input stimulus | One external axon 10+core at each timestep |
| Directed connectivity | 0→1, 1→2, 2→0 |
| Expected dispatches | 15 |
| Expected emitted and routed packets | 15, one per core/timestep |
| **Expected direct resident packet deliveries** | **15** |
| Barriers / state0 checkpoints | 5 barriers; 15 independent model-derived post-dispatch/pre-swap state CRC32s |
| Initial page-ins | 3 |
| Replacement page-ins / mutable evictions | 0 / 0 |
| Final mutable page-outs | 3 |
| Total PL page commands | 6 |
| Final DDR comparison | Three full 512 KiB records byte-exact to the **new independent Python LogicalChip model** |

The per-core context images, packet count, 15 state checkpoints,
and three golden final records are generated from
`loihi_twin_v2.LogicalChip` and its accepted hardware encoder
in `scripts/p05_1_triangle_fixture.py`. It loads a **separate
instance** of the P02 golden serialization harness and overrides
only the new instance's network parameters, leaving the
*frozen P02/P03 oracle source and existing goldens unchanged*.
The new neural network has a different core count, topology,
threshold, golden trace fingerprint and final DDR content.

This profile is designed to **force** physical resident-to-resident
packet commits. If the hardware's direct-resident routing branch
is defective, the A53 may report a packet/barrier failure, state
checkpoint failure or final DDR mismatch. All are accepted
**failures of the test**, never silently relaxed counts.

## Independent host gates before programming KV260

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_1_triangle.py \
  tests/test_p05_1_physical_probe.py \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py
```

These host-side tests validate the reference generator,
frozen-to-triangle change in neural parameters, new binary,
expected model packet count, checksum requests, positive/negative
mailbox decoding, resident-delivery counter strictness,
first-mismatch diagnostics, corrupted full-record detection,
the new three-record physical Tcl path and **destructive board
opt-in**.

Do **not** interpret a synthetic mailbox PASS as hardware evidence.

## Offline prepare — does not touch KV260

```bash
export P05_1_TRIANGLE="/tmp/v3_p05_1_triangle_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_1_triangle.sh prepare "$P05_1_TRIANGLE" \
  2>&1 | tee /tmp/v3_p05_1_triangle_prepare.log
cat "$P05_1_TRIANGLE/triangle_gate.json"
cat "$P05_1_TRIANGLE/p05_artifacts/p05_manifest.json"
```

The gate file must show 15 model spikes, 15 resident destinations,
15 checkpoints, three core IDs and six page commands. The offline
script checks the initial record CRC/SHA against all three
model-generated contexts, and the P05G header/payload ABI.

## Reuse the successful P05 ELF and accepted XSA

From the VS Code environment used for the previous physical run:

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# Restore this if opening a new terminal:
# export P05_1_BUILD_DIR="<previously successful P05 Vitis build directory>"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"
grep -aF "P05_CONFIGURABLE_A53_REGRESSION_V1" \
  "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"
```

The physical script checks staged P03 and P05 C source/header
identity against the build, verifies XSA SHA-256, original
Vivado route topology and actual ELF identity. Do not
recompile merely to change neural inputs.

## Destructive physical run — reboot first and afterward

Ensure KV260 was **fully rebooted after the first probe**,
boot firmware initialized DDR and JTAG/hw_server is available.
The `physical` command halts Linux and overwrites the
reserved **`0x40000000..0x43FFFFFF`** DDR region, including
existing contexts and descriptor. Do not run with Linux
ownership or live data in this reservation.

```bash
export P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES
set -o pipefail

bash scripts/run_p05_1_triangle.sh physical "$P05_1_TRIANGLE" \
  2>&1 | tee /tmp/v3_p05_1_triangle_physical.log

cat "$P05_1_TRIANGLE/verify.log"
```

The PC provisions once, loads the **same** P05 ELF once,
and thereafter only **passively** polls terminal status and
physically acquires **three** final DDR records. The A53
continues to perform every algorithmic dispatch, packet
delivery, barrier and final writeback without host intervention.

Strict expected output **if** hardware matches the independently
generated model:

```text
PASS: P05.1 3-core resident triangle physical golden timesteps=5 dispatches=15 packets=15 barriers=5 events=15 checkpoints=15 resident_deliveries=15 initial_ins=3 replacement_ins=0 final_outs=3
PASS: P05.1 three 512KiB final DDR records byte-exact to independent 3-core Python LogicalChip oracle
P05_1_TRIANGLE_VERIFY_EXIT=0
PASS: P05.1 SECOND independent 3-core resident triangle 15-checkpoint physical gate
```

This is **an expectation, not a reported physical PASS**.
If it fails, preserve the entire evidence folder. The verifier
always independently examines actual final DDR records, even
when terminal mailbox status is an error, and prints
`P05_TRIANGLE_FIRST_DIAGNOSTIC` with phase/fault and first
failing core/timestep/state class when available.

**Reboot KV260 after the run, PASS or FAIL. Never resume
halted Linux.**

## Closeout after independent second physical PASS

Record the actual 15 packets/resident deliveries,
15 checkpoints, five barriers, three final raw DDR SHA256s,
mailbox/ELF/XSA identities and evidence location. Then
review failure-injection evidence and whether an additional
physical negative-checkpoint probe is needed to demonstrate
that the A53's first-mismatch path works, not merely the
Python verifier's synthetic mailbox decoder.

P05.1 is accepted only after its full defined runtime,
checkpoint, telemetry and diagnostic contract is satisfied.
No merge to `main` without explicit user approval. P05.2
remains a separate subsequent coverage/hardening phase.
