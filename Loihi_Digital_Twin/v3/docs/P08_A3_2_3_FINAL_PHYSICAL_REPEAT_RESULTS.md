# P08-A3.2.3 — Final user-attested six-session physical latency study

**Recorded:** 2026-10-18 America/Denver (evidence filenames are UTC dated 2026-10-19).  
**Status:** **P08-A3.2.3 THREE-PAIR PHYSICAL LATENCY CHARACTERIZATION ACCEPTED AT THE USER-ATTESTED / DESCRIPTIVE-REPORT LEVEL.** The user ran six separately controlled KV260 physical A53 sessions (three of each pinned firmware, on the same 1,024 TRAIN-derived held-out validation images) and posted results from the three-pair reporting workflow. The terminal PASS markers of the final aggregate and original raw files were *not* uploaded here, so this document does not assert independent third-party raw-binary verification.  
**Whole P08-A milestone:** **NOT CLOSED** until P08-A5 CPU/software endpoint and final acceptance report; P08-A4 power/energy remains expressly **DEFERRED**.

## 1. Frozen hardware, sample population and counters

- Accepted original P07 test fidelity remains frozen and is **not** rerun in P08: 9,456/10,000 = 94.56% official TEST accuracy, previously 10,000/10,000 independently exact physical P07 oracle comparisons. All new P08 images are **TRAIN-derived validation**.
- Exact same first 1,024 distinct validation images, original order, 25 input ticks + 1 drain tick. Full selected 26×42 neural trace is frame 1023. The latency distributions below use **only the 1,023 ordinary frames** to avoid comparing different trace-readback scopes. Three repeated sessions of the same sample IDs are not three new independent validation populations.
- KV260 routed P03.2c XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`; original master DDR SHA256 `9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955`. The physical PL design, original P07 source/oracle and checkpoints remain unchanged.
- A2.1 image-level timing ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`. A2.2 detailed per-tick timing ELF SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`.
- A53 `CNTVCT_EL0` interval converted using the **corresponding actual run's CNTFRQ_EL0**, with **99,999,001 Hz** reported for both variants in first two pairs. Pair 3 counter values were not included in the last user excerpt; the accepted pair verifier required valid run-specific clocks. **Arm CNTFRQ is firmware-reported and is not an external calibrated timer-frequency measurement.**
- Raw FPGA PL dispatch cycles remain **distinct hardware clock domain** with no independently verified achieved PL clock frequency. No pure neuron-engine latency in seconds and no energy/power measurement is implied.
- Original stage directory: `/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z`.
- Pair 1 source paired JSON: `/home/dna/Thesis_Evidence/p08_a3_2_pair_20261019T004713Z.json`.
- Pair 2 source paired JSON: `/home/dna/Thesis_Evidence/p08_a3_2_pair2_report_20261019T011632Z.json`.
- Pair 3 source paired JSON: `/home/dna/Thesis_Evidence/p08_a3_2_pair3_report_20261019T013553Z.json`. Pair 3 individual physical evidence: A2.1 `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_1_20261019T012641Z`; A2.2 `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_2_20261019T013054Z`. The user posted `P08_A3_2_1024_BOTH_ORACLES_EXACT=1` and `P08_A3_2_1024_PAIRED_LATENCY_SINGLE_PAIR_PASS=1` for Pair 3. Physical folders for Pair 1 and Pair 2 are partially recorded in the [first-pair](P08_A3_2_2_PHYSICAL_RESULTS.md) and [second-pair](P08_A3_2_3_PAIR2_RESULTS.md) reports.
- **Final aggregate report filename and aggregate terminal PASS markers were not supplied** in the final message. The user did supply the completed summary fields returned by the designed three-pair JSON report builder. Preserve the exact local report and its SHA256; before a final publication/merge, independently verify the stored aggregate manifest and source files.

## 2. Exact user-reported paired A53 service results

All values below are from the user-provided final `P08-A3.2.3 FINAL PHYSICAL LATENCY RESULTS` display. Separate A2.1 and A2.2 medians are ordinary-frame **full A53 service** latencies, not the time spent solely in the FPGA logic. Per-pair delta is the **median of 1,023 same-image A2.2-minus-A2.1 differences**, *not* the difference of the two separately reported medians.

| Physical pair | Run order | A2.1 median (ms) | A2.2 median (ms) | Median matched-frame A2.2 − A2.1 (µs) |
| ---: | --- | ---: | ---: | ---: |
| 1 | A2.1 → A2.2 | 35.7023 | 35.7234 | **+16.840** |
| 2 | A2.2 → A2.1 | 35.6946 | 35.7163 | **+25.400** |
| 3 | A2.1 → A2.2 | 35.6696 | 35.7220 | **+29.710** |

**Distribution of the three individual physical pair-median differences (sample size = three paired sessions, not 3,069 independent images):**

| Summary across three paired medians | Value |
| --- | ---: |
| Mean of paired medians | **+23.984 µs** |
| Median of paired medians | **+25.400 µs** |
| Minimum | +16.840 µs |
| Maximum | +29.710 µs |
| Between-pair sample standard deviation | **6.551 µs** |

**Within each fixed ordinary image ID, using its three physical paired differences:**

| Measure of the max-minus-min paired difference across 3 repeats | Value |
| --- | ---: |
| Median of the 1,023 image-specific ranges | **24.730 µs** |
| P95 nearest-rank of those ranges | **73.541 µs** |

This within-image range describes how much the **A2.2 − A2.1 difference** varies across repeated physical pairs for that same image ID. It is not a per-image latency itself, nor a confidence interval. The per-pair service medians themselves vary by roughly 0.033 ms for A2.1 and 0.007 ms for A2.2 across the three posted summaries; avoid interpreting this as calibrated uncertainty without controlling run order, state and sources.

## 3. What this demonstrates

1. **Real physical feasibility and numerical correctness:** All six separately operated A53/FPGA sessions used original first1024 TRAIN-validation stages, preserved the P07 neural outputs against the immutable packed-integer oracle and passed the image/tick timing-integrity gates according to the independent paired reports. The selected full trace is verified in those original oracles. This establishes physical *fidelity* of the instrumented execution to the accepted neural semantics; it does **not** measure energy.
2. **Representative end-to-end-on-board A53 service baseline:** Both firmware versions have ordinary-frame median latency around **35.7 ms** in all three separate sessions. The scope includes per-image preparation, encoder, event bank/AXI/MMIO, PL dispatch+poll, trace readback, routing, barriers and successful result writing as defined in [timing contract](P08_A1_MEASUREMENT_CONTRACT.md). This is a measured **hardware-accelerated system service** endpoint, *not* core-only FPGA execution, host JTAG elapsed time or guaranteed deployment system throughput.
3. **A2.2 detailed timing has a modest observed net service difference:** All three paired median deltas are positive under AB/BA/AB (16.840, 25.400, 29.710 µs). Their mean **23.984 µs** corresponds descriptively to about **0.067%** of 35.7 ms; this ratio should be stated as an observed approximate *difference*, **not** isolated timer-instruction overhead. Individual matched frames can have negative deltas as shown in the first two paired reports.
4. **Repeatability is finite and important:** Between-pair median delta SD **6.551 µs** for only three pair-level replicates; within-image difference ranges median **24.730 µs**, p95 **73.541 µs**. The spread within a particular image across repeat pairs can be comparable to or exceed the typical positive median difference. AB/BA/AB tests one reversed order but is only *partially counterbalanced*, and cannot identify or remove thermal, scheduling, timer-register calibration, run-order or clock variations.
5. **No established PL-only speedup, CPU speedup, real throughput or energy:** No CPU software baseline was collected within this result, no matched CPU numerical endpoint comparison is published, no independently measured PL clock-to-seconds conversion is recorded, and the user deferred physical rail/system power/energy. Do not derive claims by summing per-stage medians, treating repeated frames as independent labels or equating `CNTFRQ_EL0` with the PL clock.
6. **Earlier exploratory bottlenecks:** The separate 16-frame pilot's A2.2 per-tick medians had event encode **499.955 µs** and bank append **312.458 µs** versus dispatch MMIO+wait **70.011 µs**. These are individually observed software-inclusive spans and a plausible next optimization target; they are **not** directly recomputed from the newly posted final three-pair excerpt. Separate 1,023-frame A2.2 per-stage distributions exist in each paired JSON and can be read before making any population-wide bottleneck claim.

## 4. Milestone closure assessment

Per the original [P08-A1 measurement contract, §§6–7](P08_A1_MEASUREMENT_CONTRACT.md):

- **P08-A1 and P08-A2:** measurement design and separately SHA-pinned experimental A53 sidecar firmware **complete** under the approved latency-first scope.
- **P08-A3 latency side:** physical pilot, dual 1,024-image numerical/sidecar independent verification and three separately cold-booted physical pairs **complete at the user-attested descriptive evidence level**. Confirm the final aggregate report gate / source hashes on host before marking **fully file-sealed**; explicit per-image raw/trace-stage acceptance and repeatability are available on user's machine.
- **P08-A3 PL timing requirement:** PL cycles were recorded but **physical PL-clock frequency calibration remains unspecified**, so absolute PL dispatch time in seconds is *not* yet supported. If the intended deliverable demands PL-time-in-seconds, obtain a clock-source/route-validated achieved PL frequency or qualify the result as raw cycles only.
- **P08-A4 power/energy:** **DEFERRED BY USER; not a blocker** for a scoped latency-only Track A study and not measured.
- **P08-A5 CPU comparator and final statistical/acceptance report:** **NOT DONE**. Requires at least two explicit CPU software endpoints (preloaded integer/packed compute loop and full image-to-class with encoder/result handling), source-identical checkpoint/raw pixels/26 ticks, documented CPU model/ISA/core count, timer/toolchain/governor/thread configuration, output parity checks and scope-matched FPGA-side endpoint discussion. Track and explain run-level uncertainty, distinct A53/PL/host clocks, selected trace frame, dataset throughput optional. Publish a final report with limitations and explicit user acceptance.

**Decision: accept/close A3.2.3 as a user-attested repeated physical latency result, but DO NOT close all P08-A or merge its feature branch yet without either completing P08-A5 or an explicit user-authorized re-scope of the original completion criteria.** No further 1,024-image FPGA run is currently required simply to satisfy the *already completed* repeated physical-latency experiment. The next work should be CPU matching and final reporting, not another destructive JTAG cycle.

## 5. Preservation and independent file-level sealing

The following CLI already exists and is OFFLINE ONLY. On the user's PC, preserve original raw files and rerun the exact three-report aggregator to establish its explicit success gate and checksum of its unique, new report:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source ~/Git/Thesis/.venv-p08/bin/activate
export P08_A3_2_PAIR1_REPORT=/home/dna/Thesis_Evidence/p08_a3_2_pair_20261019T004713Z.json
export P08_A3_2_PAIR2_REPORT=/home/dna/Thesis_Evidence/p08_a3_2_pair2_report_20261019T011632Z.json
export P08_A3_2_PAIR3_REPORT=/home/dna/Thesis_Evidence/p08_a3_2_pair3_report_20261019T013553Z.json
# Identify your EXISTING repeat report from your files (do not overwrite it):
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f -name 'p08_a3_2_three_pair_summary_*.json' -print
# Only when desired, choose a DIFFERENT, new path for re-validation:
P08_A3_2_REVALIDATED_REPORT="$HOME/Thesis_Evidence/p08_a3_2_three_pair_seal_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p08_a3_2_repeat_check.py \
  --pair-reports "$P08_A3_2_PAIR1_REPORT" "$P08_A3_2_PAIR2_REPORT" "$P08_A3_2_PAIR3_REPORT" \
  --report "$P08_A3_2_REVALIDATED_REPORT"
sha256sum "$P08_A3_2_REVALIDATED_REPORT"
```

Expected completion markers:
```text
P08_A3_2_3_DISTINCT_PHYSICAL_SESSIONS=6
P08_A3_2_3_SAME_ORIGINAL_TRAIN_FIRST1024_PASS=1
P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1
P08_A3_2_3_RESULT_SCOPE=DESCRIPTIVE_REPEATED_PILOT
P08_A3_2_3_POWER=DEFERRED
```

These are **not** included verbatim in the user's final message, so they must not be claimed as observed. The source JSONs' recorded SHA256s and selected full traces remain untracked files on the user's PC. Do not overwrite or delete them; archive if moving off temporary storage.

See [Pair 1 physical readings](P08_A3_2_2_PHYSICAL_RESULTS.md), [Pair 2 physical readings](P08_A3_2_3_PAIR2_RESULTS.md) and [A3.2.3 reproducibility protocol](P08_A3_2_3_REPEATED_LATENCY_PROTOCOL.md).
