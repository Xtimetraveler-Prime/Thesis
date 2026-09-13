from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("neuromorphic_twin")

from mnist_app.config import INPUT_AXONS, OUTPUT_NEURONS
from mnist_app.export import write_deployment
from mnist_app.inference import infer_image, load_core_from_deployment


def test_synthetic_checkpoint_exports_and_runs_through_real_core(tmp_path: Path):
    rng = np.random.default_rng(0x4D4E4953)
    weights = rng.normal(0.0, 0.03, size=(INPUT_AXONS, OUTPUT_NEURONS)).astype(np.float32)
    checkpoint = tmp_path / "synthetic.npz"
    np.savez_compressed(checkpoint, weights=weights, threshold=np.float32(1.0))

    manifest = write_deployment(checkpoint, tmp_path / "deployment")
    core = load_core_from_deployment(manifest)
    result = infer_image(core, np.zeros((28, 28), dtype=np.uint8))
    assert result.prediction == 0
    assert result.spike_counts == (0,) * OUTPUT_NEURONS
    assert result.total_input_events == 0
