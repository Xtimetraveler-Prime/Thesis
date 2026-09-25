# MNIST-10 Characterization and Loihi Comparison

**Status:** MNIST-10A/B/C scientific work complete; compact physical evidence archived and accepted. Parent MNIST-10 is ready for closure after one final application regression confirmation before merge.

## Purpose

MNIST-10 turns the validated MNIST application into a characterization result while preserving the correctness boundary established by MNIST-07 through MNIST-09.

The work is divided into three parts:

- **MNIST-10A:** compare `cropped-dense` and `native-sparse` on the same FPGA-v1 architecture;
- **MNIST-10B:** place `native-sparse` beside published Intel Loihi MNIST results with explicit workload/method caveats; and
- **MNIST-10C:** interpret `cropped-dense` as a controlled FPGA hardware-fit baseline rather than the main Loihi-facing result.

External Loihi sources and metric provenance are maintained in `MNIST_10_LOIHI_SOURCES.md`. No external number is admitted to the comparison table without a source and comparability classification.

---

## MNIST-10A — Internal FPGA profile comparison

### Accepted full-test application metrics

The following values come directly from the frozen `mnist-v1` accepted full 10,000-image FPGA-v1 golden evaluation. They are not estimated from the deliberately selected 30-image physical conformance corpus.

| Metric | cropped-dense | native-sparse |
| --- | ---: | ---: |
| Input representation | 20x20 crop | native 28x28 |
| Input axons | 400 | 784 |
| Output neurons | 10 | 10 |
| Presentation ticks | 16 | 16 |
| Stored quantized synapses | 3,893 | 4,086 |
| Golden accuracy | **90.24%** | **91.71%** |
| Mean input events / image | **1,614.46** | **1,668.58** |
| Mean CSR synapse visits / image | **15,678.95** | **6,132.83** |
| Mean output spikes / image | **26.28** | **20.50** |

Native-sparse is **+1.47 percentage points** more accurate while generating only **3.35% more input events**. Sparse row structure reduces actual synaptic work much more strongly: native-sparse performs only **39.12%** as many CSR synapse visits per image as cropped-dense. Its mean output spike count is about **78.01%** of cropped-dense.

This demonstrates why raw input-event count is not an adequate performance proxy for this architecture. One axon event may traverse a long dense CSR row, a short sparse row, or an empty row.

### Logical frozen deployment footprint

The profile-attributable logical static-memory footprint is derived from the frozen word schemas:

```text
10 neuron configs       x 128 bits
10 initial states       x  64 bits
2 weight formats        x  16 bits
stored synapses         x  32 bits
(input_axons + 1) rows  x  32 bits
11 empty route rows     x  32 bits
```

| Profile | Logical static deployment data |
| --- | ---: |
| cropped-dense | **139,712 bits = 17.055 KiB** |
| native-sparse | **158,176 bits = 19.309 KiB** |

These are application-image storage quantities, **not FPGA BRAM utilization**. The MNIST-10 runtime bitstream contains both profiles simultaneously, so routed LUT/FF/BRAM/DSP totals are shared implementation costs rather than meaningful per-profile resource values. The successful bitstream build passed the repository's existing routed-resource gate; the table above is the profile-specific memory comparison used in the thesis.

---

## Architectural timing definition

MNIST-10 inherits the physically validated M12.5 timing boundary:

```text
architectural tick latency = PL ap_clk cycles
from accepted tick_start
through observed outer-core tick_done
```

At the frozen K26 target:

```text
PL clock = 100 MHz
period   = 10 ns
```

Host Python execution, TensorFlow loading/encoding, Vivado Hardware Manager, JTAG, VIO writes/reads, JSON serialization, and comparison time are explicitly excluded from architectural inference latency.

M12.5 physically isolated the no-route FPGA-v1 costs as:

```text
quiescent tick cycles = 16 * neuron_count + 10
external input event  = 4 additional cycles/event
CSR synapse visit     = 4 additional cycles/visit
```

Both accepted MNIST profiles have ten neurons and zero recurrent routes. Therefore:

```text
cycles/image =
    16 ticks * (16*10 + 10)
    + 4 * input_events/image
    + 4 * CSR_synapse_visits/image
```

