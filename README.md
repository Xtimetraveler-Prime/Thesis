# Thesis — DDR-Backed Virtualization and Sparse SNN Acceleration

> **Research direction updated 2026-11-07 after advisor discussion.** The verified Loihi-inspired digital-twin work remains preserved as **FPGA-v3**, but the next phase is an independently designed **FPGA-v4 virtualized spiking-neural-network (SNN) inference accelerator**. V4 planning is next; no v4 RTL, hardware build, or physical performance result has been accepted yet.

## Central research questions

> **1. How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover?**

> **2. How do DDR-backed virtualization and event-driven sparsity interact to determine the performance, scalability, and hardware efficiency of FPGA-based spiking neural network accelerators?**

These are **questions to investigate**, not claims that an architecture has already answered them. The core design constraint that survives v3 is **virtualization**: more logical LIF neurons/contexts than can fit in the physical on-chip working set, backed by external DDR. V4 can abandon optional Loihi-specific limits on core size, routing, scheduling and execution organization while retaining a precisely specified, independently validated LIF model. Model-equivalent updates (including lazy leak and rounding) must be demonstrated, not assumed.

## Candidate thesis contributions (not yet demonstrated)

1. **Measure virtualization's costs and practical scaling limits.** Characterize inference latency, throughput, DDR traffic/latency, resource utilization and neural correctness as logical network size, physical resident capacity, event/connectivity sparsity and active-context locality change. Identify when movement/scheduling costs exceed sparse-compute savings.
2. **Explore sparsity-/locality-aware virtual-context management.** Design and evaluate an optional scheduling, caching, prefetching or retention policy that reduces repeated DDR context transfers. Compare against fixed-order and simple replacement baselines at matched networks, input events, hardware resources and measurement boundaries.
3. **Build a correct, resource-conscious virtualized SNN accelerator.** Demonstrate event-driven LIF inference with DDR-backed logical neural state/weights and a limited on-chip working set, including controlled **timestep/on-chip, event/on-chip, timestep/DDR, event/DDR** comparisons where all four fit. Test larger DDR-backed networks separately; use external accelerators such as YANA as qualified, workload-aware references rather than unsupported headline speedup targets.

**Novelty boundary:** time-multiplexed neurons, virtual logical cores, sparse event execution, FPGA SNN accelerators and external synaptic memory already exist in prior art (e.g. SENECA, RANC, YANA, HiAER-Spike). A potential contribution is the *controlled characterization and improvement of DDR-backed context virtualization under sparse, locality-dependent activity*, not simply that an FPGA executes an SNN or uses DDR. Any specific novelty claim requires further targeted literature review.

## Project status and reproducible baselines

- **v1** — preserved validated FPGA-v1 architecture and M1–M13 development (`Loihi_Digital_Twin/v1/`, `Loihi_Digital_Twin/v1/MILESTONES.md`).
- **v2** — preserved accepted Loihi-1-inspired manycore baseline (`Loihi_Digital_Twin/v2/`).
- **v3** — **frozen, historically validated Loihi-inspired KV260 architecture**, including PS/A53 board-local scheduling, limited PL compute, DDR-backed virtualized logical contexts, original independent LIF/neural oracles and genuine physical execution. See [v3 roadmap and authoritative freeze/cancellation](Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) and [current v3-to-v4 handoff](Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md).
- **v4** — **not yet started**; next step is to agree on hardware architecture, neural reference semantics, sparse representation, DDR-memory organization, benchmarks and controlled experimental design. No Loihi architectural fidelity requirement is automatically transferred.

On v3, the scaled 27-logical-core/1,010-neuron B_AUTH_ONCE V2 1,024-image original TRAIN-derived physical neural run was independently validated. A separate rebuilt one-core/42-neuron A2.1 baseline and its full original oracle also passed physical checks. The **new** counterbalanced A/B six-coldboot experiment was deliberately **discontinued after one accepted new Session 01 A (1/6)**; the other five scheduled physical runs are canceled, not completed. The accepted Session01 A53 ordinary 1,023-image median was **35.67722641549189 ms** at observed CNTFRQ 99,999,001 Hz. These different-size A/B workloads and timer components do **not** establish a matched-accelerator speedup, pure PL advantage, protected DDR/XMPU, or measured energy efficiency. Prior accepted evidence and SHA identities remain immutable, and the official MNIST **TEST remains sealed**.

## Reading and working in this repository

- [Literature review, including YANA, SENECA, HiAER-Spike, time-multiplexed FPGA inference and NIR](LitReview.md) — literature notes and evolving novelty boundaries.
- [v3 roadmap](Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) — complete preserved historical milestones, frozen v3 results, canceled remainder and **final deferred P10 bounded optimization**.
- [v3-to-v4 development handoff](Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md) — directory layout, local terminal verification, Git/PR workflow, original SHA/evidence policy and physical KV260 safety.
- [Historical architecture specification](Loihi_Digital_Twin/v3/docs/LOIHI1_TARGET_SPEC.md) — the original v3 fidelity contract, **not a future v4 requirement**.
- [Original experiments](EXPERIMENTS.md), [audit history](AUDIT.md), [phase-2 audit](AUDIT_PHASE2.md), [phase-3 audit](AUDIT_PHASE3.md).

### Repository layout

```text
Loihi_Digital_Twin/
  v1/        preserved early baseline and M1–M13
  v2/        preserved accepted Loihi-inspired manycore baseline
  v3/        frozen KV260 research code and evidence workflow
    src/     Python logic and independent oracle/reference modules
    scripts/ PC admissions, software verification, hardware runners
    tests/   regression and negative safety tests
    vivado/  project, sources, Tcl, implementation and hardware setup
    hls/ rtl/ hardware/ artifacts/ docs/
    LOIHI_TWIN_ROADMAP.md
  v4/        FUTURE planning target; not created or validated yet
applications/mnist_baseline/    preserved first application
LitReview.md                   root literature research notes
```

### Local verification

Start from a clean checkout of current main; create a fresh branch before modifying source. Run only **PC/no-board** verification unless a later physical test receives explicit session-specific approval.

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
PYTHONPATH="$PWD/scripts:$PWD/src" python3 -m pytest -q -rs \
  tests/test_p08_b46_4b_six_session_plan.py \
  tests/test_p08_b46_4b_session_receipt.py
```

Historical FPGA-v1 regression commands (from `Loihi_Digital_Twin/v1/`):

```bash
python -m pip install -e ".[dev,compare]"
python -m pytest -q
```

Original physical test logs, build artifacts and operator-attested receipts live outside Git in `$HOME/Thesis_Evidence/`; no GitHub CI run can independently verify those raw captures. **Do not run any retained v3 JTAG/DDR overwrite commands as part of the canceled study.** When physical work is later explicitly scoped, review all original firmware/DDR ownership risks, use fresh evidence paths and independent neural verification, and power-cycle the KV260 after any JTAG attempt.
