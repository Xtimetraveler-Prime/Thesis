# MNIST-10 Loihi Comparison Source Registry

## Purpose

This file is the provenance authority for external Loihi metrics used in the MNIST-10 comparison. A number must not enter the thesis comparison table unless its source, experimental context, and comparability status are recorded here.

The comparison deliberately distinguishes:

1. **primary benchmark measurements** reported by the authors who ran the Loihi workload;
2. **primary architecture specifications** reported by Intel/Loihi authors;
3. **secondary comparison tables** that reproduce or normalize other published results; and
4. **qualitative context** that is not used as a numeric FPGA-vs-Loihi benchmark.

When a secondary table conflicts with a primary paper, the primary paper controls.

---

## S1 — Loihi 1 architecture authority

**Citation**

Mike Davies, Narayan Srinivasa, Tsung-Han Lin, et al., “Loihi: A Neuromorphic Manycore Processor with On-Chip Learning,” *IEEE Micro*, vol. 38, no. 1, pp. 82–99, 2018.

- DOI: https://doi.org/10.1109/MM.2018.112130359
- IEEE: https://ieeexplore.ieee.org/document/8259423

**Use in this project**

Primary source for Loihi-1 architectural context, including:

- 14 nm process;
- 60 mm² die area;
- 128 neuromorphic cores plus three embedded x86 cores;
- asynchronous network-on-chip / asynchronous implementation methodology;
- event/spike-based core communication;
- Loihi neuron/state/learning architecture context.

The paper also reports a pre-silicon supervised-STDP MNIST example with ten classifier neurons and approximately 96% accuracy. That example is structurally interesting because it uses ten output neurons, but it is **not** used as the primary energy/latency comparison because it is described as a pre-silicon validation workload rather than the later measured Loihi-silicon NxTF benchmark.

**Comparability classification:** architecture facts = direct context; pre-silicon MNIST accuracy = qualitative/structural only.

---

## S2 — Loihi programming/MNIST workflow context

**Citation**

Chit-Kwan Lin, Andreas Wild, Gautham N. Chinya, Yongqiang Cao, Mike Davies, Daniel M. Lavery, and Hong Wang, “Programming Spiking Neural Networks on Intel’s Loihi,” *Computer*, vol. 51, no. 3, pp. 52–61, 2018.

- DOI: https://doi.org/10.1109/MC.2018.157113521
- IEEE: https://ieeexplore.ieee.org/document/8303802

**Use in this project**

Primary source for early Loihi programming/toolchain and MNIST workflow context. It is useful for describing how networks are specified, compiled, and executed on Loihi, but MNIST-10 does not take the headline latency/energy reference numbers from this source.

**Comparability classification:** qualitative software/workflow context.

---

## S3 — Primary Loihi MNIST performance benchmark

**Citation**

Bodo Rueckauer, Connor Bybee, Ralf Goettsche, Yashwardhan Singh, Joyesh Mishra, and Andreas Wild, “NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi,” *ACM Journal on Emerging Technologies in Computing Systems*, vol. 18, no. 3, 2022.

- DOI: https://doi.org/10.1145/3501770
- Author preprint: https://arxiv.org/abs/2101.04261

**This is the primary numeric source for the Loihi-facing MNIST benchmark.**

For the frame-based MNIST experiment, the paper reports:

- network: converted four-layer CNN;
- original ANN error: 0.74%;
- Loihi SNN error: **0.79%**, corresponding to **99.21% accuracy**;
- approximately **4k neurons** and **7k shared parameters** in the table;
- mapping: **14 Loihi neurocores**;
- presentation: **100 algorithmic time steps per sample**;
- Loihi inference energy: **0.66 mJ/sample = 660 µJ/sample**;
- Loihi inference delay: **6.65 ms/sample**;
- energy-delay product: **4.38 µJ·s**.

The paper explicitly notes that its model is a rate-coded ANN-to-SNN conversion and discusses why results from other platforms are not always directly comparable.

**Important limitation for this thesis:** our native-sparse FPGA model is not the same network. It uses 784 input axons, ten output neurons, 4,086 stored synapses, no hidden layer, and 16 presentation ticks. Therefore the NxTF numbers are a **cross-system literature reference**, not a claim that the FPGA is faster/slower or more/less energy efficient under matched conditions.

**Comparability classification:** dataset aligned (MNIST); hardware and broad rate-code paradigm aligned; topology, training, parameter count, timestep count, precision, mapping, and measurement method not matched.

---

## S4 — Secondary cross-check: 2024 SENECA comparison table

**Citation**

Yingfu Xu et al., “Optimizing event-based neural networks on digital neuromorphic architecture: a comprehensive design space exploration,” *Frontiers in Neuroscience*, vol. 18, 2024.

- DOI: https://doi.org/10.3389/fnins.2024.1335422
- Full text: https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2024.1335422/full

Table 4 reproduces a Loihi MNIST row attributed to Rueckauer et al. (2022):

- accuracy: **99.21%**;
- inference energy: **660 µJ**;
- inference time: **6.65 ms**;
- utilized silicon area: **5.74 mm²**.

