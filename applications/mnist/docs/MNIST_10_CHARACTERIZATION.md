# MNIST-10 Characterization and Loihi Comparison

**Status:** Physical timing validation accepted; compact evidence archival and final regression confirmation pending before milestone closure

## Purpose

MNIST-10 turns the already validated application into a characterization result without weakening the correctness boundary established by MNIST-07 through MNIST-09.

The work is divided into three parts:

- **MNIST-10A:** compare `cropped-dense` and `native-sparse` on the same FPGA-v1 architecture;
- **MNIST-10B:** place `native-sparse` beside published Intel Loihi MNIST results with explicit workload/method caveats; and
- **MNIST-10C:** interpret `cropped-dense` as a controlled FPGA hardware-fit baseline rather than the main Loihi-facing result.

External Loihi sources and metric provenance are maintained separately in `MNIST_10_LOIHI_SOURCES.md`. No external number is admitted to the comparison table without a source and comparability classification.

---

## MNIST-10A internal FPGA comparison

### Accepted full-test application metrics

The following values come directly from the frozen `mnist-v1` accepted full 10,000-image FPGA-v1 golden evaluation. They are not estimates from the deliberately selected 30-image physical conformance corpus.

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

The internal comparison is especially informative because the two profiles use essentially the same stored-synapse ceiling and exactly the same FPGA core implementation.

Native-sparse is **+1.47 percentage points** more accurate while generating only **3.35% more input events**. Sparse row structure reduces actual synaptic work much more strongly: native-sparse performs only **39.12%** as many CSR synapse visits per image as cropped-dense. Its mean output spike count is about **78.01%** of cropped-dense.

This demonstrates why raw event count is not an adequate performance proxy for this architecture. One axon event may traverse a long dense CSR row, a short sparse row, or an empty row.

### Logical frozen deployment footprint

`characterization.py` records a profile-attributable logical static-memory footprint using the frozen word schemas:

```text
10 neuron configs       x 128 bits
10 initial states       x  64 bits
2 weight formats        x  16 bits
stored synapses         x  32 bits
(input_axons + 1) rows  x  32 bits
11 empty route rows     x  32 bits
```

This produces:

| Profile | Logical static deployment data |
| --- | ---: |
| cropped-dense | **139,712 bits = 17.055 KiB** |
| native-sparse | **158,176 bits = 19.309 KiB** |

These are application-image storage quantities, **not FPGA BRAM utilization**. They exclude fixed-capacity event/recurrent buffers, control logic, HLS logic, VIO/debug logic, implementation padding, and bitstream overhead.

---

## Architectural timing definition

MNIST-10 inherits the physically validated M12.5 timing boundary:

```text
architectural tick latency = PL ap_clk cycles
from accepted tick_start
through observed outer-core tick_done
```

At the frozen K26 implementation target:

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

Both accepted MNIST profiles have ten neurons and zero recurrent routes. Therefore the full-test timing model is:

```text
cycles/image =
    16 ticks * (16*10 + 10)
    + 4 * input_events/image
    + 4 * CSR_synapse_visits/image
```

Applying that relation to the accepted full-test workload means gives:

| Profile | Model-derived cycles/image | Model-derived PL latency @100 MHz | Model-derived images/s |
| --- | ---: | ---: | ---: |
| cropped-dense | **71,893.61** | **0.718936 ms** | **1,390.94** |
| native-sparse | **33,925.63** | **0.339256 ms** | **2,947.62** |

The native/cropped modeled cycle ratio is **0.4719**.

### Direct MNIST physical timing validation

The model relation was then independently tested on the actual reusable MNIST application image using the passive M12.5-style PL cycle counter. The computational core, HLS neuron step, weight image, event ordering, and decoder semantics remained unchanged.

The accepted physical exercise covered the same two source images previously used to demonstrate arbitrary-image runtime operation, through both frozen profiles:

```text
cropped-dense, index 3
native-sparse,  index 3
cropped-dense, index 1
native-sparse,  index 1
```

For every run, the MNIST-10 validator required all of the following simultaneously:

1. physical output spike-count vector exactly equals the independent frozen Python golden vector;
2. physical decoded prediction equals the golden prediction;
3. exactly 16 ticks are committed;
4. physical input-event count agrees with the host request; and
5. the complete **16-element physical tick-cycle vector exactly equals** the independently predicted vector from `170 + 4*external_events + 4*CSR_synapse_visits`.

All four physical characterizations passed with no mismatches.

This changes the evidence status of the timing relation: the full 10,000-image averages above remain **model-derived workload averages**, but the underlying cycle equation is no longer merely extrapolated from M12.5 stress cases. It has now been directly and exactly spot-checked on two real MNIST schedules through each deployment profile.

The compact source-controlled evidence package is produced from the already accepted local results by:

```text
python applications/mnist/scripts/archive_mnist_10_evidence.py
```

The archive intentionally copies only the request, deterministic event schedule, independent timing expectation, physical result, exact comparison, hashes, and summary manifest. Vivado projects, bitstreams, logs, and other generated build products remain excluded.

---

## Final internal interpretation

The strongest application-level FPGA result is not simply that native-sparse has more input pixels. Under nearly the same stored-synapse limit, it simultaneously:

- preserves the original 28x28 sensory representation;
- improves golden accuracy by **1.47 percentage points**;
- incurs only **3.35%** more encoded input events;
- reduces mean CSR synapse visits by about **60.88%**; and
- under the physically validated serialized timing relation, requires about **47.19%** as many architectural cycles per image on the accepted full-test workload means.

