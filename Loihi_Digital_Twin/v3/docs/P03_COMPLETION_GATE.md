# P03 — Combined Autonomous Runtime Completion Gate (P03.3c/P03.4/P03.5)

**Implementation branch:** `agent/v3-p03-autonomous-runtime`  
**P03.3b3 physical status:** ACCEPTED from independent user KV260 evidence, 2026-10-11.  
**Combined remaining implementation:** Prepared; **native/Vitis/board verification pending**.  
**Do not merge into main** until independently verified and explicitly approved.

## 1. Accepted prerequisite: actual packet routing and dirty page survival

The user independently ran the accepted P03.2c FPD128
PS -> SmartConnect -> 32-bit AXI-Lite FPGA bitstream with a standalone
Cortex-A53 application that executed real P03.3a runtime scheduling
and P03.3b packet/DDR callbacks.

```text
PASS: P03.3b3 physical packet/page roundtrip ps_width=128
 first_packet=0x2000000020000581 second_packet=0x2000000040000A00
 core1_ddr_event1=11 core0_ddr_event0=20
 page_ins=3 page_outs=3 dispatches=4 barriers=2 routed_packets=2
P03_3B3_VERIFY_EXIT=0
P03_3B3_EVIDENCE_DIR=/tmp/v3_p03_3b3_fixed_20261012T034337Z
PASS: P03.3b3 physical Cortex-A53 two-core HLS packet/DDR/dirty-page roundtrip
```

This is physical proof of two **HLS-generated** packet words,
nonresident next-event routing, dirty eviction and reloaded event
preservation; not just a mocked C callback. This directed one-slot
scenario does **not** physically exercise direct packet delivery into
an already-resident destination. That path remains native-tested.
Diagnostic ILAs and the accepted otherwise-unmapped signature remain
instrumentation during P03.

## 2. Why remaining work uses ONE implementation and TWO acceptance runs

Rather than multiple incremental subphases, P03.3c, P03.4 and P03.5
share a **single standalone A53 application**:

```text
five frozen P02.4b logical cores (IDs 0..4)
three physical resident slots
one HLS engine
one P03.3a scheduler and P03.3b hardware adapter
one board-local external event per core per timestep
P03 launch manifest selects exactly 7 or 100 timesteps
```

The 7-timestep gate reuses **exactly the accepted P02.4b ring
workload**, not a new synthetic benchmark. The unchanged
`scripts/p02_4b_ring_fixture.py` Python reference freezes
35 dispatches and 30 packets, golden final state/event/trace/packet
memory and its accepted normalized trace digest:

```text
9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac
```

The 100-timestep profile changes only the executed timestep count,
not the ring topology or arithmetic. The reference computes its exact
golden packet stream, trace digest and five expected final DDR records
separately. It is **not** claimed to be previously physically accepted.

The original P02 host pager sometimes paged destinations to route
packets. The P03 runtime instead routes to nonresident destination
DDR NEXT banks **without paging**. Physical page counts are therefore
expected to differ while **logical state, packets and final memory**
must still match the same Python architectural oracle.

## 3. Runtime partition and source files

```text
software/p03/p03_finish_run.c         standalone launch, 7/100 manifests,
                                       PS CNTVCT timer, input injection,
                                       fail-closed result mailbox and final
                                       flush of all resident dirty contexts
software/p03/p03_runtime.c            accepted deterministic board-local loop
software/p03/p03_hw_adapter.c         accepted FPD128/MMIO/DDR packet adapter
software/p03/p03_hw_runtime_bridge.c  actual physical callbacks
software/p03/p03_hw_xilinx_io.c       Xilinx BSP read/write/cache transport
software/p03/build_p03_finish.py     isolated Vitis standalone source import
scripts/build_p03_finish.sh           frozen XSA SHA/route check, fresh build
scripts/p03_finish_fixture.py         P02.4b golden 7/100 records and manifest
scripts/run_p03_finish.sh             one-button provision/program/launch/
                                       passive terminal wait/final DDR dump
scripts/p03_finish_verify.py          mailbox + five byte-exact DDR oracles
vivado/p03_finish_xsdb_prepare.tcl    5 records + manifest + result mailbox
vivado/p03_finish_xsdb_run.tcl        A53 ELF launch and passive DONE/ERROR poll
vivado/p03_finish_xsdb_dump.tcl       physical final DDR readback
tests/test_p03_finish_autonomy.py     native/fixture/strict verifier regressions
```

