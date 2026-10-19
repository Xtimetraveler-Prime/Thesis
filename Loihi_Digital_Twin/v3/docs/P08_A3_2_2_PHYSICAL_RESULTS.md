# P08-A3.2.2 — First paired 1,024-image physical latency measurements

**User-attested on 2026-10-18 (local project log; path timestamp 20261019T00Z):**
**ACCEPTED FIRST PHYSICAL PAIR**: each original TRAIN-derived first1024 session independently passed its P07 packed-neural replay oracle, selected full 26×42 trace and strict sidecar timing/CRC integrity. **Only one physical run per firmware.** This is **not** a replicated statistical baseline or a calibrated isolated-PL computation benchmark.

## Experimental identity and scope

- Hardware: KV260 with frozen P03.2c routed XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`, frozen model/FPGA architecture and unchanged P07 original packed oracle.
- Firmware A2.1 image-only timing: pinned ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`.
- Firmware A2.2 image + per-timestep timing: pinned ELF SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`.
- Dataset: **1,024 distinct canonical held-out MNIST TRAIN-derived validation** images, same original order in both runs. The designated frame **1023** produces the selected full 26×42 neural-state trace. The summary below covers **1,023 ordinary frames**, excluding selected frame 1023; the trace frame's actual latency is not supplied in the user-posted excerpt.
- Stage directory posted during preflight: `/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z`.
- First A2.1 physical output directory posted before execution: `/home/dna/Thesis_Evidence/p08_a3_2_A2_1_1024_20261019T003224Z`.
- First A2.2 physical output directory posted before execution: `/home/dna/Thesis_Evidence/p08_a3_2_A2_2_1024_20261019T003249Z`.
- These paths were provided **before** execution. The user subsequently reported both physical tests and successful paired report creation; exact `paired_report.json` output location has not yet been shared, so do **not** invent it. Retain original untracked evidence read-only and independently check their `physical_output_sha256.txt` before further runs.
- **A53 clock:** both separate runs reported `CNTFRQ_EL0 = 99,999,001 Hz` (self-reported, same frequency on each).
- **Scope:** `after_commit - service_start` ARM timing over full **instrumented** frame service, **not** isolated FPGA neuron compute cycles; PL counters remain a separate clock domain. No power or energy readings. P07 official TEST not rerun.

## 1,023 ordinary-frame physical distributions (exact user-reported output)

All values below are **milliseconds**. The p95 is nearest-rank per existing A3.2.1 implementation. The paired delta is *frame-index-matched*, not the difference of separately calculated p95s or medians.

| Metric | A2.1 service | A2.2 service | Paired delta A2.2 - A2.1 |
|---|---:|---:|---:|
| Median | **35.7023** | **35.7234** | **+0.0168** |
| P95 (nearest rank) | 41.9667 | 41.9800 | +0.0744 |
| Minimum | 27.8371 | 27.8020 | −0.0435 |
| Maximum | 48.8564 | 48.8689 | +0.0822 |
| Sample standard deviation | 3.3939 | 3.3937 | 0.0240 |

- **Paired median increase:** 0.0168 ms = **16.8 µs**, about **0.047%** of the A2.1 median of 35.7023 ms (descriptive comparison of reported medians; not a statistical confidence bound or exactly attributable timer-instruction overhead).
- **Paired p95 increase:** 0.0744 ms = **74.4 µs**, versus 16.8 µs median. Some individual matched images were **faster** under A2.2, with minimum delta −43.5 µs. Thus the effect is not strictly positive on every image.
- **Across-image variability** in absolute service latency (both ≈3.394 ms standard deviation) is far larger than the **spread of matched deltas** (0.0240 ms). This underscores the value of paired same-frame analysis, but a single separately rebooted A2.1 run and A2.2 run cannot distinguish profiler overhead from time drift, DVFS state, thermal/load/order effects and other run-to-run variation.
- `Neural verification = PASS`, `Timing integrity = PASS_SINGLE_PAIR` are verbatim from the user's summary. The exact underlying selected full-trace and per-image source hashes are in the unuploaded physical output directories / JSON; they have **not** been re-inspected by ChatGPT.
- The ordinary 1,023-image statistics **exclude trace index 1023**; no conclusions about additional trace costs can be drawn from them.

## Interpretation and next gate

This paired experiment demonstrates source-matched, numerically correct execution and timing collection for both accepted A53 firmware builds on the full first1,024 TRAIN-derived validation dataset. A2.2 adds a small **observed** paired full-service difference on this first sample. The number **16.8 µs is NOT a calibrated cost of seven timer instructions**. The device, firmware and measurement procedures should remain frozen during repeatability work. No pure PL computation time is reported because no independently established FPGA dispatch clock is supplied.

**P08-A3.2.3 follow-up:** two more separate A2.1/A2.2 pairs (for **three sessions per firmware total**), each firmware session after a dedicated bare-metal JTAG-only reboot; preserve the first pair and original stage, use a **new evidence directory per hardware session**; alternate second pair order A2.2 → A2.1, third pair A2.1 → A2.2 to explore order drift while keeping one identified original dataset. Each trial must pass original P07 packed numerical verification and CRC/tick checks *before* comparing/reporting latency. Aggregate **three paired medians** as repeated-run descriptors, report per-frame cross-run spread without treating 3 × 1,023 samples as independent frames, and preserve distinct stage/clock/trace semantics.

Detailed methods: [Paired 1024 protocol](P08_A3_2_PAIRED_LATENCY_PROTOCOL.md), [A3.2.2 physical-capture safety](P08_A3_2_2_PHYSICAL_CAPTURE_PROTOCOL.md), [A3.1 feasibility pilot](P08_A3_1_PHYSICAL_LATENCY_RESULTS.md).

**Claim boundary:** Physical pair accepted based on the user's terminal/report output. Repeated-run uncertainty and profiler-only overhead not yet accepted. Power and energy characterization remains deferred.
