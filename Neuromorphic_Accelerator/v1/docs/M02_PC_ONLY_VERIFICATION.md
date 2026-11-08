# M02 — Native PC functional reference verification (NO BOARD)

**Status:** Pending independent user-native PASS and approval of the **provisional M02 LIF numerical contract**. This is solely a Python neural-reference exercise; no JTAG, Vivado, Vitis, DDR, PL, PS/A53, board power or MNIST TEST access.

## 1. Fetch the M02 branch safely

Run in your existing Ubuntu VS Code terminal:

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m02-lif-reference
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m02-lif-reference

cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 --version
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p "test_m02*.py" -v
python3 -m unittest discover -s tests -p "test_m01*.py" -q
~~~

**Expected:** **21** M02 native tests pass; the accepted **20** M01 tests also pass independently. Both are standard-library tests and need no Python package installation. If Python is older than the type-annotation syntax in v1, use the existing project virtual environment with Python 3.10+; do not silently change semantics.

## 2. Create original, never-overwritten M02 results in external evidence directory

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1

mkdir -p "$HOME/Thesis_Evidence"
export M02_RUN_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
export M02_EVIDENCE="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m02_pc_$M02_RUN_UTC"
mkdir "$M02_EVIDENCE" || exit 1

export M02_REPORT="$M02_EVIDENCE/m02_original_dense_vs_queued_reference.json"
python3 scripts/m02_reference_check.py \
  --seed 20261107 \
  --random-cases 50 \
  --out "$M02_REPORT" || exit 1

sha256sum "$M02_REPORT"
git rev-parse HEAD
git status --short
~~~

The CLI uses exclusive-create mode for output, so rerunning the same path **must fail rather than overwrite the original file**. Its 54 cases comprise **4 hand-curated examples and 50 deterministic generated networks**. The report contains independently comparable dense/event-queued trace hashes and input SHA256s; these are **PC-only software traces**, not hardware measurements.

## 3. Independent structure and hard-fixture acceptance

~~~bash
python3 - "$M02_REPORT" <<'PY'
from pathlib import Path
import json, sys
p = Path(sys.argv[1])
report = json.loads(p.read_text())
assert report["status"] == "PC_ONLY_PROVISIONAL_M02_REFERENCE_NO_HARDWARE"
assert report["total_cases"] == 54
assert report["random_cases"] == 50
assert len(report["cases"]) == 54
assert all(case["equal_dense_vs_event_queue"] for case in report["cases"])

assert report["cases"][0]["case"] == "threshold_equality"
assert report["cases"][0]["voltage_rows"] == [[3], [0], [2], [1]]
assert report["cases"][0]["emitted_spikes"] == [[1, 0]]

assert report["cases"][1]["case"] == "autonomous_bias_no_input"
assert report["cases"][1]["emitted_spikes"] == [[1, 0], [3, 0]]

assert report["cases"][2]["case"] == "positive_delay_recurrent_loop"
assert report["cases"][2]["emitted_spikes"] == [[0, 0], [2, 1], [3, 0]]

for case in report["cases"]:
    assert len(case["network_and_input_sha256"]) == 64
    assert len(case["voltage_spike_trace_sha256"]) == 64
    assert len(case["voltage_rows"]) == case["ticks"]
    assert len(case["spike_rows"]) == case["ticks"]

print("M02_USER_PC_INDEPENDENT_REFERENCE_REPORT_PASS=1")
PY
~~~

If any result differs, **do not modify the original output**. Report first-mismatch, source commit SHA and report checksum so the source discrepancy can be investigated.

## 4. Review this contract before accepting M02

Read [M02_PROVISIONAL_LIF_CONTRACT.md](M02_PROVISIONAL_LIF_CONTRACT.md) and [M02_TESTS_EXPLAINED.md](M02_TESTS_EXPLAINED.md).

The user should explicitly confirm or request changes to this first-stage mathematical model:

- Integer signed fixed-point **membrane voltage**, default 16 bits; global rational leak \`numerator/denominator\` rounded **toward zero each timestep**.
- Per-neuron bias, threshold, initial/reset voltage; all incoming signed currents for one target/tick summed **before** 1× saturation, threshold comparison **inclusive**, then fixed reset.
- External input specified as signed current pulses, not presynaptic input-axon spikes; **recurrent** edges supported only with **positive timestep delay >=1**.
- No separate decaying synaptic-current variable, refractory period, subtractive reset or zero-time synaptic propagation **in v1's first reference**.
- Update every neuron each tick, including quiet neurons. Event-driven implementation schedules synapse deliveries; it **does not** yet skip quiet neuron dynamics.

These are explicit **M02 implementation proposals**, not properties of Loihi, YANA or the old v3 model. Later hardware must implement the accepted model or an explicitly documented numerical variation. In particular, moving to truly lazy event-driven neuron updates requires **proof of functional equivalence** or an approved revised neural contract.

**M02 stays ACTIVE/NOT ACCEPTED until the user reports native PASS and reviews the proposed semantics.** No real board work or original MNIST TEST execution is requested.
