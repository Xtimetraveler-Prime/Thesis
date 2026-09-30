#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build/p06_preflight"
cd "$PROJECT_DIR"

python -m py_compile \
    src/loihi_twin_v2/compiler.py \
    src/loihi_twin_v2/hardware_p06.py \
    scripts/compile_p06.py \
    examples/generate_p06_demo_network.py \
    examples/generate_p06_fpga_load_vectors.py \
    examples/generate_p06_physical_vectors.py
bash -n hardware/run_p06_physical.sh

python -m pytest -q \
    tests/test_p06_compiler.py \
    tests/test_resources_and_mapping.py \
    tests/test_deployment_replay.py \
    tests/test_p05_hardware_image.py

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python examples/generate_p06_demo_network.py \
    --output "$BUILD_DIR/network.json"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python scripts/compile_p06.py \
    "$BUILD_DIR/network.json" \
    --output "$BUILD_DIR/deployment.json" \
    --report "$BUILD_DIR/report.json" \
    --fpga-report "$BUILD_DIR/fpga_report.json" \
    --compartments-per-core 2

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python examples/generate_p06_fpga_load_vectors.py \
    "$BUILD_DIR/deployment.json" \
    --output "$BUILD_DIR/fpga_load_vectors.tcl"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python examples/generate_p06_physical_vectors.py \
    "$BUILD_DIR/deployment.json" \
    --output "$BUILD_DIR/physical_vectors.tcl"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python - "$BUILD_DIR" <<'PY'
import json
from pathlib import Path
import sys

from loihi_twin_v2 import CompiledDeployment, NetworkSpec

build = Path(sys.argv[1])
network = NetworkSpec.read_json(build / "network.json")
compiled = CompiledDeployment.read_json(build / "deployment.json")
report = json.loads((build / "report.json").read_text())
fpga_report = json.loads((build / "fpga_report.json").read_text())
load_vectors = (build / "fpga_load_vectors.tcl").read_text()
physical_vectors = (build / "physical_vectors.tcl").read_text()

assert compiled.source_fingerprint == network.fingerprint
assert report["fingerprint"] == compiled.fingerprint
assert fpga_report["compiled_deployment_fingerprint"] == compiled.fingerprint
assert f"set P06_DEPLOYMENT_FINGERPRINT {compiled.fingerprint}" in load_vectors
assert f"set P06_DEPLOYMENT_FINGERPRINT {compiled.fingerprint}" in physical_vectors
assert len(compiled.logical_deployment.core_configs) == 3
assert fpga_report["logical_core_count"] == 3
assert fpga_report["physical_engine_count"] == 1
assert fpga_report["logical_capacity_changed"] is False
assert "set P06_SCENARIOS {" in physical_vectors

print(
    "PASS: P06 shared artifact pipeline "
    f"source={network.fingerprint} deployment={compiled.fingerprint} "
    "logical_cores=3 physical_engines=1"
)
PY

echo
echo "P06 compiler preflight completed successfully."
echo "Artifacts: $BUILD_DIR"
