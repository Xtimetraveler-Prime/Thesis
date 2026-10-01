#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"
ARTIFACT_ROOT="$APP_DIR/artifacts"
FINAL_DIR="$ARTIFACT_ROOT/p08_5_1_comparison_ledger"
CANDIDATE_A="$ARTIFACT_ROOT/.p08_5_1_comparison_ledger_a"
CANDIDATE_B="$ARTIFACT_ROOT/.p08_5_1_comparison_ledger_b"

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
        "ERROR: P08.5.1 requires the dedicated .venv-p08 environment "
        "(missing: %s)." % ", ".join(missing)
    )
PY

python -m py_compile applications/mnist_v2_nxtf/mnist_v2_nxtf/comparison_ledger.py
python -m pytest -q applications/mnist_v2_nxtf/tests/test_p08_5_comparison_ledger.py

rm -rf "$CANDIDATE_A" "$CANDIDATE_B"
mkdir -p "$CANDIDATE_A" "$CANDIDATE_B"

python -m mnist_v2_nxtf.comparison_ledger --output-dir "$CANDIDATE_A"
python -m mnist_v2_nxtf.comparison_ledger --output-dir "$CANDIDATE_B" >/dev/null

for artifact in p08_5_comparison_ledger.json p08_5_comparison_table.md; do
    cmp "$CANDIDATE_A/$artifact" "$CANDIDATE_B/$artifact" || {
        echo "ERROR: P08.5.1 artifact is not deterministic: $artifact" >&2
        exit 1
    }
done

P08_5_1_DIR="$CANDIDATE_A" python - <<'PY'
from __future__ import annotations

import hashlib
import json
import os
from collections import Counter
from pathlib import Path

from mnist_v2_nxtf.comparison_ledger import (
    ACCEPTED_IDENTITIES,
    COMPARABLE_WITH_RECONSTRUCTION_CAVEAT,
    CONTEXT_ONLY,
    DIRECTLY_COMPARABLE,
    LEDGER_SCHEMA,
    LEDGER_STATUS,
    NOT_COMPARABLE,
    PROJECT_SPECIFIC,
)

root = Path(os.environ["P08_5_1_DIR"])
ledger_path = root / "p08_5_comparison_ledger.json"
table_path = root / "p08_5_comparison_table.md"
if not ledger_path.is_file() or not table_path.is_file():
    raise SystemExit("ERROR: P08.5.1 generated artifacts are missing")

ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
if ledger.get("schema") != LEDGER_SCHEMA or ledger.get("status") != LEDGER_STATUS:
    raise SystemExit("ERROR: P08.5.1 schema/status drifted")
if ledger.get("accepted_identities") != ACCEPTED_IDENTITIES:
    raise SystemExit("ERROR: P08.5.1 accepted P08 identity binding drifted")
if len(ledger.get("rows", [])) != 24:
    raise SystemExit("ERROR: P08.5.1 metric-row count drifted")

counts = Counter(row["comparison_class"] for row in ledger["rows"])
expected_counts = {
    DIRECTLY_COMPARABLE: 3,
    COMPARABLE_WITH_RECONSTRUCTION_CAVEAT: 7,
    CONTEXT_ONLY: 2,
    PROJECT_SPECIFIC: 10,
    NOT_COMPARABLE: 2,
}
if counts != expected_counts:
    raise SystemExit(f"ERROR: P08.5.1 comparison classification counts drifted: {counts}")

by_id = {row["id"]: row for row in ledger["rows"]}
anchors = {
    "ann_test_error": (0.0074, 0.0126),
    "snn_test_error": (0.0079, 0.0176),
    "neuron_count": (4000, 4218),
    "trainable_parameters": (7000, 7006),
    "expanded_connections": (341000, 338880),
    "shared_weight_accounting": (6746, 64235),
    "mapped_core_count": (14, 5),
}
for metric_id, (nxtf_value, project_value) in anchors.items():
    row = by_id[metric_id]
    if row["nxtf"]["value"] != nxtf_value or row["project"]["value"] != project_value:
        raise SystemExit(f"ERROR: P08.5.1 anchor drifted for {metric_id}")

for metric_id in ("native_loihi_energy", "native_loihi_latency"):
    row = by_id[metric_id]
    if row["comparison_class"] != NOT_COMPARABLE or row["project"]["value"] is not None:
        raise SystemExit(f"ERROR: P08.5.1 {metric_id} non-comparability guard drifted")
for metric_id in ("shared_weight_accounting", "mapped_core_count"):
    row = by_id[metric_id]
    if row["comparison_class"] != CONTEXT_ONLY or row["allow_numeric_delta"]:
        raise SystemExit(f"ERROR: P08.5.1 {metric_id} context-only guard drifted")
if by_id["representative_physical_dispatch_cycles"]["comparison_class"] != PROJECT_SPECIFIC:
    raise SystemExit("ERROR: representative dispatch cycles lost project-specific classification")
if by_id["representative_physical_dispatch_time"]["project"]["value"] != 38.65:
    raise SystemExit("ERROR: representative dispatch-time derivation drifted")
if set(ledger["guardrails"].values()) != {False}:
    raise SystemExit("ERROR: one or more P08.5.1 overclaim guardrails became true")

payload = dict(ledger)
recorded = payload.pop("ledger_fingerprint", None)
recomputed = hashlib.sha256(
    json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()
if recorded != recomputed:
    raise SystemExit("ERROR: P08.5.1 ledger fingerprint does not recompute")

print(f"PASS: P08.5.1 deterministic ledger fingerprint={recorded}")
print(
    "PASS: P08.5.1 comparison boundaries "
    f"direct={counts[DIRECTLY_COMPARABLE]} "
    f"caveated={counts[COMPARABLE_WITH_RECONSTRUCTION_CAVEAT]} "
    f"context={counts[CONTEXT_ONLY]} project_specific={counts[PROJECT_SPECIFIC]} "
    f"not_comparable={counts[NOT_COMPARABLE]}"
)
print(
    "PASS: P08.5.1 accuracy anchors "
    "nxtf_ann_error=0.007400 project_ann_error=0.012600 "
    "nxtf_snn_error=0.007900 project_snn_error=0.017600"
)
print(
    "PASS: P08.5.1 structure anchors "
    "neurons=4000~vs4218 params=7000~vs7006 connections=341000~vs338880"
)
print(
    "PASS: P08.5.1 noncomparability guards "
    "energy=true latency=true shared_weight_ratio=true mapped_core_ratio=true "
    "dispatch_not_sample_latency=true full_jtag_replay=false"
)
PY

rm -rf "$FINAL_DIR"
mv "$CANDIDATE_A" "$FINAL_DIR"
rm -rf "$CANDIDATE_B"

echo
echo "P08.5.1 comparison-ledger gate completed successfully."
echo "Ledger: $FINAL_DIR/p08_5_comparison_ledger.json"
echo "Rendered table: $FINAL_DIR/p08_5_comparison_table.md"
