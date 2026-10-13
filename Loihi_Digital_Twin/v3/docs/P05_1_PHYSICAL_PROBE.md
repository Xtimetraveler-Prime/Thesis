# P05.1 — First physical A53 regression probe (35 checkpoints)

**Status:** **First physical P05.1 probe independently ACCEPTED
2026-10-12**, from the user's own KV260 terminal and strict final
`verify.log`: 7 steps/35 dispatches/30 packets/7 barriers,
**35/35 model-derived physical intermediate state checkpoints**,
five byte-exact final DDR images, `P05_1_VERIFY_EXIT=0`.
Evidence: `/tmp/v3_p05_1_probe_20261012T173751Z`.
Acceptance ledger: `docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md`.
The second independent **three-core resident triangle** network,
which checks `resident_deliveries=12`, is now prepared;
procedure: `docs/P05_1_TRIANGLE_PHYSICAL_GATE.md`.
P03 remains accepted and unchanged; P05.1 overall is not complete yet.

## Why this first workload is deliberately not a new network

Reuse **exactly** the independently accepted P02/P03 seven-step
five-core ring, identical five initial 512 KiB DDR records and the
frozen Python oracle; change ONLY the test-driver/control application
and its input representation. The **new** A53 P05G runner reads a
versioned 256-byte deployment header, separately provisioned bounded
event/checkpoint table, then exercises the **same accepted** P03 C
scheduler, physical packet router, hardware pager and FPD128 PL
bitstream.

In contrast to P03, P05.1 also validates **35 independent model-derived
CRC32 checks** for the **post-dispatch, pre-event-bank-swap**
state0 values of five cores at all seven timestep barriers.
The checkpoint mechanism samples resident FPGA debug-bank state
or nonresident authoritative DDR state depending on live residency.
Then the host dumps and byte-exactly compares all five complete
physical final records. Both the intermediate checkpoint counter and
five final records **must** pass. The oracle's `trace_sha256`
is a *reference* trace fingerprint; it is not itself a newly
captured physical trace.

This is a physical **checkpoint/replay smoke**, not yet full P05.1
acceptance: the second distinct workload is still required and
P05.2 remains pending.

## Files and ownership

- `scripts/run_p05_1_probe.sh prepare <absolute-new-dir>`:
  **host-only**, generates frozen P03/P02 golden, builds P05G
  deployment with 35 state checkpoints, verifies CRC/SHA,
  record equivalence, writes 256B zero mailbox. Touches no board.
- `scripts/run_p05_1_probe.sh physical <absolute-prepared-dir>`:
  requires explicit `P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES`;
  verifies current staged Vitis source and accepted FPD128
  XSA, actual ELF embedded signature, PS width and DDR fixture.
  Reuses the **already accepted** Vivado program Tcl and terminal-only
  P03 XSDB run/dump Tcl: their terminal convention
  `result[2] == 0x600D600D` or `0xDEADxxxx`, physical mailbox
  base `0x43FF0000` and five final DDR record addresses
  have **not changed**, though the P05R mailbox contents have.
- `vivado/p05_1_xsdb_prepare.tcl`: newly provisions via
  **nonprocessor PSU/APU physical target**, halts all available
  A53/Linux processors, writes/readbacks the five initial records,
  `0x43F00000` P05 payload, `0x43FE0000` P05 header,
  `0x43FF0000` zeroed result mailbox, validating every byte.
- `scripts/p05_1_verify.py`: parses the NEW 256-byte P05R schema,
  independently checks 35 dispatches, 30 real packet events,
  seven barriers, 35 consumed external ingress events and
  **35 passing model checkpoints**, page counts, physical MMIO ID/
  width capabilities, status/quiescence, CRC identities, and
  five full golden DDR records. Even when the mailbox fails,
  the verifier compares final DDR and prints diagnostic fields
  `failed_step`, `failed_core`, `failed_class`,
  `expected_crc`, `observed_crc`, etc. No false PASS.
- `tests/test_p05_1_physical_probe.py`: host synthetic mailboxes,
  negative field/first-mismatch mutations, corrupt physical dump
  tests, offline staging and destructive board gate.

