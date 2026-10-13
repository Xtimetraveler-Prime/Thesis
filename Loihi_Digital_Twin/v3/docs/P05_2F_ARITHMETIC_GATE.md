# P05.2f — Combined signed saturation, decay, refractory and paging physical regression

> **Subsequently physically accepted (2026-10-12).** The independent
> user-provided KV260 result reported 30/30 checkpoints,
> six barriers, 27 evictions, eight real packets, and all
> five final 512 KiB DDR images matching the independent
> Python model (`P05_2F_VERIFY_EXIT=0`). All eight packets
> were resident-delivered; the P05.2e composite separately
> covers nonresident traffic. See
> [P05.2f acceptance](P05_2F_ACCEPTANCE.md).
> The original verification commands below remain reproducible
> instructions, not a statement that the test is still pending.
>
**Status:** IMPLEMENTED ON DEVELOPMENT BRANCH; **NOT independently verified**.
**Branch:** `agent/v3-p05-board-regression`.
**Hardware target:** accepted FPD128 P03.2c FPGA shell and unchanged
P05 configurable bare-metal A53 ELF (not Linux-owned runtime).

## Purpose / scope

One **six-timestep / 30-dispatch / 30-checkpoint** physical KV260 run
tests five different single-compartment neural parameter profiles:

| Logical core | Signed synaptic weight | Current decay | Voltage decay | Bias | Threshold | Coverage |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| 0 | +127 | 4096 | 4096 | +8388607 | +8388607 | positive signed-24 saturation without false spike |
| 1 | -127 | 4096 | 4096 | -8388608 | 4 | negative signed-24 saturation |
| 2 | -5 | 2048 | 1024 | 0 | 1024 | signed integration and round-away-from-zero fractional decay |
| 3 | +3 | 2048 | 1024 | 0 | 4 | threshold/reset plus refractory_ticks=2 |
| 4 | +7 | 0 | 0 | -2 | 15 | nondecaying current/voltage, routing to core 0 |

Every core has one output route to `(core+1)%5`; service order is
`[4,1,3,0,2]`, and **three** resident slots force dirty DDR paging.
The fixture derives its expected spikes, per-step state, packet counts,
victim replacement, physical command counts and all five complete
512KiB final DDR images from independently configured `LogicalChip`
and a separate P03 scheduler-policy replay. It aborts offline if the
positive and negative saturation states, signed negative state,
refractory state, real packet routing, or substantial paging do not
occur. All 30 state0 CRC checkpoints are derived from model vectors.

The accepted P05 board runner checks the post-barrier CRC on hardware
or authoritative DDR and reports the first mismatch; the strict host
verifier additionally audits both SHA/CRC-signed deployment records,
the actual encoded config and signed synapse per core, all mailbox
counters, and **all bytes in all five physical context images**, with
no packet/trace bank exclusion. Synthetic host mailbox tests cannot
satisfy the physical gate.

## Verification sequence

1. Native test and offline fixture generation (no hardware touched).
2. Independently review `p05_2f_gate.json`, input spec,
   immutable golden hashes and `preflight_identity.txt`.
3. **Reboot** KV260 and ensure DDR initialized, hw_server and XSDB
   running. Run `physical` only after setting explicit DDR overwrite
   consent. The script will stop Cortex-A53 cores, write reserved
   `0x40000000..0x43FFFFFF` project DDR through PSU/APU, verify
   each readback, program the accepted bitstream and load the same
   P05 A53 ELF once. PC passively polls and downloads the five records.
4. Preserve `verify.log`, `physical_identity.txt`,
   `p05_a53_result.bin` and every `final_ddr/core*_after.bin`.
   **Reboot after ANY physical attempt; never resume the halted Linux.**

### Commands on user's Ubuntu workstation

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
  tests/test_p05_2f_arithmetic.py \
  tests/test_p05_2_composite.py \
  tests/test_p05_2_fanout.py \
  tests/test_p05_2_order.py \
  tests/test_p05_2_fast.py \
  tests/test_p05_2_fault.py \
  2>&1 | tee /tmp/v3_p05_2f_native.log

export P05_2F_DIR="/tmp/v3_p05_2f_arithmetic_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_2f_arithmetic.sh prepare "$P05_2F_DIR" \
  2>&1 | tee /tmp/v3_p05_2f_prepare.log

# Before physical run, restore the accepted P03_DIAG_REPORTS,
# P05_1_BUILD_DIR and P03_2C_EXPECTED_XSA_SHA from earlier accepted
# tests. These are NOT guessed from system paths.
# REBOOT KV260 FIRST. This operation overwrites reserved FPGA DDR.
P05_2F_CONFIRM_KV260_DDR_OVERWRITE=YES \
  bash scripts/run_p05_2f_arithmetic.sh physical "$P05_2F_DIR" \
  2>&1 | tee /tmp/v3_p05_2f_physical.log

grep -E 'PASS|FAIL|P05_2F_VERIFY_EXIT|P05_2F_EVIDENCE_DIR' \
  "$P05_2F_DIR/verify.log" /tmp/v3_p05_2f_physical.log
# REBOOT KV260 AGAIN (including after a failure).
```

**Acceptance** requires native tests pass and a genuine P05R terminal
`0x600D600D`, 6 barriers, 30 actual dispatches, 30 model-derived
hardware state0 checks, model-matched packet/page counts, valid
hardware activity counters and five full 512KiB records byte-for-byte
equal to the independent Python oracle with
`P05_2F_VERIFY_EXIT=0`. No acceptance from software-only fixture
generation or fabricated mailboxes.

**Explicitly not covered:** 4096-event bank saturation/overflow/
backpressure, all adversarial barrier schedules, measured AXI
byte-traffic or throughput, power/energy, and general Loihi
asynchronous timing equivalence. Command payload bytes are a
software-derived quantity and must not be labeled hardware bus bytes.
