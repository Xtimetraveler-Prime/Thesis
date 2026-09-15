# MNIST Application Milestones

## Purpose

This file tracks the MNIST application rollout separately from the baseline neuromorphic digital-twin platform milestones in the repository root. Application code must consume the validated core rather than silently changing its behavior.

The application carries two FPGA-v1 profiles under the same 4,096-synapse physical ceiling:

- **native-sparse** — original 28x28 MNIST, 784 input axons, at most 4,096 sparse/pruned synapses;
- **cropped-dense** — exact 20x20 center crop, 400 input axons, at most 4,000 dense synapses.

Both use the same deterministic 16-tick rate encoder, ten LIF output neurons, and highest-spike-count decoding with lowest neuron ID as the deterministic tie-break.

---

## MNIST-01 — Capacity Audit and Dual-Profile Architecture

**Status:** Complete

The frozen FPGA-v1 application boundary is 256 neurons, 1,024 axons, 4,096 synapses, 4,096 routes, and 4,096 external/recurrent events per tick. A dense 784x10 classifier requires 7,840 synapses and therefore does not fit.

The two accepted profiles are:

```text
native-sparse:  28x28 -> 784 axons -> <=4096 synapses -> 10 outputs
cropped-dense:  20x20 -> 400 axons -> <=4000 synapses -> 10 outputs
```

Both freeze `current_decay=4096`, `voltage_decay=0`, zero reset/bias/refractory, 16 presentation ticks, zero recurrent routes, and spike-count decoding.

See `docs/MNIST_01_CAPACITY_AUDIT.md`.

---

## MNIST-02 — Shared Dataset and Deterministic Spike Encoding

**Status:** Complete

One profile-aware encoder supports both mappings. Native-sparse preserves all 784 pixels and maps them row-major to axons `0..783`; cropped-dense applies `[4:24,4:24]` and maps the 400 retained pixels to axons `0..399`.

The same integer cumulative-rate rule produces deterministic spike schedules for both profiles. Source-level tests and TensorFlow-backed real-MNIST integration tests passed in the user application environment, and full accepted training runs consumed the standard dataset without event-bound or profile failures.

---

## MNIST-03 — Software SNN Training Baselines

**Status:** Complete

Training reuses the valid parts of the user-authored TensorFlow/Keras notebook workflow: standard MNIST loading, Adam, sparse categorical cross-entropy, elapsed-time measurement, `argmax` classification, and incorrect-sample indexing. The ANN forward path is replaced by explicit integrate-and-fire dynamics with a surrogate gradient.

Model selection uses a deterministic stratified 5,000-image validation split from the official 60,000-image training set. The official 10,000-image test split is evaluated only after model selection is frozen.

### MNIST-03A — Cropped-dense

Ten epochs were trained with all 4,000 connections. The validation-selected checkpoint achieved:

```text
best validation accuracy:      89.12%
final official test accuracy:  90.29%
nonzero float weights:          4,000
```

### MNIST-03B — Native-sparse

The full 7,840-weight software network was trained, the best dense checkpoint restored, magnitude-pruned to 4,096 connections, and then fine-tuned under a frozen mask with a reset Adam optimizer. Immediate pruning reduced validation accuracy from 90.28% to 82.50%; masked fine-tuning recovered to 90.92% at fine-tune epoch 2.

```text
selected stage:                masked-finetune epoch 2
final official test accuracy:  91.62%
nonzero float weights:          4,096
```

Native-sparse therefore finishes 1.33 percentage points above cropped-dense while remaining inside essentially the same physical synapse budget.

See `docs/MNIST_03_TRAINING_BASELINES.md`.

---

## MNIST-04 — Hardware-Aware Quantization and Export

**Status:** Complete

Both accepted checkpoints were exported into the existing project-native encoded-weight representation and M08 CSR storage contract. Export validates profile, shape, connection budget, signed mantissa range, threshold/state scale, and conservative SAT24 headroom.

