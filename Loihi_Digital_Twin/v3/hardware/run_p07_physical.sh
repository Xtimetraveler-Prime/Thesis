#!/usr/bin/env bash
set -euo pipefail

EXPECTED_VERSION="2025.2"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
P05_REPORT_DIR="$PROJECT_DIR/vivado/build/p05_impl/reports"
BIT_FILE="${P07_BIT_FILE:-$P05_REPORT_DIR/p05_virtualized.bit}"
LTX_FILE="${P07_LTX_FILE:-$P05_REPORT_DIR/p05_virtualized.ltx}"
HW_SERVER_URL="${HW_SERVER_URL:-localhost:3121}"
BUILD_DIR="$SCRIPT_DIR/build/p07_physical"
NETWORK_FILE="$BUILD_DIR/network.json"
DEPLOYMENT_FILE="$BUILD_DIR/deployment.json"
REPORT_FILE="$BUILD_DIR/mapping_report.json"
FPGA_REPORT_FILE="$BUILD_DIR/fpga_report.json"
SUMMARY_FILE="$BUILD_DIR/p07_summary.json"
CAPACITY_FILE="$BUILD_DIR/p07_capacity_failure.json"
VECTOR_FILE="$BUILD_DIR/p07_physical_vectors.tcl"
RAW_RESULT_FILE="$BUILD_DIR/p06_harness_result.txt"
RESULT_FILE="$BUILD_DIR/p07_physical_result.txt"
RAW_LOG="$BUILD_DIR/p07_physical.log"
TCL_SCRIPT="$SCRIPT_DIR/p06_physical_conformance.tcl"

command -v vivado >/dev/null 2>&1 || {
    echo "ERROR: vivado is not on PATH. Source Vivado 2025.2 settings64.sh first." >&2
    exit 2
}
if [[ "$(vivado -version 2>&1 || true)" != *"$EXPECTED_VERSION"* ]]; then
    echo "ERROR: Vivado is not reporting $EXPECTED_VERSION" >&2
    exit 2
fi
command -v sha256sum >/dev/null 2>&1 || {
    echo "ERROR: sha256sum is not on PATH" >&2
    exit 2
}
for artifact in "$BIT_FILE" "$LTX_FILE"; do
    [[ -f "$artifact" ]] || {
        echo "ERROR: required accepted P05 hardware artifact missing: $artifact" >&2
        echo "Run the accepted P05 implementation flow or set P07_BIT_FILE/P07_LTX_FILE." >&2
        exit 3
    }
done

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p07_deep_network.py" \
    --output "$NETWORK_FILE"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/scripts/compile_p06.py" \
    "$NETWORK_FILE" \
    --output "$DEPLOYMENT_FILE" \
    --report "$REPORT_FILE" \
    --fpga-report "$FPGA_REPORT_FILE" \
    --compartments-per-core 4

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/scripts/validate_p07_deep_network.py" \
    "$NETWORK_FILE" "$DEPLOYMENT_FILE" \
    --summary "$SUMMARY_FILE" \
    --capacity-failure "$CAPACITY_FILE"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p07_physical_vectors.py" \
    "$DEPLOYMENT_FILE" \
    --output "$VECTOR_FILE"

printf 'P07 physical bitstream (accepted P05 shell): %s\n' "$BIT_FILE"
printf 'P07 physical probes: %s\n' "$LTX_FILE"
printf 'P07 compiled deployment: %s\n' "$DEPLOYMENT_FILE"
printf 'P07 hardware server: %s\n' "$HW_SERVER_URL"
printf 'P07 board checker: accepted P06 mapped-deployment conformance Tcl\n'

vivado -mode batch \
    -source "$TCL_SCRIPT" \
    -tclargs "$BIT_FILE" "$LTX_FILE" "$VECTOR_FILE" "$RAW_RESULT_FILE" "$HW_SERVER_URL" \
    2>&1 | tee "$RAW_LOG"

[[ -f "$RAW_RESULT_FILE" ]] || {
    echo "ERROR: P07 reused harness did not produce $RAW_RESULT_FILE" >&2
    exit 4
}
grep -q '^result=PASS$' "$RAW_RESULT_FILE" || {
    echo "ERROR: P07 reused physical harness result is not PASS" >&2
    cat "$RAW_RESULT_FILE" >&2
    exit 5
}

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 - "$DEPLOYMENT_FILE" "$RAW_RESULT_FILE" "$SUMMARY_FILE" "$RESULT_FILE" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

from loihi_twin_v2 import CompiledDeployment

