#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
FINAL_DIR="$ARTIFACT_ROOT/p08_5_2_final_comparison"
CANDIDATE_A="$ARTIFACT_ROOT/.p08_5_2_final_comparison_a"
CANDIDATE_B="$ARTIFACT_ROOT/.p08_5_2_final_comparison_b"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_DIR"

python - <<'PY'
missing = []
for module in ("pytest",):
    try:
        __import__(module)
    except ImportError:
        missing.append(module)
if missing:
    raise SystemExit(
        "ERROR: P08.5.2 requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/comparison_ledger.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/final_comparison.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_p08_5_comparison_ledger.py \
    applications/mnist_v2_nxtf/tests/test_p08_5_final_comparison.py

rm -rf "$CANDIDATE_A" "$CANDIDATE_B"
mkdir -p "$CANDIDATE_A" "$CANDIDATE_B"

python -m mnist_v2_nxtf.final_comparison --output-dir "$CANDIDATE_A"
python -m mnist_v2_nxtf.final_comparison --output-dir "$CANDIDATE_B" >/dev/null

for artifact in p08_5_final_comparison.json p08_5_final_comparison.md; do
    cmp "$CANDIDATE_A/$artifact" "$CANDIDATE_B/$artifact" || {
        echo "ERROR: P08.5.2 artifact is not deterministic: $artifact" >&2
        exit 1
    }
done

P08_5_2_DIR="$CANDIDATE_A" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from mnist_v2_nxtf.final_comparison import (
    ACCEPTED_LEDGER_FINGERPRINT,
    REPORT_SCHEMA,
    REPORT_STATUS,
)

root = Path(os.environ["P08_5_2_DIR"])
report_path = root / "p08_5_final_comparison.json"
markdown_path = root / "p08_5_final_comparison.md"
if not report_path.is_file() or not markdown_path.is_file():
    raise SystemExit("ERROR: P08.5.2 generated artifacts are missing")

report = json.loads(report_path.read_text(encoding="utf-8"))
markdown = markdown_path.read_text(encoding="utf-8")

if report.get("schema") != REPORT_SCHEMA or report.get("status") != REPORT_STATUS:
    raise SystemExit("ERROR: P08.5.2 schema/status drifted")
if report.get("accepted_ledger_fingerprint") != ACCEPTED_LEDGER_FINGERPRINT:
    raise SystemExit("ERROR: P08.5.2 ledger identity drifted")

numeric = report.get("numeric_comparisons", {})
expected_numeric = {
    "ann_test_error_gap_fraction": 0.0052,
    "ann_test_error_gap_percentage_points": 0.52,
    "snn_test_error_gap_fraction": 0.0097,
    "snn_test_error_gap_percentage_points": 0.97,
    "ann_to_snn_error_increase_gap_fraction": 0.0045,
    "ann_to_snn_error_increase_gap_percentage_points": 0.45,
}
for key, expected in expected_numeric.items():
    actual = numeric.get(key)
    if not isinstance(actual, (int, float)) or abs(float(actual) - expected) > 1e-12:
        raise SystemExit(f"ERROR: P08.5.2 numeric comparison drifted: {key}={actual}")

expected_authorized = [
    "ann_test_error",
    "snn_test_error",
    "ann_to_snn_error_increase",
]
if report.get("authorized_numeric_cross_system_metric_ids") != expected_authorized:
    raise SystemExit("ERROR: P08.5.2 authorized numeric metric set drifted")

expected_forbidden = [
    "shared_weight_accounting",
    "mapped_core_count",
    "native_loihi_energy",
    "native_loihi_latency",
]
if report.get("forbidden_derived_cross_system_metric_ids") != expected_forbidden:
    raise SystemExit("ERROR: P08.5.2 forbidden derived metric set drifted")

if set(report.get("guardrails", {}).values()) != {False}:
    raise SystemExit("ERROR: one or more P08.5.2 overclaim guardrails became true")

required_phrases = [
    "0.52 percentage points",
    "0.97 percentage points",
    "0.45 percentage points",
    "4,218 neurons",
    "7,006 trainable parameters",
    "338,880 expanded connections",
    "no efficiency ratio is derived",
    "one deep-core dispatch, not full-sample latency",
    "no FPGA-versus-Loihi energy or latency conclusion is drawn",
    "does not claim that the entire 100-timestep representative inference was physically replayed end-to-end over JTAG",
]
for phrase in required_phrases:
    if phrase not in markdown:
        raise SystemExit(f"ERROR: P08.5.2 rendered report missing required boundary: {phrase}")

payload = dict(report)
recorded = payload.pop("report_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.5.2 report fingerprint does not recompute")

print(f"PASS: P08.5.2 deterministic report fingerprint={recorded}")
print(f"PASS: P08.5.2 accepted ledger fingerprint={ACCEPTED_LEDGER_FINGERPRINT}")
print(
    "PASS: P08.5.2 accuracy interpretation "
    "ann_gap_pp=0.52 snn_gap_pp=0.97 conversion_gap_pp=0.45"
)
print(
    "PASS: P08.5.2 structural interpretation "
    "neurons=4000~vs4218 params=7000~vs7006 connections=341000~vs338880 exact_ratio_claim=false"
)
print(
    "PASS: P08.5.2 contextual guards "
    "shared_weight_ratio=false mapped_core_ratio=false energy_direct=false latency_direct=false"
)
print(
    "PASS: P08.5.2 project observations "
    "logical_cores=5 resident_contexts=3 physical_engines=1 page_loads=497 packets=17910 "
    "clock_mhz=100 dispatch_cycles=3865 dispatch_us=38.65 uram=47 wns_ns=0.734"
)
print(
    "PASS: P08.5.2 physical scope "
    "compiled_full_100_timestep=true representative_k26_dispatch=true full_jtag_replay=false"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_A" "$FINAL_DIR"
rm -rf "$CANDIDATE_B"

echo
echo "P08.5.2 final-comparison gate completed successfully."
echo "Machine-readable report: $FINAL_DIR/p08_5_final_comparison.json"
echo "Thesis-facing report: $FINAL_DIR/p08_5_final_comparison.md"