The full 10,000-image matched evaluation produced:

| Profile | Float accuracy | Stored synapses | Quantized/golden accuracy | Delta |
|---|---:|---:|---:|---:|
| cropped-dense | 90.29% | 3,893 | 90.24% | -0.05 pp |
| native-sparse | 91.62% | 4,086 | 91.71% | +0.09 pp |

Some small trained weights quantized exactly to zero, reducing the stored synapse count from 4,000 to 3,893 for cropped-dense and from 4,096 to 4,086 for native-sparse. The resulting accuracy changes are negligible.

See `docs/MNIST_04_05_ACCEPTED_VALIDATION.md`.

---

## MNIST-05 — Python Golden-Model Evaluation

**Status:** Complete

Both accepted exported deployments were executed through the actual validated `NeuromorphicCore` using FPGA-v1 arithmetic; no application-specific neuron simulator was substituted.

On the full official 10,000-image test set:

| Profile | Float accuracy | Golden accuracy | Prediction agreement |
|---|---:|---:|---:|
| cropped-dense | 90.29% | 90.24% | 99.25% |
| native-sparse | 91.62% | 91.71% | 99.30% |

Golden evaluation preserves final accuracy, confusion matrix, predictions, incorrect indices, accuracy after every presentation tick, input events/image, output spikes/image, exact CSR synapse visits/image, no-spike count, and tied-winner count. The full application pytest suite passed before accepted validation.

See `docs/MNIST_04_05_ACCEPTED_VALIDATION.md`.

---

## MNIST-06 — Dual-Profile Deployment Freeze

**Status:** Complete

The accepted full-test MNIST-04/05 artifacts have been materialized into the source-controlled `applications/mnist/frozen/mnist-v1/` package and independently validated.

The freeze contains:

- both accepted floating-point checkpoints;
- both exact project-native deployment images and M08 weight-memory files;
- SHA-256 hashes for checkpoints, deployments, accepted-validation evidence, and the common corpus;
- the frozen 16-tick application contract;
- the accepted full-test software/golden summaries; and
- one deterministic 30-image common FPGA-validation corpus.

The corpus contains exactly three samples for every digit `0..9`: one both-correct case, one profile-divergent case, and one both-wrong case. The accepted materialized corpus required no fallbacks. The same original MNIST test indices are used for both profiles.

`validate_frozen_deployment.py` passed in the user application environment before the package was committed. The committed `mnist-v1` directory is now the sole accepted input package for MNIST-07 and later physical experiments; any changed hash requires a new freeze version rather than a silent replacement.

See `docs/MNIST_06_DEPLOYMENT_FREEZE.md`.

---

## MNIST-07 — Single-Image FPGA Conformance

**Status:** Complete

MNIST-07 used the first frozen both-correct corpus image as a shared source anchor for both profiles. In `mnist-v1` this is official MNIST test index 3, true label 0. Both profiles were presented for 16 ticks from zero initial state using their frozen deployment images.

### MNIST-07A — Cropped-dense

The physical K26 completed all 16 committed ticks with exact agreement against the independent Python golden trace and zero architectural mismatches.

### MNIST-07B — Native-sparse

The physical K26 repeated the same 16-tick test using the frozen 784-axon / 4,086-synapse sparse deployment, including its irregular CSR rows, again with zero architectural mismatches.

The accepted run reused the existing M12.3 multi-tick capture shell and JTAG/VIO transport. FPGA-visible artifacts contained static configuration/weight/row images and per-tick external events only; independent golden state, signed-64 synaptic accumulators, spike flags, spike counts, and predictions stayed host-side.

Both physical final spike-count vectors and decoded predictions matched the corresponding Python golden results. This closes the application-level physical conformance gate for both deployment profiles.

See `docs/MNIST_07_SINGLE_IMAGE_CONFORMANCE.md`.

---

## MNIST-08 — FPGA Application Corpus

**Status:** Complete

