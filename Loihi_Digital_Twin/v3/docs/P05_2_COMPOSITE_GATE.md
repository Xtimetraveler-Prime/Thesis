# P05.2e — Combined physical five-over-three regression (pending board)

**Status:** First actual KV260 run produced **A53 terminal
success `0x600D600D`**, but the original independent
whole-DDR comparator **FAILED**:
`core3 packet bank offset 0x64000 actual=0x04
old expected=0x00`.
This gate remains **NOT ACCEPTED** until a strict
recheck of the original retained actual DDR records.
Source-level cause is normalized Loihi sorted
destination trace [0,4] vs packed FPGA
output-route descriptor order [4,0].
A separate immutable physical-memory golden and a
**NO NEW BOARD RUN** recheck tool have been committed:
`docs/P05_2E_PACKET_ORDER_INCIDENT.md`.
Run that non-destructive recheck **first**; only
return to board if another non-ordering mismatch
is found. P05.2d physical fanout PASS remains accepted:
`docs/P05_2D_FANOUT_ACCEPTANCE.md`.

**Goal:** One deliberately designed hardware test covers
several previously separate architectural gaps with **one**
independent Python model and one real A53 execution.
It does **not** claim all possible arithmetic edge cases
or event-bank saturation.

## Network and coverage

| Axis | This new composite case |
|---|---|
| Logical cores | Five: 0,1,2,3,4 |
| Physical resident slots | Three |
| Actual A53 service order | **4 → 1 → 3 → 0 → 2** (new order) |
| Timesteps and global barriers | Eight |
| Dispatches and external events | 40 each |
| Independent state0 checkpoints | 40 (all five cores per barrier) |
| Threshold per logical core | 4, 5, 6, 7, 8 (heterogeneous, normal range) |
| Weight/current decay/voltage decay | 3 / 4096 / 0 |
| Routes/core | Two distinct destinations: (core+1)%5 and (core+2)%5 |
| Destination residency | Both resident **and** nonresident; inferred per emitted packet at the moment of route |
| Victim policy | Accepted P03 round-robin next-victim slot |
| Paging | Repeated dirty page-out and reload to three slots across eight timesteps |
| Golden model | Separate `LogicalChip` simulation on five-core network, independently generated 5×512KiB DDR images |
| Program | Same user-accepted P05 Cortex-A53 ELF and P03.2c FPD128 bitstream |

**Important:** The new fixture runs the accepted independent
P02 hardware-backed model with new core parameters
and computes a *separate* deterministic mirror of the
accepted C scheduler's initial slot assignment, hits,
victim order, dirty marking, page-ins and page-outs.
It then walks every independently generated packed
outgoing model packet and tests destination residency
**at that source's dispatch moment**. The expected
packet count, resident and DDR-directed packet counts,
evictions, page hits, dirty page-outs, page-in command
counts, 40 checkpoint CRCs and five entire DDR final
record hashes are generated from these **separate**
reference computations. The fixture fails before
board if it does not actually exercise **both**
routing paths, 20+ evictions and 20+ dirty-outs,
two-route fanout and 3+ CURRENT input events.

The new five-core work is **not** a re-run of accepted
single-destination paging or three-resident fanout.
A physically valid result has to pass **all** checks:

- Real A53 terminal `0x600D600D`, 40 dispatches,
  40 consumed external events and eight barriers.
- Physical packet count equals the independently
  simulated model's count.
- Measured P05R `resident_deliveries` equals
  individually predicted packet destinations in slots
  at emission; inferred nonresident count is
  `routed_packets - resident_deliveries`. Both positive.
- `replacement_ins`, `runtime_outs`,
  `evictions`, `hits`, initial/final page-ins/out
  and completed hardware `hw_pages` equal the
  deterministic C-scheduler replay.
- **40/40 state0 checkpoints**, checked on real PL
  or nonresident authoritative DDR at the safe
  global barrier.
- All **five complete physical 512 KiB final DDR
  records byte-exact** to new independent Python
  goldens, including state, event, trace and packet
  banks, not just final membrane voltage.
- Exact staged P05G CRC/SHA, model identity, A53 ELF,
  accepted bitstream XSA fingerprint and no stale
  C sources, plus zero PL pending and positive
  hardware activity counters.

### DDR page-command accounting

The accepted PS/PL adapter's programmed page payloads:

- Full page-in: `P03_HW_FULL_PAGE_BYTES=0x6B000`
  (**438,272 bytes**) per initial or replacement
  page-in.
- Mutable-only dirty/final page-out:
  `P03_HW_MUTABLE_BYTES=0x1A000`
  (**106,496 bytes**) each.

The new scheduler ledger explicitly calculates
`programmed_page_in_payload_bytes`,
`programmed_page_out_payload_bytes`,
`programmed_total_page_payload_bytes`
from those sizes and **scheduled page command counts**.
The actual A53 also returns completed hardware page
commands. These quantities are **not measured AXI
bytes transferred**, bus stalls, page throughput,
power or energy. Actual burst counters are separately
recorded as nonzero observations, but conversion to
true effective memory bandwidth needs an instrumented
bus-domain measurement. No performance benchmark
is implied.

