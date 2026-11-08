# M03 — Native PC original evidence runbook (NO BOARD)

**M03 status:** COMPLETE / USER-ACCEPTED (PC-only scope). This remains the **repeatable archival verification runbook**; user reports test PASS, but individual user-local report hashes were not furnished. This executes only Python standard-library synthetic workloads and cache/traffic models; **no KV260, JTAG, Vivado/Vitis, PS DDR, MNIST TEST, real timing, actual DDR bandwidth, power or energy**.

## 1. Fetch accepted M03 from main and verify source

In Ubuntu VS Code terminal:

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main

cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 --version
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p "test_m03*.py" -v
python3 -m unittest discover -s tests -p "test_m02*.py" -q
python3 -m unittest discover -s tests -p "test_m01*.py" -q
~~~

Expected: **28 M03 tests**, **21 M02 tests**, **20 M01 tests** all PASS (test methods, some with many source-generated subcases), and no hardware activity. Note source HEAD SHA and any failing test method/case. CI and user-native tests are separate evidence.

## 2. Generate immutable original analytic reports outside Git

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
mkdir -p "$HOME/Thesis_Evidence"
export M03_RUN_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
export M03_EVIDENCE="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m03_pc_$M03_RUN_UTC"
mkdir "$M03_EVIDENCE" || exit 1

export M03_PAIR="$M03_EVIDENCE/m03_isomorphic_pair.json"
export M03_SWEEP="$M03_EVIDENCE/m03_36_paired_sweep.json"

python3 scripts/m03_explore.py \
  --neuron-count 128 --active-roles 16 \
  --fanout-per-active 4 --external-events-per-tick 6 \
  --ticks 16 --seed 20261107 \
  --state-bytes 16 --block-neurons 8 \
  --resident-budget-bytes 512 --onchip-capacity-bytes 2048 \
  --synapse-record-bytes 8 --max-transfer-bytes 256 \
  --policy block --locality both \
  --out "$M03_PAIR" || exit 1

python3 scripts/m03_sweep.py \
  --neuron-counts 64,128,256 \
  --fanouts 0,2,4 \
  --events-per-tick-values 0,3 \
  --seeds 17,23 \
  --active-roles 16 --ticks 10 \
  --out "$M03_SWEEP" || exit 1

sha256sum "$M03_PAIR" "$M03_SWEEP"
git rev-parse HEAD
git status --short
~~~

The evidence directory must be new, and the programs use Python exclusive-create file mode. Do not delete or overwrite files to make a rerun succeed; use a new timestamped directory. Source, output and run configuration are independent provenance fields. These JSON reports are **PC-only synthetic artifacts**, not hardware traces.

## 3. Independently check original records and functional equivalence

~~~bash
python3 - "$M03_PAIR" "$M03_SWEEP" <<'PY'
from pathlib import Path
import json, sys
pair = json.loads(Path(sys.argv[1]).read_text())
sweep = json.loads(Path(sys.argv[2]).read_text())
assert pair["schema"] == "m03-isomorphic-workload-comparison-v1"
assert pair["measurement_status"] == "PC_ONLY_FUNCTIONAL_ORACLE_AND_ANALYTICAL_TRAFFIC"
assert pair["isomorphic_pair_verified"] is True

a = pair["experimental_results"]["clustered"]
b = pair["experimental_results"]["dispersed"]
assert a["canonical_role_workload_sha256"] == b["canonical_role_workload_sha256"]
assert a["canonical_functional_trace_sha256"] == b["canonical_functional_trace_sha256"]
assert a["relabeled_network_input_sha256"] != b["relabeled_network_input_sha256"]
assert a["neural_equivalence"]["exact_sparse_neuron_updates"] == 213
assert b["neural_equivalence"]["exact_sparse_neuron_updates"] == 213
assert a["neural_equivalence"]["dense_neuron_updates"] == 2048
assert a["neural_equivalence"]["total_edge_traversals_when_spiking"] == 260
for name, row in (("clustered", a), ("dispersed", b)):
    assert row["neural_equivalence"]["dense_vs_M02_queued"]
    assert row["neural_equivalence"]["dense_vs_M03_sparse_exact"]
    assert len(row["four_way_models"]) == 4
    for mode, values in row["four_way_models"].items():
        assert values["available"]
        print("M03_PC_TRAFFIC",name,mode,
              "updates",values["evaluated_neuron_steps"],
              "state_R",values["state_read_bytes"],
              "state_W",values["state_write_bytes"],
              "synapse_R",values["synapse_read_bytes"],
              "tx",values["total_modeled_transactions"])
assert a["four_way_models"]["event/ddr"]["total_modeled_transactions"] == 69
assert b["four_way_models"]["event/ddr"]["total_modeled_transactions"] == 491

assert sweep["schema"] == "m03-fixed-work-activity-locality-sweep-v1"
assert sweep["status"] == "PC_ONLY_4_WAY_ANALYTICAL_TRAFFIC_NOT_HARDWARE"
assert sweep["paired_role_isomorphic_cases"] == 36
assert len(sweep["grid"]) == 36
assert sweep["independent_pc_seed_count"] == 2
for row in sweep["grid"]:
    assert row["dense_neuron_updates"] == row["neuron_count"] * row["ticks"]
    assert row["exact_sparse_neuron_updates"] <= row["dense_neuron_updates"]
    for locality in ("clustered","dispersed"):
        values = row["cases"][locality]
        assert len(values) == 4
        assert values["event/ddr"]["available"]
        assert values["timestep/ddr"]["available"]
        if row["neuron_count"] == 256:
            assert not values["event/onchip"]["available"]
            assert not values["timestep/onchip"]["available"]
print("M03_ORIGINAL_PC_ISOMORPHIC_NEURAL_AND_TRAFFIC_PASS=1")
PY
~~~

**Expected output:** positive source-only oracle parity and modeled counters. Never report 69/491 or any other modeled transaction ratio as actual latency or speed.

## 4. Read and approve the measurement contract, not performance claims

Review [M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md](M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md) and [M03_TESTS_EXPLAINED.md](M03_TESTS_EXPLAINED.md).

M03 deliberately separates model knobs: N, active K, fanout, input pulses/tick, seed, neuron-ID locality, state-cache bytes, block size, synaptic record bytes and onchip capacity. The four-way rows are *analytical scenarios*; actual matched FPGA timesteps vs events, memory transfers, physical resource use, timer boundaries, coldboots, buffer ownership and power sensors remain M04–M09 hardware matters. A synthetic workload is not a trained accuracy benchmark.

M03 was accepted on user-reported native PASS and approval of its PC-only experimental scope. For optional repeat verification, report (1) native test summaries, (2) main HEAD commit SHA, and (3) both original JSON SHA256s if generated. **Next: M04 HLS reuse investigation, not physical board operations**; see [handoff seed](M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md). No JTAG, ELF, FPGA or DDR action is necessary or authorized.
