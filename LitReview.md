# Literature Review — Neuromorphic Architectural Modeling and FPGA Emulation

**Project:** FPGA-Based Loihi-Inspired Neuromorphic Architectural Digital Twin  
**Repository:** `Xtimetraveler-Prime/Thesis`  
**Prepared:** 2026-10-24  
**References consolidated:** 2026-11-04  
**Status:** Thesis literature-review research notes; not a systematic review.

## Scope and central distinction

This review surveys research relevant to an **FPGA-based architectural digital twin of a documented subset of Intel Loihi 1**, currently developed on the AMD/Xilinx Kria KV260 (K26 Zynq UltraScale+). The emphasis is on (1) software behavioral emulation, (2) multicore neuromorphic architectural emulation on FPGAs, (3) synchronization and hardware/software equivalence, and (4) hardware resource/performance experimentation.

**Important novelty boundary:** FPGA-based neuromorphic emulation, paired software/FPGA models, and even FPGA emulation of Loihi during Intel's design process are **not new by themselves**. The thesis must make a more specific, experimentally supported contribution. The candidate focus here is **Loihi-inspired, resource-constrained multicore execution using virtualized logical cores, DDR-backed contexts, board-local orchestration, and quantified paging/routing/synchronization costs**.

**Architectural fidelity boundary:** This project is an **architecture-level, Loihi-inspired twin**, not a bitwise reproduction of proprietary Loihi silicon, a transistor-level model, or a timing-exact/asynchronous clone. Its logical SNN advances in discrete timesteps with explicit barriers; physical FPGA circuitry is synchronous. Software/FPGA agreement demonstrates agreement with the project's own specified semantics, not full equivalence to Intel Loihi.

---

# A. Core literature: software emulation, FPGA architectures, and synchronization

## 1. Brian2Loihi (Michaelis et al., 2022)

