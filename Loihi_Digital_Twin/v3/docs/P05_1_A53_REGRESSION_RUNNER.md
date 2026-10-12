# P05.1 — New A53 regression application (implementation checkpoint)

**Branch:** `agent/v3-p05-board-regression`  
**Status:** **P05.1 functional subphase COMPLETE (2026-10-12).**
The user's independent seven-step five-core and five-step
three-core triangle physical runs passed a combined **50 real
model-derived checkpoints**, validated both nonresident and
resident packet-routing paths, and produced respectively five
and three complete final DDR records byte-exact to independent
Python oracles. See `docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md`
and `docs/P05_1_TRIANGLE_ACCEPTANCE.md`.
The remainder of this document preserves the historical
implementation/verification instructions. Early first-failure
negative probes and fast-mode equivalence remain P05.2 work.
The accepted P03 executable and RTL remain unchanged;
`main` remains untouched.

## What changed since the binary deployment contract checkpoint

The host-only P05G v1 deployment contract and Python↔C validator
were independently reported PASS. The inspection showed the frozen
P03 5-core, 7-step workload converted deterministically into
35 external events and 35 required dispatches.

The new `software/p05/p05_regression_run.c` is a **separate**
standalone Cortex-A53 application, not a P03 rewrite. It imports
the accepted `p03_runtime.c`, `p03_hw_runtime_bridge.c`,
`p03_hw_adapter.c` and `p03_hw_xilinx_io.c` unchanged.
The new `software/p05/build_p05_regression.py` and
`scripts/build_p05_regression.sh` create a separate Vitis
workspace/app `p05_regression_run.elf` with retained identity
`P05_CONFIGURABLE_A53_REGRESSION_V1`. Build guards require the
**accepted** FPD128 route metrics and exact caller-supplied XSA
SHA-256, reject an old ELF or a reserved-DDR-overlapping ELF
load segment, and never mutate the P03 binary/bitstream.

### Device-side execution

1. Reads the fixed P05G header from physical DDR `0x43FE0000`;
   bounds the stated payload size **before** touching
   `0x43F00000`, invalidates cache and runs the portable
   `p05_deployment_validate` parser. Rejects version,
   CRC, tables, range, order, duplicate IDs and unsupported values
   before hardware MMIO begins.
2. Checks live PS FPD HPM0 width and CRC32 of each complete
   512 KiB input DDR record at
   `0x40000000+logical_id*0x80000`, including record magic,
   version, stride, ID, initial event counts, config0 and
   the metadata's compartment/synapse/route counts.
3. Registers every logical core and its allowed input axon,
   initializes the **unchanged** P03 scheduler and physical
   packet/MMIO adapter, and loads the configured initial
   resident set using the standard callback bridge.
4. For each logical core in descriptor **service order** and
   each timestep, injects *exactly* the external event rows
   scheduled for (timestep,core) into the CURRENT bank,
   appending after prior routed packets. Then executes
   one real PL inference dispatch and drains/validates/routes
   real FPGA packets to NEXT via the accepted P03 adapter.
   The PC is not consulted.
5. At the global quiescence barrier, optionally reads
   model-selected **post-dispatch, pre-swap** observations
   directly from a resident FPGA debug bank or from the
   authoritative nonresident DDR record. The supported v1
   classes are state0 (8B), event0 (4B), event1 (4B),
   packet0 (8B); each sample uses little-endian CRC32.
   The first mismatched checkpoint records timestep,
   logical ID, class and expected/observed CRC and
   terminates fail-closed.
6. After all timesteps, flushes dirty resident slots to
   authoritative DDR, checks hardware page/dispatch
   completion counters, status, pending bytes and quiescence.
   The runtime must enter DONE *before* publishing terminal
   `0x600D600D` and flushing its 256-byte P05R mailbox.
   On failure, the terminal word is `0xDEAD0000|error`,
   with the sticky runtime phase/fault and first checkpoint
   mismatch fields retained.

The 256-byte P05R mailbox uses magic `0x52353050` (ASCII
`P05R`), ABI version 1, and a **different, documented layout
in `p05_regression_run.c`** from the P03 `P3RS` mailbox. It
includes processed event count, passed checkpoint count,
observed resident packet deliveries, scheduler/page/packet/
barrier/PS/PL counters and the first mismatch (words 45–49).
It does not claim hardware-wide trace capture or fixed timing
comparability with P03.

