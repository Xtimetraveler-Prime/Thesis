# P05.2a — Directed first-mismatch hardware diagnostics and coverage plan

**Status:** Software implementation staged on
`agent/v3-p05-board-regression`. **No P05.2 physical evidence yet.**
P05.1 has been accepted from TWO independent board-local neural runs;
see `docs/P05_1_FIRST_PHYSICAL_ACCEPTANCE.md` and
`docs/P05_1_TRIANGLE_ACCEPTANCE.md`. The current `main` and
the accepted P03 source/bitstream are not modified.

## Purpose of first P05.2 development slice

A PASS on a normally completed workload establishes that checkpoints
and final DDR are correct for that workload. It does **not** prove
the standalone Cortex-A53 stops promptly, identifies the first
incorrect model expectation, preserves an informative error mailbox
or avoids accidentally treating an unrelated failure as success.

Therefore we deliberately mutate ONE *expected* checkpoint CRC,
not the neural network. The three-core threshold-4 spiking
triangle that passed P05.1 remains exactly the same: 3 logical
cores, 3 resident slots, 5 timesteps, threshold 4, weight 3,
topology 0→1→2→0, one external axon 10+core each timestep.
We use the **same** working `p05_regression_run.elf` and
the same accepted P03.2c FPD128 PL shell.

`scripts/p05_2_fault_fixture.py` generates the exact clean
triangle through its independent Python LogicalChip image/DDR
model, preserves that original spec and model images, and writes
a *new versioned P05G* descriptor with the expected
`state0` checksum at index 7, (timestep 2, logical core 1),
modified by XOR 1. It reconstructs genuine CRC32/SHA256
header/payload identities. Neural inputs, spike trains, packed
configuration, DDR records and packet routing are unchanged.

The first two timesteps complete normally. At timestep 2
all three real FPGA dispatches and packet commits complete;
the barrier's model-checkpoint inspection passes core 0
then sees the deliberately wrong expectation for core 1.
The A53 must report the **real observed CRC matching the
independent original model**, fail without swapping event
banks, and stop at the first mismatch.

### Frozen expected diagnostic P05R fields

| Field | Strict expected |
|---|---|
| Terminal `result` | `0xDEAD000A`, intentionally **ERROR** |
| Application `error` | 10 (checkpoint) |
| Runtime `phase` | 19 (`P03_RT_ERROR`) |
| `first_fault`, `fault_phase` | 11 (`P03_RT_FAULT_BARRIER_INCOMPLETE`), 13 (`P03_RT_BARRIER_CHECK`) |
| Failed timestep, logical core, state class | 2, 1, 1 (`state0`) |
| `diag_flags` | 1 (actual CRC != expected CRC) |
| Expected CRC | Original clean Python model state0 CRC XOR 1 |
| Actual observed CRC | Exact original clean Python model state0 CRC |
| Completed timesteps/barriers | 2 / 2 |
| FPGA dispatches and logical packets before stop | 9 / 6 |
| Confirmed direct resident packet deliveries | 6 |
| Consumed external events | 9 |
| Previously passing checks | 7 |
| Initial page-ins, replacement-ins, evictions | 3 / 0 / 0 |
| Final dirty flush / `WRITE_RESULT` | **Not executed** |

**Important measurement restriction:** The P05R hardware-summary
fields (`hw_dispatches`, `hw_pages`, PS timer frequency)
are filled in the **success-only result-finalization callback**.
On this deliberately early A53 ERROR, those mailbox fields
remain **zero** by construction. The runtime's own completed
dispatch/packet/page counters still show the partial work.
Do not interpret those zero final-summary counters as no PL activity.

**Do not compare final DDR records to a fully completed golden**
after this injected mismatch: the early halt happens before
dirty resident-state page-outs. A P05.2 negative PASS is strictly
the expected terminal ERROR plus exact hardware error location,
input integrity and model-observed state consistency.
No `final_ddr` files are emitted by this test.

## Reproducibility / independently validated code requirements

- `scripts/p05_2_fault_fixture.py`: new test vector and per-ELF
  immutable P05G manifest, exactly one model CRC bit flipped.
- `scripts/p05_2_fault_verify.py`: independently checks the
  clean model's state at t=2/core=1, exact one-bit injection,
  unmodified original inputs/records, physical A53 P05R result
  and every first-mismatch/error/counter field. Any unrelated
  A53 failure or unexpected normal success **FAILS**.
- `scripts/run_p05_2_fault.sh`: host-only `prepare`, then
  explicitly acknowledged board-destructive `physical`.
  Same accepted FPD128 XSA/bitstream and same built P05 ELF,
  compare staged source/hardware fingerprints, PSU/APU physical
  DDR readback, A53 start once/passive terminal polling. No
  host algorithmic control.
- `tests/test_p05_2_fault.py`: synthetic-mailbox negative
  tests and deliberately corrupted input/error fields. These
  are **host regressions only**, not observed physical events.

## Independent host gate (run before any KV260 work)

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_2_fault.py \
  tests/test_p05_1_triangle.py \
  tests/test_p05_1_physical_probe.py \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py

export P05_2_FAULT="/tmp/v3_p05_2_fault_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_2_fault.sh prepare "$P05_2_FAULT" \
  2>&1 | tee /tmp/v3_p05_2_fault_prepare.log
