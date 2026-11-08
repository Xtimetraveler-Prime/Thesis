# M01 PC-only verification and immutable synthetic evidence runbook

**Status:** First-generation model/trade study; no real KV260 measurements, firmware, physical JTAG, DDR allocation, inference latency or LIF engine. **Do not** run old Loihi v3 hardware JTAG scripts. User verification is requested **before** M01 scientific/architecture signoff; this runbook creates only local JSON reports in an external directory.

## 1. Fetch the current M01 development branch

From Ubuntu VS Code terminal:

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m01-trade-study
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m01-trade-study

cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 --version
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m01*.py' -v
~~~

The M01 code uses only the Python standard library. If the existing .venv-p08 has pytest, the equivalent optional run is:

~~~bash
source ~/Git/Thesis/.venv-p08/bin/activate
python3 -m pytest -q -rs tests/test_m01_residency.py tests/test_m01_sweep.py
~~~

**Expected native result:** at least the committed **20 tests**, zero failures, and no board activity. Source/workflow CI is distinct from actual user PC verification.

## 2. Produce brand-new SHA-pinned synthetic reports OUTSIDE Git

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1

mkdir -p "$HOME/Thesis_Evidence"
export M01_RUN_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
export M01_EVIDENCE="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m01_pc_$M01_RUN_UTC"

# Exclusive-create directory: do not risk overwriting original evidence.
mkdir "$M01_EVIDENCE" || exit 1

export M01_SINGLE="$M01_EVIDENCE/m01_two_localities_pc_only.json"
export M01_SWEEP="$M01_EVIDENCE/m01_capacity_block_locality_pc_only.json"

python3 scripts/m01_explore.py \
  --neuron-count 4096 --active-neurons 64 --requests 512 \
  --state-bytes 16 --resident-budget-bytes 2048 \
  --block-neurons 16 --hybrid-pinned-neurons 32 \
  --max-transfer-bytes 256 --seed 1 --locality both \
  --out "$M01_SINGLE" || exit 1

python3 scripts/m01_sweep.py \
  --neuron-count 4096 --active-neurons 64 --requests 512 \
  --state-bytes 16 --pinned-neurons 32 --max-transfer-bytes 256 \
  --block-sizes 4,8,16,32 --resident-budgets 1024,2048,4096 \
  --seed 1 --out "$M01_SWEEP" || exit 1

sha256sum "$M01_SINGLE" "$M01_SWEEP"
git log -1 --format='%H'
git status --short
~~~

The sources reject invalid grouping and budget combinations; JSON output is written in exclusive-create mode and **must not replace original bytes**. Generated synthetic result JSON is not board-generated neural evidence; record source commit and SHA separately.

## 3. Independently inspect the key accounting quantities

~~~bash
python3 - "$M01_SINGLE" "$M01_SWEEP" <<'PY'
import json
from pathlib import Path
import sys
single = json.loads(Path(sys.argv[1]).read_text())
sweep = json.loads(Path(sys.argv[2]).read_text())
assert single["experiment"] == "M01_COLD_STATE_RESIDENCY_PC_ONLY"
assert sweep["status"] == "PC_ONLY_ANALYTICAL_TRAFFIC_NOT_REAL_DDR_OR_SNN"
assert len(sweep["grid"]) == 24

for locality, study in single["studies"].items():
    assert study["measurement_status"] == "PC_ONLY_TRAFFIC_ACCOUNTING_NOT_HARDWARE_MEASURED"
    assert study["trace"]["requests"] == 512
    print(f"LOCALITY={locality} TRACE_SHA256={study['trace']['sha256']}")
    for name, m in study["results"].items():
        assert m["resident_hits"] + m["misses"] == 512
        assert m["allocated_resident_bytes"] <= study["config"]["resident_budget_bytes"]
        assert "hypothetical_serial_memory_ns" not in m
        print(f"  {name:12s} total_bytes={m['total_bytes']:7d} "
              f"transactions={m['total_transactions']:4d} "
              f"misses={m['misses']:4d} evictions={m['evictions']:4d}")
print("M01_OPERATOR_INDEPENDENT_PC_JSON_STRUCTURE_PASS=1")
PY
~~~

**Expected synthetic reference counts at this exact frozen parameter set:** clustered individual 128, block 8, hybrid 8 transactions; dispersed individual 128, block 902, hybrid 913. These are NOT measured speedups or true DDR transactions. If a count changes, stop and investigate source/config drift; do not edit the original reports to make them pass.

## 4. Interpret correctly

Each modeled request represents one **state-modifying access**, not an input spike, fanout traversal, synapse operation, timed LIF update, inference timestep, sample, or independent physical run. The synthetic generator holds update multiplicities and order-roles fixed while moving the targeted logical neuron IDs between clustered/dispersed mappings. Pinned-prefix selection is disclosed in advance and never trained on evaluation outputs. The shared resident-state budget **excludes tag/queue/controller resource costs**, whose effect could reverse rankings on real hardware.

The optional illustrative transaction-overhead/bandwidth knobs are **not calibrated KV260 values** and are absent from default outputs. Synaptic memory placement, actual DMA/DDR burst splitting, on-chip BRAM/URAM budget, LIF semantics and training/accuracy benchmarks remain unresolved; see [architecture options](M01_ARCHITECTURE_OPTIONS.md) and [v1 roadmap](../roadmap.md).

When replying with M01 evidence, return the native test summary, last commit SHA, both JSON SHA256s, and any discrepancies. No hardware action is requested or authorized. The next decision is to accept or revise the **provisional** block-based residency baseline while retaining individual/hybrid control configurations; M02 independent neural semantics must be defined before coding a real event scheduler.
