# MNIST-08 FPGA Application Corpus

**Status:** Complete

## Goal

MNIST-08 expands the exact physical correctness result from MNIST-07 to the complete frozen application-validation corpus. The accepted `mnist-v1` freeze contains 30 original MNIST test images: three for every digit class, intentionally covering one both-correct case, one profile-divergent case, and one both-wrong case.

Each source image is executed through both frozen deployment profiles:

```text
30 source images x 2 profiles = 60 physical cases
60 cases x 16 presentation ticks = 960 committed physical ticks
```

The purpose is **physical conformance**, not an unbiased 30-image accuracy estimate. The corpus was deliberately selected to include easy, profile-sensitive, and difficult samples, so its class/prediction composition must not be presented as random test-set accuracy.

## Frozen case mapping

Case ordering is source-major. For each frozen source entry, cropped-dense is immediately followed by native-sparse. Thus each original MNIST test index is presented to both accepted deployment profiles without changing the source sample.

Every case records:

- source-corpus ordinal;
- official MNIST test index;
- true label;
- frozen selection reason;
- profile;
- expected golden prediction;
- deployment counts;
- 16-tick external-event schedule; and
- independent host-side golden trace.

## Physical correctness boundary

MNIST-08 uses the same exact comparison fields accepted in MNIST-07:

- committed tick;
- external input axons, including order and multiplicity;
- recurrent input axons (zero for these feed-forward profiles);
- exact signed-64 synaptic accumulators;
- packed state-before words;
- packed state-after words;
- per-neuron spike flags;
- routed output axons (zero for these profiles);
- core fault status;
- external-event count;
- final output spike-count vector; and
- final decoded prediction.

The FPGA is never supplied expected states, spikes, spike counts, or predictions. Those values remain in host-side golden JSON artifacts generated independently through `NeuromorphicCore`.

## Shared-static-image corpus architecture

A naive extension of the MNIST-07 include would repeat approximately four thousand synapse words for every one of the 60 cases. MNIST-08 avoids that unnecessary debug-harness cost.

The generated FPGA input image stores exactly two immutable static deployment images:

```text
profile 0: cropped-dense
profile 1: native-sparse
```

Each of the 60 dynamic cases stores only:

```text
case -> profile_id
case -> 16-tick external-event schedule
```

The staged M12.3 capture controller therefore uses the case ID for schedule selection and the corresponding profile ID for configuration/weight/CSR load-image selection. The validated architectural core RTL is unchanged.

## Profile-banked packed external-event storage

The MNIST-07/M12.3 directed-test include used a rectangular `case x tick x max_events` array. That is reasonable for a small directed corpus but wasteful for 60 MNIST cases.

MNIST-08 first compressed all case/tick schedules into a single packed 16-bit event array plus row pointers. The first full Vivado synthesis attempt exposed a tool limit rather than a core-design failure: the packed array contained **1,524,304 bits**, while Vivado synthesis rejects a single generated variable above **1,000,000 bits** (`Synth 8-4556`).

The corrected layout preserves the packed representation but banks event words by the already-frozen profile ID:

```text
M12_3_EXTERNAL_ROWS[case_tick]              -> offset within selected profile bank
M12_3_EXTERNAL_EVENTS_PROFILE0[offset]      -> cropped-dense events
M12_3_EXTERNAL_EVENTS_PROFILE1[offset]      -> native-sparse events
```

Each case/tick row pointer is therefore relative to its profile-specific bank. Event order, multiplicity, counts, schedules, golden traces, and application semantics are unchanged. Only the generated debug-ROM organization changes.

The generator computes the bit size of each profile event bank and refuses to emit the include if either bank reaches Vivado's 1,000,000-bit per-variable ceiling. It also prints both bank sizes before synthesis, turning this tool limitation into an explicit pre-Vivado validation gate.

## Capture-shell reuse

MNIST-08 continues to reuse the validated M12.3 physical transport and core integration. The application bitstream flow stages the existing sources and mechanically adapts only the capture-shell indexing needed for the larger corpus:

