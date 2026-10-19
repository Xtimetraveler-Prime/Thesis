# P08-A5 — CPU-reference benchmark and latency-only closeout protocol

**Status (2026-10-18 project timeline): A5 REAL HOST CPU MEASUREMENT AND CPU/FPGA REPORT USER-ATTESTED PASS. Original physical 1,024-image P07 packed numerical oracle and same-TRAIN-stage hash gates passed. Two CPU reference endpoints, three sequential host passes each; SHA256-bound final Markdown was generated. LAST NATIVE PYTEST RERUN AFTER TWO ASSERTION FIXES NOT EXPLICITLY POSTED; USER LATENCY-ONLY ACCEPTANCE/MERGE AUTHORIZATION RECEIVED; ACTUAL MERGE VERIFIED SEPARATELY.** Whole P08-A remains OPEN. The six-session repeated KV260 A3.2 physical latency study is user-attested complete. P08-A4 power/energy remains deferred. No firmware, physical runner, original packed oracle, checkpoint or bitstream was modified during A5 development.

**Measured user-host results:** `P08_A5_CPU_PRELOADED_MEDIAN_MS=25.552718`, `P08_A5_CPU_FULL_MEDIAN_MS=30.200338` (median across the **1,023 per-image medians** of three sequential CPU measurements). Individually, CPU preloaded per-run medians were **25.6147 / 25.6001 / 25.5735 ms**, full image-to-class CPU per-run medians **30.3930 / 30.3147 / 30.2579 ms**. These are two different descriptive estimators, so they need not be identical. FPGA-backed A53+PL original per-run service medians were **35.7023 / 35.6946 / 35.6696 ms** (A2.1), with **35.7234 / 35.7163 / 35.7220 ms** under A2.2. These endpoints are **not fully scope matched**; no pure PL speedup claimed.

**Accepted user-local report provenance:** CPU report `/home/dna/Thesis_Evidence/p08_a5_cpu_ref_20261019T023137Z.json` SHA256 `790072259dab211b57bf40f60bba2b7cb293d7a544ab3aae2660fc8d8c63127d`; original three-pair physical revalidation `/home/dna/Thesis_Evidence/p08_a5_physical_revalidation_20261019T023728Z.json` SHA256 `afd4e91f0106266179072c7242d7e361c033d9d78720d79a3a807e3ed400bf7b`; combined review draft `/home/dna/Thesis_Evidence/p08_a5_closeout_20261019T023733Z.md` SHA256 `17e88feb9330ffca5ecbbfb8735bc08b7fe68f76e74392c0c5c4a538e40233b1`. User reports `P08_A5_CPU_SOURCE_PHYSICAL_P07_1024_PACKED_ORACLE_PASS=1`, both `P08_A5_CPU_{PRELOADED,FULL}_1024_PHYSICAL_SPIKES_EXACT=1`, `P08_A5_CPU_TWO_ENDPOINT_THREE_REPEAT_BENCHMARK_PASS=1`, `P08_A3_2_3_THREE_PAIRED_LATENCY_AGGREGATION_PASS=1`, and `P08_A5_CPU_AND_PHYSICAL_SAME_TRAIN_STAGE_SHA256_PASS=1`. The raw JSON binaries remained user-local; no independent byte-level inspection claimed by assistant.

**Authoritative findings and final acceptance review:** [Measured CPU+FPGA A5 results](P08_A5_CPU_PHYSICAL_LATENCY_RESULTS.md). The commands below are historical reproduction instructions and **do not imply the benchmark is still pending**. No further KV260 work is needed. User's explicit final signoff and last native test output remain for merge readiness.

## 1. What A5 tests, and what it cannot claim

A5 uses the original project-trained frozen **784→32→10** network compiled to the original packed P03 one-core image (42 compartments, 25,408 synapses, 816 axons, 25 input ticks + final drain), unchanged original P06 encoder `image_event_schedule` and `lif_step` integer/signed24/64-bit wrap semantics. No alternative ML framework, training, stochastic input or official MNIST TEST data is benchmarked.

It declares TWO CPU software endpoints:

