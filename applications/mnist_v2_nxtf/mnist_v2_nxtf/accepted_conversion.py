"""Identity contract for the accepted P08.3.4 converted SNN artifact."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from loihi_twin_v2.compiler import CompiledDeployment, NetworkSpec

from .conversion_loihi import (
    COMPILED_DEPLOYMENT_FILENAME,
    CONVERSION_ARTIFACT_FILENAME,
    CONVERSION_MANIFEST_FILENAME,
    CONVERTED_NETWORK_FILENAME,
    DTHIR_PARAMETER_SCALE,
    _arrays_fingerprint,
)
from .policy import CONVERSION_POLICY


ACCEPTED_CONVERSION_FINGERPRINT = (
    "686e801cf2459d66772a3517cfff0411746ce97d7a84fb45554ca3ee8345cb75"
)
ACCEPTED_NETWORK_FINGERPRINT = (
    "4f7dc2b2ecfd4db7c347fc8c846aed3ad5f03d57ceb48ed973530e77865bc211"
)
ACCEPTED_COMPILED_FINGERPRINT = (
    "1dc5191354566e9e40cdfe624ff6fc48528d1b78a91d2a16a4336d12b1a4296c"
)
ACCEPTED_LOGICAL_CORES = 5
ACCEPTED_RESIDENT_CONTEXTS = 3
ACCEPTED_PHYSICAL_ENGINES = 1


def validate_accepted_conversion(directory: str | Path) -> tuple[dict[str, np.ndarray], dict]:
    """Validate and load exactly the independently accepted P08.3.4 artifact."""

    root = Path(directory)
    parameters_path = root / CONVERSION_ARTIFACT_FILENAME
    manifest_path = root / CONVERSION_MANIFEST_FILENAME
    network_path = root / CONVERTED_NETWORK_FILENAME
    compiled_path = root / COMPILED_DEPLOYMENT_FILENAME
    for path in (parameters_path, manifest_path, network_path, compiled_path):
        if not path.is_file():
            raise FileNotFoundError(f"accepted P08.3.4 artifact is missing: {path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    expected = {
        "status": "P08_3_4_CONVERTED_VALIDATION_PENDING",
        "official_test_used": False,
        "test_examples_observed": 0,
        "desired_threshold_to_input_ratio": 8,
        "dthir_parameter_scale": 64.0,
        "weight_sign_mode": "mixed",
        "weight_quantization_step": 2,
        "weight_rounding": "toward_zero",
        "weight_exponent": 0,
        "logical_core_count": ACCEPTED_LOGICAL_CORES,
        "resident_context_count": ACCEPTED_RESIDENT_CONTEXTS,
        "physical_engine_count": ACCEPTED_PHYSICAL_ENGINES,
        "conversion_fingerprint": ACCEPTED_CONVERSION_FINGERPRINT,
        "converted_network_fingerprint": ACCEPTED_NETWORK_FINGERPRINT,
        "compiled_deployment_fingerprint": ACCEPTED_COMPILED_FINGERPRINT,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise ValueError(
                f"accepted conversion mismatch for {key}: "
                f"{manifest.get(key)!r} != {value!r}"
            )

    if DTHIR_PARAMETER_SCALE != 64.0:
        raise AssertionError("P08.3.4 DThIR parameter scale drifted")
    if CONVERSION_POLICY.primary_timesteps != 100:
        raise AssertionError("accepted P08 primary horizon must remain 100 timesteps")

    with np.load(parameters_path, allow_pickle=False) as payload:
        arrays = {name: np.asarray(payload[name]) for name in payload.files}
    if _arrays_fingerprint(arrays) != ACCEPTED_CONVERSION_FINGERPRINT:
        raise ValueError("accepted converted-parameter fingerprint does not recompute")

    network = NetworkSpec.read_json(network_path)
    compiled = CompiledDeployment.read_json(compiled_path)
    if network.fingerprint != ACCEPTED_NETWORK_FINGERPRINT:
        raise ValueError("accepted converted-network fingerprint mismatch")
    if compiled.fingerprint != ACCEPTED_COMPILED_FINGERPRINT:
        raise ValueError("accepted compiled-deployment fingerprint mismatch")
    if compiled.source_fingerprint != network.fingerprint:
        raise ValueError("accepted compiled deployment is not bound to accepted network")

    return arrays, manifest