Applying that relation to the accepted full-test workload means gives:

| Profile | Full-test mean cycles/image | PL latency @100 MHz | Images/s |
| --- | ---: | ---: | ---: |
| cropped-dense | **71,893.61** | **0.718936 ms** | **1,390.94** |
| native-sparse | **33,925.63** | **0.339256 ms** | **2,947.62** |

The native/cropped cycle ratio from the full-test means is **0.4719**.

These full-test image-level values remain **project-derived workload averages**, because all 10,000 test images were not individually timed on the FPGA. Their timing equation, however, is now directly validated on the physical MNIST application.

---

## Accepted direct physical timing evidence

The source-controlled evidence package is:

```text
applications/mnist/evidence/mnist-10/physical-timing-v1/
```

Its manifest records four K26 runs on `xck26_0`, all accepted with `all_passed=true`. For every run, the validator required:

1. the physical output spike-count vector to exactly match the independent frozen Python golden vector;
2. the physical decoded prediction to equal the golden prediction;
3. exactly 16 committed ticks;
4. the physical event count to match the host request; and
5. the complete **16-element physical tick-cycle vector to exactly equal** the independent M12.5-derived prediction.

The archived direct measurements are:

| Profile | MNIST index | Label/prediction | Events | Physical cycles | PL latency @100 MHz |
| --- | ---: | ---: | ---: | ---: | ---: |
| cropped-dense | 3 | 0 / 0 | 2,345 | **103,264** | **1.03264 ms** |
| native-sparse | 3 | 0 / 0 | 2,345 | **45,832** | **0.45832 ms** |
| cropped-dense | 1 | 2 / 2 | 1,670 | **74,500** | **0.74500 ms** |
| native-sparse | 1 | 2 / 2 | 1,820 | **40,824** | **0.40824 ms** |

All 64 physical tick measurements exactly equal their independently predicted cycle counts. The archive also retains each request, deterministic event schedule, timing expectation, physical result, exact comparison, and SHA-256 hashes for those files.

The physical measurements therefore validate both the timing boundary and the exact serialized timing equation on real MNIST schedules for both frozen deployment profiles. They also reinforce the internal sparse/dense interpretation: for the same source image at index 3, both profiles receive the same 2,345 encoded events, yet native-sparse uses far fewer cycles because its CSR rows cause substantially fewer synapse visits.

---

## Final MNIST-10A interpretation

Under nearly the same stored-synapse limit, native-sparse simultaneously:

- preserves the original 28x28 sensory representation;
- improves golden accuracy by **1.47 percentage points**;
- incurs only **3.35%** more encoded input events on the full-test mean;
- reduces mean CSR synapse visits by about **60.88%**; and
- under the physically validated serialized timing relation, requires about **47.19%** as many architectural cycles per image on the accepted full-test workload means.

This result is specific to this trained model pair and the serialized FPGA-v1 datapath. It does not establish a universal property of sparse networks, but it directly demonstrates that **connection sparsity can dominate input-event count as a performance factor** in this implementation.

**MNIST-10A status: Complete.**

---

## Energy and power policy

No FPGA energy-per-inference number is claimed.

A board TDP, supply rating, or generic Vivado power estimate is not an acceptable substitute for a workload-specific measurement boundary. A future energy result would need to document measured rails/device scope, idle subtraction, measurement equipment/tool and sampling rate, workload duration/repetitions, PS/debug inclusion, and integration method.

The FPGA energy cell therefore remains **not measured** rather than presenting a speculative value.

---

## MNIST-10B — Native-sparse Loihi-facing comparison

The primary external numeric reference is Rueckauer et al., *NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi* (ACM JETC, DOI `10.1145/3501770`). `MNIST_10_LOIHI_SOURCES.md` records the source hierarchy and provenance of every admitted external metric.

The NxTF frame-based MNIST experiment reports a rate-coded converted four-layer CNN with approximately 4k neurons and 7k shared parameters, mapped to **14 Loihi neurocores** and run for **100 algorithmic time steps/sample**. The reported Loihi result is **0.79% error (99.21% accuracy), 0.66 mJ/sample, 6.65 ms/sample, and 4.38 µJ·s EDP**.