The complete frozen 30-image source corpus was executed through both accepted physical deployment profiles:

```text
30 frozen source images x 2 profiles = 60 physical cases
60 cases x 16 ticks = 960 committed physical ticks
```

The accepted K26 run completed all 60 captures, and the independent host-side differential validator reported:

```text
MNIST-08 suite: passed=True cases=60 ticks=960 mismatches=0
profile=cropped-dense cases=30 passed=30 mismatches=0
profile=native-sparse cases=30 passed=30 mismatches=0
reason=both-correct cases=20 passed=20 mismatches=0
reason=profile-divergent cases=20 passed=20 mismatches=0
reason=both-wrong cases=20 passed=20 mismatches=0
```

Every physical tick matched the corresponding Python `NeuromorphicCore` golden trace at the accepted application/core boundary, including ordered external events, signed-64 synaptic accumulators, state-before/state-after words, spike flags, fault status, final spike counts, and decoded predictions.

Scaling from MNIST-07 exposed two validation-harness issues that were corrected without changing the architectural core. First, a single packed external-event variable exceeded Vivado's 1,000,000-bit synthesis limit; the event image was changed to two profile-banked packed ROMs with a generation-time size guard. Second, the first completed 60-case capture exposed a CLI summary-key mismatch after validation had already succeeded and written the reports; regression coverage now enforces that reporting contract. Neither issue altered neuron, synapse, arithmetic, event-order, or classification semantics.

The 30-image corpus remains a deliberately selected conformance set rather than an unbiased accuracy sample.

See `docs/MNIST_08_FPGA_APPLICATION_CORPUS.md`.

---

## MNIST-09 — Shared Runtime Host Interface

**Status:** Complete

One reusable Vivado 2025.2 K26 bitstream contains both frozen `mnist-v1` deployment images while arbitrary image schedules are encoded on the host and streamed at runtime. The implementation preserves the existing M12.3 VIO shape: `capture_start` selects the frozen profile, trace space `7` appends runtime axon IDs, `capture_step` executes a buffered tick, and normal trace spaces retain their validated post-commit read semantics. The architectural core RTL and HLS neuron IP are unchanged.

The accepted physical runtime exercise used the same generated bitstream artifacts for four classifications:

```text
cropped-dense, index 3, label 0, golden prediction 0
native-sparse,  index 3, label 0, golden prediction 0
cropped-dense, index 1, label 2, golden prediction 2
native-sparse,  index 1, label 2, golden prediction 2
```

All four physical runs passed exact comparison of final output spike-count vectors and decoded predictions against the frozen Python golden result. Thus the runtime demonstrated both profile switching and image switching without rebuilding application-specific neuron logic or regenerating the bitstream.

Two host/runtime bring-up issues were corrected without changing the core: an over-broad static-image safety grep that mistook the allowed `M12_3_MAX_EXTERNAL_EVENTS` capacity constant for compiled event data, and a trace-read synchronization ordering bug after runtime space-7 event injection. Both have regression coverage.

After the final host-side synchronization patch, the complete application pytest suite passed in the user environment. JTAG/VIO transaction time remains explicitly separate from architectural FPGA execution time.

See `docs/MNIST_09_SHARED_RUNTIME.md`.

---

## MNIST-10 — Characterization and Loihi Comparison

**Status:** Complete

### MNIST-10A — Internal FPGA profile comparison

**Status:** Complete

The accepted full 10,000-image FPGA-v1 golden evaluation gives:

| Metric | cropped-dense | native-sparse |
|---|---:|---:|
| Golden accuracy | 90.24% | 91.71% |
| Mean input events/image | 1,614.46 | 1,668.58 |
| Mean CSR synapse visits/image | 15,678.95 | 6,132.83 |
| Mean output spikes/image | 26.28 | 20.50 |
| Logical static deployment data | 17.055 KiB | 19.309 KiB |
| Full-test mean architectural cycles/image | 71,893.61 | 33,925.63 |
| Full-test mean PL latency @100 MHz | 0.718936 ms | 0.339256 ms |

