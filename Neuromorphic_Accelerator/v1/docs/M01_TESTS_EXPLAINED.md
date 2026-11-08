# M01 — What the Tests Actually Ran, and How They Work

**Scope:** Neuromorphic Accelerator v1 / M01 virtualized *neuron-state residency* traffic study. The tests described here are the **actual committed tests** under `tests/test_m01_residency.py` (15 tests) and `tests/test_m01_sweep.py` (5 tests), plus the GitHub Actions checks in `.github/workflows/neuromorphic_accelerator_m01_pc_only.yml`. The user independently reported that native tests passed. At the time M01 was accepted, branch-head GitHub Actions also reported success. This documentation explains the tests; it does **not** reinterpret them as real FPGA, inference, or DDR performance measurements.

## 1. What is being modeled?

A *request* says: "read and modify the state of logical neuron N." It is **not** a neural spike, LIF evaluation, synaptic fanout, clock cycle, FPGA command, inference sample or timed physical transfer.

All three policy models process the **same ordered sequence** of requests, with an explicitly bounded data-residency budget and with cold-load and final-dirty-writeback traffic counted:

- **Individual:** cache the state of one neuron per entry; evict the least recently used (LRU) neuron after capacity is reached.
- **Block:** cache whole groups of `G` neighboring neuron records; on a miss load a group and write back a dirty group on eviction.
- **Hybrid:** pin a **predeclared contiguous prefix** of `P` neurons at startup, sharing the same budget with an LRU cache of remaining groups. Contiguous pinned prefetch and adjacent dirty writes may be coalesced. The prefix is not chosen by inspecting the input trace.

The model counts **reads, writes, transaction splitting at a specified hypothetical maximum contiguous transfer size, hits, misses, evictions, final flushes and capacity**. It does not simulate hardware DDR request scheduling, LIF/neuronal correctness, synaptic weights, DMA latency, cache tag overhead, or execution speed.

## 2. How the 15 residency tests work

File: `tests/test_m01_residency.py`. Each test invokes model functions with a **small, exactly checkable input trace**, compares explicit integer counts, or asserts that an invalid input raises `ValueError`.

| Test function | Input / test mechanism | What it checks |
| --- | --- | --- |
| `test_configuration_accepts_matched_budget` | Three policies, same valid 64-byte budget and 4 state requests | Occupied model data never exceeds budget; **hits + misses = requests**. |
| `test_config_fail_closed` | 11 invalid configurations, including booleans used as integers, nondivisible groups, zero capacity and a hybrid whose pins leave no group slot | Bad memory layouts are rejected before being compared; no silent over-allocation. |
| `test_trace_is_deterministic_and_work_matched` | Seeded clustered/dispersed 80-request traces for 8 active neurons | Repeat calls yield identical traces; total requests, active neuron count, and per-neuron request multiplicities match; neuron *locations* differ (2 vs 8 groups). |
| `test_trace_validation` | Zero/invalid network, too many active neurons, too few requests, invalid seed/type and unknown locality | Workload generator rejects invalid inputs. |
| `test_one_neuron_lru_eviction_dirty_and_end_flush` | 32-byte cache holding 4×8-byte states; requests `(0,1,2,3,4,0)` | Exactly 6 misses, 2 dirty evictions, 4 remaining end-flushes; read/write bytes and transactions conserved. |
| `test_one_neuron_lru_hit` | Requests `(0,1,0,1)` | First two miss, next two hit, with no eviction; final flush writes both dirty records. |
| `test_block_burst_and_end_flush` | Requests `(0,1,4)`, groups of 4×8-byte states, max transfer 16 bytes | 2 group misses, 1 hit, 64 B read and 64 B written; each 32 B group transfer splits into 2 modeled transactions. |
| `test_block_eviction_is_whole_group_and_dirty` | One 32-byte group slot; requests `(0,1,4)` | Loading a second group forces exactly one dirty group eviction and a final flush of the remaining group. |
| `test_hybrid_prefetch_cold_start_cost_is_visible` | 4 pinned neuron states; requests `(0,1,0)` | The model counts the **32 B cold prefetch** even if only 2 pinned neurons are touched; contiguous prefetch = 2 modeled 16-byte transfers, and adjacent dirty state writes = one transaction. |
| `test_hybrid_pinned_and_unpinned_do_not_double_cache` | Requests `(0,1,4,5,8)` | Pinned and dynamic regions share only 64 bytes; pinned neurons do not reappear in dynamic blocks; eviction and distinct-count accounting match. |
| `test_zero_pins_hybrid_equivalent_to_block` | Same trace run as block and hybrid with `P=0` | **Metamorphic test:** removing pinned state makes hybrid accounting *identical* to ordinary group caching except for the policy label. |
| `test_empty_trace_pinned_init_not_inferred_as_work` | Zero requests, but 4 pinned records | The model still charges startup reads, never invents a state update, writes nothing and handles zero-request hit rate. |
| `test_trace_rejects_invalid_and_boolean_ids` | Negative/out-of-range/boolean/noninteger neuron IDs, invalid policy | Bad state requests cannot be treated as valid addresses. |
| `test_run_study_reports_only_hypothetical_timing_if_requested` | Repeat same seed; optionally supply **both** illustrative latency/bandwidth assumptions | JSON output is deterministic and explicitly labeled **PC-only**; no timing field appears unless both hypothetical values are supplied; trace hash remains identical. |
| `test_hypothetical_transfer_model_rejects_bad_numbers` | Negative/NaN/infinite overhead or zero/nonfinite bandwidth | Invalid user-supplied timing assumptions fail instead of producing bogus latency predictions. |