**Full title:** *Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian*  
**Authors:** Carlo Michaelis, Andrew B. Lehr, Winfried Oed, Christian Tetzlaff  
**Venue:** *Frontiers in Neuroinformatics* 16:1015624 (2022)  
**DOI:** [10.3389/fninf.2022.1015624](https://doi.org/10.3389/fninf.2022.1015624)  
**Article:** https://www.frontiersin.org/journals/neuroinformatics/articles/10.3389/fninf.2022.1015624/full  
**Relevance:** High — software behavioral reference and fidelity methodology.

### Research objective

Make important Intel Loihi neural-computation features accessible in a software environment so investigators can develop and test algorithms without requiring direct access to the processor. The implementation is built on the Brian 2 simulation framework rather than being an FPGA hardware design.

### Contributions and demonstrated results

- Open-source Loihi emulator integrated with Brian 2 simulation workflows.
- Explicit modeling of Loihi neuron dynamics, state updates, spike emission, and aspects of synaptic computation.
- Attention to the integer-valued computational semantics required for Loihi-faithful results.
- Reproduction of single-neuron and recurrent-network behavior: the authors report **errorless software emulation in the tested non-plastic cases**.
- Modeling of learning/plasticity, with residual discrepancies related to stochastic rounding.
- Comparison against Loihi hardware to establish confidence in the modeled neural behavior.

### Boundaries and limitations relevant to this thesis

- The paper **explicitly excludes routing and mapping restrictions**, including restrictions on neuron and synapse capacity that depend on hardware configuration.
- It is primarily a behavioral/software emulator, not an architectural representation of a complete physical multicore Loihi mesh.
- It does not deliver an FPGA implementation, on-board scheduling, DDR-backed context virtualization, or measured FPGA memory/routing overhead.
- It does not prove full-system identity with all Loihi features; some functions are omitted and plasticity has rounding-related differences.

### Relationship to this project

Brian2Loihi establishes the value of a trusted, independently checked software representation of neural semantics. The thesis extends toward **architectural execution resources**: logical cores, core capacity constraints, axon/synapse addressing, event delivery, synchronization, and execution on the KV260.

In the earlier project direction, Brian2Loihi was considered a reference for validating neuron arithmetic and spike behavior, while the project's own Python model becomes the **golden model** for its FPGA implementation. That distinction matters: **a validated software model alone does not establish correctness of architectural routing or FPGA integration**.

### Candidate research opportunities (not claims of first-ever invention)

- Preserve precise model-defined neuron/event semantics while adding constrained multicore resource mapping.
- Measure physical effects of logical-core scheduling, resident-memory capacity, routing, and DDR context movement.
- Validate FPGA-visible state transitions and spike traces against an independently implemented oracle.


---

## 2. RANC (Mack et al., 2021)

**Full title:** *RANC: Reconfigurable Architecture for Neuromorphic Computing*  
**Authors:** Joshua Mack, Ruben Purdy, Kris Rockowitz, Michael Inouye, Edward Richter, Spencer Valancius, Nirmal Kumbhare, Md Sahil Hassan, Kaitlin Fair, John Mixter, Ali Akoglu  
**Venue:** *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, 40(11), 2265–2278 (2021); published online in November 2020  
**DOI:** [10.1109/TCAD.2020.3038151](https://doi.org/10.1109/TCAD.2020.3038151)  
**Preprint:** https://arxiv.org/abs/2011.00624  
**Relevance:** **Very high — among the closest direct precedents for this thesis.**

### Research objective

Create an accessible, configurable environment for **neuromorphic architecture exploration**, enabling designers to change processor parameters and evaluate hardware/software tradeoffs instead of being restricted to a fixed commercial ASIC.

### Contributions and demonstrated results

- Open-source ecosystem with **C++ software simulation and FPGA hardware emulation**.
- Configurable neuromorphic cores and parameters such as network organization, neuron/axon counts, and precision/behavior.
- Reproduces **IBM TrueNorth-like architectural behavior**, with validation against IBM's Compass simulation environment and published evidence.
- Supports experiments in architecture parameters and their consequences for application mapping and efficiency.
- FPGA study uses an **Alveo U250**, including post-route resource-use and throughput analysis for synthetic aperture radar classification and vector-matrix multiplication.
- Authors report a demonstrated emulation scale of approximately **259,000 distinct neurons and 73.3 million distinct synapses** in studied configurations.

### Why this paper is a serious prior-art challenge

RANC already demonstrates several ideas that might otherwise sound novel:

- Software model paired with FPGA emulator.
- Neuromorphic multicore organization and spike-based routing.
- Architectural configurability and hardware-level tradeoff studies.
- Reference-based verification of modeled processor behavior.
- Research using FPGAs to evaluate neuromorphic processor design choices.

**Do not claim that merely building a neuromorphic FPGA digital twin, using a golden model, or creating configurable multicore routing is unprecedented.**

### Differences and possible gaps relative to this thesis

- RANC's principal validated architectural target is **IBM TrueNorth**, not a source-backed subset of Intel Loihi 1.
- Its particular architecture, memory residency scheme, and experimental platform differ from this project's three-resident-slot, **DDR-backed virtual logical-core** execution strategy.
- This thesis explores how many **logical Loihi-inspired cores** can be executed on a limited number of **physical FPGA engines**, with explicit accounting of page-in/page-out and board-local scheduler overhead.
- The specific Loihi-style axon/synapse lookup, source-backed capacity constraints, discrete timestep semantics, and board-local runtime are central to this thesis's architectural contract.

These are **scoping distinctions, not proof that virtualization or memory paging has never been explored elsewhere**. More targeted prior-art searching is necessary before claiming a unique paging or virtualization mechanism.

### Relationship to this project

RANC is the strongest argument for treating the thesis as an **architectural engineering and experimental evaluation** contribution rather than an invention of FPGA neuromorphic emulation itself. The comparison should be explicit and respectful, not framed as RANC having failed to address a problem it did not intend to solve.

### Candidate research opportunities

- Reconstruct and validate a Loihi-inspired rather than TrueNorth-inspired execution contract.
- Quantify the cost of **logical-core virtualization and DDR-backed context residency**.
- Distinguish compute-engine execution, context transfers, routing/barrier processing, and end-to-end sample latency.
- Test scaling and occupancy effects using reproducible neural workloads on the KV260.


---

## 3. NeuroScale (Li, Imam & Manohar, 2025)

**Full title:** *A deterministic neuromorphic architecture with scalable time synchronization*  
**Authors:** Congyang Li, Nabil Imam, Rajit Manohar  
**Venue:** *Nature Communications* 16, article 10329 (published 24 November 2025)  
**DOI:** [10.1038/s41467-025-65268-z](https://doi.org/10.1038/s41467-025-65268-z)  
**Article:** https://www.nature.com/articles/s41467-025-65268-z  
**Relevance:** High — synchronization choices, deterministic execution, hardware/software comparison.

### Research objective

Develop **NeuroScale**, a neuromorphic architecture with local, decentralized time synchronization, and compare it with globally barrier-synchronized systems such as TrueNorth and Loihi.

### Contributions and demonstrated results

- Defines a scheme in which each core maintains/progresses its local simulated time using communication with connected cores rather than waiting for a system-wide timestep barrier.
- Uses distributed, event-driven synchronization while maintaining deterministic model behavior.
- Explores an asynchronous hardware design approach and corresponding FPGA prototyping methodology.
- Demonstrates matching spike timing among the **software reference model, hardware simulation, and FPGA prototype** for a tested network of **200 neurons across four cores**.
- Studies scaling with more cores using **detailed hardware simulation**; larger reported architectural scaling comparisons should **not** be presented as if they were all realized on large physical FPGA systems.
- Distinguishes *algorithmic/simulation time* from physical wall-clock time; this conceptual distinction is directly useful to this thesis.

### Boundaries and limitations relative to this thesis

- NeuroScale designs a **new synchronization architecture**; it does not attempt to reproduce a complete subset of original Intel Loihi hardware.
- Loihi-inspired resource-capacity mapping and this project's DDR-backed virtualization scheme are not its main questions.
- Its large-scale performance claims rely on simulations, while the documented deterministic FPGA demonstration is smaller.

These are differences in purpose and evaluation scope, not deficiencies in NeuroScale.

### Relationship to this project

This thesis's Loihi-inspired model uses **discrete algorithmic timesteps and a global synchronization/barrier discipline**. It is **not a physical asynchronous Loihi clone** merely because spike events are processed sparsely or because original Loihi uses asynchronous circuitry.

NeuroScale is most useful as a precedent for **a clearly posed architectural hypothesis with measured consequences**. For this thesis that might be: How much time and bandwidth are spent in computation, synchronization, routing, and context paging under increasing logical-core count or activity?

Replacing barriers with independent local-time execution would be a substantial future architectural experiment, not a feature already implemented or required for Loihi-faithful behavior.

### Candidate research opportunities

- Quantify synchronization/barrier cost in the chosen global-timestep architecture.
- Separate packet activity and barrier quiescence overhead from actual neuron arithmetic.
- Investigate scaling with logical-core count, event density, and physical residency constraints.
- Only if scope allows: compare alternative synchronization policies as a **modified architecture**, keeping such experiments separate from fidelity claims.


---

# B. Closely related supplementary sources

## 4. YANA (Pachideh et al., 2026)

**Full title:** *YANA: Bridging the Neuromorphic Simulation-to-Hardware Gap*  
**Authors:** Brian Pachideh, Sven Nitzsche, Moritz Neher, Jann Krausse, Carmen Weigelt, Klaus Knobloch, Victor Pazmino Betancourt, Juergen Becker  
**Status:** arXiv preprint posted 3 April 2026 (do not assume journal peer-review status)  
**Preprint:** https://arxiv.org/abs/2604.03432  
**Relevance:** High — closely related FPGA family, SNN event pipeline and deployability.

### What the researchers built

- **YANA (Yet Another Neuromorphic Accelerator)**: an open-source digital FPGA accelerator for spiking neural networks.
- Five-stage event-driven processing pipeline using temporal/spatial sparsity.
- Configurable point-to-point neuron connectivity, event preprocessing, and hardware-efficient leak updates via lookup tables.
- End-to-end emphasis on moving from simulation to deployable FPGA computation; integration with **Neuromorphic Intermediate Representation (NIR)**.
- Evaluation on the Spiking Heidelberg Digits dataset, including sparsity-dependent inference runtime.
- Deployed a core on **AMD Kria KR260 (K26 family)**, a particularly close hardware cousin of this project's KV260.
- Reported per-core configuration supports up to **2^10 = 1,024 neurons** and **2^17 = 131,072 synapses**; reported implementation uses **740 LUTs, 918 registers, 7 BRAMs, and 24 URAMs** for the cited configuration.

### Relevance and boundaries

YANA shows that a useful SNN accelerator can be engineered on essentially the same SoM family and provides nearby implementation/measurement practice. Its principal research claim is **efficient, accessible SNN acceleration**, not an architectural twin of Loihi 1 with Loihi-inspired capacities and explicit virtual-core semantics.


---

## 5. *Loihi Asynchronous Neuromorphic Research Chip* (Lines et al., 2018)

**Authors:** Andrew Lines, Prasad Joshi, Ruokun Liu, Steve McCoy, Jonathan Tse, Yi-Hsin Weng, Mike Davies  
**Venue:** *2018 24th IEEE International Symposium on Asynchronous Circuits and Systems (ASYNC)*  
**DOI:** [10.1109/ASYNC.2018.00018](https://doi.org/10.1109/ASYNC.2018.00018)  
**IEEE:** https://ieeexplore.ieee.org/document/8589981/  
**Relevance:** **Very high — primary Loihi implementation reference and explicit FPGA-emulation precedent.**

### What the Intel team documented

- Original **Loihi 1** processor with **128 neuron cores**, each supporting up to **1,024 neural units**.
- Asynchronous circuit implementation using communicating sequential processes and bundled-data pipelines.
- Internal event/spike processing and circuit methodology.
- **Pre-silicon verification included FPGA emulation**, alongside static timing analysis and gate-level simulation.
- FPGA emulation modified how the asynchronous pipeline controls advance: it preserved key logical features while not replicating physical timing precisely.

### Implications for the thesis

- **Important precedent:** The original Loihi designers themselves used FPGA emulation. Thus the argument cannot be that no one had emulated Loihi-related hardware with FPGAs.
- This thesis takes a different path: independently reconstructing a **publicly documented architectural subset** on an accessible KV260, not reproducing Intel's proprietary RTL, gate netlists, analog timing, or manufacturing implementation.
- Supports the distinction between **behavioral/architectural fidelity** and **physical timing / circuit fidelity**.
- Strong companion to Davies et al. (2018), *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning*, DOI [10.1109/MM.2018.112130359](https://doi.org/10.1109/MM.2018.112130359), which is a major source for core resources and functional architecture.


---

## 6. *FPGA Based Emulation Environment for Neuromorphic Architectures* (Valancius et al., 2020)

**Authors:** Spencer Valancius, Edward Richter, Ruben Purdy, Kris Rockowitz, Michael Inouye, Joshua Mack, Nirmal Kumbhare, Kaitlin Fair, John Mixter, Ali Akoglu  
**Venue:** *2020 IEEE International Parallel and Distributed Processing Symposium Workshops (IPDPSW)*, pp. 90–97  
**DOI:** [10.1109/IPDPSW50202.2020.00022](https://doi.org/10.1109/IPDPSW50202.2020.00022)  
**Preprint:** https://arxiv.org/abs/2004.06061  
**Relevance:** **Very high — earlier RANC-line FPGA work on a Zynq UltraScale+ MPSoC.**

### What the researchers built and evaluated

- Open-source FPGA-based environment for neuromorphic architecture exploration.
- **IBM TrueNorth-derived** reference architecture with configurable digital components.
- **Streaming-enabled implementation on a Zynq UltraScale+ MPSoC**, especially pertinent to the KV260/K26 project.
- Evaluation of resource usage, MNIST and vector-matrix multiplication tasks, and comparison to IBM Compass simulation outcomes.
- Shows how altering neuron behavior can improve application mapping and motivate new hypothetical hardware choices.

### Implications for the thesis

This is another **direct predecessor**, especially in hardware platform class. It makes generic claims about a configurable, validated, streaming-enabled neuromorphic FPGA architecture particularly weak as novelty statements. The thesis distinction must instead be evidenced through its specific **Loihi-inspired semantic contract; logical-to-physical core virtualization; DDR-backed contexts and board-local scheduling/routing; and rigorous physical, end-to-end cost decomposition**.


---

# C. Comparative positioning

| Paper / system | Primary focus | Software vs FPGA | Architecture targeted | Most relevant distinction from this thesis |
| --- | --- | --- | --- | --- |
| **Brian2Loihi (2022)** | Loihi neuron and learning behavior | Software, validated against Loihi hardware | Selected Loihi neural semantics | Excludes routing/mapping/resource constraints and FPGA deployment |
| **RANC (2021)** | Configurable neuromorphic architecture exploration | C++ simulator + FPGA emulator | Primarily TrueNorth-inspired | Already covers much of FPGA architectural emulation; thesis needs specific Loihi/virtualization measurements |
| **NeuroScale (2025)** | Deterministic local-time synchronization | Software, hardware simulation + FPGA proof | New proposed neuromorphic architecture | Studies synchronization architecture, not Loihi-like DDR-backed logical-core virtualization |
| **YANA (2026)** | Practical event-driven SNN accelerator | End-to-end software/hardware workflow on KR260 | Configurable SNN accelerator | Same hardware family, different goal from reproducing Loihi architecture |
| **Lines et al. (2018)** | Original Loihi hardware implementation | Original ASIC design + FPGA verification | Actual Intel Loihi | Original-owner pre-silicon FPGA emulation; not independent public-spec reproduction |
| **Valancius et al. (2020)** | FPGA-based neuromorphic architecture emulator | FPGA + modeling/verification | TrueNorth-inspired | Already demonstrates FPGA architecture emulation on Zynq UltraScale+ |
| **Intel Loihi architecture and compiler (2018–2022)** | Original architecture, runtime and resource-aware compilation | Published ASIC/compiler research | Original Loihi and NxTF | Authoritative architecture evidence; exact NxTF paper network not fully recovered from tutorial |
| **Catalyst N1 (2026)** | Open independent neuromorphic RTL/software architecture | RTL, CPU simulation, FPGA reproduction | Other Loihi-inspired architecture | Comparative prior art, not Loihi silicon ground truth |
| **Rao / Renner / Diehl & Cook** | Alternative SNN training and benchmark work | Source-backed studies | Loihi and non-Loihi | Reviewed as alternative workloads; not the adopted FPGA benchmark |
| **Eshraghian et al. (2023)** | SNN/surrogate-gradient training | Tutorial and research synthesis | General SNN | Methodological context, not the project's bit-exact hardware semantics |

## A credible research gap statement

**Not defensible as novelty:**
- "No previous work has emulated neuromorphic processors on FPGAs."
- "This is the first Loihi-related FPGA emulator."
- "Using Python to validate an FPGA neuromorphic architecture is new."
- "This FPGA implementation is asynchronous because it uses spikes."

**Potentially defensible, subject to a targeted exhaustive search and measured results:**
- "We investigate an independently specified **Loihi-1-inspired multicore architecture** on a resource-constrained embedded FPGA, distinguishing neural/architectural correctness from physical implementation choices."
- "We experimentally quantify how **logical-core virtualization, DDR-backed residency, board-local scheduling and spike routing** influence complete SNN inference latency, throughput, and potentially power/energy."
- "We provide reproducible verification across independently implemented golden-model and physical execution boundaries, with explicit acknowledgment of fidelity limits."

The claimed contribution may ultimately be a **carefully validated design-and-measurement case study**, not a never-before-used mechanism. This is a legitimate thesis contribution if the evaluation is rigorous and the interpretation remains limited to demonstrated evidence.

---

# D. Relationship to the project's current GitHub development

The project repository's published roadmap identifies **FPGA-v3** as the active direction and preserves v1/v2 as earlier baselines. Current status statements below reflect the repository documentation examined **as of 2026-10-24**, and should be rechecked before presenting new results.

**Relevant repository documentation:**

- [Root README](README.md)
- [v3 roadmap](Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md)
- [Loihi-1 architectural target contract](Loihi_Digital_Twin/v3/docs/LOIHI1_TARGET_SPEC.md)
- [P07-B handoff](Loihi_Digital_Twin/v3/docs/P07_B_NEXT_CHAT_HANDOFF_SEED.md)
- [Experimental roadmap](EXPERIMENTS.md)

### Core architectural approach

- Python golden model with defined Loihi-inspired neuron/event behavior.
- Logical multicore network with explicit core capacities, axon identifiers, synaptic storage and packet delivery semantics.
- Distinction between **logical neuromorphic cores** and the **FPGA's actual compute engines**.
- KV260 architecture uses the Zynq **Processing System (PS)** for runtime/scheduling/routing control, the **Programmable Logic (PL)** for neural/core execution, and K26 **DDR** for non-resident logical context storage.
- The accepted design direction uses **three resident logical-core context slots and one physical execution engine**; additional physical engines remain a deferred optimization.
- Discrete, global logical-timestep synchronization; event-driven network semantics are **not** equivalent to a physically asynchronous silicon datapath.

### What is demonstrated vs what must still be proved

- Earlier versions validated a Python/FPGA neural architecture baseline and smaller physical workflows.
- Accepted v3 work established DDR page movement and autonomous Cortex-A53 execution for representative physical workloads.
- A project-trained single-core MNIST path has a separate accepted physical baseline; do **not** conflate this with a scaled multicore result.
- The larger trained 784 → 1,000 → 10 SNN and its **27 logical core** mapping have host-side validation/packing results; **full physically accepted 27-core execution must be treated as pending until separately verified**.
- Physical end-to-end latency, throughput, energy, and board power claims require carefully distinguished measurements, not extrapolation from one dispatch or host simulations.
- Do not claim equivalence with original Loihi silicon, on-chip learning, original mesh timing, or physical asynchronous logic where these were not reproduced and tested.

### Potential experiments grounded in this architecture

1. **Functional correctness:** compare spike times, neuron states, packet deliveries, output classes, and final context images against independent model/oracle results.
2. **Logical-core virtualization:** vary logical-core counts and resident-slot pressure; measure page-ins/outs, DDR transfer bytes, engine occupancy, and context hit/miss behavior.
3. **Timing decomposition:** measure PL dispatch, PS scheduling, routing/barrier time, page-transfer time, total sample latency, and steady-state throughput separately.
4. **Traffic/scaling:** vary event density, recurrent connections, partitioning and mapping choices to observe communication and memory costs.
5. **Power/energy (after measurement contract):** distinguish idle vs active board power and measure energy/inference using appropriate real board telemetry.
6. **Future architecture variants (clearly labeled):** compare scheduling or synchronization strategies without silently altering what counts as Loihi fidelity.

### Possible central research question

> How faithfully can a resource-constrained FPGA system reproduce a defined subset of Intel Loihi 1's multicore execution semantics, and what latency, memory, routing, and energy tradeoffs arise when many logical neuromorphic cores share a smaller number of physical execution resources?

A narrower, hardware-measurable alternative:

> What are the dominant costs of DDR-backed logical-core virtualization during board-local execution of a Loihi-inspired multicore spiking neural network on the KV260?

Both formulations demand a *specific, reproducible evaluation*, not simply an implementation demonstration.

---



# E. Additional references recovered from the repository and project materials

The following sources were **cited or reviewed previously** in repository architecture contracts, M13 comparison work, P06 benchmark selection, P08 NxTF work, or project-attached notes. These are not newly reproduced thesis results. Each entry gives its **source trail**, including the distinction between adopted methodology, an independent comparison, and a rejected or deferred workload.

## 7. Loihi programming and compiler infrastructure (Lin et al., 2018)

**Title:** *Programming Spiking Neural Networks on Intel's Loihi*  
**Authors:** Chit-Kwan Lin, Andreas Wild, Gautham N. Chinya, Yongqiang Cao, Mike Davies, Daniel M. Lavery, Hong Wang  
**Venue:** *Computer* 51(3), 52–61 (2018)  
**DOI:** [10.1109/MC.2018.157113521](https://doi.org/10.1109/MC.2018.157113521)  
**Status:** Primary source on the programming environment, compiler, runtime, and Loihi execution targets.

The article documents how spiking models are programmed and deployed, helping distinguish a functional software model from actual processor resources. It is a programming/toolchain reference, not evidence for every proprietary internal circuit detail.

**Project provenance:** [M13.1 reference manifest](Loihi_Digital_Twin/v1/references/m13_1_reference_manifest.json); [M13.1 methodology](Loihi_Digital_Twin/v1/docs/M13_1_REFERENCE_BASELINE.md); [v3 Loihi-1 target specification](Loihi_Digital_Twin/v3/docs/LOIHI1_TARGET_SPEC.md).

## 8. Loihi survey and architectural context (Davies et al., 2021)

**Title:** *Advancing Neuromorphic Computing With Loihi: A Survey of Results and Outlook*  
**Authors:** Mike Davies et al.  
**Venue:** *Proceedings of the IEEE* 109(5), 911–934 (2021)  
**DOI:** [10.1109/JPROC.2021.3067593](https://doi.org/10.1109/JPROC.2021.3067593)  
**Status:** Contextual Loihi survey.

Used in the source hierarchy of the Loihi-1 architectural specification to corroborate processor organization and spike/event behavior. The 2018 Davies and Lines original-design papers remain the preferred authorities for detailed original-chip claims.

**Project provenance:** [v3 Loihi-1 target specification](Loihi_Digital_Twin/v3/docs/LOIHI1_TARGET_SPEC.md).

## 9. NxTF compiler and SNN mapping (Rueckauer et al., 2022)

**Title:** *NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi*  
**Authors:** Bodo Rueckauer, Connor Bybee, Ralf Goettsche, Yashwardhan Singh, Joyesh Mishra, Andreas Wild  
**Venue:** *ACM Journal on Emerging Technologies in Computing Systems* 18(3) (2022)  
**DOI:** [10.1145/3501770](https://doi.org/10.1145/3501770)  
**Preprint:** https://arxiv.org/abs/2101.04261  
**Status:** Key mapping/benchmark reference.

NxTF contributes an especially relevant comparison for deep SNN placement, axon/synapse sharing, compression, and compiler limits. P08 investigated its frame-based MNIST experiment. **Important limitation:** the surviving Intel tutorial graph does not have the same reported parameter count or timestep setting as the particular paper benchmark. It must not be presented as proof that its precise training checkpoint and architecture have been recovered.

**Project provenance:** [v3 target specification](Loihi_Digital_Twin/v3/docs/LOIHI1_TARGET_SPEC.md); [P08 source audit](Loihi_Digital_Twin/v3/docs/P08_NXTF_SOURCE_AUDIT.md); [P08 comparison contract](Loihi_Digital_Twin/v3/docs/P08_MNIST_COMPARISON_CONTRACT.md).

## 10. Catalyst N1 (2026): independent neuromorphic RTL and simulator

**Publication record:** *Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with Programmable Synaptic Plasticity* (title recorded in the frozen M13 manifest; upstream variants exist).  
**Stable DOI:** [10.5281/zenodo.18727094](https://doi.org/10.5281/zenodo.18727094)  
**Source repository:** https://github.com/catalyst-neuromorphic/catalyst-n1  
**Status:** Independently implemented comparison system; **not** authoritative for undocumented Intel Loihi behavior.

M13 pinned Catalyst's RTL and software simulator, reproduced external regressions, and examined different neuron arithmetic, scheduling, and network-interface conventions. It also documented originality/attribution boundaries. Catalyst is crucial comparative prior art, but cross-model agreement does not establish Loihi silicon identity. Identify the DOI and pinned code revision when describing a particular version.

**Project provenance:** [M13.1 reference manifest](Loihi_Digital_Twin/v1/references/m13_1_reference_manifest.json); [M13.2 architectural crosswalk](Loihi_Digital_Twin/v1/docs/M13_2_ARCHITECTURAL_CROSSWALK.md); [source originality audit](AUDIT.md).

## 11. Spike-based LSTM with after-hyperpolarization (Rao et al., 2022)

**Title:** *A Long Short-Term Memory for AI Applications in Spike-based Neuromorphic Hardware*  
**Authors:** Arjun Rao, Philipp Plank, Andreas Wild, Wolfgang Maass  
**Venue:** *Nature Machine Intelligence* 4, 467–479 (2022)  
**DOI:** [10.1038/s42256-022-00480-w](https://doi.org/10.1038/s42256-022-00480-w)  
**Preprint:** https://arxiv.org/abs/2107.03992  
**Status:** Investigated **alternative**, not the adopted LIF MNIST checkpoint.

The paper demonstrates sequential computation using AHP/multicompartment spiking neurons on Loihi. P06 examined the author's released code and published sMNIST measurements, but did **not** establish that the released weight arrays were the exact checkpoint behind the reported silicon accuracy, latency, and energy. Those published metrics must remain contextual, not attributed to this FPGA implementation.

**Project provenance:** [P06 candidate audit](Loihi_Digital_Twin/v3/docs/P06_1_PAPER_CANDIDATE_AUDIT.md); [metric/attribution audit](Loihi_Digital_Twin/v3/docs/P06_1_PAPER_METRIC_AUDIT_AND_DECISION.md); [LSNN source manifest](Loihi_Digital_Twin/v3/docs/P06_1_LSNN_SOURCE_MANIFEST.json).

## 12. Backpropagation on spiking hardware (Renner et al., 2024)

**Title:** *The backpropagation algorithm implemented on spiking neuromorphic hardware*  
**Authors:** Alpha Renner, Forrest Sheldon, Anatoly Zlotnik, Louis Tao, Andrew Sornborger  
**Venue:** *Nature Communications* 15, 9691 (2024)  
**DOI:** [10.1038/s41467-024-53827-9](https://doi.org/10.1038/s41467-024-53827-9)  
**Author implementation:** https://github.com/lanl/spikingBackprop  
**Status:** Studied and not selected as the project benchmark.

The paper is relevant to on-chip learning, which is outside the present inference-oriented FPGA validation claim. P06 did not locate a published trained checkpoint corresponding to the paper's headline results in the inspected source tree, so no exact result-reproduction claim is warranted.

**Project provenance:** [P06 candidate audit](Loihi_Digital_Twin/v3/docs/P06_1_PAPER_CANDIDATE_AUDIT.md).

## 13. Unsupervised STDP-MNIST (Diehl & Cook, 2015)

**Title:** *Unsupervised learning of digit recognition using spike-timing-dependent plasticity*  
**Authors:** Peter U. Diehl, Matthew Cook  
**Venue:** *Frontiers in Computational Neuroscience* 9:99 (2015)  
**DOI:** [10.3389/fncom.2015.00099](https://doi.org/10.3389/fncom.2015.00099)  
**Author code and weights:** https://github.com/peter-u-diehl/stdp-mnist  
**Status:** Investigated non-Loihi training/benchmark alternative, not the selected workload.

This offered a source-backed SNN and released weights, but P06 flagged a reproducibility caveat: do not confuse a repository demonstration's reported accuracy with the paper's formally evaluated result, or silently transfer source metrics to a different FPGA implementation.

**Project provenance:** [P06 benchmark pivot](Loihi_Digital_Twin/v3/docs/P06_1_NON_LOIHI_BENCHMARK_PIVOT.md).

## 14. Surrogate-gradient SNN training (Eshraghian et al., 2023)

**Title:** *Training Spiking Neural Networks Using Lessons From Deep Learning*  
**Authors:** Jason K. Eshraghian et al.  
**Venue:** *Proceedings of the IEEE* 111(9), 1016–1054 (2023)  
**DOI:** [10.1109/JPROC.2023.3308088](https://doi.org/10.1109/JPROC.2023.3308088)  
**Companion tutorial:** https://snntorch.readthedocs.io/en/stable/tutorials/tutorial_5.html  
**Status:** **Adopted methodological background** for the project-trained compact and scaled LIF MNIST networks.

The paper supplies the training and spike-encoding context; the tutorial is an example training recipe. The project's actual input encoder, signed integer state transitions, reset behavior, and next-event-bank routing are separately specified and tested. **Do not** claim numerical equivalence to the tutorial or that the project's weights are the authors' published trained model.

**Project provenance:** [P06 two-track plan](Loihi_Digital_Twin/v3/docs/P06_TWO_TRACK_LIF_PLAN.md); [P06 benchmark pivot](Loihi_Digital_Twin/v3/docs/P06_1_NON_LOIHI_BENCHMARK_PIVOT.md).

## Non-paper resources and earlier exploration

These resources were also directly cited/inspected. They are **code or documentation links**, not additional peer-reviewed papers. Reference exact software revisions where conclusions depend on behavior.

| Resource | Link | Where and why it appeared |
| --- | --- | --- |
| Brian2Loihi | https://github.com/sagacitysite/brian2_loihi | Independent software validation for earlier milestones and M13; pinned version in M13.1. |
| Catalyst N1 code | https://github.com/catalyst-neuromorphic/catalyst-n1 | M13 independent CPU/RTL comparison. |
| Intel model source tree | https://github.com/intel-nrc-ecosystem/models | P06 LSNN author source and P08 NxTF tutorial; paper benchmark may differ. |
| SNN Toolbox | https://github.com/NeuromorphicProcessorProject/snn_toolbox | P08 historical ANN-to-SNN conversion evidence. |
| snnTorch repository and examples | https://github.com/jeshraghian/snntorch ; https://github.com/snntorch/Spiking-Neural-Networks-Tutorials | P06 training-method development, not a matching pretrained checkpoint. |
| Gymnasium MuJoCo environments | https://gymnasium.farama.org/environments/mujoco/ | Earlier exploratory biped/SNN actor–critic conversation, outside the active Loihi twin. |
| OpenAI Spinning Up: PPO | https://spinningup.openai.com/en/latest/algorithms/ppo.html | Earlier exploratory PPO/actor–critic discussion, outside FPGA architectural validation. |

The final two links appear in the attached project note `ML on FPGA with Vivado.txt`, not the repository's active specification. The attached note `Branch · THESIS DIRECTION SPELLED OUT.txt` discusses Brian2Loihi as an independent software validator of the project's own golden model. Neither note is itself a publication or an independent physical validation record.

**Authority and citation boundary:** Cite original Loihi publications (Davies 2018; Lines 2018; Lin 2018; Davies 2021) for Intel's documented architecture, Michaelis for Brian2Loihi's validated subset, Rueckauer for NxTF, and RANC/Valancius/YANA/NeuroScale/Catalyst for other implementations. Cite Eshraghian for the training methodology. This project's source contracts and captured physical evidence, not external papers, support statements about its own measured functionality.

---

# F. Consolidated bibliography

1. Michaelis, C., Lehr, A. B., Oed, W., & Tetzlaff, C. (2022). *Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian.* Frontiers in Neuroinformatics, 16, 1015624. https://doi.org/10.3389/fninf.2022.1015624
2. Mack, J., et al. (2021). *RANC: Reconfigurable Architecture for Neuromorphic Computing.* IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 40(11), 2265–2278. https://doi.org/10.1109/TCAD.2020.3038151 ; https://arxiv.org/abs/2011.00624
3. Li, C., Imam, N., & Manohar, R. (2025). *A deterministic neuromorphic architecture with scalable time synchronization.* Nature Communications, 16, 10329. https://doi.org/10.1038/s41467-025-65268-z
4. Pachideh, B., et al. (2026). *YANA: Bridging the Neuromorphic Simulation-to-Hardware Gap.* arXiv preprint arXiv:2604.03432. https://arxiv.org/abs/2604.03432
5. Lines, A., Joshi, P., Liu, R., McCoy, S., Tse, J., Weng, Y.-H., & Davies, M. (2018). *Loihi Asynchronous Neuromorphic Research Chip.* 2018 24th IEEE International Symposium on Asynchronous Circuits and Systems. https://doi.org/10.1109/ASYNC.2018.00018
6. Valancius, S., et al. (2020). *FPGA Based Emulation Environment for Neuromorphic Architectures.* Proceedings of 2020 IEEE IPDPS Workshops, 90–97. https://doi.org/10.1109/IPDPSW50202.2020.00022 ; https://arxiv.org/abs/2004.06061
7. Davies, M., et al. (2018). *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning.* IEEE Micro, 38(1), 82–99. https://doi.org/10.1109/MM.2018.112130359

8. Lin, C.-K., Wild, A., Chinya, G. N., Cao, Y., Davies, M., Lavery, D. M., & Wang, H. (2018). *Programming Spiking Neural Networks on Intel's Loihi.* Computer, 51(3), 52–61. https://doi.org/10.1109/MC.2018.157113521
9. Davies, M., et al. (2021). *Advancing Neuromorphic Computing With Loihi: A Survey of Results and Outlook.* Proceedings of the IEEE, 109(5), 911–934. https://doi.org/10.1109/JPROC.2021.3067593
10. Rueckauer, B., Bybee, C., Goettsche, R., Singh, Y., Mishra, J., & Wild, A. (2022). *NxTF: An API and Compiler for Deep Spiking Neural Networks on Intel Loihi.* ACM Journal on Emerging Technologies in Computing Systems, 18(3). https://doi.org/10.1145/3501770
11. Catalyst N1 (2026). *Catalyst N1: A 131K-Neuron Open Neuromorphic Processor with Programmable Synaptic Plasticity* (M13 manifest title; upstream versions differ). Zenodo. https://doi.org/10.5281/zenodo.18727094
12. Rao, A., Plank, P., Wild, A., & Maass, W. (2022). *A Long Short-Term Memory for AI Applications in Spike-based Neuromorphic Hardware.* Nature Machine Intelligence, 4, 467–479. https://doi.org/10.1038/s42256-022-00480-w
13. Renner, A., Sheldon, F., Zlotnik, A., Tao, L., & Sornborger, A. (2024). *The backpropagation algorithm implemented on spiking neuromorphic hardware.* Nature Communications, 15, 9691. https://doi.org/10.1038/s41467-024-53827-9
14. Diehl, P. U., & Cook, M. (2015). *Unsupervised learning of digit recognition using spike-timing-dependent plasticity.* Frontiers in Computational Neuroscience, 9, 99. https://doi.org/10.3389/fncom.2015.00099
15. Eshraghian, J. K., et al. (2023). *Training Spiking Neural Networks Using Lessons From Deep Learning.* Proceedings of the IEEE, 111(9), 1016–1054. https://doi.org/10.1109/JPROC.2023.3308088

**Use as research notes:** Primary-source assertions, comparison interpretations, and speculative thesis gaps are deliberately separated above. Before the final thesis literature-review chapter, expand the search for Loihi-specific FPGA emulators, virtualized multicore SNN accelerators, neuromorphic paging architectures, and rigorous power/energy methodologies; revise novelty claims accordingly.