1. **Preloaded 26-tick integer packed compute.** Model packed synapses, neuron configuration, axon and route lookup are decoded **once outside per-image time**. Input event schedules for **all** 1,024 images are encoded **before any timing**. Each timed invocation reinitializes neuron and packet state and executes exactly 26 recurrent steps: per-tick ingress mapping, synaptic sum with signed64 wrap, signed24 LIF update, NEXT-bank routing and drain/drop policy, 10-class output spike count/readout. This is a **Python pure scalar** reference, not native compiled C performance, nor the FPGA PL dispatch interval.
2. **Raw 784-byte image → class.** The same pre-decoded immutable packed network, but each timed call includes the **original pixel encoder** and the entire 26-tick recurrence, spike readout and class selection. It excludes physical MMIO, DDR page access, board journal writing, host file reads and one-time model load/compile. This is a CPU software service endpoint and is **not exactly identical** to the hardware A53 instrumented full frame-service scope.

A5 explicitly does NOT claim that `CPU full / KV260 service` is a scope-matched FPGA speedup, nor that a Python-scalar CPU time is the best optimized CPU time. In particular, the P08-A3 physical median ≈35.7 ms contains **ARM host-side event bank staging and JTAG-independent PS/PL MMIO/poll, not pure FPGA logic**. The PL raw dispatch cycle counter still lacks independently confirmed achieved-frequency and architectural counter boundary calibration; it must not be converted using the Arm reported 99,999,001 Hz timer frequency.

## 2. Physical and host source integrity

Scripts/implementation:
- `src/loihi_twin_v2/p08_a5_cpu_reference.py` — `prepare_cpu`, `preloaded_compute`, `image_to_class`, all-output physical journal and original independent packed-oracle differential assertions.
- `src/loihi_twin_v2/p08_a5_cpu_benchmark.py` — monotonic PC `time.perf_counter_ns()`, exactly **three separately measured sequential passes per endpoint**, two untimed warmup frames by default, per-frame original 26×10 physical journal checks both before and after each timed call, run-order alternation, full host CPU model/core/affinity/governor/Python/timer provenance and no-overwrite raw per-frame times.
- `scripts/p08_a5_cpu_benchmark.py` — offline-only CLI; invokes accepted original `p07_a4_2_verify.py` on a previously accepted original **real** A2.1 source physical run **before** accepting CPU timing, checks frozen first1024 TRAIN stage/source IDX ledger and candidate SHA-pinned checkpoint, recompiles exactly the accepted packed image/fingerprint/mapping, differential-checks seven representative frames against the original full P06 packed replay, verifies **all 1024×26×10** CPU spike outputs and associated count, packet, external-event and class fields against physical records.
- `src/loihi_twin_v2/p08_a5_closeout.py` and `scripts/p08_a5_closeout_report.py` — require the CPU benchmark report and six-session three-pair aggregate to share the original stage descriptor/pixels/manifest SHA256, and require the CPU reference journal to come from an A2.1 capture already accepted in the three physical pairs. Write a **draft** provenance-bound readable comparison without a fabricated PL-only seconds value, unqualified acceleration ratio, or implicit acceptance.
- `tests/test_p08_a5_cpu.py`, `tests/test_p08_a5_closeout.py` — synthetic native tests for same-core packet routing, 25+1 drain, original packed scalar replay parity, forged per-tick physical disagreement, 1024 sample count, 3× host measured arrays, report source/hash drift and falsely scope-equivalent latency tables. These are **unit fixtures, not physical benchmark output**.

**Sample policy:** same user-accepted `/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z`, same first1024 TRAIN-derived validation source indices, original order and raw image bytes. Source validation loads **TRAIN gzip files only**, never t10k TEST. Physical reference journal/selected trace from already accepted user-run **Pair3 A2.1**:
`/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_1_20261019T012641Z`.

Physical A2.1 ELF identity SHA256 `fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0`. Original reference packed checkpoint state_dict SHA256 `0b0e8a2a9be3ceb19f206f8f55bfd8e73b52e7c2e39f271d7696c39fc9b6fd88`; effective signed integer weights SHA256 `1396f93d21f03b7cff6580ed9cc3176ce40a7afaf53254643120174572b9fe0b`, pinned by original `p06_a4_snapshot.require_pinned_training_candidate`. Source P07 journal and selected full trace independently rereplayed by original oracle before CPU reports are accepted. A5 timing is performed **on the user's PC**, not on the KV260 or A53.

## A5 first native regression corrections (user's initial run)

The first user-executed A5 native regressions returned **two assertion failures** (not CPU performance measurements; no physical hardware use):

