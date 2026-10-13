# P05.2h — Adversarial 16-barrier dual-event-bank and mixed-residency routing

**Status: IMPLEMENTED — native and physical independent verification PENDING.**
The independently user-confirmed P05.2g 4096-full and 4097-admission
physical PASS is recorded separately at [P05.2g acceptance](P05_2G_ACCEPTANCE.md).

## One-run integration gate

One physical run on the **accepted unchanged P03.2c FPGA PL and P05
standalone Cortex-A53 ELF** uses five logical cores over three
physical slots. Sixteen timesteps, service order `[4,1,3,0,2]`,
fixed core thresholds `[2,3,4,5,6]`, and two outgoing
destinations per firing neuron generate both resident and
nonresident NEXT-bank packets while the A53 repeatedly evicts
and restores dirty DDR contexts. No host PC decides any
algorithmic routing, victim selection or barrier advancement.

At **each of 16 actual barriers**, check `state0`, the first
`event0` word and the first `event1` word for **all five logical
cores** (240 minimum actual-device CRC observations). Check a
fourth class, `packet0`, whenever the source emitted physical
packets in that timestep. Those checks are independently calculated
from the original generated `LogicalChip` mathematical state
vectors and a separate chronological event-bank/NEXT packet
replay. The latter is independent of KV260 output and explicitly
tracks both alternating 4096-word banks.

The reference logical packet traces are destination-sorted, but
HLS packet RAM uses registered **source route descriptor order**.
A separate, source-derived `barrier_physical_golden` changes
**only the two packet RAM words** where required; it does not
alter `barrier_logical_golden`, the neurons, descriptor, or the
real DDR. The physical verifier compares **all five entire
512 KiB physical DDR records**, including event0/event1, state,
packet RAM, trace, and static/reserved memory, to that independent
reference, not just a single checksum from the device.

### Portable native-first verification

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
    tests/test_p05_2h_barrier.py \
    tests/test_p05_2g_capacity.py \
    tests/test_p05_2f_arithmetic.py \
    tests/test_p05_2_composite.py \
    2>&1 | tee /tmp/v3_p05_2h_native.log
grep -E 'passed|failed|error|FAIL|ERROR' /tmp/v3_p05_2h_native.log
```

**STOP if any native regression fails.** In particular, the
synthetic P05R/DDR tests only exercise verifier failure detection;
they do not establish a physical KV260 PASS. The new script
fails before any JTAG action if its Python files do not compile.

### Offline preparation — one command, does not access the KV260

```bash
export P05_2H_DIR="/tmp/v3_p05_2h_barrier_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p05_2h_barrier.sh prepare "$P05_2H_DIR" \
    2>&1 | tee /tmp/v3_p05_2h_prepare.log
```

Check the previously accepted `P03_DIAG_REPORTS`,
`P05_1_BUILD_DIR`, and `P03_2C_EXPECTED_XSA_SHA` environment
values before touching the board.

**REBOOT THE KV260**. This physical operation **halts Linux
and overwrites reserved project DDR**
`0x40000000..0x43FFFFFF`. Ensure JTAG/hw_server is usable.
Never resume halted Linux.

```bash
P05_2H_CONFIRM_KV260_DDR_OVERWRITE=YES \
P05_2H_RUN_MAX_SECONDS=1800 \
bash scripts/run_p05_2h_barrier.sh physical "$P05_2H_DIR" \
    2>&1 | tee /tmp/v3_p05_2h_physical.log

grep -E 'PASS|FAIL|P05_2H_VERIFY_EXIT' "$P05_2H_DIR/verify.log"
```

**REBOOT THE KV260 afterward on success, error, or timeout.**
Preserve the entire evidence directory, physical binary images
and P05R mailbox. Never reuse the path for another physical run.

## Strict acceptance and limits

- `P05_2H_VERIFY_EXIT=0` ONLY if live P05R terminal is success,
  16 barriers completed, 80 HLS dispatches, all expected per-barrier
  state/bank/packet CRC checks passed, live page/packet counters match
  the separate paging replay, both destination residency modes are
  present, and five complete physical DDR images match independently
  generated golden values.
- This proves substantial alternating-bank/barrier behavior
  under multi-core routing/paging pressure. It does **not** prove
  in-loop event bank exhaustion/backpressure recovery at 4097
  *routed* packets or calibrated AXI bus transfer bytes. The test
  preserves those limits explicitly for later gates.
- No new bitstream, Vitis rebuild, changed C runtime, HLS logic
  or FPGA synthesis is needed.

Main files:
`scripts/p05_2h_barrier_fixture.py`,
`scripts/p05_2h_barrier_verify.py`,
`scripts/run_p05_2h_barrier.sh`,
`vivado/p05_2h_barrier_prepare.tcl`,
`tests/test_p05_2h_barrier.py`.
