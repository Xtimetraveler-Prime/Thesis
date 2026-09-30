#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
BUILD_DIR="$PROJECT_DIR/build/p07_preflight"
cd "$PROJECT_DIR"

python -m pytest -q \
    tests/test_p07_deep_mapped_snn.py \
    tests/test_p06_compiler.py \
    tests/test_p05_hardware_image.py \
    tests/test_virtualization.py

python -m py_compile \
    src/loihi_twin_v2/workload_p07.py \
    examples/generate_p07_deep_network.py \
    examples/generate_p07_physical_vectors.py \
    scripts/validate_p07_deep_network.py

bash -n hardware/run_p07_physical.sh

rm -rf "$BUILD_DIR"
mkdir -p "$BUILD_DIR"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python examples/generate_p07_deep_network.py \
    --output "$BUILD_DIR/network.json"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python scripts/compile_p06.py \
    "$BUILD_DIR/network.json" \
    --output "$BUILD_DIR/deployment.json" \
    --report "$BUILD_DIR/mapping_report.json" \
    --fpga-report "$BUILD_DIR/fpga_report.json" \
    --compartments-per-core 4

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python scripts/validate_p07_deep_network.py \
    "$BUILD_DIR/network.json" "$BUILD_DIR/deployment.json" \
    --summary "$BUILD_DIR/p07_summary.json" \
    --capacity-failure "$BUILD_DIR/p07_capacity_failure.json"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python examples/generate_p07_physical_vectors.py \
    "$BUILD_DIR/deployment.json" \
    --output "$BUILD_DIR/p07_physical_vectors.tcl"

PYTHONPATH="$PROJECT_DIR/src${PYTHONPATH:+:$PYTHONPATH}" \
python - "$BUILD_DIR" <<'PY'
from __future__ import annotations

import json
from pathlib import Path
import sys

from loihi_twin_v2 import CompiledDeployment, NetworkSpec

build = Path(sys.argv[1])
network = NetworkSpec.read_json(build / "network.json")
compiled = CompiledDeployment.read_json(build / "deployment.json")
report = json.loads((build / "mapping_report.json").read_text(encoding="utf-8"))
fpga_report = json.loads((build / "fpga_report.json").read_text(encoding="utf-8"))
summary = json.loads((build / "p07_summary.json").read_text(encoding="utf-8"))
capacity = json.loads((build / "p07_capacity_failure.json").read_text(encoding="utf-8"))
vectors = (build / "p07_physical_vectors.tcl").read_text(encoding="utf-8")

assert compiled.source_fingerprint == network.fingerprint
assert report["fingerprint"] == compiled.fingerprint
assert report["logical_core_count"] == 3
assert report["placement_count"] == 12
assert report["ingress_route_count"] == 4
assert report["static_route_estimate"] == {"total": 10, "local": 6, "remote": 4}
assert report["connection_sharing"]["expanded_connections"] == 28
assert report["connection_sharing"]["stored_shared_parameters"] == 6
assert fpga_report["compiled_deployment_fingerprint"] == compiled.fingerprint
assert fpga_report["logical_core_count"] == 3
assert fpga_report["physical_engine_count"] == 1
assert fpga_report["logical_capacity_changed"] is False
assert summary["layers"] == 6
assert summary["neurons"] == 12
assert summary["capacity_probe"]["result"] == "EXPECTED_REJECTION"
assert capacity["code"] == "logical_core_capacity"
assert capacity["context"] == {"required": 3, "limit": 2}
assert f"set P06_DEPLOYMENT_FINGERPRINT {compiled.fingerprint}" in vectors
assert "set P07_LAYERS 6" in vectors
assert vectors.count("timestep ") == 21

print(
    "PASS: P07 deep mapped artifact pipeline "
    f"source={network.fingerprint} deployment={compiled.fingerprint} "
    "layers=6 neurons=12 logical_cores=3 physical_engines=1 "
    "expanded=28 stored=6 capacity_probe=EXPECTED_REJECTION"
)
PY

echo
echo "P07 deeper mapped SNN preflight completed successfully."
echo "Artifacts: $BUILD_DIR"
