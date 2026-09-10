#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE="${1:-$ROOT/build/m13_5/catalyst-k26-vivado}"
CLOSURE_JSON="${2:-$ROOT/references/m13_5_closure.json}"
CLOSURE_MD="$ROOT/build/m13_5/m13_5_closure_summary.md"

cd "$ROOT"

# Re-parse the preserved vendor reports independently before trusting the
# normalized JSON result or promoting any tracked closure evidence.
PYTHONPATH=src python3 examples/validate_m13_5_native_reports.py \
  --evidence-dir "$EVIDENCE"

PYTHONPATH=src python3 examples/close_m13_5_hardware_reproduction.py \
  --evidence-dir "$EVIDENCE" \
  --output-json "$CLOSURE_JSON" \
  --output-md "$CLOSURE_MD"

python3 -m pytest --override-ini addopts='' -q \
  tests/test_m13_5_hardware_audit.py \
  tests/test_m13_5_hardware_comparison.py \
  tests/test_m13_5_hardware_closure.py \
  tests/test_m13_5_native_report_validation.py

python3 -m pytest --override-ini addopts='' -q

cd "$ROOT/.."
git diff --name-only origin/main...HEAD > /tmp/m13_5_closure_branch_files.txt
if grep -E '^Neuromorphic Digital Twin/(hls/core_v1|rtl/core_v1|src/neuromorphic_twin/(model|arithmetic|core|routing|weights)\.py)' /tmp/m13_5_closure_branch_files.txt; then
  echo 'ERROR: M13.5 unexpectedly changed a frozen computational baseline path.' >&2
  exit 2
fi

printf 'M13.5.3 closure validation PASS: closure=%s summary=%s\n' "$CLOSURE_JSON" "$CLOSURE_MD"
git status --short -- "$CLOSURE_JSON"
