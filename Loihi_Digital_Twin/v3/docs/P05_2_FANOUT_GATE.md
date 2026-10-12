# P05.2d — Two-route packet fanout and NEXT-bank aggregation

**Status:** Implemented on `agent/v3-p05-board-regression`;
**independent host regressions and KV260 physical acceptance PENDING**.
P05.2a wrong-expected-state detection, P05.2b fast/no-checkpoint
equivalence and P05.2c permuted service-order invariance
were already physically accepted. No new C, Vitis, RTL,
Vivado XSA/bitstream or native P03 source changes here.

## Architectural question

Previous physical workloads routed **at most one packet
per firing source**. This gate makes each spiking source
emit TWO distinct `OutputRoute` destination packets and
tests convergence: each resident destination receives
two routed events in its NEXT bank for the following
timestep, in addition to a separate external input
event. Packets may not be lost, duplicated or consumed
during the incorrect timestep.

The new independent `LogicalChip` model contains three
fully resident logical cores `(0,1,2)`, all-to-all
connections **without self-loops**:

```text
source 0 -> destinations 1,2
source 1 -> destinations 0,2
source 2 -> destinations 0,1
```

One compartment and one external input axon per core;
weight=3, threshold=4, current decay=4096,
voltage decay=0; five timesteps. A core first accumulates
subthreshold input, then emits spikes for four
subsequent timesteps. The **model must independently
verify** its prediction of 24 packets, not trust
hard-coded counters. The inference schedule is three
dispatches per timestep, preserving the accepted
P03/P05 A53 3-resident/1-HLS-engine architecture.

| Property | Strict expected physical result |
|---|---:|
| Logical cores / resident slots | 3 / 3 |
| Timestep barriers | 5 |
| Core dispatches | 15 |
| Emitted and routed packets | **24** |
| Physical direct resident deliveries | **24** |
| Routes per firing core | **2** |
| Routed NEXT input events/destination, per firing timestep | **2** |
| Total CURRENT input events/core on those timesteps | **3** (two routed + one external) |
| External events consumed | 15 |
| Independent hardware state0 checkpoint CRCs | 15 / 15 |
| Initial full page-ins | 3 |
| Replacement page-ins, evictions, runtime page-outs | 0 |
| Final mutable page-outs | 3 |
| Total hardware page commands | 6 |
| Final real DDR images | 3×512KiB **exactly equal** to separate Python oracle |

All 15 diagnostic state0 CRCs are derived from the new
Python model's actual per-dispatch neural state vectors;
the entire final DDR image is independently modeled,
including packet and event memory banks, not just
a few final state words. The strict verifier rejects
a mailbox PASS if any model-derived CRC, route-count
metadata, event row, physical packet count or byte of
the full DDR dump differs.

**Scope warning:** This covers **two outgoing routes per
firing source**, **multiple convergent packets per
destination**, and correct timing across the global
barrier. It **does not** establish backpressure
or overflow behavior at the 4096-entry event-bank
limit. Event-capacity/saturation cases remain
separate directed P05.2 work.

## New implementation

- `scripts/p05_2_fanout_fixture.py`: fresh
  `LogicalChip` + packed DDR three-core fanout
  oracle, independent 24-packet/15-checkpoint gate,
  legitimate P05G v1 descriptor.
- `scripts/p05_2_fanout_verify.py`: strict P05R,
  model, CRC/SHA and 3×512KiB DDR comparison;
  requires 24 real physical packet deliveries and
  all 15 hardware checkpoints to pass.
- `vivado/p05_2_fanout_prepare.tcl`: physical
  PSU/APU DDR provisioning and exact byte readback
  of three new neural contexts, bounded binary P05G
  payload/header and cleared result mailbox.
- `scripts/run_p05_2_fanout.sh`: distinct,
  opt-in KV260 physical pipeline reusing unchanged
  accepted bitstream, source-matched P05 A53 ELF,
  terminal polling, and three-record physical dump.
- `tests/test_p05_2_fanout.py`: host-only model
  generation, synthetic verifier positive/negative
  mailboxes, tampered neural input, corrupted raw
  DDR, topology and DDR overwrite opt-in guards.
  **A synthetic PASS is not physical evidence.**

## First independent native gate

From VS Code Ubuntu terminal:

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
  tests/test_p05_2_fanout.py \
  tests/test_p05_2_order.py \
  tests/test_p05_2_fast.py \
  tests/test_p05_2_fault.py \
  tests/test_p05_1_triangle.py \
  tests/test_p05_1_physical_probe.py \
  tests/test_p05_1_deployment.py \
  tests/test_p05_1_runtime_source.py
```

If any new assertion about the 24-packet model, P05G
physical routing metadata or full model DDR fails,
**do not loosen the physical verifier or proceed
to board**; inspect and fix the fixture/model assumption.

## Host-only prepare (no board accessed)

```bash
export P05_2_FANOUT="/tmp/v3_p05_2_fanout_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/run_p05_2_fanout.sh prepare "$P05_2_FANOUT" \
  2>&1 | tee /tmp/v3_p05_2_fanout_prepare.log

cat "$P05_2_FANOUT/p05_2_fanout_gate.json"
cat "$P05_2_FANOUT/p05_artifacts/p05_manifest.json"
```

Expect `expected_dispatches=15`,
`expected_packets=24`,
`expected_direct_resident_deliveries=24`,
`per_core_routes=2`,
`expected_checkpoints=15`.
No change to accepted P03, original triangle, or
frozen model evidence.

## Destructive physical gate — ONLY after native PASS

Reboot the KV260 first to initialize DDR. Confirm JTAG
and `hw_server` access and that the project's reserved
DDR range is not needed by Linux or other software.
**The command halts Linux and overwrites
`0x40000000..0x43FFFFFF`.** Reboot the board
after success or failure; never resume halted Linux.

Restore the same previously accepted shell/ELF:

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# Restore to the previously successful existing P05 Vitis folder if unset:
# export P05_1_BUILD_DIR="<previous accepted P05 A53 Vitis build dir>"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"

export P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES
set -o pipefail
bash scripts/run_p05_2_fanout.sh physical "$P05_2_FANOUT" \
  2>&1 | tee /tmp/v3_p05_2_fanout_physical.log

cat "$P05_2_FANOUT/verify.log"
```

The PC provisions and launches once, passively polls
the terminal and physically reads the three final
DDR records. **All packet delivery, inference,
barrier synchronization and any data-path faults
are handled on the physical A53/PL.**

Expected success markers **only if real hardware passes**:

```text
PASS: P05.2d physical two-route fanout model timesteps=5 dispatches=15 packets=24 resident_deliveries=24 barriers=5 events=15 checkpoints=15
PASS: P05.2d three complete 512KiB final DDR records byte-exact to independent fanout LogicalChip model (2 routes/source; two NEXT deliveries/destination on firing timesteps)
P05_2_FANOUT_VERIFY_EXIT=0
PASS: P05.2d physical dual-route packet fanout gate
```

Preserve the entire evidence folder on any error, and
record actual SHA256s, model fingerprint, A53/FPGA
identities and counters after first independent
hardware execution. **P05.2d and P05.2 overall
are not yet accepted.**

## Remaining P05.2 hardening

One fanout test does not close arithmetic boundary,
true near-capacity event-bank pressure/backpressure,
more pathological dirty replacement paging,
global-barrier fault behavior or comprehensive PS/PL/DDR
counter provenance. Plan those as additional directed
sub-gates with explicit software model and real board
evidence before declaring the overall P05 phase complete.