The PC is not called by the A53 scheduler. After a single `con`,
XSDB passively reads the standalone application's terminal result
mailbox; it never issues paging, packet, dispatch or timestep actions.
DDR readback occurs only **after** the A53 has halted on DONE/ERROR.

The A53 validates a fixed 256-byte versioned launch manifest at
`0x43FE0000` using CRC32, checks the five 512 KiB initial DDR records
(`0x40000000`.. `0x4027FFFF`) against manifest CRC32s and static
header identities, verifies each initial resident config,
and injects one external axon `10 + core_id` into the CURRENT
event bank immediately **before that core's dispatch** on every
timestep. This exactly reproduces P02.4b's architectural ingress
timing without the PC entering the loop.

The runtime callback drains packets from the real FPGA after each
dispatch, updating the PS-owned event-count table. Before DONE,
the A53 performs mutable-only page-out for each still-dirty resident
slot so **all five full DDR records** are authoritative. The external
verifier then compares every byte of every record against the P02
golden, including packed compartment state, trace, packet bank and
the raw stale event words outside the active NEXT counts. This is
stronger than a successful launch counter alone.

The 256-byte result mailbox includes first fault/phase, dispatch,
page, packet, barrier, victim/hit counters, five 64-bit final state
words, all five final NEXT-event counts, PL cycle totals,
PS generic timer ticks and CNTFRQ_HZ, and static MMIO status.
The PS inference/control timing counters stop before the final
`write_result` callback and its dirty flush; these intervals must
**not** be mislabeled as full end-to-end launch-to-mailbox latency
in later P08 measurements. The PS clock is raw CNTVCT_EL0; timer
frequency is read from CNTFRQ_EL0 (not assumed).

**Security/scoping:** CRC32 checks accidental corruption, not
cryptographic authenticity. The old P02 DDR SHA-256 payload header is
not automatically refreshed as mutable state changes; that is an
explicit ABI/runtime metadata consistency limitation, not a reason
to weaken physical golden comparison. The temporary DDR window is
used only when Linux's A53 contexts have been stopped.

## 4. Native regression and one-time Vitis build

On Ubuntu/VS Code:

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python -m pytest -q \
    tests/test_p03_finish_autonomy.py \
    tests/test_p03_3b3_physical_probe.py \
    tests/test_p03_3b_hw_adapter.py \
    tests/test_p03_3a_native_runtime.py \
    tests/test_p02_4b_ring_fixture.py

export P03_DIAG_REPORTS="$(ls -dt "$PWD"/vivado/build/p03_2c_fpd128_route_*/reports | head -1)"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_FINISH_BUILD_DIR="$PWD/vivado/build/p03_finish_$(date -u +%Y%m%dT%H%M%SZ)"
set -o pipefail
bash scripts/build_p03_finish.sh 2>&1 | tee /tmp/v3_p03_finish_build.log
```

Required pre-physical marker:

```text
PASS: P03 final A53 ELF contains retained P03 final diagnostic firmware identity
PASS: P03 final ELF avoids 64 MiB reserved DDR fixture/mailbox window
PASS: P03 final standalone A53 runtime-adapter probe build ready for board verification
```

**Those are expected strings, not already observed build results.**

## 5. 7-step and 100-step physical gates (same ELF)

Reboot the KV260 and allow normal PS DDR initialization before each
run; keep `hw_server` running. This stops Linux, changes the FPGA
bitstream, overwrites the **project-designated** DDR records,
launch config and result mailbox within `0x40000000..0x43FFFFFF`,
and requires another board reboot afterward.

Seven-step acceptance first:

```bash
export P03_FINISH_EVIDENCE_7="/tmp/v3_p03_finish_7_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_finish.sh 7 "$P03_FINISH_EVIDENCE_7" \
    2>&1 | tee /tmp/v3_p03_finish_7_physical.log
