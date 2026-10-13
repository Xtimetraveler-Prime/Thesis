# P05.2i — Final P05 page-AXI transfer-counter provenance / closeout gate

**Status: IMPLEMENTED — independent native and physical KV260 verification PENDING.**
P05.2h is independently physically accepted:
[318 checkpoints, 156 packets (78 resident/78 nonresident), 77 evictions,
five full DDR records](P05_2H_ACCEPTANCE.md).
The preceding P05.2g exact 4096-input-bank and CRC-valid 4097-deployment
rejection are also [physically accepted](P05_2G_ACCEPTANCE.md).

## Physical experiment — one run, no new RTL or firmware

Rerun the **unchanged accepted P05.2h 16-timestep five-core,
three-slot physical regression** (80 real HLS dispatches, 318
post-barrier neural/event/packet checks and 5 complete 512 KiB
DDR images) with the existing accepted P05 A53 ELF and P03.2c
FPD128 shell. After the A53 emits its verified final `P05R`
mailbox and is halted, capture four adjacent, read-only **live
PL MMIO registers** from `0xA4000044` through `0xA4000050`
using PSU/APU physical debugger access. Read twice and insist on
identical 16-byte snapshots. No clock/reset/page/dispatch/write
commands are issued in the new counter-capture stage.

The register contract comes from existing
`rtl/p03_ps_control_regs.v` connected to
`rtl/p02_axi128_burst_adapter.v`, whose successful AXI
transport is fixed at 16 beats × 128 bits = 256 bytes per
transaction:

| Physical register | Measured quantity | Frozen expected |
|---|---|---:|
| `0xA4000044` | Completed AXI read bursts | **136,960** |
| `0xA4000048` | Completed AXI write bursts | **33,280** |
| `0xA400004C` | Successful page AXI bytes, low 32 bits | **43,581,440** |
| `0xA4000050` | Successful page AXI bytes, high 32 bits | **0** |

These numbers derive **before physical execution** from the
separate accepted P03 scheduler replay:

- Initial full page-ins: **3**;
- Replacement full page-ins: **77**;
- Runtime dirty mutable page-outs: **77**;
- Final dirty mutable page-outs: **3**;
- Full-in commands: **80 × 0x6B000 = 35,061,760 bytes**;
- Mutable-out commands: **80 × 0x1A000 = 8,519,680 bytes**;
- Physical read burst count: 35,061,760 ÷ 256 = **136,960**;
- Physical write burst count: 8,519,680 ÷ 256 = **33,280**;
- Combined successful AXI page bytes: **43,581,440**.

These are **PL page-engine HP0 DDR transfer counters**, NOT
total platform AXI traffic, host-provisioning traffic, PS
DDR-side routing stores, cache maintenance costs or real
system-wide bandwidth. Both the independent A53 P05R
`hw_read_bursts`/`hw_write_bursts` and the direct halted
PL hardware counter snapshot must match these expected
values. Exact 64-bit `axi_bytes_moved` must equal the
successful burst total × 256, with PL/PS raw cycle counters
present and no PAGE_PENDING/GLOBAL_STATUS errors.

One failed physical checkpoint, full 512 KiB DDR mismatch,
wrong burst count, missing witness, changed model manifest,
unrelated A53 fault or truncated capture means **P05.2i
FAILS**. The host cannot accept a self-declared `PASS`
from the FPGA.

## Native-first verification

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail
PYTHONPATH="$PWD/src" python -m pytest -q \
    tests/test_p05_2i_axi_closeout.py \
    tests/test_p05_2h_barrier.py \
    tests/test_p05_2g_capacity.py \
    tests/test_p05_2f_arithmetic.py \
    tests/test_p05_2_composite.py \
    2>&1 | tee /tmp/v3_p05_2i_native.log
grep -E 'passed|failed|error|FAIL|ERROR' /tmp/v3_p05_2i_native.log
```

**STOP on any native failure.** The native P05.2i
mailbox/witness construction tests are expressly synthetic,
not a physical success claim.

## Offline prepare (one new evidence directory)

```bash
export P05_2I_DIR="/tmp/v3_p05_2i_axi_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_2i_axi_closeout.sh prepare "$P05_2I_DIR" \
    2>&1 | tee /tmp/v3_p05_2i_prepare.log
```

The script prepares frozen P05.2h logical and physical oracles,
P05G deployment, preflight SHA ledger and model-derived exact
AXI counter expectations. It does not touch the KV260.

## Physical test (exactly one accepted A53/FPGA execution)

Restore all **previously accepted** `P03_DIAG_REPORTS`,
`P05_1_BUILD_DIR`, `P03_2C_EXPECTED_XSA_SHA`, and
XSDB/hw_server environment configuration.

**REBOOT KV260 FIRST.** This operation HALTS Linux and
OVERWRITES reserved project DDR `0x40000000..0x43FFFFFF`.
Do not resume halted Linux.

```bash
P05_2I_CONFIRM_KV260_DDR_OVERWRITE=YES \
P05_2I_RUN_MAX_SECONDS=1800 \
bash scripts/run_p05_2i_axi_closeout.sh physical "$P05_2I_DIR" \
    2>&1 | tee /tmp/v3_p05_2i_physical.log