### Thesis-facing side-by-side table

| Quantity | FPGA native-sparse | NxTF Loihi MNIST | Comparison status |
| --- | ---: | ---: | --- |
| Dataset/input image | MNIST 28x28 | MNIST 28x28 | Directly aligned at source-image level |
| Accuracy | **91.71%** | **99.21%** | Numeric context; different models/training |
| Computational neurons | 10 output neurons | ~4k neurons | Not matched |
| Stored/shared weights | 4,086 stored synapses | ~7k shared parameters | Not equivalent representations |
| Presentation length | 16 ticks | 100 algorithmic time steps | Not matched |
| PL/model latency | **0.339256 ms/image** full-test mean, project-derived from physically validated relation | **6.65 ms/sample** measured | Side-by-side context only; no speedup ratio claimed |
| Energy/inference | **not measured** | **660 µJ/sample** measured | No FPGA energy comparison claimed |
| Hardware | K26 FPGA, serialized FPGA-v1 core | Loihi neuromorphic ASIC | Fundamentally different implementation |
| Training | direct surrogate SNN + prune/fine-tune + project quantization | ANN training + rate-based SNN conversion | Not matched |

The latency values must **not** be divided and reported as an architectural speedup. The workload graphs, neuron counts, timestep counts, precision/mapping, training methods, and measurement implementations differ.

For Loihi-1 chip facts, the project uses Davies et al., *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning* (IEEE Micro, DOI `10.1109/MM.2018.112130359`) as the primary authority. The source registry also preserves later secondary cross-checks and explicitly records conflicting copied-table fields rather than silently adopting them.

**MNIST-10B status: Complete.**

---

## MNIST-10C — Cropped-dense interpretation

Cropped-dense is not the primary Loihi comparator because it changes the sensory representation from 28x28 MNIST to a 20x20 center crop.

Its value is as a controlled FPGA-v1 hardware-fit baseline: under essentially the same stored-synapse ceiling it retains dense input-to-output connectivity, whereas native-sparse retains full sensory resolution and uses sparse connectivity. The pair therefore provides a cleaner internal architecture/application tradeoff than either profile can provide against an unmatched external workload.

**MNIST-10C status: Complete.**

---

## Evidence classes used in the thesis

MNIST-10 keeps four evidence classes separate:

| Evidence class | Examples |
| --- | --- |
| Direct project measurement | archived 64 physical MNIST tick-cycle measurements; physical spike-count/prediction checks |
| Project-derived metric | 10,000-image mean cycles/latency from measured workload counts using the physically validated cycle equation; logical deployment bits |
| Primary external measurement | NxTF Loihi MNIST accuracy, energy, latency, core mapping, timestep count |
| Secondary/qualitative context | secondary utilized-area normalization; Loihi-2 architecture context |

A derived value may be tightly constrained and experimentally validated without becoming a direct measurement of every image in the 10,000-image test set.

---

## Tooling and provenance

```text
mnist_app/characterization.py
mnist_app/characterization_runtime.py
mnist_app/characterization_evidence.py
scripts/build_characterization_baseline.py
scripts/characterize_fpga.py
scripts/archive_mnist_10_evidence.py
tests/test_characterization.py
tests/test_characterization_evidence.py
docs/MNIST_10_CHARACTERIZATION.md
docs/MNIST_10_LOIHI_SOURCES.md
```

Generated full-test baseline:

```text
applications/mnist/build/mnist-10/characterization_baseline.json
```

Accepted source-controlled physical evidence:

```text
applications/mnist/evidence/mnist-10/physical-timing-v1/
```

---

## Closure status

The scientific and hardware characterization gates for **MNIST-10A, MNIST-10B, and MNIST-10C are complete**. No additional FPGA experiment is required for the milestone as currently scoped.

Before merging the parent MNIST-10 branch, perform one final application regression run after the evidence archival/documentation updates:

```text
pytest applications/mnist/tests -q
```

If that passes, the parent **MNIST-10** can be marked Complete and merged without any additional physical run.
