# M07 source-only verification runbook — November 10, 2026

**Branch:** `agent/neuromorphic-accelerator-v1-m07-cache-baselines` created from actual `main` commit `a33c717f4101e248dd56637e5188682872fe83c6`. M07 remains in progress and MUST NOT be merged without owner review/approval.

## Linux VS Code terminal — NO hardware access

From the owner's existing `~/Git/Thesis` checkout, first ensure local changes are committed or stashed; do not discard uncommitted owner work.

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m07-cache-baselines
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m07-cache-baselines
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -p 'test_m02*.py' -v
python3 -m unittest discover -s tests -p 'test_m03*.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 -m unittest discover -s tests -v
~~~

Optional local RTL functional regression **only where Icarus/vvp are installed**. The inherited M06 GitHub Actions job already provides its local Icarus regressions; a missing Icarus binary may cause local skips. **Do not rerun existing accepted original Vivado/Vitis owner gates** merely for this source-only M07 policy addition.

### Local combined-suite import regression and M07.2 matched controls

The owner's initial full-suite run reported **one error**: `test_m06_paged_hls_tooling` imported the M05 helper named `prepare_hls_config` because combined unittest discovery shares Python's module cache. That test now explicitly imports its intended M06 helper by file location; no M05/M06 HLS tool script or top allowlist was changed. Re-run the **full** discovery, not only individually filtered milestones, to verify import-order safety.

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_paged_hls_tooling.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v
~~~

Generate the M07.2 model-only matched pair using a **unique filename** in your existing evidence folder:

~~~bash
mkdir -p "$HOME/Thesis_Evidence/M07"
OUT="$HOME/Thesis_Evidence/M07/m07_2_four_way_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_four_way.py --output "$OUT"
sha256sum "$OUT"
~~~

This runs two locality mappings, two policies, and all four M03 logical controls per policy. State traffic is from the M06 Python paging model, timestep state updates are guided by independently verified M02 dense voltages, and DDR-style adjacency traffic is M03 *analytical* only. No original vendor simulation, physical DDR transfer or measured hardware time is performed. For an above-capacity case:

~~~bash
OUT="$HOME/Thesis_Evidence/M07/m07_2_capacity_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_four_way.py --neurons 256 --active-roles 16 --output "$OUT"
sha256sum "$OUT"
~~~

With the default 2048 B full-onchip capacity and 16 B/record, a 256-neuron on-chip comparator is explicitly marked unavailable; the DDR-style source models continue. Check `docs/M07_TESTS_EXPLAINED.md` for per-test objectives and honest simulation boundaries.

### M07.3 fixed-capacity / block-width / locality ablations (NO BOARD)

After pulling the latest M07 branch, reproduce the exact CI model-only sweep on Linux. The default experiment is documented as `M07.3-GRID-A` in `docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md`: 2 independent PC seeds × 3 resident byte budgets × 3 block widths × 2 locality maps × 2 policies × 4 logical controls. Neither YANA's original RTL nor a measured YANA/KV260 performance point is involved.

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m07-cache-baselines
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m07-cache-baselines
git rev-parse HEAD

cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -p 'test_m02*.py' -v
python3 -m unittest discover -s tests -p 'test_m03*.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 -m unittest discover -s tests -v
~~~

Preserve **a new** unique JSON file and its SHA256 in the original evidence directory, NOT in the Git checkout. If another run starts in the exact same second, choose a different output name rather than overwriting.

~~~bash
mkdir -p "$HOME/Thesis_Evidence/M07"
OUT="$HOME/Thesis_Evidence/M07/m07_3_grid_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_ablation.py --output "$OUT"
sha256sum "$OUT"
~~~

Expected default schema `m07-residency-locality-ablation-v1`, `num_parameter_combinations=18`, `num_policy_locality_four_way_rows=288`, and `physical_hardware_measured=false`. The JSON contains SHA256s of 11 actual Python source/CLI files, seeds, block/budget/slot settings and role-canonical neural hashes. Each exact per-mode counter is a **software page movement** or a **separately estimated M03 synapse access**, not an observed AXI transaction or FPGA runtime.

For smaller one-seed reproduction before the complete grid:

~~~bash
OUT="$HOME/Thesis_Evidence/M07/m07_3_mini_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_ablation.py --neurons 32 --active-roles 8 --ticks 6 --seeds 17 --blocks 2,4 --budgets 128,256 --onchip-capacity-bytes 1024 --output "$OUT"
sha256sum "$OUT"
~~~

### YANA-count-only partial configuration overlap (do not compare performance)

This **optional** experiment deliberately matches only the YANA paper's **1,024 logical neurons per core capacity parameter**. Our signed16 M02 4-tick input, 16KiB canonical state, 256B bytearray cache, off-chip-style state paging and *unavailable* full-on-chip controls are **not** YANA's fixed-point/LUT leak, KR260 placed-and-routed core, resource utilization or hardware latency. The result is HOST ONLY; see `docs/M07_PRIOR_ART_CONFIGURATION_COMPARISON.md` entry `M07.3-YANA-COUNT-ONLY`.

~~~bash
OUT="$HOME/Thesis_Evidence/M07/m07_3_yana_count_only_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_ablation.py \
  --neurons 1024 --active-roles 16 --ticks 4 \
  --fanout 2 --events-per-tick 4 --seeds 17 \
  --blocks 8,16 --budgets 256 --onchip-capacity-bytes 2048 \
  --output "$OUT"
