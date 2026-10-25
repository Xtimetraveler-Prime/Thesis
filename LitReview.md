# Literature Review — Neuromorphic Architectural Modeling and FPGA Emulation

**Project:** FPGA-Based Loihi-Inspired Neuromorphic Architectural Digital Twin  
**Repository:** `Xtimetraveler-Prime/Thesis`  
**Prepared:** 2026-10-24  
**Status:** Working literature-review notes for thesis research and committee presentation; not a systematic review.

## Scope and central distinction

This review surveys research relevant to an **FPGA-based architectural digital twin of a documented subset of Intel Loihi 1**, currently developed on the AMD/Xilinx Kria KV260 (K26 Zynq UltraScale+). The emphasis is on (1) software behavioral emulation, (2) multicore neuromorphic architectural emulation on FPGAs, (3) synchronization and hardware/software equivalence, and (4) hardware resource/performance experimentation.

**Important novelty boundary:** FPGA-based neuromorphic emulation, paired software/FPGA models, and even FPGA emulation of Loihi during Intel's design process are **not new by themselves**. The thesis must make a more specific, experimentally supported contribution. The candidate focus here is **Loihi-inspired, resource-constrained multicore execution using virtualized logical cores, DDR-backed contexts, board-local orchestration, and quantified paging/routing/synchronization costs**.

**Architectural fidelity boundary:** This project is an **architecture-level, Loihi-inspired twin**, not a bitwise reproduction of proprietary Loihi silicon, a transistor-level model, or a timing-exact/asynchronous clone. Its logical SNN advances in discrete timesteps with explicit barriers; physical FPGA circuitry is synchronous. Software/FPGA agreement demonstrates agreement with the project's own specified semantics, not full equivalence to Intel Loihi.

---

# A. Primary papers for the committee presentation

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

### Suggested slide bullets

**Software Emulation — Brian2Loihi (2022)**

- Developed a Loihi-focused emulator within Brian 2.
- Reproduced and validated neuron and SNN behavior against Loihi.
- Demonstrated high-fidelity software modeling of selected integer neural semantics.
- Explicitly excludes hardware routing and mapping constraints.
- **Thesis connection:** Carry validated neural behavior into a resource-constrained multicore FPGA execution architecture.

**Suggested spoken transition:** Emulating the computation performed by neurons is different from emulating the processor architecture responsible for executing, storing, and routing those computations.

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

### Suggested slide bullets

**FPGA Architectural Emulation — RANC (2021)**

- Open-source C++ simulator plus FPGA-based neuromorphic architecture emulator.
- Configurable cores, connectivity, neural behavior, and mapping parameters.
- Validated TrueNorth-oriented behavior against IBM Compass.
- Measured hardware resource usage and throughput; demonstrated large emulated neural configurations.
- **Closest precedent:** FPGA architectural emulation and hardware/software validation are already established.
- **Thesis connection:** Loihi-inspired semantics plus DDR-backed logical-core virtualization and measured board-local overheads.

**Suggested spoken transition:** Prior work shows that an FPGA can serve as a research platform for neuromorphic processor architectures; the question becomes which *specific* architectural choices and constraints to investigate.

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

### Suggested slide bullets

**Neuromorphic Synchronization — NeuroScale (2025)**

- Developed deterministic local-time synchronization across neuromorphic cores.
- Removed global timestep barriers from the proposed architecture.
- Demonstrated matching spike timing across software, simulation, and a four-core FPGA prototype.
- Used hardware simulation for larger-scale synchronization comparisons.
- **Thesis connection:** Explore measurable synchronization/routing costs in a Loihi-inspired execution architecture.

**Suggested spoken transition:** An FPGA emulator is useful not just for showing that neurons fire correctly, but for identifying which architecture-level mechanisms control performance and scalability.

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

**Suggested optional slide/reference note:** Contemporary K26-based neuromorphic accelerator; a practical hardware comparison, but do not equate its performance numbers with this thesis without matching workloads, clocking, precisions, boundaries, and resource accounting.

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

**Suggested optional slide/reference note:** Intel used FPGA emulation for verification of its own design; our research instead develops an independently specified, testable architectural twin with explicit constraints and hardware tradeoff measurements.

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