**No new Vivado implementation or P05 source/ELF rebuild is
necessary** if the previously built ELF is selected and its staged
P05 files byte-match this checkout. Otherwise the physical runner
rejects the stale build *before* touching the board; rebuild the
P05 ELF in a new directory and repeat.

## Step 1 — Pull and independently validate new physical tooling

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_1_physical_probe.py \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py
```

A host synthetic P05R PASS is only a test of the **verifier's
ability to recognize evidence**, not a fabricated physical PASS.

## Step 2 — Generate new dry-run evidence

```bash
export P05_1_EVIDENCE="/tmp/v3_p05_1_probe_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_1_probe.sh prepare "$P05_1_EVIDENCE" \
  2>&1 | tee /tmp/v3_p05_1_probe_prepare.log
cat "$P05_1_EVIDENCE/p05_artifacts/p05_manifest.json"
```

Expected: `timesteps=7`, five cores, three slots,
`events=35`, `checkpoints=35`, `dispatches=35`.
The script prints
`PASS: P05.1 offline probe generated; board has NOT been touched`.
Do **not** interpret this as physical acceptance.

## Step 3 — Reuse accepted XSA, bitstream and NEW Vitis ELF

Use the **same shell session as the successful Vitis build**,
if available; otherwise restore `P05_1_BUILD_DIR` to the
existing directory containing
`vitis_workspace/p05_regression_run.elf`.
Do not rerun the Vitis build just to run a different fixture.

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# Only if previous terminal lost the Vitis build environment:
# export P05_1_BUILD_DIR="<path/from/your/successful/P05.1/build>"

echo "$P05_1_BUILD_DIR"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"
grep -aF "P05_CONFIGURABLE_A53_REGRESSION_V1" \
  "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"
```

The physical runner verifies every staged C source/header against
the current checkout and rejects incompatible ELF/XSA/route metrics.

## Step 4 — Physical run (destructive to reserved DDR)

Before running, **reboot KV260**, let boot firmware initialize DDR,
keep JTAG/hw_server accessible and close conflicting Vivado sessions.
The runner **stops Linux and overwrites**
`0x40000000..0x43FFFFFF`; do not treat it as a test that
can run alongside Linux or on a board with useful data in that
reserved DDR range. Do not resume Linux after standalone A53
execution: reboot the board after **success or failure**.

```bash
export P05_1_CONFIRM_KV260_DDR_OVERWRITE=YES
set -o pipefail

bash scripts/run_p05_1_probe.sh physical "$P05_1_EVIDENCE" \
  2>&1 | tee /tmp/v3_p05_1_probe_physical.log

cat "$P05_1_EVIDENCE/verify.log"
```

The PC does not select logical cores, page victims, routes,
events or barriers during the A53 algorithmic loop. The probe
uses XSDB only for initial memory provisioning, one ELF launch,
passive terminal mailbox polling and final physical DDR
record retrieval.

Expected strictly post-verification marker **if** the run succeeds:

```text
PASS: P05.1 independent physical 35-checkpoint ring replay steps=7 cores=5 slots=3 dispatches=35 packets=30 barriers=7 events=35 checkpoints=35 ...
PASS: P05.1 all five final 512KiB DDR records byte-exact to frozen P02 oracle
P05_1_VERIFY_EXIT=0
PASS: P05.1 first 7-step 35-checkpoint A53 physical golden probe
```

These are **expected markers, not observed results**.

If an error occurs, preserve the entire evidence folder and
`verify.log`. The verifier prints
`P05_FIRST_DIAGNOSTIC` for an A53 terminal error and reports
whether the final DDR records are independently correct.
Do not interpret a failed checkpoint as necessarily incorrect
final model semantics; an observation/read path could also
be responsible, and the full DDR comparison distinguishes
those hypotheses.

## Next gate, not yet started

After this **first** physical probe succeeds, generate a
genuinely different network configuration and independently
computed Python golden (different core count and/or topology,
and ideally resident destination packet routing), and execute
it using **the same P05 ELF**. This second physical profile,
plus credible checkpoint and first-failure coverage, is needed
to accept P05.1. P05.2 then hardens broader arithmetic,
fanout/backpressure, paging and service-order invariance
coverage. Do not merge to `main` before explicit user approval.
