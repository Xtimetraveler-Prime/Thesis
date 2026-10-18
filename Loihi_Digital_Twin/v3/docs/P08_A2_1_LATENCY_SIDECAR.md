# P08-A2.1 — Experimental A53 image-latency sidecar (source candidate)

**Status (2026-10-18): IMPLEMENTED ON FEATURE BRANCH / HOST TESTS AND USER VITIS BUILD NOT YET VERIFIED / PHYSICAL KV260 NOT RUN.**  
**Scope revision approved by user:** latency, throughput and their PS/PL overhead first; **power and energy characterization deferred** to a future user-authorized phase. No invented power readings. The P08-A1 measurement boundary proposal was accepted in this narrower sense; power-equipment selection is not an active gate.

## Why a separate firmware?

We preserve the exact accepted P07-A4 source under `software/p07/`, `P07A4R01` 1MiB result journal, signed-24 neural behavior, XSA/bitstream and 94.56% accepted official accuracy result. No deployment on the **original** accepted P07-A4.2b ELF is modified. Instead P08-A2.1 adds `software/p08/p08_a2_board.c` (a separately named, instrumented *copy* of P07's accepted A53 board implementation), linking the **unchanged** `software/p07/p07_a2_runtime.c`, P03 scheduler/PL adapter, event encoder, and P07 journal codec. It requires a separately built Vitis standalone ELF with the identity string `P08_A2_1_LATENCY_ONLY_KV260_A53_CANDIDATE_V1` and the exact accepted P03.2c routed XSA SHA256. A new candidate ELF is **not** physically accepted until separate numerical oracle validation.

## Version 1 of timing sidecar

`P08ALAT1`, separate from P07 neural result journal:

- Reserved DDR base `0x43000000`, 1MiB `0x43000000..0x430FFFFF`, within the previously reserved JTAG-only window, **not** the immutable master at `0x43F00000`, the P07 result journal at `0x42000000`, or the selected full trace at `0x43FF0000`. Previously accepted P07 byte layouts are unchanged.
- Exactly **256B** header and up to **10,000 × 96B** records; rest is zero. Explicit little-endian fields, record/header CRC32, version, count/trace index, terminal status, completed frames, exact A53 `CNTFRQ_EL0` value, dataset start/stop `CNTVCT_EL0` samples, memory capacity.
- For each image, four ordered A53 timestamps: `service_start` (`execute_image` entry), `after_ingress` (validated ingress built), `after_neural` (return from P07-A2 26-tick call **including per-frame prepare/reset/page-in**), and `after_commit` (P07 96B record and selected full trace flushed).
- Also a *separate-clock-domain* sum of `pl_dispatch_cycles` and `pl_page_cycles`, and A53 `ps_inference_ticks`, `ps_control_ticks`, `ps_route_ticks`, `ps_barrier_ticks` captured at the existing P03 `write_result` callback. Those counters and intervals are **not all disjoint**.
- The per-image `after_commit` boundary explicitly **excludes the extra timing-sidecar record/header flush**, whereas the full dataset start→stop interval **includes that profiling overhead**, software journal progress commits, and the autonomous loop. Do not call one the other. The single selected full-trace image normally costs more than an ordinary image and is flagged in each timing record.
- Fail-closed host parsing rejects corrupted headers/records, wrong count/index/trace flag, non-monotone timestamps, impossible durations, nonzero tails, missing exact terminal `0x600D600D`, missing A53 frequency or record overrun. No `PL Hz` or HLS neuron-only latency is inferred.

The host `scripts/p08_a2_timing_check.py` reports the raw A53-clock-scoped candidate distributions and **explicitly sets physical numerical acceptance to false**. It does NOT run the independent P07 packed oracle; that separate physical-gate step is mandatory before calling any measured number accepted.

The new `vivado/p08_a2_xsdb_run.tcl` is for **later P08-A3**: reads 1MiB journal + 64KiB selected trace + 1MiB sidecar, checks new firmware marker, refuses file overwrite, and waits for **BOTH** the original P07 terminal status and the P08 sidecar terminal status before stopping A53. This prevents stopping after the P07 journal finishes but before the P08 header closes.

## P08-A2.1 entry checks for USER (do NOT launch JTAG yet)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q tests/test_p08_a2_timing.py tests/test_p07_a4_official.py tests/test_p07_a4_fault.py
bash -n scripts/build_p08_a2.sh
python -m py_compile software/p08/build_p08_a2.py src/loihi_twin_v2/p08_a2_timing.py scripts/p08_a2_timing_check.py
```

Expected gate: **zero failures** in selected pytest suites, valid shell syntax, Python compilation success. Portable native test compiles `p08_a2_timing.c` with strict `-std=c11 -Wall -Wextra -Werror`, constructs an example two-frame 1MiB sidecar, checks C→Python parity and tests many corrupted binary scenarios. If `cc` is missing, pytest skips that fixture; such a skip **does not satisfy the full native C parity gate**. Review the full test summary.

### Separate Vitis build gate (USER machine only)

Run once Vitis 2025.2 tools are loaded and your **existing** accepted `P03_DIAG_REPORTS` points to the pinned routed XSA; never guess that directory:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
export P08_A2_BUILD_DIR="/tmp/v3_p08_a2_build_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p08_a2.sh
```

This is a **build-only** step and does **not** touch the board. Expected:

```text
P08_A2_A53_VITIS_BUILD_PASS=1
P08_A2_1_ELF_DDR_ISOLATION_PASS=1
P08_A2_1_VITIS_BUILD_PASS=1
P08_A2_1_KV260_LATENCY=NOT_RUN
```

Candidate ELF: `$P08_A2_BUILD_DIR/vitis_workspace/p08_a2_board.elf`; its observed SHA256 is emitted in `$P08_A2_BUILD_DIR/build_identity.txt`. It must be **different** from the frozen P07 accepted ELF. Fail if exact XSA pin or fresh destination/LOAD-section isolation does not match.

## Pending: P08-A2.2 per-tick timing, A3 KV260 verification

A2.1 deliberately provides **per-image aggregate** counters, not individual 26 per-tick event-source and event-bank MMIO timings. A2.2 should separately add encoder, append, dispatch MMIO wrapper, output trace, route and barrier **per-tick endpoints** with fixed-size, fail-closed telemetry; this must be native-tested and built/verified independently before claiming pure event-source latency. We should test A2.1 on your machine and finish its gate before beginning A2.2.

For the later P08-A3 **physical** gate, use ONLY synthetic or the predeclared 1,024 TRAIN-derived validation images, never rerun the official TEST by default. Preserve all original P07 numerical journal/trace and six provisioning readbacks. Confirm the board is rebooted to dedicated **JTAG-only bare-metal DDR ownership**, collect new raw sidecar and hashes with a **fresh** no-overwrite output directory, and run the existing independent `scripts/p07_a4_2_verify.py` against the *unchanged* P07 journal/trace plus the P08 timing parser. No such KV260 run is claimed now.

**No P08 power or energy study will be initiated until the user explicitly resumes it.**