**Suggested optional slide/reference note:** Earlier FPGA-emulation environment on a Zynq UltraScale+; cite alongside RANC when discussing closest similar work.

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

# E. Presentation organization / slide notes

## Slide 4 — Brian2Loihi: software emulation

- What? Loihi neuron/state/plasticity emulator based on Brian 2.
- Established? Selected neural computations can be closely reproduced and validated in software.
- Leaves open relative to thesis? Mapping, routing, core resources, and physical hardware execution.
- Bridge: **From neural semantics to an executable multicore architecture.**

## Slide 5 — RANC: FPGA architectural emulation

- What? Software + FPGA configurable neuromorphic architecture framework.
- Established? Multicore hardware emulation and measured design tradeoffs already exist.
- Leaves open relative to thesis? This particular Loihi-inspired logical-core contract and DDR-backed embedded-platform virtualization.
- Mention Valancius et al. (2020) if asked about related Zynq hardware.
- Bridge: **From demonstrating emulation to testing distinctive architectural questions.**

## Slide 6 — NeuroScale: architectural experimentation

- What? Local asynchronous synchronization architecture.
- Established? Determinism can coexist with alternative synchronization mechanisms; FPGA/reference comparison is feasible.
- Leaves open relative to thesis? Physical costs of globally synchronized Loihi-inspired execution with virtualization and limited residency.
- Bridge: **From faithful execution to measurement and tradeoff analysis.**

## Backup sources

- **YANA (2026):** comparable KR260/K26 deployment; event-driven SNN accelerator rather than Loihi twin.
- **Lines et al. (2018):** Intel's Loihi implementation; FPGA emulation already used during original chip verification.
- **Valancius et al. (2020):** very close FPGA neuromorphic architecture research precedent, including Zynq UltraScale+.

---

# F. References / reading links

1. Michaelis, C., Lehr, A. B., Oed, W., & Tetzlaff, C. (2022). *Brian2Loihi: An emulator for the neuromorphic chip Loihi using the spiking neural network simulator Brian.* Frontiers in Neuroinformatics, 16, 1015624. https://doi.org/10.3389/fninf.2022.1015624
2. Mack, J., et al. (2021). *RANC: Reconfigurable Architecture for Neuromorphic Computing.* IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems, 40(11), 2265–2278. https://doi.org/10.1109/TCAD.2020.3038151 ; https://arxiv.org/abs/2011.00624
3. Li, C., Imam, N., & Manohar, R. (2025). *A deterministic neuromorphic architecture with scalable time synchronization.* Nature Communications, 16, 10329. https://doi.org/10.1038/s41467-025-65268-z
4. Pachideh, B., et al. (2026). *YANA: Bridging the Neuromorphic Simulation-to-Hardware Gap.* arXiv preprint arXiv:2604.03432. https://arxiv.org/abs/2604.03432
5. Lines, A., Joshi, P., Liu, R., McCoy, S., Tse, J., Weng, Y.-H., & Davies, M. (2018). *Loihi Asynchronous Neuromorphic Research Chip.* 2018 24th IEEE International Symposium on Asynchronous Circuits and Systems. https://doi.org/10.1109/ASYNC.2018.00018
6. Valancius, S., et al. (2020). *FPGA Based Emulation Environment for Neuromorphic Architectures.* Proceedings of 2020 IEEE IPDPS Workshops, 90–97. https://doi.org/10.1109/IPDPSW50202.2020.00022 ; https://arxiv.org/abs/2004.06061
7. Davies, M., et al. (2018). *Loihi: A Neuromorphic Manycore Processor with On-Chip Learning.* IEEE Micro, 38(1), 82–99. https://doi.org/10.1109/MM.2018.112130359

**Use as research notes:** Primary-source assertions, comparison interpretations, and speculative thesis gaps are deliberately separated above. Before the final thesis literature-review chapter, expand the search for Loihi-specific FPGA emulators, virtualized multicore SNN accelerators, neuromorphic paging architectures, and rigorous power/energy methodologies; revise novelty claims accordingly.
