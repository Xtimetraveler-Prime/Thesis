from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("neuromorphic_twin")

from mnist_app.config import CROPPED_DENSE, NATIVE_SPARSE, OUTPUT_NEURONS
from mnist_app.export import write_deployment
from mnist_app.inference import infer_image, load_deployment


def _synthetic_weights(profile, rng):
    weights = np.zeros((profile.input_axons, OUTPUT_NEURONS), dtype=np.float32)
    if profile.is_sparse:
        flat = weights.reshape(-1)
        flat[: profile.max_synapses] = rng.normal(
            0.0,
            0.03,
            size=profile.max_synapses,
        )
    else:
        weights[:] = rng.normal(0.0, 0.03, size=weights.shape)
    return weights


@pytest.mark.parametrize("profile", [CROPPED_DENSE, NATIVE_SPARSE])
def test_synthetic_checkpoint_exports_and_runs_through_real_core(
    tmp_path: Path,
    profile,
):
    rng = np.random.default_rng(0x4D4E4953)
    weights = _synthetic_weights(profile, rng)
    checkpoint = tmp_path / f"{profile.name}.npz"
    np.savez_compressed(
        checkpoint,
        weights=weights,
        threshold=np.float32(1.0),
        profile=np.asarray(profile.name),
    )

    manifest = write_deployment(
        checkpoint,
        tmp_path / f"{profile.name}-deployment",
    )
    runtime = load_deployment(manifest)
    assert runtime.profile == profile

    result = infer_image(
        runtime.core,
        np.zeros((28, 28), dtype=np.uint8),
        profile=runtime.profile,
    )
    assert result.prediction == 0
    assert result.spike_counts == (0,) * OUTPUT_NEURONS
    assert result.total_input_events == 0