The first three numbers agree with S3 and are used only as a cross-check. The **5.74 mm²** utilized-area figure is available from this secondary comparison table; if area is shown in the thesis, it must be labeled as a secondary-source utilized-core-area estimate, not as a direct NxTF paper measurement and not as Loihi chip die area.

**Comparability classification:** secondary normalization/cross-check only.

---

## S5 — Secondary table with a known configuration inconsistency

**Citation**

Y. Yu et al., “A TTFS-based energy and utilization efficient neuromorphic CNN accelerator,” *Frontiers in Neuroscience*, 2023.

- DOI: https://doi.org/10.3389/fnins.2023.1121592
- Full text: https://www.frontiersin.org/journals/neuroscience/articles/10.3389/fnins.2023.1121592/full

Its Table 6 contains a Loihi MNIST row with 99.21% accuracy and 660 µJ/frame, consistent with the widely reproduced Loihi result, but the table lists **128 cores**, whereas the primary NxTF paper states that its MNIST CNN maps to **14 neurocores**.

Because of that discrepancy, MNIST-10 **does not use the core-count field from this secondary table**. This source is retained in the registry specifically to document why copied comparison tables are not treated as authorities over the primary benchmark paper.

**Comparability classification:** secondary context only; conflicting fields rejected in favor of S3.

---

## S6 — Loihi 2 architecture context

**Citation / source**

Intel, “Taking Neuromorphic Computing to the Next Level with Loihi 2,” technology brief, 2021.

- Intel PDF: https://download.intel.com/newsroom/2021/new-technologies/neuromorphic-computing-loihi-2-brief.pdf

The brief describes Loihi 2 as retaining a fully asynchronous neuromorphic-core architecture, with up to 128 neuron cores, six embedded microprocessor cores, up to 8,192 neurons per neuromorphic core, and up to 128 KB synaptic memory per core, along with graded spike payloads and programmable neuron models.

**Use in this project**

Loihi 2 is used only for architectural/state-of-the-field context unless a workload-matched published Loihi-2 MNIST measurement is identified and separately entered in this registry. **No Loihi-2 latency, energy, or MNIST accuracy value is currently used in the FPGA comparison.**

**Comparability classification:** architecture context only.

---

## S7 — Loihi 2 research context

**Citation**

Garrick Orchard, E. Paxon Frady, Daniel Ben Dayan Rubin, et al., “Efficient Neuromorphic Signal Processing with Loihi 2,” 2021.

- arXiv: https://arxiv.org/abs/2111.03746

This source demonstrates Loihi-2 programmable neuron capabilities and signal-processing workloads. It is useful for describing how Loihi 2 expands the model space beyond Loihi 1, but it is **not an MNIST benchmark source** and contributes no numeric value to the MNIST comparison table.

**Comparability classification:** qualitative Loihi-2 research context.

---

## Metric-source map for the thesis table

| Loihi metric | Value currently admitted | Authority | Status |
| --- | ---: | --- | --- |
| MNIST accuracy | 99.21% | S3 NxTF | Primary measured benchmark |
| MNIST inference energy | 660 µJ/sample | S3 NxTF | Primary measured benchmark |
| MNIST inference delay | 6.65 ms/sample | S3 NxTF | Primary measured benchmark |
| MNIST EDP | 4.38 µJ·s | S3 NxTF | Primary measured/derived benchmark |
| Neurocores used by NxTF MNIST | 14 | S3 NxTF | Primary mapping result |
| Algorithmic time steps/sample | 100 | S3 NxTF | Primary workload definition |
| Approx. neurons / shared params | 4k / 7k | S3 NxTF | Primary table context |
| Utilized silicon area | 5.74 mm² | S4 Xu et al. | Secondary estimate; label as such |
| Loihi process / chip architecture | 14 nm / 128 neuromorphic cores | S1 Davies et al. | Primary architecture specification |
| Loihi chip die area | 60 mm² | S1 Davies et al. | Primary architecture specification; **not** utilized-area metric |
| Loihi-2 architecture | see S6/S7 | Intel / Orchard et al. | Context only; no MNIST performance claim |

---

## Comparison rules

1. **Do not divide FPGA and Loihi latency/energy values and call the ratio an architectural speedup/efficiency advantage unless the workloads are matched.** The current NxTF workload is not matched.
2. Dataset equality alone is insufficient. Record topology, input representation, coding, timestep count, training/conversion method, precision, parameter/synapse count, and measurement boundary.
3. The native-sparse 28x28 profile is the primary Loihi-facing FPGA profile because it preserves the original MNIST spatial representation. The cropped-dense 20x20 profile is an internal FPGA hardware-fit baseline.
4. FPGA JTAG/VIO wall time is never compared to Loihi inference delay. Only PL architectural execution time may appear in a latency column.
5. Do not report FPGA energy per inference until the measurement boundary and method are defensible and documented. If no such measurement is completed, leave FPGA energy as “not measured” rather than estimating it from board TDP.
6. Secondary tables may be used to cross-check or add clearly labeled secondary quantities, but primary papers control their own workload definitions and measured values.