The image-level timing means are project-derived from measured workload counts using the M12.5 no-route equation:

```text
cycles/image = 16*(16*10 + 10) + 4*input_events + 4*CSR_synapse_visits
```

MNIST-10 directly validated that equation on the physical K26 using the actual reusable MNIST runtime. Four accepted runs cover two distinct source images through both profiles, and all **64 physical tick-cycle measurements exactly equal** their independent predictions while preserving exact golden spike-count/prediction agreement.

Accepted physical image totals:

```text
cropped-dense index 3: 103264 cycles = 1.03264 ms
native-sparse  index 3:  45832 cycles = 0.45832 ms
cropped-dense index 1:  74500 cycles = 0.74500 ms
native-sparse  index 1:  40824 cycles = 0.40824 ms
```

The compact evidence and SHA-256 provenance are source-controlled under `evidence/mnist-10/physical-timing-v1/`.

The strongest internal result is that native-sparse is +1.47 percentage points more accurate while using only 39.12% as many mean CSR synapse visits and about 47.19% as many derived architectural cycles per image under nearly the same stored-synapse ceiling. The shared dual-profile bitstream passed the existing routed-resource gate; profile-specific memory is reported separately as logical frozen-deployment storage rather than incorrectly attributing shared LUT/FF/BRAM/DSP totals to one profile.

FPGA energy/inference remains explicitly **not measured** because no defensible workload-specific physical power boundary was established.

See `docs/MNIST_10_CHARACTERIZATION.md`.

### MNIST-10B — Native-sparse Loihi-facing comparison

**Status:** Complete

Native-sparse is the primary external comparison because it preserves the full 28x28 MNIST representation. External Loihi metrics are governed by `docs/MNIST_10_LOIHI_SOURCES.md`.

The primary numeric Loihi MNIST reference is Rueckauer et al., *NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi* (ACM JETC, DOI `10.1145/3501770`). Its frame-based MNIST benchmark reports a converted four-layer CNN mapped to 14 neurocores, run for 100 algorithmic time steps/sample, with 0.79% error (99.21% accuracy), 0.66 mJ/sample, and 6.65 ms/sample.

Those numbers are retained as cross-system literature context, not a workload-matched speedup/energy comparison. The FPGA network topology, neuron/parameter count, training path, presentation length, precision/mapping, and timing/measurement boundary differ. The thesis-facing table therefore does not divide the FPGA and Loihi latency values into an architecture speedup claim.

Primary papers control their own benchmark values when secondary comparison tables disagree. Davies et al. remains the primary Loihi-1 architecture source; later comparison tables are used only for explicitly labeled secondary quantities/cross-checks.

### MNIST-10C — Cropped-dense interpretation

**Status:** Complete

Cropped-dense is retained as a controlled FPGA-v1 hardware-fit baseline rather than the primary Loihi comparator because it changes the sensory representation to a 20x20 crop. Its main value is the internal comparison against native-sparse under essentially the same stored-synapse ceiling.

The final comparison explicitly separates direct project measurements, project-derived metrics, primary external literature measurements, secondary-source estimates, and qualitative architecture context.

See `docs/MNIST_10_CHARACTERIZATION.md` and `docs/MNIST_10_LOIHI_SOURCES.md`.

The full application regression passed after the archived physical evidence and final MNIST-10 documentation changes, and the accepted branch was merged into `main`.

---

## MNIST-11 — Brian2Loihi Matched Reference Experiment

**Status:** Planned

MNIST-11 replaces the loose published-Loihi comparison with a matched **software/reference-model** experiment. The accepted native-sparse deployment is translated into Brian2Loihi without retraining, using the same 28x28 source images, 4,086-connection graph, accepted effective weights where representable, exact deterministic 16-tick event schedules, zero initial state, and spike-count decoder.

