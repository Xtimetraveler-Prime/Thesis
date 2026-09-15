# MNIST-10 Characterization and Loihi Comparison

**Status:** In progress — internal full-test workload baseline and Loihi source registry implemented; direct MNIST physical timing validation and final comparison pending

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

The following values come directly from the frozen `mnist-v1` accepted full 10,000-image FPGA-v1 golden evaluation. They are not estimates from the 30-image physical conformance corpus.

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

The internal comparison is especially informative because the two profiles use essentially the same physical synapse ceiling and exactly the same FPGA core implementation.

Native-sparse is **+1.47 percentage points** more accurate while generating only **3.35% more input events**. More importantly, sparse row structure reduces actual synaptic work dramatically: native-sparse performs only **39.12%** as many CSR synapse visits per image as cropped-dense. Its mean output spike count is also about **78.01%** of cropped-dense.

This is why raw input-event count alone is not a sufficient performance proxy for the FPGA architecture. One input axon event may traverse a long dense CSR row or a short/empty sparse row.

### Logical frozen deployment footprint

`characterization.py` also records a profile-attributable logical static-memory footprint using the frozen word schemas:

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

These numbers are useful for comparing the two frozen application images, but they are **not** FPGA BRAM utilization. They intentionally exclude fixed-capacity event/recurrent buffers, core control logic, HLS logic, VIO/debug logic, implementation padding, and bitstream overhead. Routed Vivado utilization must remain a separate device-level metric.

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

Host Python execution, TensorFlow loading/encoding, Vivado Hardware Manager, JTAG, VIO writes/reads, JSON serialization, and comparison time are **not** architectural inference latency.

M12.5 physically isolated the no-route FPGA-v1 costs as:

```text
quiescent tick cycles = 16 * neuron_count + 10
external input event  = 4 additional cycles/event
CSR synapse visit     = 4 additional cycles/visit
```

Both accepted MNIST profiles have ten neurons and zero recurrent routes. Therefore the currently implemented full-test timing model is:

```text
cycles/image =
    16 ticks * (16*10 + 10)
    + 4 * input_events/image
    + 4 * CSR_synapse_visits/image
```

Applying that model to the full 10,000-image workload means gives:

| Profile | Model-derived cycles/image | Model-derived PL latency @100 MHz | Model-derived images/s |
| --- | ---: | ---: | ---: |
| cropped-dense | **71,893.61** | **0.718936 ms** | **1,390.94** |
| native-sparse | **33,925.63** | **0.339256 ms** | **2,947.62** |

The modeled native/cropped cycle ratio is **0.4719**.

### Important evidence label

These image-level timing values are currently **model-derived from a physically measured M12.5 timing decomposition**. They are not yet labeled as direct MNIST physical latency measurements.

MNIST-10A will not close until a passive PL-cycle measurement on the MNIST application independently spot-checks the model. The intended physical timing instrument must remain outside the computational datapath and must not alter neuron, synapse, arithmetic, event-order, or decoding semantics.

---

## Energy and power policy

No FPGA energy-per-inference number is currently claimed.

A board TDP, supply rating, or generic Vivado power estimate is not an acceptable substitute for a workload-specific measured energy boundary. If a defensible measurement can be made later, the documentation must state:

- what rails/device scope were measured;
- idle subtraction policy;
- sampling equipment/tool and rate;
- workload duration/repetitions;
- whether PS/JTAG/debug power is included; and
- how energy per inference is integrated.

If such a measurement is not completed, the FPGA energy cell in the final Loihi comparison will remain **not measured** rather than presenting a speculative value.

---

## MNIST-10B Loihi-facing comparison policy

The primary external numeric reference is Rueckauer et al., *NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi* (ACM JETC, DOI `10.1145/3501770`). The source registry records the exact role of this and all supporting sources.

The NxTF MNIST benchmark reports a rate-coded converted four-layer CNN on Loihi with approximately 4k neurons / 7k shared parameters, mapped to 14 neurocores and run for 100 algorithmic time steps per sample. The reported Loihi result is 0.79% error (99.21% accuracy), 0.66 mJ/sample, and 6.65 ms/sample.

Those numbers are valid published Loihi measurements, but they are **not workload matched** to this project's native-sparse network:

| Dimension | FPGA native-sparse | NxTF Loihi MNIST |
| --- | --- | --- |
| Dataset | MNIST 28x28 | MNIST 28x28 |
| Network | 784 input axons -> 10 output neurons | four-layer CNN |
| Stored/shared weights | 4,086 stored synapses | about 7k shared parameters |
| Neurons | 10 computational output neurons in this app | about 4k |
| Presentation | 16 ticks | 100 algorithmic time steps |
| Training path | direct surrogate-trained SNN, prune/fine-tune, project quantization | trained ANN -> rate-based SNN conversion |
| Hardware | serialized FPGA-v1 core on K26 | Loihi neuromorphic ASIC |
| Timing boundary | PL architectural cycles only | Loihi benchmark execution time |
| Energy | not measured | 0.66 mJ/sample reported |

Consequently, MNIST-10 may compare the values side-by-side as **cross-system literature context**, but it will not report a simple FPGA/Loihi latency or energy ratio as though it were an architecture-only speedup.

### Source hierarchy

The comparison uses this hierarchy:

1. primary workload paper for its own benchmark numbers;
2. primary Loihi architecture paper for chip specifications;
3. later comparison tables only for cross-checks or clearly labeled secondary quantities.

For example, later papers reproduce the NxTF 99.21% / 660 µJ / 6.65 ms result. One secondary table reports a core count that conflicts with NxTF's own statement that the MNIST CNN maps to 14 neurocores. MNIST-10 therefore retains the primary-paper value and documents the discrepancy rather than silently copying the secondary table.

See `MNIST_10_LOIHI_SOURCES.md` for the complete source registry, DOI/URL list, admitted metrics, and rejected/secondary fields.

---

## MNIST-10C cropped-dense interpretation

Cropped-dense should not be presented as the main Loihi comparator because it changes the sensory representation from the original 28x28 MNIST image to a 20x20 center crop.

Its value is internal: under essentially the same FPGA synapse ceiling it preserves dense input-to-output connectivity while native-sparse preserves full sensory resolution and uses sparse connectivity. The measured accuracy/workload results therefore give a controlled architecture-design comparison inside this FPGA implementation.

---

## Current tooling

```text
mnist_app/characterization.py
scripts/build_characterization_baseline.py
tests/test_characterization.py
docs/MNIST_10_CHARACTERIZATION.md
docs/MNIST_10_LOIHI_SOURCES.md
```

Generate the current internal baseline with:

```text
python applications/mnist/scripts/build_characterization_baseline.py
```

Output:

```text
applications/mnist/build/mnist-10/characterization_baseline.json
```

The JSON intentionally carries evidence labels (`measured-software-golden`, `derived-from-frozen-storage-schema`, and `model-derived-from-M12.5-physical-decomposition`) so later tables cannot accidentally erase the distinction between measurement and derivation.

---

## Remaining gates

MNIST-10 is complete only after:

1. characterization unit tests and the full application pytest suite pass;
2. the full-test internal baseline is reproducibly generated from `mnist-v1`;
3. a passive MNIST PL-cycle measurement validates the timing model on physical K26 execution;
4. final internal profile timing/resource interpretation is assembled;
5. Loihi comparison numbers are traceable to `MNIST_10_LOIHI_SOURCES.md`;
6. all non-matched workload dimensions are stated beside the external comparison;
7. no unsupported FPGA energy claim is introduced; and
8. the final thesis-facing comparison separates direct measurements, derived metrics, external literature values, and qualitative-only context.
