> **Latest v1 neuromorphic accelerator milestone status (2026-11-10): M01–M06 COMPLETE at individually approved, explicitly bounded scopes.** M06 was verified using five distinct genuine original-HLS+AMD Vivado 2025.2 XSim PASS owner archives: original neural/state parity across one-slot eviction, write/read AXI faults, stalled write-response watchdog poison, and external simulated 64KiB image discard/restore followed by gated clean 16-trace/1-metrics output. [M06 acceptance evidence and nonclaims](Neuromorphic_Accelerator/v1/docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md); [current M01–M09 roadmap](Neuromorphic_Accelerator/v1/roadmap.md). **M06 is offline simulation-scoped; no physical PS DDR, KV260 deployment, real DMA/latency, automatic crash-atomic rollback or board execution.** M07 planned and M08 physical measurement remains separately gated.

# Thesis — Virtualized Neuromorphic Computing on FPGA

**Current thesis direction (2026-11-07):** Study the costs, benefits, and limits of **DDR-backed virtualization** in sparse/event-driven FPGA spiking neural network (SNN) inference. We are preserving the verified LIF neuron dynamics and logical-to-physical virtualization learned from our Loihi-inspired v3 digital twin, while **removing Loihi-specific architectural constraints** for the new **`Neuromorphic_Accelerator/v1`** research program. The KV260 remains the current research board. **M01 is accepted as a PC-only memory-residency trade study** and **M02 as the current independently verified v1 LIF software reference**; **M03 is user-accepted in its PC-only scope**, with reproducible role-isomorphic synthetic networks and modeled state/synaptic traffic. **M04 is NEXT**, a new-branch inspection of the existing v3 HLS LIF engine; it has not started. There is still **no new FPGA HLS/RTL accelerator, bitstream, board performance result or trained-model benchmark**.

## Central research questions

> **1. How much performance must we sacrifice to virtualize a larger network, and how much of that cost can sparsity-aware execution recover?**

> **2. How do DDR-backed virtualization and event-driven sparsity interact to determine the performance, scalability, and hardware efficiency of FPGA-based spiking neural network accelerators?**

The central research challenge is not merely whether hardware can time-multiplex neurons—that is established prior art—but **when virtualizing neuron/context state in external memory is worthwhile, how sparse activity interacts with context locality, and which working-set policies recover memory and scheduling overhead**.

## Potential thesis contributions (hypotheses, NOT demonstrated results)

1. **Controlled characterization of virtualization cost.** Measure end-to-end inference latency, throughput, effective synaptic work, DDR bytes/transactions, context swaps and stalls, on-chip resource consumption, network-size scaling, activity/connectivity sparsity, and **active-context locality**. Determine how virtualization cost changes with on-chip resident capacity, rather than treating all sparsity distributions as equivalent.
2. **Sparsity-aware virtual-context scheduling and caching.** Design and test one or more activity-/locality-aware policies against explicit simple baselines (e.g., fixed order or no cache); quantify cache hits, context transfers, scheduler stalls, and inference correctness. A performance win is a hypothesis to test, not a presumed outcome.
3. **A verified, resource-constrained virtualized SNN inference accelerator.** Reuse and independently verify the LIF reference semantics while relaxing Loihi implementation restrictions. Establish fair on-chip/DDR and timestep/event-driven controls at network sizes that fit all configurations, then study DDR-backed scaling beyond on-chip capacity. Compare with external FPGA accelerators only when network, numeric precision, dataset and measurement boundary are disclosed; do not claim unmatched speed, energy, or power without measurement.

**Candidate experimental matrix:** timestep-driven/on-chip, event-driven/on-chip, timestep-driven/DDR, and event-driven/DDR. This is a planning framework, not four existing RTL builds. Investigate access locality at fixed event count, and distinguish per-engine, transfer, scheduler and true end-to-end timing. Relevant prior work includes YANA, SENECA, HiAER-Spike, time-multiplexed FPGA SNN accelerators, NIR, and NeuroBench; see the [preserved and extended literature review](LitReview.md). Time-multiplexing, virtual neurons, and off-chip synaptic storage are not novel in themselves.

## Status and versioned history

