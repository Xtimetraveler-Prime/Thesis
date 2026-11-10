# M07 next-chat handoff — Neuromorphic Accelerator v1
**Prepared November 10, 2026 — after M06 acceptance and documentation cleanup**

This is the current continuation handoff, **not** a direction to rerun completed experiments. In a new chat, start by reading the [v1 README](../README.md), [M01–M09 roadmap](../roadmap.md), [M05 acceptance](M05_ACCEPTANCE_REVIEW_2026_11_09.md), [M06 acceptance](M06_ACCEPTANCE_REVIEW_2026_11_10.md), and [M03 measurement contract](M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md). Historical M05/M06 runbooks may still show obsolete OPEN statuses; the accepted reviews and current roadmap supersede them. Verify the documentation-cleanup PR #81 is merged before creating the M07 branch.

## 1. Repository and research orientation

- GitHub repository: **Xtimetraveler-Prime/Thesis**.
- Owner workstation: Linux / VS Code; checkout **~/Git/Thesis**.
- Active source root: **Neuromorphic_Accelerator/v1/**.
- Frozen separate prior work: **Loihi_Digital_Twin/v3/**; the new accelerator v1 is NOT Loihi Digital Twin v4 and does not adopt the v3 27-core restriction.
- Target hardware: AMD Kria KV260/K26; separate hardware permission is required.
- Owner-only original toolchain: Vivado/Vitis **2025.2**, NOT available on GitHub runners.
- Immutable original evidence: **~/Thesis_Evidence/**, outside the repository.

**Research questions:** how much extra cost does neural-state virtualization introduce, and when can event sparsity and active-context locality recover it? Compare a bounded physical resident working set against larger logical networks, without asserting speedup or novelty for known time-multiplexing, cache, lazy-leak or sparse-worklist ideas. The target four-way controls are timestep/on-chip, event/on-chip, timestep/DDR-style, and event/DDR-style, with matched networks and neural numerics **where all configurations fit**. Hold event count and synaptic work constant while varying active-group locality.

**Numerical invariants:** the accepted M02 integer LIF dynamics, signed synaptic accumulation, ordered spikes, delayed recurrent deliveries, quiet-neuron updates, and no lost/duplicate events must be preserved. The M03 role-isomorphic network generator, safe-sparse reference, four-way traffic model and measurement contract are authoritative initial test inputs. M01 selected tunable block residency provisionally, retaining neuron-granular/hybrid controls.

## 2. Accepted milestones and immutable evidence

| Milestone | Status at handoff | Evidence boundary |
| --- | --- | --- |
| M01 | COMPLETE | PC-only state-residency alternatives, configurable block baseline; [design memo](M01_ARCHITECTURE_OPTIONS.md). |
| M02 | COMPLETE | PC-only independent scalar and event-bucket LIF oracles; [contract](M02_PROVISIONAL_LIF_CONTRACT.md). |
| M03 | COMPLETE | PC-only role-isomorphic workloads, reference parity and modeled traffic; [measurement contract](M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md). |
| M04 | COMPLETE | Audit of v3 HLS numerical reuse and bounded host candidate, not an M04 synthesis claim; [audit](M04_HLS_ENGINE_AUDIT.md). |
| M05 | COMPLETE; PR #79 merged | Original Vitis/HLS signed32 rolling on-chip engine and integrated original RTL simulation, NOT deployed board; [acceptance review](M05_ACCEPTANCE_REVIEW_2026_11_09.md). |
| M06 | COMPLETE; PR #80 merged | Genuine original Vitis HLS+AMD SmartConnect/width-converter XSim with privately owned 64 KiB simulated canonical image, paging/dirty evictions, independent neural/state parity, fault quarantine and explicitly commanded restore; [acceptance review](M06_ACCEPTANCE_REVIEW_2026_11_10.md). |
| **M07** | **NEXT; not implemented by documentation handoff** | Cache/scheduling alternatives and controlled, independently neural-correct ablations. |
| M08 | PLANNED | Separately authorized real KV260, physical PS-DDR, timing/resource and throughput experiments. |
| M09 | PLANNED | Thesis-grade quantitative interaction/locality/virtualization analysis with uncertainty. |

**Important distinction:** M06 simulated **original vendor HLS and AMD RTL**, not pretend functional vendor mocks; however the backed image is an **externally controlled 64 KiB simulation scratch memory**. M06 does NOT demonstrate physical PS DDR ownership, real DMA transfers, installed bitstream, automatic persistent rollback, placed/routed complete virtual-state shell, or hardware latency/energy/speedup. These claims cannot be inferred from XSim or CI.

Five separately accepted original Vivado 2025.2 owner ZIPs: G3.3 independent 32-neuron ×4-tick / one-slot / high-address dirty-eviction M02/M03 neural and final state parity; G4 first write B SLVERR; first read R SLVERR; genuine held memory B with zero HLS B acknowledgments and directed 1024-cycle timeout quarantine; and explicit whole-65536-byte canonical image reset/restore followed by clean original HLS AP_DONE/status0 and **16 six-field traces + one metrics** released only postcommit. Original 40 HLS RTL, 14 HLS initialization files, 67 AMD RTL source hash rows match across five experiments; both original AMD DWC XCI checks passed. The exact five ZIP names, SHA256, owner source commits and XSim times are in [M06 acceptance](M06_ACCEPTANCE_REVIEW_2026_11_10.md). Preserve the first two failed stalled-B trial ZIPs as historical failures; never substitute them for the accepted PASS ZIP. Do NOT rerun unchanged accepted vendor experiments.

**Useful source layout (inspect before editing; don't invent exact files):**
- src/neuromorphic_accelerator_v1/ — M01/M02/M03 models and M06 pager, reference and traffic logic.
- hls/ — on-chip rolling and paged engine source and Vitis original-tool support.
- rtl/ — local stream/control/AXI guard, scratch/residency and output quarantine RTL (G4 in rtl/m06/).
- scripts/ — sweep/replay, original owner runners, strict hashes, packaging and evidence audit.
- tests/ — host reference, unit, negative boundary and local RTL/source tests.
- docs/ — acceptance decisions, detailed milestone experiments, required test explanations and runbooks.
- Root .github/workflows/ — no-board M01–M06 independent CI workflows.

## 3. M07 goals and recommended first development

**Authoritative roadmap:** [M07 full plan and acceptance criteria](../roadmap.md#4-m07--schedulingcache-policy-variants-and-ablation-controls).

M07 answers **which cache/scheduling policy is useful, if any**, with matched neural inputs and transparent memory/queue accounting. Order matters; do not implement a complicated locality scheduler before proving simple baselines.

1. **Inspect existing source first.** Inventory M06 software paging/residency models and counters, M03 network generators and model-only traffic measurements, M02 independent LIF oracles, and G4/RTL safety invariants. Identify the smallest safe policy extension point, without rewriting accepted source contracts.
2. **Baseline first.** Implement or verify a deterministic no-cache/direct state-fetch (or minimal fixed-residency) control; add one simple transparent FIFO/LRU-class policy. Decide and document block identity, dirty eviction/fill semantics, bounds and exact counter units.
3. **Independent correctness and fairness.** Every policy must reproduce M02 state/spike/trace output exactly on matched M03 synthetic networks, including delayed/recurrent cases, quiet-neuron updates and forced evictions. Track state-versus-synapse traffic independently, misses/hits, fill/writeback, outstanding requests, response fences, queue stalls and simulation service time. Never call a modeled traffic counter a physical DDR measurement.
4. **Four-way matched tests.** Timestep/on-chip, event/on-chip, timestep/DDR-style, event/DDR-style must use the same workload, neural semantics and fair resource assumptions where all four fit. Mark an on-chip comparator UNAVAILABLE when its logical state cannot fit. Sweep resident budget, state block size, mapping/locality and event batching; **hold total event count constant** when testing locality.
5. **Only after baseline evidence** consider at most one activity/locality-aware candidate policy. A slower or null result is valid. If future source changes affect original HLS/AMD interactions, add a separate original-tool owner gate; don't infer that model parity proves hardware.
6. **Later hardware evaluation stays later.** M07 should start with source/model and relevant local RTL tests. Physical PS DDR and board work require M08 gates and new authorization.

**M07 acceptance:** repeatable policy variants and matched controls, independent M02 oracle parity, transparent policy-specific counters/ablation artifacts, documented simulation-versus-physical timing boundaries, and honest negative outcomes. Work may be grouped as M07.1 when useful, but do not proliferate artificial micro-milestones.

**Best initial task in the next chat:** inspect M06 pager source and M03 workload/traffic API, write a concise M07 baseline implementation-and-testing plan, create the M07 development branch from merged main, and start implementing the simplest baseline and exact-parity/negative tests. Do not start from the documentation branch, and do not alter accepted golden reference data to obtain a policy win.

## 4. Development and evidence workflow — REQUIRED

- **Real GitHub repository editing.** Inspect actual files/PR status, create an M07 branch from the **ACTUAL merged main HEAD**, commit source/tests/docs on that branch. Do not only present suggestions or phantom code. Main remains clean until independently accepted.
- **Each milestone has its own branch and review.** Draft PR is useful for CI and owner review. Do not merge M07 or mark it COMPLETE from host tests alone.
- **Maintain docs/M07_TESTS_EXPLAINED.md.** For each test explain objective, fixture/input, sequence, expected output, failure/negative cases, actual verified tool level and limitations. Also maintain a local verification runbook, roadmap milestone status and short branch PR description.
- **After every substantive change** run Python compileall, relevant independent M02/M03/M06/M07 unit tests and negative cases, any applicable genuine local Icarus/vvp RTL functional or syntax tests, and check new-head GitHub Actions. Report pass/fail/skip and *always give the owner exact Linux VS Code git pull and test commands*. The user expects commands each development turn.
- **Original vendor owner evidence is distinct.** Only the owner runs original Vivado/Vitis 2025.2; preserve the FIRST failure as distinct immutable evidence. Keep generated Vitis/AMD HDL, all 14 HLS dat assets where applicable, DWC .xci identity, exact source SHA, tool stages, simulated timing, and original CLI console in unique timestamped ~/Thesis_Evidence directories. Package a mode-specific ZIP for review. Do NOT pretend Icarus interface declaration stubs or source CI are actual HLS/AMD functional simulation, and do not rerun accepted original experiments unchanged.
- **Do not perform physical operations.** FPGA programming, JTAG, Linux halt, new boot ownership, real DDR writes and bitstream use require separate *session-specific* operator authorization and safety preflight; a real power cycle is mandatory after each JTAG attempt. Never resume halted Linux. No physical work is authorized by this handoff.
- **Scientific integrity.** Do not unseal official MNIST TEST, call modeled bytes physical bandwidth, assume real energy savings without measurements, claim unmatched workloads are accelerations, or present common virtual neuron/cache/event concepts as new inventions. Preserve historical frozen Loihi v3 work.
- **Historical handoffs are historical.** Older files may report M05/M06 still OPEN, PRs draft or simulations untested. The current [roadmap](../roadmap.md) and accepted M05/M06 review are authoritative. The original pre-cleanup long log remains in [version-pinned commit 33916ffd](https://github.com/Xtimetraveler-Prime/Thesis/tree/33916fffd4f5935aac9ec060a0e62d92977b3c05), indexed by [cleanup provenance](REPOSITORY_DOCS_CLEANUP_2026_11_10.md).

## 5. Reproducible VS Code commands

**Confirm merged main and accepted source tests (do not run old vendor owner gates):**

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 -m unittest discover -s tests -p 'test_m03*.py' -v
~~~

**After the new assistant has actually created and pushed an M07 branch, use the ACTUAL branch it reports:**

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch <ACTUAL_M07_BRANCH>
git pull --ff-only origin <ACTUAL_M07_BRANCH>
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 -m unittest discover -s tests -p 'test_m03*.py' -v
~~~

The M07 tests and branch DO NOT exist merely because this handoff mentions them. The new chat must create them during real development. Host-only broad suite: 'python3 -m unittest discover -s tests -v'. Icarus and vvp must be installed for local RTL simulations; keep syntax-only stub tests distinct from genuine original vendor XSim.

## 6. Checklist for the new chat

1. Verify PR #80 M06 and PR #81 documentation cleanup are merged; check current main SHA and current code instead of trusting a hard-coded commit.
2. Read the cleaned v1 README, current roadmap, accepted M05/M06 reviews, M03 measurement contract and this handoff.
3. Inventory real M06 pager and M03 policy/workload hooks; explain feasible baseline vs optional policies.
4. Create a NEW M07 development branch and (if helpful) draft PR from merged main, not documentation branch.
5. Begin M07 baseline code/test development with independent M02 parity, exact traffic/queue counters and negative cases; keep M07 open.
6. Run real available tests and current-head CI, then supply exact owner VS Code pull/tests commands, updated test-explanation doc and short PR status.
7. Do not advance to M08, merge M07, repeat accepted original owner tests or run physical board actions without separate owner authorization.

**Suggested first assistant response:** summarize the M07 baseline and comparison goals, confirm live repo state, and begin source/test development on the new M07 branch. Do not ask the owner to repeat already recorded research goals or milestone approvals.
