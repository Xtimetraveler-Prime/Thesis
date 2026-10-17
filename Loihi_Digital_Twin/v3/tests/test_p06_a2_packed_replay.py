"""A2.4: independent packed replay with hand-built fixture and native integration.

No actual FPGA/Vitis HLS is claimed: hardware image is the existing P03 ABI.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest

from loihi_twin_v2.p06_compact_inference import CompactNetwork, infer_image
from loihi_twin_v2.p06_integer_oracle import LIFParameters
from loihi_twin_v2.p06_packed_replay import replay_p03_image


def fixture_small_packed():
    # One selected pixel -> hidden 0 -> output 0, every edge weight 2.
    # Neuron ID layout is hidden 0..31, then output 32..41.
    config = 4096 | (4096 << 13) | (1 << 26)
    axon_valid = 1 << 41
    axon0 = (0 << 0) | (1 << 15) | (0 << 31) | axon_valid
    axon1 = (1 << 0) | (1 << 15) | (32 << 31) | axon_valid
    syn0 = 0 | (2 << 10)
    syn1 = 0 | (2 << 10)
    return SimpleNamespace(
        core_id=0, compartment_count=42, synapse_count=2, route_count=1,
        config_words=(config,) * 42, state_words=(0,) * 42,
        axon_words=(SimpleNamespace(index=0, word=axon0), SimpleNamespace(index=1, word=axon1)),
        synapse_words=(syn0, syn1),
        route_descriptor_words=(SimpleNamespace(index=0, word=(1 << 12) | (1 << 25)),),
        route_words=((1 << 7),),
    )


def test_handbuilt_packed_pipeline_next_tick_and_output_readout():
    img = fixture_small_packed()
    # Map 784 distinct pixel axons: 0 has one synapse, 1..783 have
    # zero-length rows. Reserve separate axon 900 for hidden self-routing.
    img.axon_words = (
        SimpleNamespace(index=0, word=img.axon_words[0].word),
        SimpleNamespace(index=900, word=img.axon_words[1].word),
    ) + tuple(SimpleNamespace(index=i, word=1 << 41) for i in range(1, 784))
    img.route_words = (900 << 7,)
    result = replay_p03_image(img, tuple(range(784)), bytes([255] + [0] * 783))
    assert len(result.ticks) == 26
    assert result.ticks[0].fired_compartments == (0,)
    assert result.ticks[0].next_packet_axons == (900,)
    assert result.ticks[0].output_counts == (0,) * 10
    assert result.ticks[1].fired_compartments == (0, 32)
    assert result.ticks[1].accumulators[32] == 2
    assert result.ticks[25].fired_compartments == (32,)
    assert result.output_counts == (25,) + (0,) * 9
    assert result.predicted_class == 0
    assert result.dropped_boundary_packets == ()

    hi = [[0] * 784 for _ in range(32)]
    ho = [[0] * 32 for _ in range(10)]
    hi[0][0] = 2
    ho[0][0] = 2
    p = LIFParameters(4096, 4096, 1)
    oracle = infer_image(CompactNetwork.from_uniform_parameters(hi, ho, p, p), bytes([255] + [0] * 783))
    assert result.output_counts == oracle.output_counts
    for tick in range(26):
        t = result.ticks[tick]
        expected = oracle.traces[tick]
        assert t.fired_compartments == expected.hidden_spikes + tuple(32 + i for i in expected.output_spikes)
        assert t.accumulators == expected.hidden_synaptic_inputs + expected.output_synaptic_inputs
        assert t.states_after == expected.hidden_after + expected.output_after


def test_corrupt_packed_word_fails_closed():
    img = fixture_small_packed()
    img.config_words = ((1 << 120),) + img.config_words[1:]
    with pytest.raises(ValueError, match="reserved"):
        replay_p03_image(img, tuple(range(784)), bytes([0] * 784))


def test_native_compiler_image_logicalchip_and_uncompiled_reference_agree():
    """Runs only in the actual Thesis/v3 repository (not local mirror)."""
    from loihi_twin_v2.compiler import MappingOptions, compile_network
    from loihi_twin_v2.hardware_p03 import export_one_core_image

    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("native_p06_compiler_probe", root / "scripts" / "p06_lif_compiler_probe.py")
    assert spec is not None and spec.loader is not None
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)

    compiled = compile_network(m.make_synthetic_exploratory_network(32), MappingOptions(max_logical_cores=1))
    assert len(compiled.logical_deployment.core_configs) == 1
    hardware = export_one_core_image(compiled.logical_deployment.core_configs[0])
    routes = sorted(compiled.ingress_routes, key=lambda r: r.input_index)
    assert len(routes) == 784
    assert [r.input_index for r in routes] == list(range(784))
    assert all(r.destination_core == 0 for r in routes)
    pixel_to_axon = tuple(r.destination_axon for r in routes)
    params = LIFParameters(4096, 205, 2048)
    reference_net = CompactNetwork.from_uniform_parameters(
        [[m.dense_weights(source, hidden, 784, 32) for source in range(784)] for hidden in range(32)],
        [[m.dense_weights(hidden, output, 32, 10) for hidden in range(32)] for output in range(10)],
        params, params,
    )
    images = (
        bytes([0] * 784),
        bytes([255] * 784),
        bytes((i * 43 + 7) % 256 for i in range(784)),
    )
    from loihi_twin_v2.p06_input_contract import pixel_spikes
    for image in images:
        expected = infer_image(reference_net, image)
        packed = replay_p03_image(hardware, pixel_to_axon, image)
        chip = compiled.build_chip()  # per-image reset
        assert packed.output_counts == expected.output_counts
        assert packed.predicted_class == expected.predicted_class
        for tick in range(26):
            reference = expected.traces[tick]
            observed = packed.ticks[tick]
            events = compiled.external_packets("pixels", pixel_spikes(image, tick), target_timestep=tick)
            chip_trace = chip.step(events)
            core = chip_trace.cores[0]
            spikes = reference.hidden_spikes + tuple(32 + i for i in reference.output_spikes)
            assert observed.fired_compartments == spikes == core.spikes_out, f"spike mismatch t={tick}"
            assert observed.accumulators == reference.hidden_synaptic_inputs + reference.output_synaptic_inputs
            expected_states = reference.hidden_after + reference.output_after
            assert observed.states_after == expected_states
            assert tuple((s.state.current, s.state.voltage, s.state.refractory_remaining)
                         for s in core.compartment_state_after) == tuple(
                             (s.current, s.voltage, s.refractory_remaining) for s in expected_states
                         ), f"state mismatch t={tick}"
            assert observed.output_counts == reference.output_spike_counts
            assert len(core.packets_out) == len(observed.next_packet_axons)
            assert sorted(p.destination_axon for p in core.packets_out) == sorted(observed.next_packet_axons)


def test_signed_negative_packed_synapse_and_repeat_frame_reset():
    img = fixture_small_packed()
    img.synapse_words = (img.synapse_words[0], ((1 << 24) - 2) << 10)
    img.axon_words = (
        SimpleNamespace(index=0, word=img.axon_words[0].word),
        SimpleNamespace(index=900, word=img.axon_words[1].word),
    ) + tuple(SimpleNamespace(index=i, word=1 << 41) for i in range(1, 784))
    img.route_words = (900 << 7,)
    white_pixel = bytes([255] + [0] * 783)
    first = replay_p03_image(img, tuple(range(784)), white_pixel)
    assert first.ticks[1].accumulators[32] == -2
    assert first.output_counts == (0,) * 10
    assert first.predicted_class == 0
    # Full-frame replay always resets states, counters and current/NEXT banks.
    blank = replay_p03_image(img, tuple(range(784)), bytes(784))
    assert blank.ticks[0].axons_current == ()
    assert blank.output_counts == (0,) * 10
    assert replay_p03_image(img, tuple(range(784)), white_pixel) == first
