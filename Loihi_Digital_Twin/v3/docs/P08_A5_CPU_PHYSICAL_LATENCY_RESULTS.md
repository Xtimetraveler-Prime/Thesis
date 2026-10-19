# P08-A5 — Verified-host CPU reference and KV260 A53/FPGA service comparison

**Status (recorded after user's 2026-10-18 local results):** CPU measurement and two-endpoint report **USER-ATTESTED PASS**; frozen original physical P07 neural oracle and physical/CPU dataset-source binding **reported PASS**. **REVIEWED AS LATENCY-ONLY P08-A ACCEPTANCE CANDIDATE; NOT FINAL USER ACCEPTANCE, NOT A PR MERGE.**

This document preserves the user's reported terminal output of the *actual* 1,024-image CPU benchmark, the revalidated original six-session KV260 evidence, and the offline-generated Markdown closeout. The original untracked binary and JSON files have not been uploaded for independent byte-level inspection here. Hashes below are copied from the user's local `sha256sum` results; **do not represent independently recomputed hashes by the assistant**. All numeric data below come from the user's posted report, **not fabricated optimized CPU/PL benchmark numbers**.

## 1. Frozen evidence, sample and source integrity

- Canonical first **1,024 distinct MNIST TRAIN-derived held-out validation** images in original accepted source order. **1,023 ordinary images** comprise all statistics here. Image **1023** triggers the physically selected **26 × 42** full state trace and is **excluded from ordinary-image distributions**. No official independent TEST rerun.
- Original frozen 784→32→10 compact network, 42 compartments, 25 external input event ticks plus one final drain, P03 exact signed24/LIF/64-bit accumulator semantics, original pixel encoder and 10-class spike-count readout.
- Accepted routed FPGA XSA SHA256: `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`. A2.1 firmware ELF SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`. A2.2 firmware ELF SHA256 `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361`. Original training checkpoint SHA256 `0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`, pinned effective integer weights SHA256 `1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`. Original P07 official TEST 9,456/10,000 (94.56%) was accepted in P07, **not measured by P08**.
- Frozen stage (user's original physical source): `/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z`.
- CPU host-run evidence: `/home/dna/Thesis_Evidence/p08_a5_cpu_ref_20261019T023137Z.json`; **SHA256 `790072259dab211b57bf40f60bba2b7cb293d7a544ab3aae2660fc8d8c63127d`**.
- Independently regenerated three-pair physical latency aggregate: `/home/dna/Thesis_Evidence/p08_a5_physical_revalidation_20261019T023728Z.json`; **SHA256 `afd4e91f0106266179072c7242d7e361c033d9d78720d79a3a807e3ed400bf7b`**.
- Generated closeout review report: `/home/dna/Thesis_Evidence/p08_a5_closeout_20261019T023733Z.md`; **SHA256 `17e88feb9330ffca5ecbbfb8735bc08b7fe68f76e74392c0c5c4a538e40233b1`**.
- Original CPU benchmark sourced its accepted real **Pair 3 A2.1** journal and full trace from `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_1_20261019T012641Z`.
- The source-bound closeout generated `P08_A5_CPU_AND_PHYSICAL_SAME_TRAIN_STAGE_SHA256_PASS=1`. Its original train-stage descriptor/pixels/manifest checksums match the physical triple-pair evidence and the CPU replay source. The full original P07 1,024-frame physical replay oracle and selected 26×42 trace were run before accepting any CPU timing.

### Original terminal pass markers (verbatim, as reported)

```text
P08_A5_CPU_SOURCE_PHYSICAL_P07_1024_PACKED_ORACLE_PASS=1
P08_A5_CPU_PRELOADED_1024_PHYSICAL_SPIKES_EXACT=1
P08_A5_CPU_FULL_1024_PHYSICAL_SPIKES_EXACT=1
P08_A5_CPU_TWO_ENDPOINT_THREE_REPEAT_BENCHMARK_PASS=1
P08_A5_CPU_VS_FPGA_CLAIM=SCOPES_NOT_IDENTICAL
P08_A5_FPGA_PL_ONLY_SECONDS=NOT_MEASURED
P08_A5_POWER=DEFERRED
P08_A5_OFFICIAL_TEST=SEALED
P08_A3_2_3_DISTINCT_PHYSICAL_SESSIONS=6
P08_A3_2_3_SAME_ORIGINAL_TRAIN_FIRST1024_PASS=1
P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1
P08_A3_2_3_ORDINARY_PAIR_MEDIAN_DELTAS_MS=0.016840,0.025400,0.029710
P08_A3_2_3_RESULT_SCOPE=DESCRIPTIVE_REPEATED_PILOT
P08_A5_CPU_AND_PHYSICAL_SAME_TRAIN_STAGE_SHA256_PASS=1
P08_A5_TWO_CPU_ENDPOINTS_SEPARATE=1
P08_A5_FINAL_REPORT_CANDIDATE_BUILT=1
P08_A5_FPGA_SPEEDUP=NOT_CLAIMED_NON_EQUIVALENT_ENDPOINTS
P08_A5_FINAL_USER_ACCEPTANCE=PENDING
P08_A4_POWER=DEFERRED
```

**Separate original scalar CPU benchmark terminal summaries** (not the same statistic as the per-run medians below): `P08_A5_CPU_PRELOADED_MEDIAN_MS=25.552718` and `P08_A5_CPU_FULL_MEDIAN_MS=30.200338`. These come from aggregating the **per-image median across three CPU passes, then taking the median across images**. That quantile operation need not equal the median of the three individual-run medians. Do **not** treat the two presentations as contradictory or silently substitute one for the other.

## 2. Ordinary-image 1,023-frame per-run latency distributions

All values **milliseconds**, unless marked µs. The CPU host CPU benchmark was three sequential passes in **one process**, rather than three independent CPU reboots. The FPGA A2.1/A2.2 experiment comprises **three separately executed cold-boot paired runs** (six hardware sessions).

| Metric | CPU preloaded packed scalar, ms | CPU raw 784B→class scalar, ms | KV260 A53+PL A2.1 full service, ms | KV260 A53+PL A2.2 detailed full service, ms |
|---|---:|---:|---:|---:|
| Run 1 median | 25.6147 | 30.3930 | 35.7023 | 35.7234 |
| Run 2 median | 25.6001 | 30.3147 | 35.6946 | 35.7163 |
| Run 3 median | 25.5735 | 30.2579 | 35.6696 | 35.7220 |
| Run 1 p95 (nearest rank) | 38.2640 | 43.1727 | 41.9667 | 41.9800 |
| Run 2 p95 (nearest rank) | 38.1781 | 43.1790 | 41.9578 | 41.9317 |
| Run 3 p95 (nearest rank) | 38.2943 | 43.1702 | 41.9104 | 41.9816 |
| Run 1 sample SD | 6.9749 | 7.0062 | 3.3939 | 3.3937 |
| Run 2 sample SD | 6.9527 | 6.9845 | 3.3940 | 3.3940 |
| Run 3 sample SD | 6.9652 | 6.9991 | 3.3932 | 3.3937 |

**The CPU's reported median is lower than the FPGA-backed full A53 service median, but the CPU raw-image p95 (~43.17 ms) exceeds the A53 service p95 (~41.9–42.0 ms).** This is a descriptive crossing of distributions under **non-equivalent endpoints** on different hardware and different clock environments. It is **not evidence of a bare FPGA neural-engine slowdown or speedup**. CPU preloaded excludes event encoding; CPU full includes the encoder but no physical DDR writes/AXI/MMIO/PL polling or A53 result commit, and does not match every physical-service boundary. The A53 service measurement includes FPGA dispatch and software control; neither A53 service median is pure PL arithmetic.

**CPU benchmark terminal aggregate-of-per-image-medians:** preloaded **25.552718 ms**, raw-image full **30.200338 ms**. These are alternative, clearly specified cross-run estimators, not fourth physical repeats.

## 3. Repeated physical instrumentation perturbation and uncertainty

Original first1,024 validation imaging is frozen and test-independent. In ordinary 1,023 frames per physical pair:

| Pair / order | A2.1 ms median | A2.2 ms median | Paired A2.2−A2.1 median (µs) |
|---|---:|---:|---:|
| 1 / A2.1→A2.2 | 35.7023 | 35.7234 | +16.840 |
| 2 / A2.2→A2.1 | 35.6946 | 35.7163 | +25.400 |
| 3 / A2.1→A2.2 | 35.6696 | 35.7220 | +29.710 |

- Mean **23.984 µs** across three pair-level frame-paired medians; sample SD **6.551 µs**. These have only **n=3 independent physical pairs**, not n=3,069 independent sample identities.
- Fixed-image A2.2−A2.1 three-repeat spread: median range **24.730 µs**, p95 range **73.541 µs**. Repeating the same image does not create new independent image identities.
- Additional A2.2 measurement instrumentation is associated with **small positive descriptive frame-service differences** across three AB/BA/AB sessions, about **0.067% of ~35.7 ms**. The difference is *not* calibrated timer cost; separate board runs can drift by run order, thermal state or other effects.
- Median CPU full software path ~30.2–30.4 ms with per-run SD ~7 ms; physical A53 service ~35.7 ms with per-run SD ~3.39 ms. Different distributions and source measurement boundaries mean no scope-matched CPU/FPGA speedup can be computed reliably.
- No statistical inferential CI is claimed for three physical session pairs; no finite n=3 experiment can isolate all run-order and hardware state effects. The project preserves raw per-image arrays and CPU timing ns in the corresponding original untracked JSONs.

## 4. Host CPU implementation and measurement conditions

- Actual user-reported CPU: **Intel Core i5-4590S @ 3.00GHz**, **x86_64**, **4 logical CPUs**, measured process affinity **[0, 1, 2, 3]**; Linux frequency scaling governor **`schedutil`**; sampled cpu0 scaling frequency **3,515,959 kHz** (a single reported value, **not** fixed or calibrated CPU frequency).
- **CPython 3.12.3**, built with **GCC 13.3.0**; one interpreter thread for neural inference, pure Python scalar arithmetic/iteration, **not** optimized native C, GPU, JIT, vectorized NumPy/Torch execution. Python interpreter startup, checkpoint load/model decode, canonical TRAIN IDX read, benchmark report JSON writing and physical oracle validation are excluded from per-image timed regions.
- Host timer `time.perf_counter_ns()`; that is a host wall-clock monotonic interval, not A53 `CNTVCT_EL0` and **not PL neural cycles**. Host CPU governor and CPU operating frequency were observed when possible, **not** pinned, thermal state not held constant. Three sequential CPU repeats in one process cannot be described as independent cold-boot CPU trials.
- A53 `CNTFRQ_EL0` for the first two original physical pairs was firmware-reported **99,999,001 Hz**. It is not an external PL clock measurement. PL raw dispatch cycles remain raw; **no independently verified achieved PL frequency** and no reliable pure-PL seconds or FPGA-only speedup follow from this experiment.
- Physical power and energy **DEFERRED BY USER; NOT MEASURED**. No energy-per-inference, measured Loihi chip power, performance/watt or efficiency gain claim. Original 94.56% official MNIST TEST result belongs to P07 only.

## 5. Acceptance boundary and recommended decision

The originally prescribed [P08-A1 contract](P08_A1_MEASUREMENT_CONTRACT.md) §§6–7 required **two explicitly named CPU baselines**, comparable original checkpoint/input/26-step semantics, true KV260 timing not simulator estimates, original packed-neural parity, reproducible methods and uncertainty, and an explicit decision about deferred power. All **latency-only technical deliverables** are met at the **user-reported measurement/host-gate level**: six real physical sessions, original independent neural parity, image and per-tick timing/CRC, host CPU dual-endpoint benchmark with source parity and frozen stage, paired uncertainty descriptors, strong endpoint caveats, an original-user SHA-256 chain and a reproducible draft comparison.

**Recommended: prepare P08-A for explicit user acceptance under the agreed LATENCY-ONLY scope.** Do not automatically merge: `P08_A5_FINAL_USER_ACCEPTANCE=PENDING`, and the conversation has not supplied an explicit command to approve PR merge. A5's corrected full native regression pytest final summary (post the two earlier assertion fixes) was not pasted; actual host CPU benchmark/oracle and report gates have passed. Before final merge, request or run a concise user-native final selected regression gate and `git status --short`. Keep P08-A4 deferred for any future separate user-approved power study, not misreported as a measured deliverable.

**Thesis-safe conclusion:** “The frozen 784→32→10 Loihi-inspired packed-integer SNN was executed with exact P07 neural parity on the KV260, providing a reproducible ~35.7 ms FPGA-backed full A53 image-service latency baseline on held-out TRAIN-derived validation images; an independent scalar CPython reference on an Intel i5-4590S measured ~25.6 ms preloaded computation and ~30.3 ms input-to-class service under different boundaries. Detailed per-timestep A53 instrumentation was associated with a small +16.8 to +29.7 µs paired median full-service difference over three separately booted pairs. No pure FPGA acceleration factor, PL-only inference latency or power/energy improvement is claimed.” This summary is descriptive and conditional on the user's preserved raw evidence.

Sources: [Original measurement contract](P08_A1_MEASUREMENT_CONTRACT.md), [P08-A3 six-session numerical measurements](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md), [A5 host benchmark protocol](P08_A5_CPU_REFERENCE_PROTOCOL.md), [P08-A5 closeout gates](P08_A5_REMAINING_CLOSEOUT_GATES.md).