grep -E 'PASS|FAIL|P05_2I_VERIFY_EXIT|P05_2I_MEASUREMENTS' \
    "$P05_2I_DIR/p05_2i_verify.log"
```

**REBOOT KV260 AFTERWARD, including on failure or timeout.**
Do not overwrite evidence and never rerun physical on the
same directory.

### Recovery from the observed XSDB software memory-map rejection

**Observed on the real KV260, 2026-10-13**: The fully
accepted P05.2h physical workload completed again (80
dispatches, 318 checkpoints, 156 packets, 78 resident
and 78 nonresident, 77 evictions, five complete byte-exact
DDR records), then the ORIGINAL XSDB `mrd -bin -file`
attempt at `0xA4000044` stopped because the debugger
had not added PS-to-PL memory to its address map.
This was a **debugger address admission failure**, not a
neural/HLS failure. No final P05.2i AXI witness or
`p05_2i_verify.log` was produced; overall P05.2i
remains **PENDING**.

AMD UG1725/UG1400 documents `mrd -force` to override
debugger-side reserved/invalid address **software**
protection. It does not bypass a true hardware firewall or
recreate page-engine registers after a PL reset. The new
capture script uses `mrd -force -bin -file`, twice and
checks stable values. It preserves any zero-byte file
created by the original rejected unforced read under
`p05_2i_axi_witness.bin.original_unforced_block.bin`.
It never overwrites a nonempty counter witness.

**If the KV260 has NOT rebooted, reset or been
reprogrammed since this physical run**, leave the halted
board intact and reuse the existing evidence folder.
Pull the updated branch and run the guarded **read-only**
recovery, without re-running FPGA inference:

```bash
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p05-board-regression
git pull --ff-only origin agent/v3-p05-board-regression
cd Loihi_Digital_Twin/v3

export P05_2I_DIR=/tmp/v3_p05_2i_axi_20261013T010913Z
P05_2I_CONFIRM_READONLY_RECOVERY=YES \
bash scripts/run_p05_2i_axi_recover.sh "$P05_2I_DIR" \
  2>&1 | tee /tmp/v3_p05_2i_recovery.log
grep -E 'PASS|FAIL|P05_2I_VERIFY_EXIT|P05_2I_MEASUREMENTS' \
    "$P05_2I_DIR/p05_2i_verify.log"
```

The recovery script validates the prior original A53
`P05R`, manifest SHA and physically captured full DDR,
then captures the four counters via read-only JTAG,
and runs the entire final independent P05.2i
verification. **Reboot the KV260 afterward**, even on
a failure. If direct `mrd -force` produces an actual
hardware bus-access fault, preserve the evidence and
stop. Do not create artificial byte data or weaken checks.

**If the board has ALREADY rebooted**, no live
PL counter recovery is possible from the earlier run.
Keep that directory unchanged and perform the ordinary
`prepare` + `physical` flow above in a completely
NEW evidence folder. The patched physical flow will
now use `-force` at the final MMIO capture. It must
still pass the exact physical counter equality checks.

### If the read-only debugger-side MMIO capture fails

Some debugger/PSU target configurations might not forward
DAP physical accesses to the PS-to-PL HPM0 AXI4-Lite
window while Linux is halted. We cannot assume this
accessibility merely from A53 firmware working. If
`p05_2i_axi_capture.log` contains an MMIO/JTAG error,
the test remains **not accepted**; preserve the raw
original successful P05.2h device evidence and report the
error. A subsequent approach might require a separately
approved counter-readable A53 diagnostics ELF or Xilinx
XSDB target-mode change. **Do not tamper with the accepted
bitstream/ELF, fake a hardware witness, or silently
substitute predicted page-command bytes for the counter.**

## Phase-5 closure policy

A real `P05_2I_VERIFY_EXIT=0` plus the previously accepted
P05.1 and P05.2a–h hardware gates supports closing **the
validated P05 architectural correctness/observability
scope**. The closure report must explicitly distinguish
three separate claims:

1. Physically verified: neuron arithmetic, signed
   saturation/refractory, paging, double event banks,
   resident/nonresident routing and fanout, stable
   barriers, source-order packet memory, 4096 accepted
   external events and 4097 CRC-valid P05G admission
   rejection, five complete DDR references, and directly
   counted AXI page-engine bursts/bytes.
2. Portable C/native verified only: routing adapter
   rejects an overflow attempted beyond 4096 NEXT events
   before a DDR store/clean.
3. **NOT physically demonstrated:** a *routed* 4097th
   NEXT-bank packet in a real inference run, packet stall
   timing or automatic recovery from runtime overflow,
   and total-system AXI/energy/bandwidth. These cannot be
   counted as accepted measurements. Document as explicit
   limitations and revisit if the benchmark requires them.

**Do not merge or mark P05 complete before the user
independently verifies this gate and explicitly approves
the closeout scope.** Model-derived numbers alone are
not an actual AXI measurement.
