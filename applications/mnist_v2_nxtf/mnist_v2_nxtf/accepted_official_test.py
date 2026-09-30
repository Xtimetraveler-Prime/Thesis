"""Identity contract for the accepted P08.4.1 official-test measurement."""

from __future__ import annotations

import json
from pathlib import Path

from .accepted_ann import ACCEPTED_ANN_WEIGHTS_FINGERPRINT
from .official_test_evaluation import OFFICIAL_TEST_SCHEMA
from .source_recovered_validation import (
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
)

ACCEPTED_OFFICIAL_TEST_EXAMPLES = 10_000
ACCEPTED_OFFICIAL_TEST_TIMESTEPS = 100
ACCEPTED_ANN_TEST_ACCURACY = 0.987400
ACCEPTED_SNN_TEST_ACCURACY = 0.982400
ACCEPTED_ANN_MINUS_SNN_TEST_ACCURACY = 0.005000
ACCEPTED_ANN_TEST_PREDICTION_FINGERPRINT = (
    "7f807496616d93cf76a456bb83a97ff17ca39028b894b9398005ff6a88989f0e"
)
ACCEPTED_SNN_TEST_PREDICTION_FINGERPRINT = (
    "16910272d13517fd3b67fb205f8773882bbbb8c576d9f63ebe6e350be2b64741"
)
ACCEPTED_SNN_TEST_EVIDENCE_FINGERPRINT = (
    "34263540ebb85fb03dcee878b2984e1373aee9ad4e8ad03183c790ee9c8810f4"
)


def validate_accepted_official_test_manifest(path: str | Path) -> dict[str, object]:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"accepted P08.4.1 manifest is missing: {source}")
    manifest = json.loads(source.read_text(encoding="utf-8"))
    required = {
        "schema": OFFICIAL_TEST_SCHEMA,
        "official_test_used": True,
        "test_examples_observed": ACCEPTED_OFFICIAL_TEST_EXAMPLES,
        "timesteps": ACCEPTED_OFFICIAL_TEST_TIMESTEPS,
        "selection_decisions_after_test": 0,
        "post_test_training": False,
        "post_test_conversion_tuning": False,
        "post_test_threshold_tuning": False,
        "post_test_decoder_tuning": False,
        "post_test_timestep_tuning": False,
        "accepted_ann_weights_fingerprint": ACCEPTED_ANN_WEIGHTS_FINGERPRINT,
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "ann_prediction_fingerprint": ACCEPTED_ANN_TEST_PREDICTION_FINGERPRINT,
        "snn_prediction_fingerprint": ACCEPTED_SNN_TEST_PREDICTION_FINGERPRINT,
        "snn_evidence_fingerprint": ACCEPTED_SNN_TEST_EVIDENCE_FINGERPRINT,
    }
    for key, expected in required.items():
        if manifest.get(key) != expected:
            raise ValueError(
                f"accepted P08.4.1 manifest mismatch for {key}: "
                f"{manifest.get(key)!r} != {expected!r}"
            )

    for key, expected in (
        ("ann_accuracy", ACCEPTED_ANN_TEST_ACCURACY),
        ("snn_accuracy", ACCEPTED_SNN_TEST_ACCURACY),
        ("ann_minus_snn_accuracy", ACCEPTED_ANN_MINUS_SNN_TEST_ACCURACY),
    ):
        if abs(float(manifest[key]) - expected) > 5e-7:
            raise ValueError(f"accepted P08.4.1 {key} mismatch")
    return manifest
