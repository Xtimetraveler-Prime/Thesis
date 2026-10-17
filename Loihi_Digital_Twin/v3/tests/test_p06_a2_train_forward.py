"""A2.5: exact inference-forward parity and distinct surrogate gradients."""
from __future__ import annotations

import math
import random

import pytest

torch = pytest.importorskip("torch")

from loihi_twin_v2.p06_compact_inference import infer_image
from loihi_twin_v2.p06_integer_oracle import LIFParameters, STATE_MAX
from loihi_twin_v2.p06_train_forward import IntegerForwardSNN


def make_model():
    return IntegerForwardSNN(
        LIFParameters(current_decay=4096, voltage_decay=205, threshold=2048),
        LIFParameters(current_decay=4096, voltage_decay=205, threshold=128),
        surrogate_width=256,
    )


def compare_frames(model, images):
    network = model.to_integer_network()
    batch = torch.tensor(images, dtype=torch.uint8)
    with torch.no_grad():
        scores = model(batch)
    assert scores.dtype == torch.float64
    assert scores.shape == (len(images), 10)
    assert torch.equal(scores, scores.round())
    for index, raw in enumerate(images):
        oracle = infer_image(network, raw)
        assert scores[index].tolist() == list(oracle.output_counts), f"first divergent image index={index}"
        assert int(scores[index].argmax()) == oracle.predicted_class


def test_silent_and_maximum_activity_parity():
    model = make_model()
    compare_frames(model, [[0]*784, [255]*784, [128]*784])
    with torch.no_grad():
        model.w_input_hidden.fill_(11.5)
        model.w_hidden_output.fill_(9.5)
    compare_frames(model, [[0]*784, [255]*784, [128]*784, [(i*43+7)%256 for i in range(784)]])


def test_signed_halves_negative_weights_and_saturation_parity():
    model = make_model()
    with torch.no_grad():
        vals = [-4.5, -3.5, -1.5, -0.5, 0.5, 1.5, 8_388_607.0, -8_388_608.0]
        for j in range(32):
            model.w_input_hidden[j] = torch.tensor([vals[(i+j)%len(vals)] for i in range(784)])
        for j in range(10):
            model.w_hidden_output[j] = torch.tensor([vals[(i+j)%len(vals)] for i in range(32)])
    compare_frames(model, [[255] * 784, [0]*784, [i%256 for i in range(784)]])


def test_deterministic_random_integer_or_float_weight_parity():
    model = make_model()
    rng = random.Random(20261013)
    with torch.no_grad():
        model.w_input_hidden.copy_(torch.tensor([[rng.uniform(-80,80) for _ in range(784)] for _ in range(32)], dtype=torch.float32))
        model.w_hidden_output.copy_(torch.tensor([[rng.uniform(-60,60) for _ in range(32)] for _ in range(10)], dtype=torch.float32))
    frames = [[rng.randrange(256) for _ in range(784)] for _ in range(3)]
    compare_frames(model, frames)
    compare_frames(model, frames)  # no cross-frame state/counter leakage


def test_refractory_and_negative_decay_boundary_parity():
    model = IntegerForwardSNN(
        LIFParameters(1, 4095, threshold=7, bias=-2, refractory_ticks=4),
        LIFParameters(4096, 4095, threshold=1, bias=3, refractory_ticks=2),
    )
    with torch.no_grad():
        model.w_input_hidden.fill_(13)
        model.w_hidden_output.fill_(-5)
    compare_frames(model, [[255]*784, [0]*784, [128]*784])


def test_training_gradient_flows_through_both_quantized_layers():
    model = IntegerForwardSNN(
        LIFParameters(4096, 4096, threshold=4),
        LIFParameters(4096, 4096, threshold=1),
        surrogate_width=5,
    )
    with torch.no_grad():
        model.w_input_hidden.fill_(5.25)
        model.w_hidden_output.fill_(1.75)
    x = torch.zeros((2,784), dtype=torch.uint8)
    x[0, 0] = 255
    x[1, 1] = 255
    values = model(x)
    target = torch.arange(10, dtype=torch.float64)
    loss = ((values - target)**2).sum()
    loss.backward()
    for par in (model.w_input_hidden, model.w_hidden_output):
        assert par.grad is not None
        assert bool(torch.isfinite(par.grad).all())
        assert bool((par.grad.abs() > 0).any())
    assert torch.equal(values.detach(), values.detach().round())


def test_invalid_input_types_and_export_bounds_fail_closed():
    model = make_model()
    with pytest.raises(TypeError, match="uint8"):
        model(torch.zeros((1,784), dtype=torch.float32))
    with pytest.raises(ValueError, match="784"):
        model(torch.zeros((1,783), dtype=torch.uint8))
    with pytest.raises(ValueError, match="batch"):
        model(torch.zeros((0,784), dtype=torch.uint8))
    with pytest.raises(ValueError, match="positive finite"):
        IntegerForwardSNN(LIFParameters(4096, 205, 5),LIFParameters(4096, 205, 5),surrogate_width=-1)
    with torch.no_grad():
        model.w_input_hidden[0,0] = float("nan")
    with pytest.raises(ValueError, match="nonfinite"):
        model.to_integer_network()
    with torch.no_grad():
        model.w_input_hidden[0,0] = STATE_MAX + 128.0
    with pytest.raises(ValueError, match="outside signed24"):
        model.to_integer_network()


def test_parameter_shapes_and_train_step_smoke():
    model = IntegerForwardSNN(LIFParameters(4096,4096,3),LIFParameters(4096,4096,3),surrogate_width=10)
    with torch.no_grad():
        model.w_input_hidden.fill_(0.75)
        model.w_hidden_output.fill_(0.75)
    optimizer = torch.optim.SGD(model.parameters(), lr=0.01)
    image = torch.zeros((2,784), dtype=torch.uint8)
    image[:,0] = 255
    before = model(image)
    optimizer.zero_grad()
    loss = ((before - torch.tensor([[3.]*10,[2.]*10], dtype=torch.float64))**2).sum()
    loss.backward()
    assert math.isfinite(float(loss.item()))
    optimizer.step()
    after = model(image)
    assert torch.isfinite(after).all()
    compare_frames(model, image.tolist())
