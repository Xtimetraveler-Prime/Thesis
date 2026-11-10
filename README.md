# Thesis — Virtualized Neuromorphic Computing on FPGA

Research question: **What does virtualizing neural state cost on an FPGA, and when can event sparsity and locality reduce that cost?**

The current research program is [Neuromorphic Accelerator v1](Neuromorphic_Accelerator/v1/), an independently versioned FPGA-targeted spiking neural network (SNN) design. It builds on lessons from the frozen Loihi-inspired digital twin, **without inheriting its fixed 27-core structure or requiring Loihi silicon fidelity**. The AMD Kria KV260/K26 is the intended physical evaluation platform.

## Research goals

The two central questions are:

1. How much performance is sacrificed to virtualize a larger neural network, and how much of that cost can sparsity-aware execution recover?
2. How do DDR-backed virtualization and event-driven sparsity interact to determine FPGA SNN performance, scaling and hardware efficiency?

The proposed research contribution is a **controlled characterization**, not a claim to have invented time-multiplexed neurons, caching or sparse scheduling. Compare identical neural workloads and numerics under a four-way experimental design:

| Execution strategy | On-chip state | DDR-backed state |
| --- | --- | --- |
| Timestep-driven | Control A | Control C |
| Event-driven | Control B | Control D |

Evaluate virtualization penalty, sparsity benefit and their interaction while varying **active-context locality independently of event count**. Record end-to-end latency, throughput, on-chip resources, transferred bytes, context/cache misses, evictions, scheduler stalls, and verified neural outputs. Compare competing accelerators only with matched datasets, numerical precision, workload, resource and measurement boundaries; a negative result is scientifically useful.

Starting points: [research roadmap](Neuromorphic_Accelerator/v1/roadmap.md) · [literature review and prior art](LitReview.md) · [workload and measurement contract](Neuromorphic_Accelerator/v1/docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md).

## Current status — November 10, 2026

**M01–M06 are complete at their individually approved, bounded scopes. M07 is the next planned development milestone; M08 is reserved for separately authorized physical evaluation and M09 for analysis.**

| Work | Accepted scope |
| --- | --- |
| M01–M03 | PC-only residency design alternatives, independent LIF/event semantics, matched workloads and analytical traffic accounting |
| M04 | Audit of existing HLS arithmetic and bounded host reuse feasibility; no synthesis was required for M04 closure |
| M05 | Offline FPGA-targeted signed32 on-chip event engine and genuine integrated HLS/RTL simulation; [acceptance review](Neuromorphic_Accelerator/v1/docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md) |
| M06 | Original Vitis HLS and AMD interconnect **genuine Vivado simulation**, including paged one-slot neural/state parity, AXI read/write errors, missing-response timeout, and explicit recovery of a **64 KiB simulation-owned memory image**; [acceptance review](Neuromorphic_Accelerator/v1/docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md) |

**Boundary:** M06 is a connected offline RTL/simulated-memory result, **not a physical PS DDR transfer, deployed KV260 accelerator, measured FPGA latency or automatic crash-atomic rollback**. No hardware speedup, DDR bandwidth, energy, or full-system timing has been demonstrated for this new program. Previous prototype metrics must not be relabeled as new v1 physical measurements.

## Repository map and historical context

| Location | Purpose |
| --- | --- |
| [Neuromorphic_Accelerator/v1](Neuromorphic_Accelerator/v1/) | **Active new research program**: source, RTL, HLS, models, tests and current roadmap |
| [Loihi_Digital_Twin/v1](Loihi_Digital_Twin/v1/) | Preserved first validated twin and [M1–M13 milestones](Loihi_Digital_Twin/v1/MILESTONES.md) |
| [Loihi_Digital_Twin/v2](Loihi_Digital_Twin/v2/) | Preserved accepted Loihi-inspired manycore architecture |
| [Loihi_Digital_Twin/v3](Loihi_Digital_Twin/v3/) | **Frozen** original FPGA/PS-based experimental baseline; [authoritative historical roadmap](Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) |
| [applications](applications/) | Application workloads, including [MNIST baseline](applications/mnist_baseline/) |
| [LitReview.md](LitReview.md), [EXPERIMENTS.md](EXPERIMENTS.md), [AUDIT.md](AUDIT.md) | Literature, archived experiment records and audit context |

The v3 project established Loihi-inspired integer LIF validation, 27 logical cores and 1,010 neurons with historical DDR-based orchestration, separately from a smaller 42-neuron track. **Different-size workloads are not a matched accelerator performance comparison.** Historical full-1,024-image neural checks and A53 service measurements must not be mistaken for pure-PL acceleration. Only one of six planned new A/B physical sessions was accepted; the remaining five were **canceled**, not performed. The optional v3 P10 optimization remains **deferred**, and the official MNIST TEST split is still **sealed**.

Preserve the prior implementation, evidence hashes and v3 intellectual lineage, but do not automatically import old firmware, exact logical-core partitions, or a claim of a Loihi silicon-accurate or fully asynchronous twin. An existing compatibility symlink, 'Neuromorphic Digital Twin', points to the historical v1 and should not be renamed.

## Working safely

Create a new branch from current main for a development milestone or document cleanup; run relevant host regressions, inspect no-board CI and preserve original vendor-generated results under **~/Thesis_Evidence/**, outside Git. Merge only after user acceptance. The [v1 README](Neuromorphic_Accelerator/v1/README.md) provides current commands and evidence rules.

**Real hardware is a separate approval gate:** JTAG, Linux halt, fabric programming, boot ownership or physical DDR writes require session-specific operator approval, isolation/preflight and a mandatory physical power cycle after each JTAG attempt; never resume halted Linux. Do not run archived v3 JTAG instructions as if they were automatically authorized.

For the historical first-generation digital twin, the preserved verification command from its directory is:

~~~bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v1
python -m pip install -e ".[dev,compare]"
python -m pytest -q
~~~

Use 'python -m pytest' rather than bare 'pytest' because the old suite imports project-root examples.

## Finding the detailed original history

This README is a navigation page, not the experiment ledger. [The roadmap](Neuromorphic_Accelerator/v1/roadmap.md), its milestone acceptance documents and the immutable ZIPs contain current evidence. **No experimental record was deleted during documentation cleanup:** the complete original README, v1 README and long chronological roadmap remain in [the pre-cleanup main revision](https://github.com/Xtimetraveler-Prime/Thesis/tree/33916fffd4f5935aac9ec060a0e62d92977b3c05). See [cleanup provenance](Neuromorphic_Accelerator/v1/docs/REPOSITORY_DOCS_CLEANUP_2026_11_10.md).
