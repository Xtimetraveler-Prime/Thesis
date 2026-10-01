#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
FINAL_DIR="$ARTIFACT_ROOT/p08_5_3_final_closure"
CANDIDATE_A="$ARTIFACT_ROOT/.p08_5_3_final_closure_a"
CANDIDATE_B="$ARTIFACT_ROOT/.p08_5_3_final_closure_b"

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
        "ERROR: P08.5.3 requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/comparison_ledger.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/final_comparison.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/final_closure.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_p08_5_comparison_ledger.py \
    applications/mnist_v2_nxtf/tests/test_p08_5_final_comparison.py \
    applications/mnist_v2_nxtf/tests/test_p08_5_final_closure.py

rm -rf "$CANDIDATE_A" "$CANDIDATE_B"
mkdir -p "$CANDIDATE_A" "$CANDIDATE_B"

python -m mnist_v2_nxtf.final_closure --output-dir "$CANDIDATE_A"
python -m mnist_v2_nxtf.final_closure --output-dir "$CANDIDATE_B" >/dev/null

for artifact in p08_final_closure.json p08_final_closure.md; do
    cmp "$CANDIDATE_A/$artifact" "$CANDIDATE_B/$artifact" || {
        echo "ERROR: P08.5.3 closure artifact is not deterministic: $artifact" >&2
        exit 1
    }
done

P08_5_3_DIR="$CANDIDATE_A" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from mnist_v2_nxtf.final_closure import (
    ACCEPTED_LEDGER_FINGERPRINT,
    ACCEPTED_MERGES,
    ACCEPTED_REPORT_FINGERPRINT,
    CLOSURE_SCHEMA,
    CLOSURE_STATUS,
    EXPECTED_RESULTS,
    REQUIRED_NONCLAIMS,
)

root = Path(os.environ["P08_5_3_DIR"])
json_path = root / "p08_final_closure.json"
md_path = root / "p08_final_closure.md"
if not json_path.is_file() or not md_path.is_file():
    raise SystemExit("ERROR: P08.5.3 generated closure artifacts are missing")

closure = json.loads(json_path.read_text(encoding="utf-8"))
if closure.get("schema") != CLOSURE_SCHEMA or closure.get("status") != CLOSURE_STATUS:
    raise SystemExit("ERROR: P08.5.3 schema/status drifted")
if closure.get("p08_complete") is not False:
    raise SystemExit("ERROR: P08 completion must remain pending until independent acceptance")
if closure.get("accepted_ledger_fingerprint") != ACCEPTED_LEDGER_FINGERPRINT:
    raise SystemExit("ERROR: P08.5.3 ledger fingerprint binding drifted")
if closure.get("accepted_report_fingerprint") != ACCEPTED_REPORT_FINGERPRINT:
    raise SystemExit("ERROR: P08.5.3 report fingerprint binding drifted")
if closure.get("accepted_merge_commits") != ACCEPTED_MERGES:
    raise SystemExit("ERROR: P08.5.3 accepted merge binding drifted")
if closure.get("results") != EXPECTED_RESULTS:
    raise SystemExit("ERROR: P08.5.3 final result summary drifted")
if tuple(closure.get("explicit_nonclaims", [])) != REQUIRED_NONCLAIMS:
    raise SystemExit("ERROR: P08.5.3 explicit non-claim set drifted")
if set(closure.get("guardrails", {}).values()) != {False}:
    raise SystemExit("ERROR: P08.5.3 overclaim guardrail became true")
if len(closure.get("evidence_chain", [])) != 8:
    raise SystemExit("ERROR: P08.5.3 evidence-chain length drifted")

payload = dict(closure)
recorded = payload.pop("closure_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.5.3 closure fingerprint does not recompute")

r = closure["results"]
print(f"PASS: P08.5.3 deterministic closure fingerprint={recorded}")
print(
    "PASS: P08.5.3 accepted chain "
    f"ledger={ACCEPTED_LEDGER_FINGERPRINT} report={ACCEPTED_REPORT_FINGERPRINT} "
    f"p08_4_merge={ACCEPTED_MERGES['p08_4']} p08_5_1_merge={ACCEPTED_MERGES['p08_5_1']} "
    f"p08_5_2_merge={ACCEPTED_MERGES['p08_5_2']}"
)
print(
    "PASS: P08.5.3 frozen result "
    f"ann={r['ann_test_accuracy']:.6f} snn={r['snn_test_accuracy']:.6f} "
    f"delta={r['ann_to_snn_accuracy_drop']:.6f} timesteps={r['primary_timesteps']}"
)
print(
    "PASS: P08.5.3 architecture scope "
    f"neurons={r['neurons']} params={r['trainable_parameters']} expanded={r['expanded_connections']} "
    f"logical_cores={r['logical_cores']} resident_contexts={r['resident_contexts']} physical_engines={r['physical_engines']}"
)
print(
    "PASS: P08.5.3 physical scope "
    f"full_compiled_100_timestep=true representative_k26_dispatch=true "
    f"dispatch_cycles={r['physical_dispatch_cycles']} dispatch_us={r['physical_dispatch_us']:.2f} full_jtag_replay=false"
)
print(
    "PASS: P08.5.3 thesis boundary "
    "exact_paper_topology=false native_storage_equivalence=false energy_direct=false latency_direct=false "
    "shared_weight_ratio=false mapped_core_ratio=false dispatch_is_sample_latency=false "
    "physical_async_equivalence=false post_test_tuning=false"
)
print("PASS: P08.5.3 completion candidate_ready=true p08_complete=false independent_acceptance_required=true")
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_A" "$FINAL_DIR"
rm -rf "$CANDIDATE_B"

echo
echo "P08.5.3 final-closure gate completed successfully."
echo "Closure JSON: $FINAL_DIR/p08_final_closure.json"
echo "Closure report: $FINAL_DIR/p08_final_closure.md"
