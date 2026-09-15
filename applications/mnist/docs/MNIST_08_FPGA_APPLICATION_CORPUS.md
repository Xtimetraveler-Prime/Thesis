# MNIST-08 FPGA Application Corpus

**Status:** Implementation complete; local software/Vivado/physical validation pending

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

## Packed external-event storage

The MNIST-07/M12.3 directed-test include used a rectangular `case x tick x max_events` array. That is reasonable for a small directed corpus but wasteful for 60 MNIST cases.

MNIST-08 stores external events contiguously and emits a row-pointer table:

```text
M12_3_EXTERNAL_ROWS[case_tick]
M12_3_EXTERNAL_EVENTS[packed_event_index]
```

The existing per-case/tick event counts remain present. Event order and multiplicity are unchanged; only the debug input-ROM layout is compressed.

## Capture-shell reuse

MNIST-08 continues to reuse the validated M12.3 physical transport and core integration. The application bitstream flow stages the existing sources and mechanically adapts only the capture-shell indexing needed for the larger corpus:

1. static image reads use `M12_3_CASE_PROFILE_IDS[active_case_id]`;
2. external-event reads use packed row pointers; and
3. the existing four-bit `capture_phase` case witness is compared to the low nibble of case IDs above 15.

The complete case identity is still validated by the exact captured external-event schedule and independent golden differential, so a wrong high case-ID bit cannot silently pass.

The core neuron/synapse/routing RTL and packaged HLS neuron IP are not modified by MNIST-08.

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
applications/mnist/build/mnist-08/
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

MNIST-08 closes when:

1. the application pytest suite passes with the new corpus/adapter tests;
2. the generator reconstructs exactly 30 frozen source images and 60 profile/image cases;
3. every regenerated golden prediction matches the prediction recorded in the committed `mnist-v1` corpus;
4. the Vivado 2025.2 K26 implementation passes the existing timing/resource gates with the shared-static/packed-event capture image;
5. all 60 physical cases complete all 16 ticks;
6. all 960 committed physical ticks produce zero architectural mismatches;
7. every physical final spike-count vector and prediction matches its independent Python golden case; and
8. the suite report records 60/60 passing cases, including 30/30 for each profile and complete both-correct/profile-divergent/both-wrong coverage.
