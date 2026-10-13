# P05.2g — Exact 4096-event hardware capacity and CRC-valid 4097-event fail-closed rejection

**Status: IMPLEMENTED, HOST/NATIVE + KV260 INDEPENDENT VERIFICATION PENDING.**
**Branch:** `agent/v3-p05-board-regression` (not merged).

## Why two physical modes?

One accepted P05 bare-metal A53 execution owns one deployment and
deliberate early errors halt its runtime. To verify a **successful
exact-capacity execution** and an **expected pre-dispatch rejection**,
run separate physical profiles with a fresh KV260 reboot between
them. Both use the accepted unchanged P03.2c FPD128 FPGA and P05 A53
ELF; no new HLS, bitstream, DDR ABI, or scheduler C is required.

**Physical FULL:** 1 logical core / 1 resident slot / 1 timestep.
Exactly **4,096 external axon-10 events** are consumed in the CURRENT
bank; a single signed-24 neuron integrates them with weight 1,
current_decay=0, voltage_decay=0, threshold=7000 without firing.
The independent `LogicalChip` predicts current=4096,
voltage=4096, zero outgoing packets, 1 dispatch, 1 barrier, 3
device checkpoints (state0/event0/event1), 1 initial page-in and
1 final mutable-out. Host verification compares the **entire**
actual 512 KiB core0 DDR image: all 4,096 event0 words, untouched
event1 bank, state, trace, config and reserved memory bytes.

**Physical OVERFLOW:** Same original 512 KiB logical core and
same `P05_CONFIGURABLE_A53_REGRESSION_V1` ELF, but a deliberately
constructed descriptor contains **4,097 registered events at t0**.
It has consistent length, offsets and both correct payload/header
CRC32 checksums: the bad event COUNT, not broken integrity, must
trigger device-side `P05_BAD_EVENT`. Expect the board's *precise*
fail-closed terminal `0xDEAD0002`, `error=2`, with **zero**
runtime dispatches, pages, events consumed, checkpoints and barriers,
and complete initial DDR image unchanged. An arbitrary board error
is a failed test. This physically verifies deployment admission,
**not runtime hardware event-bank overflow**.

### Native routing overflow check

`tests/p05_2g_route_guard.c` compiles the unchanged
`software/p03/p03_hw_adapter.c` and asserts a nonresident NEXT
bank at count 4095 accepts precisely the final legal packet at
index 4095 and increments to 4096, then rejects the next packet
with `P03_HW_OVERFLOW` **before** a further DDR write/clean.
This is **portable C transport simulation**, not physical routed
packet congestion, and must be reported as such.

## Independent Ubuntu reproduction

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
    tests/test_p05_2g_capacity.py \
    tests/test_p05_2f_arithmetic.py \
    tests/test_p05_2_composite.py \
    2>&1 | tee /tmp/v3_p05_2g_native.log

export P05_2G_ROOT="/tmp/v3_p05_2g_capacity_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_2g_capacity.sh prepare "$P05_2G_ROOT" \
    2>&1 | tee /tmp/v3_p05_2g_prepare.log

# Restore previously accepted P03_DIAG_REPORTS, P05_1_BUILD_DIR,
# P03_2C_EXPECTED_XSA_SHA from successful physical P05 tests.

# REBOOT KV260, ensure initialized DDR and XSDB/hw_server.
P05_2G_CONFIRM_KV260_DDR_OVERWRITE=YES \
    bash scripts/run_p05_2g_capacity.sh physical-full "$P05_2G_ROOT" \
    2>&1 | tee /tmp/v3_p05_2g_full.log

# REBOOT KV260 AGAIN; same board/ELF/bitstream, new CRC-valid 4097 P05G.
P05_2G_CONFIRM_KV260_DDR_OVERWRITE=YES \
    bash scripts/run_p05_2g_capacity.sh physical-overflow "$P05_2G_ROOT" \
    2>&1 | tee /tmp/v3_p05_2g_overflow.log

grep -E "PASS|FAIL|P05_2G_.*VERIFY_EXIT" \
    "$P05_2G_ROOT/full/verify.log" \
    "$P05_2G_ROOT/overflow/verify.log"
# REBOOT KV260 AFTER THE SECOND RUN, SUCCESS OR FAILURE.
```

**STOP if any native test or offline prepare fails.**
**Physical runs intentionally halt Linux and overwrite reserved
DDR 0x40000000..0x43FFFFFF. Do not resume halted Linux; reboot
before/after each run, including on timeout/failure.** Preserve
`preflight_identity.txt`, `physical_identity.txt`, each run's
`p05_a53_result.bin`, `verify.log`, `a53_run.log`,
and original `final_ddr/core0_after.bin`.

## What is NOT yet established

The positive case fills a **CURRENT** event bank with
host-provisioned external events through A53 MMIO; it does not
fill the NEXT bank from 4,096 FPGA-generated routed packets.
The negative case verifies **A53 descriptor admission**, not
a live hardware 4097th packet. The portable C test verifies
one live route-handler boundary in an injected I/O mock, not
real FPGA backpressure or stall timing. Therefore **true
physical routed overflow/backpressure and adversarial barrier
traffic remain open P05.2 work**, as do calibrated bus bytes.
Do not close P05.2 on the basis of these tests alone.
