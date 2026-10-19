# P08-A3.2 — Paired 1,024-image physical latency baseline

**State (2026-10-18 project timeline): A3.2.1 HOST NATIVE VERIFIED; A3.2.2 AND A3.2.3 PHYSICAL KV260 THREE-PAIR REPEATED LATENCY RESULTS USER-ATTESTED COMPLETE. THREE RUN-PAIR MEDIAN A2.2−A2.1 SERVICE DIFFERENCES +16.840, +25.400, +29.710 µs (MEAN +23.984 µs; PAIR-LEVEL SD 6.551 µs). FINAL AGGREGATE RAW FILE/BINARY EVIDENCE STILL USER-LOCAL, NOT INDEPENDENTLY INSPECTED HERE; A5 CPU COMPARATOR REMAINS OPEN.**

**First paired physical result:** A2.1 ordinary 1023-image median **35.7023 ms** (p95 **41.9667 ms**), A2.2 median **35.7234 ms** (p95 **41.9800 ms**), matched-image median delta **+0.0168 ms / 16.8 µs** (matched p95 **+0.0744 ms**), both reported A53 clock frequencies **99,999,001 Hz**, original neural verification **PASS**, timing integrity **PASS_SINGLE_PAIR**. Preserve exact readings and provenance in [A3.2.2 first paired physical report](P08_A3_2_2_PHYSICAL_RESULTS.md). A3.2.3 extends with [two further cold-boot physical pairs](P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md); it must not pool repeated image IDs as independent data.

**Final experiment update:** All three physical pairs completed (A2.1→A2.2, A2.2→A2.1, A2.1→A2.2) on the frozen first1024 TRAIN-derived validation stage. This document's earlier proposal language is retained as research history, not a statement that further A3 physical experiments remain pending. [Final three-pair results and A5 closure requirements](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md). No new physical KV260 run is needed for the completed repeated latency study; power remains deferred.

## Motivation: measured A3.1 pilot is dominated by PS-side service

The [physically observed A3.1 pilot](P08_A3_1_PHYSICAL_LATENCY_RESULTS.md) contains 16 distinct TRAIN-derived validation images, exact 26×10 output flags and designated 26×42 full trace parity, observed A53 CNTFRQ_EL0 **99,999,001 Hz**, median **35.4432 ms** instrumented image service (min 31.2682 ms; max 41.2175 ms), and per-tick medians: **event encoder 499.955 µs**, **event-bank append 312.458 µs**, dispatch MMIO/wait **70.011 µs**, route **54.631 µs**, trace **33.030 µs**, barrier **0.940 µs**. Event encoding and event-bank staging are the measured dominant individual spans in this 16-image pilot. Stage medians are *not additive*; these timings do **not** isolate pure PL neuron execution.

A3.2 therefore measures how reproducible this observation is at the accepted full **1,024-image TRAIN-derived validation prefix** and how expensive the seven-boundary A2.2 instrumentation is relative to the separately built lower-overhead A2.1 image-only sidecar.

## Experimental controls and proposed run schedule (not yet physically authorized)