- **v1 — preserved validated baseline** under [`Loihi_Digital_Twin/v1/`](Loihi_Digital_Twin/v1/), with completed [M1–M13 milestones](Loihi_Digital_Twin/v1/MILESTONES.md).
- **v2 — preserved accepted Loihi-inspired manycore architecture** under [`Loihi_Digital_Twin/v2/`](Loihi_Digital_Twin/v2/).
- **v3 — FROZEN research and physical-evidence baseline** under [`Loihi_Digital_Twin/v3/`](Loihi_Digital_Twin/v3/): original trained LIF MNIST source, DDR-backed 27-logical-core/1,010-neuron SNN execution, original all-1,024-image neural verification and real KV260 A53 service measurements; also a separately verified smaller 42-neuron Track A. These unequal workload measurements do **not** establish matched-network acceleration. The planned six independent A/B sessions stopped after **one new accepted A session (1/6)**; the five remaining physical sessions were **canceled, not executed**. The former v3 future milestones were canceled or archived, with **P10 a final, optional, DEFERRED bounded optimization milestone**, not authorized for execution. Existing physical receipts and exact checksums remain immutable; official MNIST TEST remains sealed. Read the [authoritative frozen v3 roadmap](Loihi_Digital_Twin/v3/LOIHI_TWIN_ROADMAP.md) and [current handoff](Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md) rather than interpreting old 'NEXT' sections as live instructions.
- **Neuromorphic Accelerator v1 — NEW, independently versioned research program.** [`Neuromorphic_Accelerator/v1/`](Neuromorphic_Accelerator/v1/) is a first-generation design workspace, **not** a continuation called `Loihi_Digital_Twin/v4`. The accepted M01 block-based state residency is a **provisional baseline** retaining neuron/hybrid controls, M02's initial integer LIF neural reference is approved, and M03 is an **unaccepted PC-only** workload/model study; no v1 HLS/RTL engine, bitstream or FPGA performance evidence exists yet. The [M01–M09 roadmap](Neuromorphic_Accelerator/v1/roadmap.md) documents M01/M02 acceptance, current [accepted M03 workload and measurement assumptions](Neuromorphic_Accelerator/v1/docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md), the [M04 authoritative handoff seed](Neuromorphic_Accelerator/v1/docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md), and future HLS reuse, sparse scheduling, DDR residency, matched physical controls and quantitative characterization.

**What v3 established:** independent software–hardware LIF numerical validation, FPGA/PS orchestration and DDR virtual-context movement on real hardware. **What it did not establish:** a Loihi silicon-exact replica, true fully asynchronous physics, protected DDR/XMPU context backups, all six new A/B physical sessions, matched A/B workloads or timing boundaries, pure-PL acceleration, power/energy savings, or new-accelerator performance.

## Repository structure and working workflow

- [`Loihi_Digital_Twin/`](Loihi_Digital_Twin/) — **frozen historical** v1/v2/v3 architecture and evidence (not the new project's home).
- [`Neuromorphic_Accelerator/`](Neuromorphic_Accelerator/) — **new top-level umbrella** for independent accelerator and virtualization research; first generation [`v1/`](Neuromorphic_Accelerator/v1/) and its [open design questions](Neuromorphic_Accelerator/v1/docs/ARCHITECTURE_DESIGN_QUESTIONS.md).
- [`applications/`](applications/) — application workloads, including [MNIST baseline](applications/mnist_baseline/).
- [`LitReview.md`](LitReview.md) — existing research notes and new event-driven/virtualization prior art.
- [`EXPERIMENTS.md`](EXPERIMENTS.md), [`AUDIT.md`](AUDIT.md) — historical experiments and audit evidence.
- [`Neuromorphic Digital Twin`](Neuromorphic%20Digital%20Twin) — historical compatibility symlink to v1; don't rename.

**Local PC (VS Code Ubuntu):**

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
  tests/test_p08_b46_4b_session_receipt.py \
  tests/test_p08_b45_perf_full1024_independent_cli.py
```

For new `Neuromorphic_Accelerator/v1` research, branch from freshly updated `main`, keep evidence under `$HOME/Thesis_Evidence/` outside the checkout, run relevant native tests and no-board CI, record original source/ELF/bitstream SHAs and separate physical acceptance, and merge only with express approval. **Do not launch any old KV260 JTAG runner from an archived runbook without a newly reviewed, session-specific destructive-risk authorization**; power-cycle the board after any JTAG attempt and never resume halted Linux.

## Preserved FPGA-v1 regression

From `Loihi_Digital_Twin/v1/`:

```bash
python -m pip install -e ".[dev,compare]"
python -m pytest -q
```

The historical v1 suite intentionally uses `python -m pytest` (not bare `pytest`) because one preserved test imports project-root `examples/` helpers. Generated caches, package metadata and outputs are excluded from source control.