sha256sum "$OUT"
~~~

Check `num_parameter_combinations=2`, `num_policy_locality_four_way_rows=32`, both full-onchip controls unavailable, and `performance_or_yana_equivalence_claim=false`. This test does NOT execute YANA itself or any FPGA/Vivado/Vitis/JTAG operation.

Optional read-only CI inspection:

~~~bash
cd ~/Git/Thesis
gh run list --branch agent/neuromorphic-accelerator-v1-m07-cache-baselines --limit 20
gh pr view 82 --json isDraft,state,headRefOid,statusCheckRollup
~~~

The source-only experiment intentionally does **not** model event batching, queue service time, B-before-AR cycle latency, external synapse transfer issued by the pager, or FPGA cache-tag area. Preserve `M07.3` as in-progress until owner verification and additional acceptance gates. Previously accepted original M05/M06 Vitis 2025.2 archives and M06 XSim owner gates must not be rerun without a separate technical reason.

### M07.4 single causal activity-history policy pilot (NO BOARD, NO VITIS)

Pull the existing M07 branch with `git status --short; git fetch origin; git switch agent/neuromorphic-accelerator-v1-m07-cache-baselines; git pull --ff-only origin agent/neuromorphic-accelerator-v1-m07-cache-baselines` from `~/Git/Thesis`. Do not discard uncommitted local changes.

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
git rev-parse HEAD
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m07_activity_history.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -p 'test_m02*.py' -v
python3 -m unittest discover -s tests -p 'test_m03*.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 -m unittest discover -s tests -v
~~~

Source-only M07.4 JSON (2 fixed synthetic seeds × 4 block/budget pairs × 2 localities × 3 history depths = **48 matched comparisons**):

~~~bash
mkdir -p "$HOME/Thesis_Evidence/M07"
OUT="$HOME/Thesis_Evidence/M07/m07_4_history_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_activity_pilot.py --output "$OUT"
sha256sum "$OUT"
~~~

The source report uses exclusive creation and includes SHA256 hashes of 10 source/CLI files. Verify `geometry_seed_cases=8`, `policy_history_comparisons=48`, `lookahead=false`, `reordered_deliveries=false`, and `service_cycles=null`. Check both non-neural access-pattern controls: a hot-page reuse scenario in which history beats LRU **and** an obsolete-hot-page counterexample in which LRU beats history. Both must produce identical modeled canonical end state. The M03 neural fixtures independently match M02 dense/queued and M03 sparse exactly; the non-neural controls are *not* neural inference tests.

A quick one-seed/two-geometry report for inspecting details:

~~~bash
OUT="$HOME/Thesis_Evidence/M07/m07_4_small_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_activity_pilot.py --neurons 32 --active-roles 8 \
  --ticks 6 --seeds 17 --geometries 2:64,4:128 \
  --history-depths 2,8 --onchip-capacity-bytes 1024 --output "$OUT"
sha256sum "$OUT"
~~~

**Interpretation caution:** `state_bytes_saved_vs_lru` is the signed **software canonical-state byte count difference**, not time saved. Additional history SRAM and victim-scan hardware/controller cycles are **uncosted**, so it is invalid to infer resource-matched throughput, energy or area. The separately described YANA hot-neuron FIFO/pipeline is not implemented or executed. Before an M07 hardware-service-time conclusion, we will need **owner-authorized evidence** about actual M06 B-before-AR/AXI service timing, queue depths, and implementation costs; not required for the current source-only causal pilot. Do not rerun original M06 Vivado/Vitis vendor gates or touch JTAG/physical DDR without separate authorization.

### Preserve a new model-only artifact

~~~bash
mkdir -p "$HOME/Thesis_Evidence/M07"
OUT="$HOME/Thesis_Evidence/M07/m07_1_source_only_$(date -u +%Y%m%dT%H%M%SZ).json"
python3 scripts/m07_cache_baseline.py --output "$OUT"
sha256sum "$OUT"
~~~

The script uses exclusive file creation; repeating the same output path fails rather than overwriting evidence. Archive the exact commit SHA, console results, optional skip counts and model JSON SHA in a new timestamped receipt. This JSON contains emulated state page traffic, **NOT** DDR physical measurements. Original M05/M06 owner ZIPs in `~/Thesis_Evidence` must remain immutable.

### Review CI (read-only)

~~~bash
cd ~/Git/Thesis
gh pr status
gh run list --branch agent/neuromorphic-accelerator-v1-m07-cache-baselines --limit 20
# For a specific run returned above:
gh run view <RUN_ID> --log-failed
~~~

Use GitHub Actions jobs from the exact HEAD, and record PASS/FAIL/SKIP. `gh` commands require the GitHub CLI and an authenticated session. If `gh` is unavailable, open the repository Actions and M07 draft PR checks in the GitHub web UI.

**Verification boundaries:** Python M02/M03/M06/M07 host tests establish source correctness. Icarus `iverilog/vvp` establishes local standalone RTL behavior only. Any declaration-only fake-stub compile says nothing about functional AMD/HLS. Previous genuine Vivado/Vitis 2025.2 simulations are accepted as M05/M06 evidence and are not a new M07 result. Physical KV260, JTAG, PS halt, DDR writes, bitstream programming, and PS Linux memory ownership are not authorized.
