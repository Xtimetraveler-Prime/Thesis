# P08-A — Compact KV260 latency-only Track A final acceptance candidate

**Review state:** **READY FOR EXPLICIT USER SIGNOFF (NOT YET ACCEPTED OR MERGED)**, recorded after the user's local 2026-10-18 physical and CPU benchmark reports. No physical re-execution, firmware rebuild, or official MNIST TEST rerun is necessary for the already completed latency-only scope. The PR remains **DRAFT** until the user explicitly approves closure/merge.

## 1. Original contract and agreed scope

This acceptance refers to [P08-A1 Measurement Contract](P08_A1_MEASUREMENT_CONTRACT.md) §§6–7, *under the user-approved latency-first scope*:

- **Power/energy P08-A4:** **DEFERRED BY USER; NEVER MEASURED.** Must not silently label this gate PASS or infer Loihi comparative energy/power.
- **Neuron/model/accuracy:** previously accepted P07 frozen checkpoint/packed-integer semantics and official TEST accuracy (94.56%) remain immutable. This study used only 1,024 distinct canonical TRAIN-derived held-out validation images, no official independent TEST rerun.
- **Inference scope:** **25 input ticks + 1 final drain**, original 784→32→10 topology with **42 compartments**, packed P03 design, selected frame 1023 26×42 physical trace.
- **Clock/speedup:** A53 full-image service intervals are instrumented physical values. PL dispatch cycles are an independent uncalibrated clock domain; no isolated pure-PL compute seconds, CPU-to-bare-FPGA acceleration ratio, production throughput or energy/efficiency claim is supported.
- **CPU comparator:** the original implementation is a **single-threaded pure-Python scalar packed-integer reference** on a user-reported Intel i5-4590S. It is a valid correctness and explicit software latency reference, **not** an optimized native CPU speed limit. Host CPU full raw-image-to-class and PS/PL physical full A53 service are not exactly equivalent endpoints.

## 2. Milestone acceptance matrix

| Stage | Deliverable and best available evidence | Gate state |
|---|---|---|
| **A1** | Frozen P07 model/DDR/XSA/latency measure contracts, reproducibility and explicit latency-only scope | **COMPLETE / REFERENCE DOCUMENTED** |
| **A2.1** | Original pinned SHA `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0` per-image A53 timing ELF + 1,024-image real physical capture | **USER-ATTESTED PASS** |
| **A2.2** | Original pinned SHA `87cf5fc4fe37d9d053a3c365db8ae9fdc7e782857612f273835cf5e611aba361` per-tick timing ELF, verified on KV260 with original P07 26×42 trace | **USER-ATTESTED PASS** |
| **A3.1** | First 16 TRAIN-validation physical pilot, original packed oracle + full-trace parity, median **35.4432 ms** A53 service | **USER-ATTESTED PASS** |
| **A3.2** | **Six physical sessions / three paired original first1024 TRAIN validation runs**, original P07 full 26×10 spikes and selected full trace parity, CRC/timestamp integrity, unique raw evidence, three-pair stage-SHA aggregation | **USER-ATTESTED PASS** |
| **A4** | Direct physical power/energy measurement | **DEFERRED BY USER, NOT A LATENCY-ONLY BLOCKER** |
| **A5 reference computation** | Original 26-tick packed Python CPU, preloaded and raw784 image-to-class endpoints, all1024 physical P07 journal output-spike parity + original independent packed oracle | **USER-ATTESTED PASS** |
| **A5 timing and reporting** | 3 sequential CPU host passes per endpoint, CPU model/Python/timer/governor, 3-pair physical uncertainty, p95/SD, source hashes and generated draft | **USER-ATTESTED PASS** |
| **A5 corrected native pytest suite** | Two initial assertion failures corrected on branch; no final post-correction pytest output pasted | **NOT INDEPENDENTLY CONFIRMED — RECOMMEND FINAL NATIVE RUN** |
| **Final user decision** | Explicit latency-only acceptance / PR #45 merge authorization | **PENDING — DO NOT MERGE** |

**Interpretation:** All *measured latency-only technical evidence deliverables* are satisfied at the level of user-posted terminal PASS markers and immutable file SHA attestations. Missing external calibration/energy/optimized CPU comparison are stated **limitations or deferred scope**, not quietly invented successes. Final acceptance remains subject to user review and any desired regression confirmation.

## 3. Exact summary of observed performance

**A53-controlled KV260 FPGA-backed ordinary full image service (not bare PL compute):**

| KV260 physical paired session | A2.1 ms median | A2.2 ms median | Same-image A2.2−A2.1 median µs |
|---|---:|---:|---:|
| 1, A2.1→A2.2 | 35.7023 | 35.7234 | **16.840** |
| 2, A2.2→A2.1 | 35.6946 | 35.7163 | **25.400** |
| 3, A2.1→A2.2 | 35.6696 | 35.7220 | **29.710** |

Mean pair-median difference **23.984 µs**, between-pair sample SD **6.551 µs**; within-image three-repeat delta range median **24.730 µs**, p95 **73.541 µs**. These are **n=3 physical run pairs**, not n=3,069 independent validation examples.

**Host CPU dual software endpoints, same 1023 ordinary images, 3 repeated passes in one CPU process (ms):**

