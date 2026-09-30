#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
REPO_DIR="$(cd -- "$PROJECT_DIR/../.." && pwd)"
APP_DIR="$REPO_DIR/applications/mnist_v2_nxtf"

export PYTHONPATH="$PROJECT_DIR/src:$APP_DIR${PYTHONPATH:+:$PYTHONPATH}"
cd "$REPO_DIR"

python - <<'PY'
missing = []
for module in ("numpy", "pytest"):
    try:
        __import__(module)
    except ImportError:
        missing.append(module)
if missing:
    raise SystemExit(
        "ERROR: P08.2 preflight requires the dedicated .venv-p08 application "
        "environment (missing: %s). From the repository root run:\n"
        "  python3.12 -m venv .venv-p08\n"
        "  source .venv-p08/bin/activate\n"
        "  python -m pip install --upgrade pip\n"
        "  python -m pip install -e Loihi_Digital_Twin/v2\n"
        "  python -m pip install -e 'applications/mnist_v2_nxtf[test]'"
        % ", ".join(missing)
    )
PY

python -m py_compile \
    Loihi_Digital_Twin/v2/src/loihi_twin_v2/paging.py \
    Loihi_Digital_Twin/v2/src/loihi_twin_v2/hardware_p08.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/config.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/reconstruction.py \
    applications/mnist_v2_nxtf/mnist_v2_nxtf/structural.py

python -m pytest -q \
    applications/mnist_v2_nxtf/tests/test_data_contract.py \
    applications/mnist_v2_nxtf/tests/test_reconstruction.py \
    applications/mnist_v2_nxtf/tests/test_p08_2_paging.py \
    Loihi_Digital_Twin/v2/tests/test_p08_paging.py \
    Loihi_Digital_Twin/v2/tests/test_virtualization.py \
    Loihi_Digital_Twin/v2/tests/test_p05_hardware_image.py \
    Loihi_Digital_Twin/v2/tests/test_p06_compiler.py \
    Loihi_Digital_Twin/v2/tests/test_p07_deep_mapped_snn.py

python - <<'PY'
from loihi_twin_v2 import export_paged_compiled_fpga_image
from mnist_v2_nxtf import TOPOLOGY_STATUS
from mnist_v2_nxtf.reconstruction import PROPOSED_METRICS, RECONSTRUCTION_STATUS
from mnist_v2_nxtf.structural import compile_structural_probe

accepted_or_later = {
    "P08_1_RECONSTRUCTION_ACCEPTED_P08_2_PENDING",
    "P08_2_PAGING_ACCEPTED_P08_3_POLICY_FROZEN",
}
assert TOPOLOGY_STATUS in accepted_or_later
assert RECONSTRUCTION_STATUS == "ACCEPTED_P08_1_SOURCE_BOUNDED"
compiled = compile_structural_probe()
paged = export_paged_compiled_fpga_image(compiled)
report = paged.report()

assert report["logical_core_count"] == 5
assert report["resident_context_count"] == 3
assert report["physical_engine_count"] == 1
assert report["requires_paging"] is True
assert report["logical_capacity_changed"] is False

print(
    "PASS: P08.2 paging boundary "
    f"logical_cores={report['logical_core_count']} "
    f"resident_contexts={report['resident_context_count']} "
    f"physical_engines={report['physical_engine_count']} "
    f"source={compiled.source_fingerprint} compiled={compiled.fingerprint}"
)
print(
    "PASS: P08 accepted reconstruction unchanged "
    f"filters={PROPOSED_METRICS.filters} neurons={PROPOSED_METRICS.neuron_count} "
    f"params={PROPOSED_METRICS.trainable_parameters} "
    f"expanded={PROPOSED_METRICS.expanded_connections}"
)
PY

echo
echo "P08.2 software/context-paging preflight completed successfully."
echo "P08.2 is accepted; later P08 phase markers are allowed by this regression gate."