- `test_rejects_wrong_encoder_frame_and_timestep_schedule`: the production reference correctly rejected a 25-entry schedule with `A5 requires canonical 25 input ticks plus empty drain tick`. The test incorrectly searched for the literal token `26`. **Fixed only the test assertion** to match the accepted 25-input + 1-drain rule.
- `test_a5_closeout_candidate_same_stage_and_caveats`: the draft report used the lowercase prose `Physical power/energy deferred`, but the regression required an explicit `DEFERRED` status. **Fixed the report** to contain `Physical power/energy status: DEFERRED BY USER; NOT MEASURED.` and strengthened the test to require that exact wording.

The frozen neural arithmetic, encoder, 26-tick computation, source identity pins, physical P07 oracle and both CPU timing endpoints are **unchanged**. Both fixes are committed, but the corrected suite still requires a fresh user-local rerun. **No A5 numerical/CPU benchmark PASS is asserted from the initial failed native tests.** If a later test fails, stop before CPU timing and preserve the exact traceback.

## 3. New host native regression gate (no board)

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
  src/loihi_twin_v2/p08_a5_cpu_reference.py \
  src/loihi_twin_v2/p08_a5_cpu_benchmark.py \
  src/loihi_twin_v2/p08_a5_closeout.py \
  scripts/p08_a5_cpu_benchmark.py \
  scripts/p08_a5_closeout_report.py
```

**Current acceptance nuance:** The user subsequently posted *actual* original-P07-oracle-gated CPU performance and successful generated closeout markers, so the CPU hardware benchmark is **no longer pending**. They have **not explicitly pasted the final native pytest pass total after the two earlier assertion corrections**; request one targeted rerun before merging if that record is required. No Vitis rebuild or FPGA interaction is necessary. Source-level package imports may require the original repository's `.venv-p08` torch dependency.

## 4. Original A3 evidence sealing (offline, optional but recommended)

The original three paired physical JSONs:
```bash
export P08_A3_2_PAIR1_REPORT="$HOME/Thesis_Evidence/p08_a3_2_pair_20261019T004713Z.json"
export P08_A3_2_PAIR2_REPORT="$HOME/Thesis_Evidence/p08_a3_2_pair2_report_20261019T011632Z.json"
export P08_A3_2_PAIR3_REPORT="$HOME/Thesis_Evidence/p08_a3_2_pair3_report_20261019T013553Z.json"
sha256sum "$P08_A3_2_PAIR1_REPORT" "$P08_A3_2_PAIR2_REPORT" "$P08_A3_2_PAIR3_REPORT"
find "$HOME/Thesis_Evidence" -maxdepth 1 -type f -name 'p08_a3_2_three_pair_summary_*.json' -print
```

If you have an original verified three-pair report, use that immutable file in A5. Do not overwrite it. If the file is missing, generate a **NEW** report from the three original paired JSONs via `scripts/p08_a3_2_repeat_check.py` (existing helper) and verify all `P08_A3_2_3_...PASS` markers. Existing accepted physical raw source directories must not be deleted, restarted or modified. No physical JTAG action is needed.

## 5. Run A5 CPU measurements once, on the actual PC (offline)

**Only after A5 native regressions PASS**, from v3 root:

```bash
export P08_A5_CPU_REPORT="$HOME/Thesis_Evidence/p08_a5_cpu_ref_$(date -u +%Y%m%dT%H%M%SZ).json"
PYTHONPATH="$PWD/src" python scripts/p08_a5_cpu_benchmark.py \
  --stage-dir "/home/dna/Thesis_Evidence/p08_a3_2_stage1024_20261019T003150Z" \
  --physical-a21-run-dir "/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_1_20261019T012641Z" \
  --physical-a21-elf "/tmp/v3_p08_a2_build_20261018T193149Z/vitis_workspace/p08_a2_board.elf" \
  --candidate-dir "artifacts/p06_a3_candidate_seed20261013" \
  --train-data-dir "data/mnist_raw" \
  --report "$P08_A5_CPU_REPORT"