1. static image reads use `M12_3_CASE_PROFILE_IDS[active_case_id]`;
2. external-event reads use packed row pointers and the selected profile's synthesis-safe event bank; and
3. the existing four-bit `capture_phase` case witness is compared to the low nibble of case IDs above 15.

The complete case identity is still validated by the exact captured external-event schedule and independent golden differential, so a wrong high case-ID bit cannot silently pass.

The core neuron/synapse/routing RTL and packaged HLS neuron IP are not modified by MNIST-08.

## Accepted physical result

The corrected Vivado 2025.2 build completed, and the physical K26 capture ran every case to completion. The capture shell reported **60 cases and 960 committed ticks** before Hardware Manager exited.

The independent host validator then reported:

```text
MNIST-08 suite: passed=True cases=60 ticks=960 mismatches=0
profile=cropped-dense cases=30 passed=30 mismatches=0
profile=native-sparse cases=30 passed=30 mismatches=0
reason=both-correct cases=20 passed=20 mismatches=0
reason=profile-divergent cases=20 passed=20 mismatches=0
reason=both-wrong cases=20 passed=20 mismatches=0
```

Thus all **60/60 physical workloads** and all **960/960 committed FPGA ticks** matched their independent Python golden traces exactly at the accepted application/core boundary. Both accepted deployment profiles passed every frozen source case, including the deliberately difficult profile-divergent and both-wrong categories. Physical final spike-count vectors and decoded predictions matched the frozen Python results for every case.

## Validation-harness issues discovered during scale-up

Two issues were discovered while expanding from the two-case MNIST-07 gate to the 60-case MNIST-08 corpus. Both were outside the architectural core and were corrected without changing neuron, synapse, arithmetic, event-order, or classification semantics.

First, the original single packed external-event variable exceeded Vivado's per-variable synthesis-size ceiling. The profile-banked packed layout described above resolved that failure and is now guarded before synthesis.

Second, the first successful 60-case physical capture completed and the host validator wrote the per-case reports plus `suite_report.json`, but the CLI crashed while printing the final summary because it requested stale key names. The summary contract was corrected and regression-tested. The expensive physical captures did not need to be repeated; rerunning only the host validator over the preserved captures produced the accepted zero-mismatch result above.

These failures are therefore treated as validation-harness scalability/debugging findings, not evidence of a core behavioral discrepancy.

## Tooling

Generation and validation:

```text
mnist_app/fpga_corpus.py
mnist_app/fpga_corpus_shell.py
scripts/generate_fpga_corpus.py
scripts/validate_fpga_corpus_suite.py
```

Physical flows:

```text
fpga/run_mnist_08_bitstream.sh
fpga/run_mnist_08_hardware.sh
```

Generated build tree:

```text
applications/mnist_baseline/build/mnist-08/
├── golden/
│   ├── manifest.json
│   ├── hardware_cases.tsv
│   └── 60 *.golden.json traces
├── artifacts/
│   ├── neuromorphic_twin_mnist_08.bit
│   ├── neuromorphic_twin_mnist_08.ltx
│   ├── neuromorphic_twin_mnist_08.xsa
│   └── neuromorphic_twin_mnist_08_routed.dcp
├── captures/
│   └── 60 *.physical.json traces
└── differential_reports/
    ├── 60 *.report.json files
    └── suite_report.json
```

## Completion criteria

All completion criteria were met:

1. the application pytest suite passed with the corpus/adapter/reporting tests;
2. the generator reconstructed exactly 30 frozen source images and 60 profile/image cases;
3. every regenerated golden prediction matched the prediction recorded in the committed `mnist-v1` corpus;
4. both profile-specific event banks passed the synthesis-size guard and the Vivado 2025.2 K26 implementation passed the existing implementation gates;
5. all 60 physical cases completed all 16 ticks;
6. all 960 committed physical ticks produced zero architectural mismatches;
7. every physical final spike-count vector and prediction matched its independent Python golden case; and
8. the suite report recorded 60/60 passing cases, including 30/30 for each profile and complete both-correct/profile-divergent/both-wrong coverage.
