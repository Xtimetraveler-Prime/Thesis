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