- Exactly **first 1,024 distinct held-out validation images** from the original accepted **MNIST TRAIN** corpus and original source split, with original-order sample IDs/byte sequence. No official t10k TEST access or replay; no checkpoint/weights/firmware modifications. `scripts/p07_a4_2_prepare.py --validation-first 1024 --trace-index 1023` produces only the immutable stage, with `p07_a4_2_check.py` and original full TRAIN source verification required.
- Firmware **A2.1** image-only probe: SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`. Firmware **A2.2** per-tick probe: SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`. They both use XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`; no Vitis rebuild expected unless byte identity fails.
- **Proposed** three *separate* JTAG-only, cold-reboot executions of each version (3 A2.1 + 3 A2.2), alternating order across pairs to check order/thermal/host effects. This requires acceptance of a specific run plan before running. Exactly **1,024 independent distinct image identities**, not 3×1,024 independent labels. The existing A3.1 first16 runner is **not** approved for 1,024.
- Only real A53 `CNTVCT_EL0` timestamps divided by the **matching run's own CNTFRQ_EL0**; do not assume the two runs have exactly equal firmware-reported rate. PL dispatch cycles form a separate custom FPGA clock domain and are **not converted** using the ARM frequency.
- Distinguish `frame=1023` selected full 42-neuron 26-tick readback from the 1,023 standard 10-output-read frames. Use **1023 ordinary images** for representative paired service and stage distributions; separately report frame1023 rather than pretending its path is ordinary.
- A2.1-to-A2.2 paired `after_commit-service_start` differences include all added A53 timer/callback sampling and schedule/memory effects plus run-to-run variability; they are **not** an exact counter-read instruction latency calibration. Throughput includes inter-frame timing record writes not included in the scoped frame-service endpoint.

## A3.2.1 — Offline pair analysis implementation

Code: `src/loihi_twin_v2/p08_a3_2_analysis.py`; guarded CLI `scripts/p08_a3_2_pair_check.py`. This phase makes **no board calls**, does not instantiate synthetic physical results, and does not run the official MNIST TEST.

The CLI (once future A3.2.2 raw run directories exist) takes `--stage-dir`, `--a21-run-dir`, `--a22-run-dir`, `--a21-elf`, `--a22-elf`, `--report`. The independently staged 1,024 validation corpus **must** have trace frame **1023**. Each run must have unique preserved raw evidence in a different directory, `physical_identity.txt` containing the right firmware identity, SHA256 and scope and a terminal success marker in its `a53_run.log`.

For **each** real capture independently, the analysis CLI first launches frozen `scripts/p07_a4_2_verify.py` and demands exact `P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1`, `P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1`, and `P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1`. This checks all 1024×26×10 physical output flags, class/count, routes and events against the original P03 packed replay oracle **and** the selected full 26×42 trace for **both versions**. A sidecar terminal alone is **not** enough.

After these two passes, parse:
- Original 1MiB P07 neural journals and 1MiB image A53 timing for each version, with count/CRC/trailing-zero/wire-format checks;
- Detailed A2.2 3MiB tick telemetry `P08TCK02` with tick-order/A53-clock/descriptor/trace/PL-cycle-sum crosschecks;
- Frozen 26-tick encoder schedule and journal event, route and drop counts for all 1024 images;
- Cross-firmware neural payload identity for all 1024 entries (exclude P07 elapsed-cycle field; that is not a neural-semantic output);
- Explicit distinct run directories and observed on-disk ELF SHA256s equal to the user-accepted version pins.

**Single-pair output**, created at a **fresh** report path, includes 1,024 exact per-image service values (in ms), frame-paired `A2.2 - A2.1` delta vectors, 1,023 ordinary-image distribution and selected frame separate; for both individual service and paired differences: min, median, mean, **p95 nearest rank**, max and sample standard deviation. Per-tick stage distributions are from **26×1,023 ordinary detailed ticks** in µs. The nearest-rank p95 is element `ceil(0.95*N)` in sorted observations, **not** interpolated. Raw per-frame PL dispatch cycles are retained in their native domain.

**No trial may assert `P08_A3_2_REPEATED_BASELINE_ACCEPTED=1` based on one pair.** Run-repeated variance and possible order effects require later A3.2.3 aggregation. The original 16-image measurements are a distinct feasibility pilot, not an extra paired 1024 measurement.

## A3.2.2 — Dual-mode JTAG capture implemented, native and physical verification pending

The [new, source-level A3.2.2 runner and full operator protocol](P08_A3_2_2_PHYSICAL_CAPTURE_PROTOCOL.md) have been implemented on the feature branch. The code still requires the user's native tests and first offline preflights before any approved board execution. The dedicated runner is `scripts/run_p08_a3_2_1024.sh` and per-run original oracle/timing gate is `scripts/p08_a3_2_single_check.py`. Its new native tests are `tests/test_p08_a3_2_capture.py`. The runner can take exactly one mode (`A2_1` or `A2_2`), never mixes build identities and never changes original P07/P03 C/HLS/bitstream. The original P07-A4.2a first1024 TRAIN stage (including selected trace=1023) is shared across all runs. The runner must prove all stage bytes/source hashes before any hardware call, enforce **post-reboot** dedicated JTAG-only consent, reject Linux DDR ownership, keep evidence outside Git and use a new no-overwrite directory for each run. It must perform physical XSDB byte-exact provisioning and pin original routed bit/ltx/XSA before launching one autonomous A53 dataset inference session.

Collect original P07 1MiB neural journal, selected 64KiB trace, 1MiB A2.1 timing sidecar and, only for A2.2, 3MiB per-tick sidecar. Exit as a **physical terminal but unverified numerical** until the original packed-oracle check succeeds. Raw failure logs and partial evidence are preserved. The A3.2.1 paired CLI is then run only when **both** individual hardware trials independently pass. Do not reuse an A3.1 `first16` evidence directory as `first1024`.

## Native A3.2.1 verification (USER REPORTED PASS), A3.2.2 tests PENDING

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q \
  tests/test_p08_a3_2_capture.py tests/test_p08_a3_2_analysis.py \
  tests/test_p08_a3_1_pilot.py tests/test_p08_a2_2_ticks.py \
  tests/test_p08_a2_timing.py tests/test_p07_a4_official.py tests/test_p07_a4_fault.py
python -m py_compile \
  src/loihi_twin_v2/p08_a3_2_analysis.py \
  scripts/p08_a3_2_pair_check.py scripts/p08_a3_2_single_check.py
bash -n scripts/run_p08_a3_2_1024.sh
```

The user already confirmed A3.2.1 host-native tests passed. The new A3.2.2 native capture tests and 1,024-image board trials have not been observed. No single-pair hardware pass or 3-pair physical baseline is asserted until actual independent board evidence exists.

## Sources and interpretation provenance

- [A3.1 physical numerical results](P08_A3_1_PHYSICAL_LATENCY_RESULTS.md) — exact user-supplied A53 seconds/µs and raw FPGA cycles.
- [A3.1 physical acceptance](P08_A3_1_PHYSICAL_ACCEPTANCE.md) — successful original packed-oracle and real board evidence.
- `software/p07/p07_a2_runtime.c`, `software/p03/p03_hw_adapter.c`, `scripts/p07_a4_2_verify.py`, `src/loihi_twin_v2/p07_a4_stream.py` — primary **accepted code** defining neural semantics, independent replay and wire capture contracts.
- [A2.2 hardware timing method](P08_A2_2_TIMING_METHODS.md) — Arm Generic Timer `CNTVCT_EL0` and `CNTFRQ_EL0` meanings and AMD UG1399 caveat on configured versus achieved FPGA clock. This project-defined paired method/nearest-rank statistic is not claimed to be an external published benchmark standard.

**Power/energy characterization remains deferred until explicit user direction.**