That result is specific to this trained pair of models and this serialized FPGA-v1 architecture. It does not establish that sparse networks are universally faster or more accurate, but it does show that **connection sparsity can matter much more than event count alone** for the implemented CSR/event-processing datapath.

---

## Energy and power policy

No FPGA energy-per-inference number is claimed.

A board TDP, supply rating, or generic Vivado power estimate is not an acceptable substitute for a workload-specific measurement boundary. A future energy result would need to document measured rails/device scope, idle subtraction, measurement equipment/tool and sampling rate, workload duration/repetitions, PS/debug inclusion, and integration method.

If that experiment is not performed, the FPGA energy cell remains **not measured** rather than presenting a speculative number.

---

## MNIST-10B Loihi-facing comparison

The primary external numeric reference is Rueckauer et al., *NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi* (ACM JETC, DOI `10.1145/3501770`). `MNIST_10_LOIHI_SOURCES.md` records the source hierarchy and the provenance of every admitted external metric.

The NxTF frame-based MNIST experiment reports a rate-coded converted four-layer CNN with approximately 4k neurons and 7k shared parameters, mapped to 14 Loihi neurocores and run for 100 algorithmic time steps/sample. The reported Loihi result is **0.79% error (99.21% accuracy), 0.66 mJ/sample, 6.65 ms/sample, and 4.38 µJ·s EDP**.

### Thesis-facing side-by-side table

| Quantity | FPGA native-sparse | NxTF Loihi MNIST | Comparison status |
| --- | ---: | ---: | --- |
| Dataset/input image | MNIST 28x28 | MNIST 28x28 | Directly aligned at source-image level |
| Accuracy | **91.71%** | **99.21%** | Numeric context; different models/training |
| Computational neurons | 10 output neurons | ~4k neurons | Not matched |
| Stored/shared weights | 4,086 stored synapses | ~7k shared parameters | Not equivalent representations |
| Presentation length | 16 ticks | 100 algorithmic time steps | Not matched |
| PL/model latency | **0.339256 ms/image** full-test mean, model-derived from physically validated cycle relation | **6.65 ms/sample** measured | Side-by-side context only; no speedup ratio claimed |
| Energy/inference | **not measured** | **660 µJ/sample** measured | No FPGA energy comparison claimed |
| Hardware | K26 FPGA, serialized FPGA-v1 core | Loihi neuromorphic ASIC | Fundamentally different implementation |
| Training | direct surrogate SNN + prune/fine-tune + project quantization | ANN training + rate-based SNN conversion | Not matched |

The latency values must **not** be divided and reported as an architectural speedup. The workload graphs, neuron counts, timestep counts, precision/mapping, training methods, and timing/measurement implementations differ. NxTF itself explicitly discusses the difficulty of comparing results across dissimilar neuromorphic implementations.

### Loihi architecture context

For Loihi-1 chip facts, the project uses Davies et al., *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning* (IEEE Micro, DOI `10.1109/MM.2018.112130359`) as the primary authority. Loihi is reported as a **60 mm², 14 nm chip with 128 neuromorphic cores plus three embedded x86 cores**.

A later SENECA comparison table reproduces the NxTF 99.21%, 660 µJ, and 6.65 ms values and gives **5.74 mm²** as utilized silicon area for that Loihi row. If used, that value is labeled a **secondary utilized-core-area estimate**, not Loihi die area and not a direct NxTF measurement.

`MNIST_10_LOIHI_SOURCES.md` also records secondary-source inconsistencies instead of silently copying them. In particular, a later comparison table lists 128 cores for the NxTF-like Loihi MNIST row, while the primary NxTF paper explicitly states that this MNIST CNN maps to **14 neurocores**. The primary workload paper therefore controls.

---

## MNIST-10C cropped-dense interpretation

Cropped-dense is not the primary Loihi comparator because it changes the sensory representation from 28x28 MNIST to a 20x20 center crop.

Its value is as a controlled FPGA-v1 hardware-fit baseline: under essentially the same stored-synapse ceiling it retains dense input-to-output connectivity, whereas native-sparse retains full sensory resolution and uses sparse connectivity. The pair therefore isolates an application design tradeoff inside the same FPGA core more cleanly than either can be compared against an unrelated external architecture.

---

## Evidence classes used in the thesis

MNIST-10 keeps four evidence classes separate:

| Evidence class | Examples |
| --- | --- |
| Direct project measurement | physical exact cycle vectors for the four accepted timing cases; routed core validation from earlier milestones |
| Project-derived metric | 10,000-image mean cycles/latency calculated from measured workload counts using the physically validated cycle equation; logical deployment bits |
| Primary external measurement | NxTF Loihi MNIST accuracy, energy, latency, core mapping, timestep count |
| Secondary/qualitative context | SENECA utilized-area normalization; Loihi-2 architectural context |

This distinction is intentional. A derived value may be highly constrained and experimentally validated without becoming a direct measurement of every image in the 10,000-image test set.

---

## Tooling

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

The generated full-test baseline is:

```text
applications/mnist/build/mnist-10/characterization_baseline.json
```

The accepted compact physical evidence is archived to:

```text
applications/mnist/evidence/mnist-10/physical-timing-v1/
```

---

## Remaining closure gates

The scientific/physical characterization gates are satisfied. Before MNIST-10 is merged, the remaining repository gates are:

1. archive the already-passed four physical timing outputs into the source-controlled evidence directory;
2. rerun the full application pytest suite including the new evidence-archive tests;
3. regenerate the characterization baseline once more from the frozen package; and
4. commit/push the evidence package so the exact physical cycle vectors and SHA-256 provenance are retained with the thesis repository.

No additional FPGA experiment is required unless the archive validator finds an inconsistency in the already-passed results.
