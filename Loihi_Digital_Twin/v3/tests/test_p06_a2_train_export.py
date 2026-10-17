"""A2.5 exporter fidelity across training-forward -> compiler -> packed ABI.

Requires actual complete repository; no official dataset or FPGA is accessed.
"""
from __future__ import annotations

import random

import pytest

torch = pytest.importorskip("torch")

from loihi_twin_v2.compiler import MappingOptions, compile_network
from loihi_twin_v2.hardware_p03 import export_one_core_image
from loihi_twin_v2.p06_compact_inference import CompactNetwork, infer_image
from loihi_twin_v2.p06_integer_oracle import LIFParameters
from loihi_twin_v2.p06_input_contract import pixel_spikes
from loihi_twin_v2.p06_packed_replay import replay_p03_image
from loihi_twin_v2.p06_train_export import compact_to_compiler_spec
from loihi_twin_v2.p06_train_forward import IntegerForwardSNN


def test_compiler_export_produces_exact_dense_weights_config_and_image_parity():
    hidden = LIFParameters(4096, 205, threshold=2048, bias=-17)
    output = LIFParameters(4096, 205, threshold=128, bias=5)
    train = IntegerForwardSNN(hidden, output, surrogate_width=128)
    with torch.no_grad():
        for dest in range(32):
            train.w_input_hidden[dest] = torch.tensor(
                [((src * (dest + 3) + dest * 11) % 89 - 24) + 0.25 for src in range(784)],
                dtype=torch.float32,
            )
        for dest in range(10):
            train.w_hidden_output[dest] = torch.tensor(
                [((src * (dest + 7) + 3 * dest) % 73 - 12) - 0.25 for src in range(32)],
                dtype=torch.float32,
            )
    model = train.to_integer_network()
    spec = compact_to_compiler_spec(model)
    assert len(spec.input_projections[0].connections) == 784 * 32
    assert len(spec.projections[0].connections) == 32 * 10
    compiled = compile_network(spec, MappingOptions(max_logical_cores=1))
    img = export_one_core_image(compiled.logical_deployment.core_configs[0])
    assert (img.compartment_count, len(compiled.ingress_routes)) == (42, 784)
    routing = sorted(compiled.ingress_routes, key=lambda row: row.input_index)
    pixel_to_axon = tuple(item.destination_axon for item in routing)
    assert all(item.destination_core == img.core_id for item in routing)
    rng = random.Random(0xA25)
    images = (bytes(784), bytes([255] * 784), bytes(rng.randrange(256) for _ in range(784)))
    with torch.no_grad():
        counts = train(torch.tensor([list(x) for x in images], dtype=torch.uint8))
    for i, raw in enumerate(images):
        dense = infer_image(model, raw)
        packed = replay_p03_image(img, pixel_to_axon, raw)
        if i == 1:
            assert dense.traces[0].hidden_spikes, "maximal input must route actual hidden spikes"
            assert dense.traces[1].output_spikes, "maximal input must fire output neurons"
        chip = compiled.build_chip()
        assert tuple(int(v) for v in counts[i]) == dense.output_counts == packed.output_counts
        for t in range(26):
            trace = chip.step(compiled.external_packets("pixels", pixel_spikes(raw, t), target_timestep=t)).cores[0]
            got = packed.ticks[t]
            reference = dense.traces[t]
            assert got.accumulators == reference.hidden_synaptic_inputs + reference.output_synaptic_inputs, f"t={t} accumulator"
            assert got.states_after == reference.hidden_after + reference.output_after, f"t={t} dense states"
            assert got.fired_compartments == trace.spikes_out, f"t={t} spike IDs"
            assert tuple((s.state.current, s.state.voltage, s.state.refractory_remaining)
                         for s in trace.compartment_state_after) == tuple(
                (s.current, s.voltage, s.refractory_remaining) for s in got.states_after
            ), f"t={t} chip states"
            assert sorted(p.destination_axon for p in trace.packets_out) == sorted(got.next_packet_axons)
        assert dense.predicted_class == packed.predicted_class


def test_nonuniform_per_neuron_parameters_are_rejected():
    p = LIFParameters(4096, 205, 2048)
    q = LIFParameters(4096, 205, 2048, bias=1)
    train = IntegerForwardSNN(p, p)
    compact = train.to_integer_network()
    nonuniform = CompactNetwork(
        compact.input_to_hidden, compact.hidden_to_output,
        (p,) * 31 + (q,), compact.output_params,
    )
    with pytest.raises(ValueError, match="uniform LIF config"):
        compact_to_compiler_spec(nonuniform)
