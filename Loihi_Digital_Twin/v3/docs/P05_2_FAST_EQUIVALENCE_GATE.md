# P05.2b — Fast-mode hardware equivalence (pending physical test)

**Status:** Implementation committed to
`agent/v3-p05-board-regression`; **host tests and KV260
physical execution pending**. P05.1 is accepted from two
independently verified physical workloads; P05.2a hardware
negative-checkpoint localization is also accepted from user
evidence `/tmp/v3_p05_2_fault_20261012T181015Z`.

## Precisely what changes and what must remain invariant

Use the accepted **three-core, five-timestep, threshold-4
spiking triangle**, 15 external input events, 12 expected
routed packets, three resident destinations per timestep
after the first, and **the exact same P05 A53 ELF and
P03.2c FPD128 bitstream**.

The only intended deployment differences:

| Aspect | Accepted diagnostic P05.1 | New P05.2b fast |
|---|---:|---:|
| P05G mode word 3 | 1 (diagnostic) | 0 (fast) |
| P05G checkpoint count word 14 | 15 | 0 |
| Exactly preserved neural 512KiB images | 3 | 3 |
| Exactly preserved core metadata/ingress table | 3 + 15 rows | Same exact bytes |
| Expected dispatches | 15 | 15 |
| Expected routed packets | 12 | 12 |
| Expected direct resident deliveries | 12 | 12 |
| Expected global barriers | 5 | 5 |
| Expected final DDR page-outs | 3 | 3 |

The board must execute **five complete timesteps** with no
checkpoint reads. The A53 terminal must be `0x600D600D`
with `checkpoints_passed=0`, `diagnostic_mode=0` and
`expected_checks=0`. Hardware dispatch/page/packet counts
must match the accepted diagnostic run. The PC still
only provisions, starts A53 once, passively polls terminal
status and retrieves final DDR records.

**Primary acceptance condition:** all THREE physically
retrieved final full 512KiB DDR images match **both** the
independent Python `LogicalChip` oracle and the separately
accepted P05.1 diagnostic hardware final images exactly
(SHA-256 values below). This demonstrates disabling
checkpoint collection does not change neural state:

| Core | Accepted P05.1 physical diagnostic SHA-256 |
|---|---|
| 0 | `5c4288e41e1599aea5f854a4022fb88a6b04ddc003b01238e16f5a7c59665381` |
| 1 | `2767f8cbca59d8e9bb85d0f37d055a7b4a7c4e94676d56bbd3efeff4f4f6c0f2` |
| 2 | `d6c8982882023c8b0065ca856a3caf35a1b6fa54196a6fb546b774deca32c82f` |

No new Vitis/FPGA build is required. The binary ABI,
existing accepted scheduler and PS/PL adapter remain unchanged.
The fast-mode path still performs packet MMIO observations
needed for routing, and retains mailbox counters; **do not
call this a benchmark or claim calibrated speedups.**
PS and PL timers do not cover identical intervals and do
not by themselves measure energy or total AXI traffic.

## New files

- `scripts/p05_2_fast_fixture.py`: independently creates
  accepted triangle golden; saves exact prior diagnostic
  header/payload for comparison; changes only mode and
  checkpoint table; rebuilds proper P05G CRC/SHA and
  records the three prior physically accepted DDR hashes.
- `scripts/p05_2_fast_verify.py`: verifies original and
  fast P05G CRC/SHA, byte-identical core/event vectors,
  correct no-checkpoint mode and PS/PL operation counts;
  checks full 3×512KiB live DDR against both model and
  prior independent hardware SHA256.
- `scripts/run_p05_2_fast.sh`: safe `prepare` (host-only)
  and explicitly opted-in `physical` KV260 test, reusing
  accepted JTAG physical provisioning, program and dump Tcl,
  Vitis source/ELF/XSA identity guards, fail-closed result.
- `tests/test_p05_2_fast.py`: shared-data conformance,
  synthetic positive/no-checkpoint mailbox, bad counter
  rejection, three-record corruption, pinned historical
  SHA mismatch, forged CRC/SHA event drift.

## Independent host tests — before board

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_2_fast.py \
  tests/test_p05_2_fault.py \
  tests/test_p05_1_triangle.py \
  tests/test_p05_1_physical_probe.py \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py
```

**The new P05.2b tests have not been independently run yet.**
Do not run physical mode until pytest passes.

## Host-only evidence preparation

```bash
export P05_2_FAST="/tmp/v3_p05_2_fast_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/run_p05_2_fast.sh prepare "$P05_2_FAST" \
  2>&1 | tee /tmp/v3_p05_2_fast_prepare.log
cat "$P05_2_FAST/p05_2_fast_gate.json"
cat "$P05_2_FAST/p05_artifacts/p05_manifest.json"
```

Expect `dispatches=15`, `events=15`,
`checkpoints=0`, `diagnostic_mode=false`,
`expected_packets=12`, `expected_resident_deliveries=12`.
Only the P05G checkpoint-table and mode words differ.
The output also includes the earlier diagnostic descriptor
files for audit, independently hashed in the fast gate.

## Opt-in physical KV260 run

**Reboot KV260 after P05.2a**, allow DDR initialization,
make JTAG/hw_server accessible, and verify no other owner
needs data in the project `0x40000000..0x43FFFFFF`
DDR reservation. This will stop Linux, program accepted
PL and overwrite that range. **Reboot after success or
failure, never resume halted Linux.**

Select previous working P05 ELF and accepted route:

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# Restore if the shell lost your existing successful build:
# export P05_1_BUILD_DIR="<previous successful P05 Vitis build folder>"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"

export P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES
bash scripts/run_p05_2_fast.sh physical "$P05_2_FAST" \
  2>&1 | tee /tmp/v3_p05_2_fast_physical.log

cat "$P05_2_FAST/verify.log"
```

Expected **only if the real hardware run passes**:

```text
PASS: P05.2 fast/no-checkpoint A53 triangle timesteps=5 dispatches=15 packets=12 resident_deliveries=12 barriers=5 events=15 checkpoints=0
PASS: P05.2 fast mode three final 512KiB DDR records byte-exact to BOTH independent Python oracle and earlier physical diagnostic-mode KV260 SHA256s
P05_2_FAST_VERIFY_EXIT=0
PASS: P05.2b fast/no-checkpoint same-neural-model physical equivalence gate
```

Keep full evidence on errors, and **do not mark P05.2
complete on this single gate**. Next directed tests still
include arithmetic boundary/saturation, multi-output fanout,
event-depth/backpressure, pathological paging, barriers,
service-order permutations and PS/PL/AXI counter provenance.
All need source-independent golden criteria and physical
coverage or explicit documented limitations.
