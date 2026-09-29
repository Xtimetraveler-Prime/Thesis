#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_DIR"

command -v python3 >/dev/null 2>&1 || {
    echo "ERROR: python3 is not on PATH" >&2
    exit 2
}
command -v pytest >/dev/null 2>&1 || {
    echo "ERROR: pytest is not on PATH. Activate .venv-v2 first." >&2
    exit 2
}

for tool in vitis-run xvlog xelab xsim vivado; do
    command -v "$tool" >/dev/null 2>&1 || {
        echo "ERROR: $tool is not on PATH. Source Vivado/Vitis 2025.2 settings64.sh first." >&2
        exit 2
    }
done

export HLS_PART="${HLS_PART:-xck26-sfvc784-2LV-c}"

echo '=== P04 Python regression ==='
pytest -q

echo
echo '=== P04 vector-generation smoke tests ==='
HLS_VECTOR_TMP="${TMPDIR:-/tmp}/generated_p04_vectors_${UID:-0}.inc"
PHYSICAL_VECTOR_TMP="${TMPDIR:-/tmp}/generated_p04_physical_${UID:-0}.tcl"
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p04_hls_vectors.py" --output "$HLS_VECTOR_TMP"
grep -q 'P04_SCENARIOS' "$HLS_VECTOR_TMP"
grep -q 'recurrent_multicast' "$HLS_VECTOR_TMP"
PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python3 "$PROJECT_DIR/examples/generate_p04_physical_vectors.py" --output "$PHYSICAL_VECTOR_TMP"
grep -q 'set P04_SCENARIOS' "$PHYSICAL_VECTOR_TMP"
grep -q 'logical_capacity_changed' "$PROJECT_DIR/vivado/create_p04_impl_project.tcl"
rm -f "$HLS_VECTOR_TMP" "$PHYSICAL_VECTOR_TMP"

echo
echo '=== P04 Python/HLS two-core differential ==='
bash "$PROJECT_DIR/hls/core_v2/run_p04_csim.sh"

echo
echo '=== P04 standalone router/barrier XSim ==='
bash "$PROJECT_DIR/rtl/run_p04_router_barrier_sim.sh"

echo
echo '=== P04 two-core controller XSim ==='
bash "$PROJECT_DIR/rtl/run_p04_two_core_controller_sim.sh"

echo
echo 'PASS: P04 source-level preflight completed successfully.'