deployment_path, raw_path, summary_path, output_path = map(Path, sys.argv[1:])
compiled = CompiledDeployment.read_json(deployment_path)
raw_lines = [line.strip() for line in raw_path.read_text(encoding="utf-8").splitlines() if line.strip()]
summary = json.loads(summary_path.read_text(encoding="utf-8"))

kv = {}
scenario_lines = []
for line in raw_lines:
    if line.startswith("scenario="):
        scenario_lines.append(line)
    elif "=" in line:
        key, value = line.split("=", 1)
        kv[key] = value

if kv.get("result") != "PASS":
    raise RuntimeError("P07 raw physical result is not PASS")
if kv.get("deployment_fingerprint") != compiled.fingerprint:
    raise RuntimeError("P07 raw physical fingerprint does not match deployment")
if kv.get("source_fingerprint") != compiled.source_fingerprint:
    raise RuntimeError("P07 raw physical source fingerprint does not match deployment")
if len(scenario_lines) != 42:
    raise RuntimeError(f"P07 expected 42 physical tick records, got {len(scenario_lines)}")

sharing = summary["connection_sharing"]
capacity = summary["capacity_probe"]
lines = [
    "schema=p07-deep-mapped-snn-v1",
    f"device={kv['device']}",
    f"source_fingerprint={compiled.source_fingerprint}",
    f"deployment_fingerprint={compiled.fingerprint}",
    "layers=6",
    "neurons=12",
    "input_channels=4",
    "logical_contexts=3",
    "physical_engines=1",
    "logical_capacity_changed=0",
    f"expanded_connections={sharing['expanded_connections']}",
    f"stored_shared_parameters={sharing['stored_shared_parameters']}",
    f"expanded_per_stored_parameter={sharing['expanded_per_stored_parameter']}",
    f"capacity_probe_result={capacity['result']}",
    f"capacity_probe_code={capacity['code']}",
    f"capacity_probe_required={capacity['context']['required']}",
    f"capacity_probe_limit={capacity['context']['limit']}",
    "scenarios=3",
    "physical_ticks=42",
    *scenario_lines,
    "result=PASS",
]
output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
PY

grep -q '^result=PASS$' "$RESULT_FILE" || {
    echo "ERROR: P07 final physical result is not PASS" >&2
    exit 6
}

if heartbeat_line="$(grep 'P06 reset release verified:' "$RAW_LOG" | tail -n 1)" && [[ -n "$heartbeat_line" ]]; then
    echo "${heartbeat_line/P06/P07}"
fi
grep '^scenario=' "$RESULT_FILE" | sed 's/^/P07 physical tick PASS: /'
echo "P07 deeper mapped SNN Python/FPGA conformance PASS: result=$RESULT_FILE"

STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
EVIDENCE_DIR="$SCRIPT_DIR/evidence/p07_physical_${STAMP}"
mkdir -p "$EVIDENCE_DIR"
cp "$RESULT_FILE" "$EVIDENCE_DIR/"
cp "$RAW_RESULT_FILE" "$EVIDENCE_DIR/"
cp "$RAW_LOG" "$EVIDENCE_DIR/"
cp "$NETWORK_FILE" "$EVIDENCE_DIR/"
cp "$DEPLOYMENT_FILE" "$EVIDENCE_DIR/"
cp "$REPORT_FILE" "$EVIDENCE_DIR/"
cp "$FPGA_REPORT_FILE" "$EVIDENCE_DIR/"
cp "$SUMMARY_FILE" "$EVIDENCE_DIR/"
cp "$CAPACITY_FILE" "$EVIDENCE_DIR/"
cp "$VECTOR_FILE" "$EVIDENCE_DIR/"
for report in \
    p05_post_route_metrics.txt \
    timing_summary_post_route.rpt \
    utilization_post_route.rpt \
    bus_skew_post_route.rpt \
    drc_post_route.rpt \
    methodology_post_route.rpt; do
    if [[ -f "$P05_REPORT_DIR/$report" ]]; then
        cp "$P05_REPORT_DIR/$report" "$EVIDENCE_DIR/"
    fi
done
{
    printf 'bitstream=%s\n' "$BIT_FILE"
    printf 'debug_probes=%s\n' "$LTX_FILE"
    printf 'compiled_deployment=%s\n' "$DEPLOYMENT_FILE"
    sha256sum "$BIT_FILE" "$LTX_FILE" "$DEPLOYMENT_FILE" "$NETWORK_FILE"
} > "$EVIDENCE_DIR/artifact_sha256.txt"

echo
echo '=== P07 physical result ==='
cat "$RESULT_FILE"
echo
echo "P07 deeper mapped SNN physical conformance gate completed successfully."
echo "Build evidence: $BUILD_DIR"
echo "Archived evidence: $EVIDENCE_DIR"