The milestone proceeds in five gates:

1. **MNIST-11.1 — Toolchain/provenance freeze:** isolate and pin the older Brian2Loihi environment and reproduce upstream examples before adding project code.
2. **MNIST-11.2 — Semantic mapping audit:** classify decay, threshold, reset, refractory, weight scaling, rounding, saturation, update-order, and spike-timing semantics as `EXACT`, `EQUIVALENT`, `TRANSLATED`, `UNREPRESENTABLE`, or `NOT_USED`.
3. **MNIST-11.3 — Micro-conformance:** compare directed single-neuron/network traces before attempting MNIST-scale claims.
4. **MNIST-11.4 — Frozen 30-image corpus:** replay the same source indices/event schedules and report state/spike/prediction agreement plus first-divergence causes.
5. **MNIST-11.5 — Full 10,000-image evaluation:** if the mapping is stable, measure Brian2Loihi accuracy, prediction agreement, spike-vector agreement, and disagreement indices using the unchanged frozen network.

Brian2Loihi CPU wall time is not Loihi hardware latency and must not be compared to FPGA PL latency. If exact mapping is impossible, a quantified semantic-divergence result is acceptable; retuning the network to force agreement is not.

See `docs/MNIST_11_BRIAN2LOIHI_MATCHED_REFERENCE.md`.

---

## MNIST-12 — Catalyst N1 Matched Hardware Comparison

**Status:** Planned

MNIST-12 moves from a Loihi emulator to an independent **Loihi-class hardware architecture**. The first target is Catalyst N1 because its public project provides a relatively simple fixed-point LIF design, Python SDK/reference simulator, open Verilog RTL, and an explicit Kria K26 build target. Catalyst is not Intel Loihi, so its results remain a separate external-architecture comparison.

The milestone proceeds in six gates:

1. **MNIST-12.1 — Upstream/K26 feasibility audit:** pin the exact Catalyst N1 revision, reproduce software regressions, verify the exact K26/Vivado target, and audit neuron/synapse/event/routing capacities for the frozen 784-input/10-output/4,086-connection network.
2. **MNIST-12.2 — Semantic mapping audit:** classify Catalyst LIF/weight/update semantics using the same explicit mapping categories as MNIST-11.
3. **MNIST-12.3 — Catalyst CPU/reference experiment:** deploy the unchanged translated graph through Catalyst's software reference before touching hardware and compare it against FPGA-v1 and Brian2Loihi.
4. **MNIST-12.4 — Physical Catalyst N1 K26 run:** begin with MNIST indices 3 and 1, then expand to the 30-image conformance corpus if stable; physical Catalyst output must first agree with its own pinned software reference.
5. **MNIST-12.5 — Same-K26 characterization:** collect locally generated Vivado resources/timing and a defensible on-device execution boundary. Host transport is excluded unless both targets deliberately use equivalent boundaries.
6. **MNIST-12.6 — Final matched matrix:** separate `MATCHED GRAPH + MATCHED DYNAMICS`, `MATCHED GRAPH + TRANSLATED DYNAMICS`, and `UNMATCHED LITERATURE REFERENCE` evidence across FPGA-v1, Brian2Loihi, Catalyst software/hardware, and published Loihi context.

No energy/inference comparison is admitted from board TDP or Vivado estimated power. A physical K26 blocker may close a feasibility sub-gate but does not count as a hardware comparison result.

See `docs/MNIST_12_CATALYST_MATCHED_HARDWARE.md`.

### Follow-on decision — actual Intel Loihi / Lava

MNIST-11 and MNIST-12 still do not execute the workload on Intel Loihi silicon. Brian2Loihi is a Loihi-1 software emulator, while Catalyst is independently developed Loihi-class hardware. If authenticated Loihi-2/Lava hardware access becomes available, create a separate follow-on milestone using the same frozen comparison contract rather than folding an unmatched Loihi-2 experiment into MNIST-12.