The full 512 KiB records still need to be **physically dumped
and compared to independent Python reference images** after
the A53 finishes, as in P03. A passing mailbox alone is not
sufficient P05.1 physical acceptance. No PC-level
per-dispatch step/route/paging automation is authorized.

### Model-derived checkpoints for initial physical probe

`scripts/p05_deployment.py from-p03 --state-checkpoints`
now reads the *frozen P02-generated*
`p02_4b_vectors.tcl` table `P02B_EXPECT_STATE` and
derives one expected **state0** CRC32 for each of the
35 (timestep,logical-core) combinations in the accepted
P03.4 seven-step workload.

This deliberately exercises checkpoint requests against
an **independent neural oracle**, not test-generated guesses.
It is an observation overlay on unchanged P03-compatible
input and final DDR images. The native C/Python ABI test
checks that the 35 checksums parse consistently. Real board
MMIO debug-bank capture and resident/nonresident parity
are unverified until the physical run.

Note that this first replay profile still has
`resident_deliveries=0`, so it does **not** close the
direct-to-already-resident routing coverage gap. We must
generate/verify a different supported network topology
for that later directed physical gate.

## Current independent verification checkpoint: Ubuntu native + Vitis

From a VS Code terminal:

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

# New P05.1 binary contract + real P02 state-checkpoint oracle:
python -m pytest -q \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py

# Preserve frozen P03 acceptance and original P02 model regressions:
python -m pytest -q \
  tests/test_p03_finish_autonomy.py \
  tests/test_p03_3b3_physical_probe.py \
  tests/test_p03_3b_hw_adapter.py \
  tests/test_p03_3a_native_runtime.py \
  tests/test_p02_4b_ring_fixture.py

# Generate P03 golden + P05 diagnostic payload to confirm the
# independent oracle-derived 35 post-barrier checkpoints:
export P05_1_SMOKE="/tmp/v3_p05_1_a53_$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$P05_1_SMOKE"
python scripts/p03_finish_fixture.py \
  --timesteps 7 --output-dir "$P05_1_SMOKE/p03_golden"
python scripts/p05_deployment.py from-p03 \
  --fixture-dir "$P05_1_SMOKE/p03_golden" \
  --output-spec "$P05_1_SMOKE/p05_spec.json" \
  --state-checkpoints
python scripts/p05_deployment.py build \
  --spec "$P05_1_SMOKE/p05_spec.json" \
  --output-dir "$P05_1_SMOKE/p05_artifacts"
cat "$P05_1_SMOKE/p05_artifacts/p05_manifest.json"

# Build distinct A53 ELF from the P03-accepted routed FPD128 XSA:
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P05_1_BUILD_DIR="$PWD/vivado/build/p05_1_regression_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/build_p05_regression.sh 2>&1 | tee /tmp/v3_p05_1_a53_build.log
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"
```

**Expected pre-board result:** both pytest suites PASS, generated
P05 manifest `events=35,dispatches=35,checkpoints=35`, and a
new P05-specific ELF builds with a retained marker and no reserved
DDR load segment. This is NOT a board PASS. Source and Vitis
build must be independently verified on the user's machine.

**Now implemented:** `scripts/run_p05_1_probe.sh` has a
**host-only `prepare`** and a separately opt-in destructive
**`physical`** mode. `vivado/p05_1_xsdb_prepare.tcl`
provisions/readbacks the P05G ABI from the PSU physical target,
and `scripts/p05_1_verify.py` checks the new P05R mailbox
plus **every byte of all five DDR records** against the frozen
P02 model. It independently rechecks all 35 model-derived
checkpoint values and 35 external ingress rows, even if
the supplied manifest's CRC/SHA fields have been recomputed
to cover an incorrect workload.

First independently run the new host synthetic verifier tests:
`python -m pytest -q tests/test_p05_1_physical_probe.py`.
Then follow the preparation/physical board commands in
`docs/P05_1_PHYSICAL_PROBE.md`. The Vitis ELF was already
reported successful; reuse that **exact** build if its staged
source and XSA still match. No P05 hardware PASS is claimed.
A second genuinely distinct network is still needed for
P05.1 closure.