cat "$P05_2_FAULT/p05_2_fault_gate.json"
```

Expected host preflight (NOT physical evidence):
`target_step=2`, `target_core=1`,
`target_checkpoint_index=7`,
`expected_terminal=0xDEAD000A`,
`expected_dispatches_before_stop=9`,
and `expected_passing_checkpoints_before_stop=7`.

## Optional physical gate — after host tests PASS

Reboot KV260 to initialize DDR and ensure JTAG/hw_server are
accessible. The test **halts Linux and overwrites**
the accepted project's `0x40000000..0x43FFFFFF` DDR
reservation. **Reboot after every physical attempt, even
a failure. Never resume halted Linux.**

Reuse the **previously accepted P05 ELF build** (there
are no C changes in this P05.2a slice):

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# If your terminal lost the prior P05 build path, restore it:
# export P05_1_BUILD_DIR="<successful P05 Vitis build directory>"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"

export P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES
set -o pipefail
bash scripts/run_p05_2_fault.sh physical "$P05_2_FAULT" \
  2>&1 | tee /tmp/v3_p05_2_fault_physical.log
cat "$P05_2_FAULT/verify.log"
```

**Expected only if the REAL physical first-mismatch diagnosis
works (do not treat this as an observed PASS yet):**

```text
P03 board-local terminal result=0xDEAD000A after ... poll(s)
PASS: P05.2 deliberate bad checkpoint REJECTED by real A53
      terminal=0xDEAD000A fault=11 fault_phase=13
      first_mismatch_timestep=2 core=1 class=state0 ...
      dispatches_before_stop=9 packets=6 resident_deliveries=6
      completed_barriers=2 checkpoints_passed=7
PASS: P05.2 prior real neural records/events unchanged;
      rejected only deliberately incorrect model expectation
P05_2_NEGATIVE_VERIFY_EXIT=0
PASS: P05.2 first hardware negative-checkpoint gate
```

A printed P03 prefix above comes from the accepted generic
XSDB *terminal-only launcher*, which is reused for P05 and
does not imply the P03 ELF was launched. The actual embedded
P05 executable identity is checked separately.

## Full P05.2 directed coverage matrix — not yet complete

| Behavior | Existing physical evidence | Remaining directed P05.2 work |
|---|---|---|
| Fixed-point one-compartment arithmetic, spike threshold | Two normal ring/triangle cases, 50 total real state0 checks | Saturation/sign/refractory/reset/decay boundary vectors and full 64-bit state |
| Nonresident packet delivery into DDR NEXT | First P05.1 ring, 30 packets | Multiple packets to same destination, event-bank depth, order |
| Direct-to-resident packet delivery | Second P05.1 triangle, 12 packets | Fanout, multiple axon/packet destinations and contention |
| Page-in, dirty eviction and final flush | First P05.1 35 page-ins/out; triangle 3/3 no replacements | Alternating victim/pathological replacement and burst stress |
| Global quiescence barrier | 7 + 5 real barriers | Stall injection, event overflow and no premature bank swap |
| First-error localization | Synthetic negative-host-only | **This P05.2a physical negative first-mismatch gate** |
| Fast/no-checkpoint execution | ABI/native-only | Physical fast-vs-diagnostic full-DDR equivalence with same inputs |
| Legal service-order invariance | Scheduler interface supports explicit order | New model-oracle variants and physical golden for reordered execution |
| Fanout/backpressure | No explicit physical coverage | New topology and pressure-directed vectors, PL instrumentation if necessary |

**P05.2 acceptance remains pending** across this matrix, not
just the first negative test.

## Counter and instrumentation audit (no new Vivado shell yet)

The existing PS A53 P05R result contains dispatch counts,
packet counts, explicit resident deliveries, page-ins/out,
evictions/hits, completed barriers, consumed external events,
passing checkpoints, and separate cumulative PS generic-timer
and PL cycle counters. The success callback also reads the
PL hardware ID/capabilities, dispatch/page-completed counts,
**last transfer page size**, global status/pending bytes
and AXI read/write **burst counts**.

**Do not mislabel `hw_last_page_bytes` as total DDR traffic.**
A full page-in transfers **438,272** bytes of project
context and mutable-only page-out transfers **106,496** bytes,
according to the accepted PS/PL page protocol. From software
operation counts we can compute *expected programmed payload
bytes*, but these are **not** directly measured AXI traffic
including overhead or stalls. PL hardware burst counts are
additional observations; their units and payload efficiency
must be checked before claiming delivered DDR throughput.
Likewise `ps_inference_ticks` excludes initial page
admission and finalization, `ps_timer_hz` is read from
`CNTFRQ_EL0`, and `pl_page_cycles`/`pl_dispatch_cycles`
are in their own PL domain. Avoid claiming calibrated
end-to-end latency, power or energy from P05 results.

**Priority for future P05.2:** quantify packet backpressure,
barrier wait and actual AXI bytes only if there are trustworthy
existing RTL counters; otherwise freeze an observability
contract and route new logic before quoting these metrics.
The accepted P03 bitstream remains the known-good fallback.

## Exit from P05.2a

Independent native tests and a real first-mismatch
A53 hardware error are both required. Record the complete
256-byte physical result mailbox, ELF/XSA/bitstream SHA,
source revision, neural model fingerprint, modified P05G
SHA and checkpoint-7 expected/observed CRC. Do not merge
the branch or claim full P05.2 completion on this narrow
test alone.