### Scope limitations

Heterogeneous *normal-range* thresholds are useful
arithmetic variation; they are not signed-overflow,
saturation, refractory or decay-boundary tests.
Even 3+ incoming events per core are nowhere near
the 4096-entry event-bank limit, so **true
backpressure and overflow recovery remain
unverified**. This composite also covers only one
specific core permutation over three slots, not
every legal scheduler order.

## Important: reverify ORIGINAL captured physical evidence first

For the user-confirmed first-run directory,
`/tmp/v3_p05_2_composite_20261012T190000Z`,
retain `verify.log` (the original FAIL) and execute
the new `scripts/recheck_p05_2_composite_evidence.py`
according to `docs/P05_2E_PACKET_ORDER_INCIDENT.md`.
This creates only a new derived route-order golden
and reports a complete DDR recheck for all five
originally captured physical DDR images. It does
**not** reprogram KV260 or change the A53/PL
model. If this recheck fails on any other byte,
preserve both logs and debug that discrepancy;
do not relax the comparator.

## First independent native checkpoint — must PASS

```bash
cd ~/Git/Thesis
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
    tests/test_p05_2_composite.py \
    tests/test_p05_2_fanout.py \
    tests/test_p05_2_order.py \
    tests/test_p05_2_fast.py \
    tests/test_p05_2_fault.py \
    tests/test_p05_1_triangle.py \
    tests/test_p05_1_physical_probe.py \
    tests/test_p05_1_deployment.py \
    tests/test_p05_1_runtime_source.py
```

These new synthetic mailbox and corrupted-DDR tests
are host-only verifier checks, not physical KV260
acceptance.

## Offline preparation (does not touch board)

```bash
export P05_2_COMPOSITE="/tmp/v3_p05_2_composite_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/run_p05_2_composite.sh prepare "$P05_2_COMPOSITE" \
    2>&1 | tee /tmp/v3_p05_2_composite_prepare.log

cat "$P05_2_COMPOSITE/p05_2_composite_gate.json"
cat "$P05_2_COMPOSITE/p05_artifacts/p05_manifest.json"
```

Look for `service_order=[4,1,3,0,2]`,
`expected_dispatches=40`,
`expected_checkpoints=40`, five logical cores,
three slots, **positive resident and nonresident
delivery counts**, and **at least 20 real replacement
paging and dirty writebacks** in the independently
computed `scheduler_model` section.
If the model or schedule preflight fails, STOP;
do not modify expectations merely to force a
hardware PASS.

## Physical KV260 verification — only if host PASS

Reboot the KV260 first, let its boot firmware
initialize DDR, confirm JTAG and `hw_server`
access. This run **halts Linux** and overwrites
reserved DDR `0x40000000..0x43FFFFFF`.
Never resume halted Linux; reboot again after
success or failure. Keep the evidence directory
if something breaks.

**Same accepted ELF and FPGA:** no new Vitis or
Vivado rebuild should be necessary. Restore
the accepted paths from prior P05 physical tests:

```bash
export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"

# If lost after restarting VS Code, restore exact successful build dir:
# export P05_1_BUILD_DIR="<previous successful P05 Vitis build>"
ls -lh "$P05_1_BUILD_DIR/vitis_workspace/p05_regression_run.elf"

export P05_2_CONFIRM_KV260_DDR_OVERWRITE=YES
set -o pipefail
bash scripts/run_p05_2_composite.sh physical "$P05_2_COMPOSITE" \
    2>&1 | tee /tmp/v3_p05_2_composite_physical.log

cat "$P05_2_COMPOSITE/verify.log"
```

A real PASS should produce **only if** everything
is physically correct:

```text
PASS: P05.2e physical FIVE-over-THREE composite order=4,1,3,0,2 steps=8 dispatches=40 packets=<model> resident_deliveries=<model> nonresident_deliveries=<model> barriers=8 events=40 checkpoints=40 replacement_ins=<model> runtime_outs=<model> evictions=<model>
PASS: P05.2e five complete 512KiB physical DDR records byte-exact to independent mixed-threshold five-core dual-fanout LogicalChip oracle
P05_2_COMPOSITE_VERIFY_EXIT=0
PASS: P05.2e MULTI-TARGET composite physical oracle and paging gate
```

**The variable counts are resolved by the independent
Python model and deterministic C scheduler replay**;
there is no invented fixed packet count. The prepared
`p05_2_composite_gate.json` contains the numeric
expected result before FPGA access.

After the physical run, copy the full `verify.log`
with all SHA-256 results. Record explicit coverage,
limit claims to supported observations, and continue
with the separate arithmetic-boundary and real
event-bank-pressure tests if P05.2 remains open.
No merge to `main` without user approval.