| Endpoint | CPU run 1 median | Run 2 | Run 3 |
|---|---:|---:|---:|
| Preloaded packed integer 26 ticks | 25.6147 | 25.6001 | 25.5735 |
| Raw784 pixel encoder + packed 26 ticks to class | 30.3930 | 30.3147 | 30.2579 |

Host CLI median of **per-image** median over the 3 sequential repeats: **25.552718 ms** preloaded, **30.200338 ms** full image to class. That estimator need not equal the median of each run's medians. CPU full-image p95 ≈43.17 ms versus A53+PL full-service p95 ≈41.9–42.0 ms, but the CPU has lower medians; both statements are purely descriptive under different endpoints. Do not infer bare FPGA superiority/inferiority or an isolated timer overhead number.

## 4. Reproducible immutability and hashes

Original user-local sealed sources:

```text
CPU 1024 dual-endpoint report:
  /home/dna/Thesis_Evidence/p08_a5_cpu_ref_20261019T023137Z.json
  SHA256 790072259dab211b57bf40f60bba2b7cb293d7a544ab3aae2660fc8d8c63127d

3-pair original physical source revalidation:
  /home/dna/Thesis_Evidence/p08_a5_physical_revalidation_20261019T023728Z.json
  SHA256 afd4e91f0106266179072c7242d7e361c033d9d78720d79a3a807e3ed400bf7b

Generated full A5 CPU/FPGA Markdown review report:
  /home/dna/Thesis_Evidence/p08_a5_closeout_20261019T023733Z.md
  SHA256 17e88feb9330ffca5ecbbfb8735bc08b7fe68f76e74392c0c5c4a538e40233b1
```

- Successful terminal original numerical oracle `P08_A5_CPU_SOURCE_PHYSICAL_P07_1024_PACKED_ORACLE_PASS=1`; both CPU endpoint 1024 physical 26×10 spike parity `=1); explicit `P08_A5_CPU_TWO_ENDPOINT_THREE_REPEAT_BENCHMARK_PASS=1`.
- Original 3-pair revalidation: `P08_A3_2_3_DISTINCT_PHYSICAL_SESSIONS=6`, `P08_A3_2_3_SAME_ORIGINAL_TRAIN_FIRST1024_PASS=1`, `P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1`.
- Final report generator: `P08_A5_CPU_AND_PHYSICAL_SAME_TRAIN_STAGE_SHA256_PASS=1`, `P08_A5_TWO_CPU_ENDPOINTS_SEPARATE=1`, `P08_A5_FINAL_REPORT_CANDIDATE_BUILT=1`, `P08_A5_FINAL_USER_ACCEPTANCE=PENDING`.
- Files remain on user's PC, not uploaded; only displayed paths and hashes were available to this assistant. Archiving should keep original bytes and `physical_output_sha256.txt` checks readable outside git. **Do not commit tracked copies of sensitive/large raw evidence or silently rewrite physical result JSON.**

## 5. Final transition / merge stop gate

**Prepared but not authorized:**

1. User checks [A5 final measured report](P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md), [final A3 physical results](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md), and original [P08-A1 scope contract](P08_A1_MEASUREMENT_CONTRACT.md).
2. User optionally confirms the corrected selected A5 native tests and clean working tree, using the commands below; verify any unexpected failures before closing.
3. User **explicitly** states that they accept **P08-A under the latency-only scope with P08-A4 power/energy deferred and with no PL-only speedup claim** and authorizes **merging draft PR #45 to main**. Until that instruction, maintain branch as-is, PR DRAFT/UNMERGED and A5 closeout in **CANDIDATE** state.
4. Following explicit authorization, update acceptance status from CANDIDATE to ACCEPTED, update roadmap and PR, then merge using the allowed repo workflow. Provide the post-merge VS Code checkout/pull/native verification commands. **No automatic merge from this documentation update.**

### Native final verification on the user's PC (no FPGA)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p08-a-physical-baseline
git pull --ff-only origin agent/v3-p08-a-physical-baseline
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/src" python -m pytest -q \
    tests/test_p08_a5_cpu.py tests/test_p08_a5_closeout.py \
    tests/test_p08_a3_2_repeats.py tests/test_p08_a3_2_capture.py \
    tests/test_p08_a3_2_analysis.py tests/test_p08_a3_1_pilot.py \
    tests/test_p08_a2_2_ticks.py tests/test_p08_a2_timing.py \
    tests/test_p07_a4_official.py tests/test_p07_a4_fault.py
python -m py_compile \
    scripts/p08_a5_cpu_benchmark.py scripts/p08_a5_closeout_report.py \
    src/loihi_twin_v2/p08_a5_cpu_reference.py \
    src/loihi_twin_v2/p08_a5_cpu_benchmark.py \
    src/loihi_twin_v2/p08_a5_closeout.py
```

**All tests above are local CPU/no-board tests; do not rerun physical KV260 or official MNIST TEST.**

References: [Measured A5 CPU/FPGA report](P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md); [final A3 six-session report](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md); [A5 full method](P08_A5_CPU_REFERENCE_PROTOCOL.md); [A5 closure/limitations checklist](P08_A5_REMAINING_CLOSEOUT_GATES.md); [P08-A1 original accepted contract](P08_A1_MEASUREMENT_CONTRACT.md).