cat "$P03_FINISH_EVIDENCE_7/verify.log"
```

Required if physical success:

```text
PASS: P03 autonomous five-over-three P02/v2 normalized golden timesteps=7 dispatches=35 packets=30 barriers=7 ...
PASS: P03 all five final 512KiB DDR records byte-exact to frozen Python P02 oracle
P03_FINISH_VERIFY_EXIT=0
PASS: P03 7-step independent board-autonomous physical golden gate
```

**Reboot** KV260 and allow its normal DDR initialization again.
Then run the 100-step gate using the SAME ELf build and same
`P03_FINISH_BUILD_DIR` environment variable:

```bash
export P03_FINISH_EVIDENCE_100="/tmp/v3_p03_finish_100_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/run_p03_finish.sh 100 "$P03_FINISH_EVIDENCE_100" \
    2>&1 | tee /tmp/v3_p03_finish_100_physical.log
cat "$P03_FINISH_EVIDENCE_100/verify.log"
```

Require `dispatches=500`, `barriers=100`, byte-exact final records,
and the Python golden packet count/trace fingerprint generated for
**this exact 100-step fixture** (not inferred from the 7-step run).
Then reboot KV260; do not resume the halted Linux context.

## 6. Acceptance boundary and remaining physical signoff

**Offline regression or a successful ELF build cannot accept P03.4/5.**
The standalone board-local 7/100 golden gates must be independently
run on KV260. The 256-byte mailbox and five full DDR dumps must be
preserved for reproducibility.

The 7-step physical gate would accept P03.3c + P03.4 functionality.
The 100-step physical gate would accept P03.5 if normalized byte-exact
equality and model-owned packet counts pass. Direct resident-destination
MMIO routing remains physically untested by the original P03.3b3
one-slot test, so a stricter end-to-end signoff should verify this
path when actually exercised in the three-slot run, not merely infer
coverage from the presence of resident slots. Any acceptable final
P03 closeout should document this evidence boundary.

The accepted P03.2c bitstream retains temporary diagnostic ILAs,
VIO observation/reset and otherwise-unmapped signature. The final
production cleanup remains a separate opt-in release/retiming gate;
do not silently replace the accepted FPGA candidate.

**Do not merge the branch or claim P03 complete** until independent
7/100 evidence passes, failure cases are handled, and the user
explicitly approves acceptance.


## 7. Local Python package resolution regression repaired (2026-10-11)

The first user-run consolidated P03 regression reported four failures,
all from the same early subprocess import:

```text
scripts/p03_finish_fixture.py -> scripts/p02_4b_ring_fixture.py
ModuleNotFoundError: No module named 'loihi_twin_v2.ddr_abi'
```

Unlike the parent pytest process, a direct `python scripts/file.py`
process searches `scripts/` rather than `v3/src/` by default.
The existing `.venv-p08` can also have an older package with the same
`loihi_twin_v2` name but without the newer `ddr_abi` module.

Both `scripts/p03_finish_fixture.py` and
`scripts/p03_finish_verify.py` now explicitly prepend the **current
v3 checkout's** `src/` directory before dynamically loading the
unchanged accepted P02.4b oracle. This resolves the same defect during
generation and independent post-run DDR verification.

The existing `tests/test_p03_finish_autonomy.py` subprocess helper now
deliberately supplies a shadowing `loihi_twin_v2` package via
`PYTHONPATH`, and runs from an unrelated temporary working directory.
A script that imports the environment's older package, rather than
`v3/src/`, therefore fails the regression. No golden model,
7/100 workload, FPGA C implementation, or accepted P02 source was
modified by these import-path changes.

**Verification:** fix committed; full user-side pytest and Vitis
build remain pending. The four reported failures did not reach
manifest or physical-inference assertions. Do not label P03.3c/P03.4/
P03.5 accepted until the focused test suite and independent board
gates have completed.