The tests are ordinary Python `unittest` test methods; some contain several `subTest` cases. **"15 tests" does not mean only 15 assertion checks**, nor does it mean 15 hardware experiments.

## 3. How the five sweep tests work

File: `tests/test_m01_sweep.py`.

| Test function | Input / test mechanism | What it checks |
| --- | --- | --- |
| `test_full_sweep_is_deterministic_and_matched_within_cell` | Run the whole **3 resident budgets × 4 block sizes × 2 localities = 24 scenarios** twice | JSON is bytewise-deterministic when serialized with fixed ordering; each scenario evaluates all 3 methods; hit/miss conservation, total resident budget, and trace SHA identities are checked. |
| `test_reference_example_recorded_from_real_no_board_ci` | One frozen cell: 2 KiB, 16 neurons/block, 512 requests, 64 active IDs | Independent numerical regression for modeled transactions: clustered **individual/block/hybrid = 128/8/8**, dispersed **128/902/913**; dispersed block misses **451** and total bytes **230,912**. |
| `test_parameter_list_fails_closed` | Good `4,8,16`, bad empty/zero/negative/duplicate/noninteger/trailing-comma groups | Parsing rejects ambiguous and invalid sweep axes. |
| `test_invalid_sweep_cell_is_not_silently_skipped` | Nondivisible group size and insufficient resident capacity | The sweep fails rather than dropping an inconvenient configuration or quietly changing the experiment. |
| `test_cli_exclusive_create_does_not_overwrite` | Launch the sweep twice with the **same file path** in a temporary directory | First call succeeds; second refuses to overwrite; original JSON bytes remain exactly identical. |

The 24 scenarios are **modeled combinations**, not 24 physical runs or independent statistical repetitions.

## 4. What CI ran in addition to the 20 unit tests

GitHub workflow: `../../../../.github/workflows/neuromorphic_accelerator_m01_pc_only.yml` (path is repository-relative when viewed in Git).

1. **Python compilation:** `python3 -m compileall -q src scripts tests` checks source syntax.
2. **Native regression suite:** `python3 -m unittest discover -s tests -p "test_m01*.py" -v` runs all 20 committed tests without pytest, Vivado, Vitis, access to the KV260, or external packages.
3. **Two-locality CLI:** `scripts/m01_explore.py` creates a fresh JSON report; a separate Python block verifies the source-scope labels, identical 512-request accounting, resident budget and absence of default timing claims.
4. **Full 24-cell sweep CLI:** `scripts/m01_sweep.py` produces a separate JSON report; a Python block checks the 24 cells, correct PC-only labels and conservation/budget invariants.
5. **Fail-closed output/configuration checks:** the workflow intentionally attempts to overwrite the original output and to run invalid grouping; **both invocations must fail**.
6. **Artifact retention:** uploads the two original modeled-traffic JSON files as a GitHub Actions artifact (not hardware evidence).

The first CI attempt failed solely because the artifact upload used a malformed file path. A subsequent implementation revision corrected the upload path, and the tests exposed a fairness issue in hybrid pinned prefetch accounting. That modeling issue was fixed by coalescing contiguous prefix prefetch and adjacent dirty writes, updating the reference counts and rerunning CI. **The accepted source revision is the corrected implementation, not the first attempt.**

## 5. What was established — and what was not

**Established under the documented model:** deterministic case generation; capacity and transfer accounting; fail-closed invalid inputs; preserved output files; and a strong dependency of whole-block transfer counts on the spatial distribution of requested neurons, given the model assumptions.

**Not established:** which architecture has lower **real KV260 inference latency**; true DDR transaction latency, utilization or cache tag costs; LIF spike/state accuracy; event scheduling efficiency; physical achievable group size; synaptic-memory placement; board power or energy; acceleration versus v3 or YANA; or applicability to trained network spike patterns.

**Engineering decision accepted for next work:** use configurable **block-based residency as a provisional implementation baseline**, retain independent-neuron and hybrid models as mandatory alternatives/controls, and keep **neuron-state and synaptic-connectivity placement as separate design axes** until later measurements. This is **not** a claim that block caching always wins.

## 6. How to independently repeat it

~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m01-trade-study
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m01-trade-study
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m01*.py' -v
python3 scripts/m01_explore.py --seed 1 --locality both
python3 scripts/m01_sweep.py --seed 1 > /tmp/m01_example_pc_only.json
~~~

For **immutable SHA-pinned original evidence** rather than a disposable demonstration, follow [the no-overwrite operator runbook](M01_PC_ONLY_REPRODUCIBILITY_RUNBOOK.md), which creates timestamped files under `$HOME/Thesis_Evidence/` and computes SHA-256. Local user-verification reported PASS, but **no source-backed user-local JSON hashes were supplied to Git**, so no particular local evidence SHA is claimed here.

**Relevant source:** [M01 design/assumptions](M01_ARCHITECTURE_OPTIONS.md) · [v1 roadmap](../roadmap.md) · [M01 source](../src/neuromorphic_accelerator_v1/m01_residency.py). 