```

This intentionally performs a full 1024-frame original packed physical journal verification **before** accepting per-image CPU measurements, then benchmarks two CPU endpoints × 1024 original frames × 3 repeated passes each. Timing starts after the first original neural model decode and excludes first-inference warmup. It records six 1024-value timing arrays on the PC with the original physical journal output parity gate still enforced per frame. No real CPU timing values exist yet; never fill in missing results.

Expected terminal markers (numerical medians depend on actual PC):

```text
P08_A5_CPU_SOURCE_PHYSICAL_P07_1024_PACKED_ORACLE_PASS=1
P08_A5_CPU_PRELOADED_1024_PHYSICAL_SPIKES_EXACT=1
P08_A5_CPU_FULL_1024_PHYSICAL_SPIKES_EXACT=1
P08_A5_CPU_PRELOADED_MEDIAN_MS=...
P08_A5_CPU_FULL_MEDIAN_MS=...
P08_A5_CPU_TWO_ENDPOINT_THREE_REPEAT_BENCHMARK_PASS=1
P08_A5_CPU_VS_FPGA_CLAIM=SCOPES_NOT_IDENTICAL
P08_A5_FPGA_PL_ONLY_SECONDS=NOT_MEASURED
P08_A5_POWER=DEFERRED
P08_A5_OFFICIAL_TEST=SEALED
```

If CPU timing varies with operating system, governor or cooling, do not report a stable/optimized CPU performance claim. Save the original `P08_A5_CPU_REPORT`, including per-image ns, hostname-independent architecture data, Python version, available processor/governor/affinity and original dataset hashes. This is a *single host process with three sequential replay passes*, not three independent freshly rebooted host trials; note that distinction in thesis reporting.

## 6. Draft full physical vs CPU comparison (offline)

Once the measured CPU JSON and **existing accepted** A3.2.3 three-pair aggregate JSON are available:

```bash
export P08_A3_2_REPEAT_REPORT="/home/dna/Thesis_Evidence/REPLACE_WITH_YOUR_ACTUAL_VERIFIED_THREE_PAIR_SUMMARY.json"
export P08_A5_CLOSEOUT_MD="$HOME/Thesis_Evidence/p08_a5_cpu_fpga_closeout_$(date -u +%Y%m%dT%H%M%SZ).md"
PYTHONPATH="$PWD/src" python scripts/p08_a5_closeout_report.py \
  --cpu-report "$P08_A5_CPU_REPORT" \
  --physical-three-pair-report "$P08_A3_2_REPEAT_REPORT" \
  --output-md "$P08_A5_CLOSEOUT_MD"
```

Replace **the placeholder file** with the exact filename obtained from `find` before executing; never copy `REPLACE_WITH` literally. The CLI rejects report overwrite, stage SHA mismatches, wrong physical source run and mismatched CPU report boundaries. It records both source JSON SHA256s in its draft Markdown and displays **`P08_A5_FINAL_USER_ACCEPTANCE=PENDING`**, not `PASS`.

**Result update:** Both offline A5 CPU benchmark and original 3-pair A53 numerical replay/report generation are user-verified PASS. Sections 5–6 are retained for reproducibility, not additional compulsory measurements. Their `REPLACE_WITH_...` example remains a historical placeholder; **actual exact filenames are listed above** and should be used in any revalidation.

## 7. Boundaries for final P08-A closeout

- **A3 complete at physical descriptive level** (six real sessions on the same first1024 validation images), subject to user-local raw SHA256 sealing and explicit acknowledgment.
- **A5 physical-backed host CPU benchmark and human-readable closeout candidate generated (user-attested PASS)**. Two CPU endpoints and six physical sessions were bound to the original TRAIN stage, with reported CPU/physical report SHA256s, numerical-oracle PASS and source parity PASS. **Final human approval and corrected native pytest suite result still pending documentation; no PR merge until explicit authorization.**
- The final report must not confuse **Python scalar host performance** with optimized native CPU performance or the **A53-controlled FPGA full service** with bare PL neural compute. Any comparative latency figures need clear scope qualifiers. Pure PL seconds/speedup require accepted PL achieved Hz first; this A5 candidate does not claim them.
- **Power/energy P08-A4 remain deferred** by user. Original P07 official 10k TEST accuracy is historical and not rerun in this experiment.
- User explicitly reviewed and approved the two CPU endpoints, neural parity, source hashes, deferred power and latency-only acceptance scope, and authorized PR #45 merge. Verify actual GitHub merge SHA before claiming successful merge; final native pytest summary was not supplied.

Research source of truth: [original A1 measurement contract](P08_A1_MEASUREMENT_CONTRACT.md) §§3–7; [final A3 physical measurements](P08_A3_2_3_FINAL_PHYSICAL_REPEAT_RESULTS.md); [A5 remaining acceptance gates](P08_A5_REMAINING_CLOSEOUT_GATES.md).
