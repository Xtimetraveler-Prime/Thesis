"""Source-annotated project event-encoding feasibility, no MNIST checkpoint."""
from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]

def load(path,name):
    spec=importlib.util.spec_from_file_location(name,ROOT/"scripts"/path)
    assert spec is not None and spec.loader is not None
    obj=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(obj)
    return obj

P=load("p06_lif_input_probe.py","p06_lif_input_probe")
M=load("p06_lif_compiler_probe.py","p06_lif_compiler_probe")

def test_extrema_quota_rate_input_and_output_flush():
    assert P.rate_coded_pixel_indices([0]*784,0)==()
    for t in range(25):
        assert P.rate_coded_pixel_indices([255]*784,t)==tuple(range(784))
    assert P.rate_coded_pixel_indices([255]*784,25)==()
    assert sum(len(P.rate_coded_pixel_indices([0]*784,t)) for t in range(26))==0

def test_mid_gray_produces_deterministic_bounded_rate_pattern():
    pixels=[0]*784
    pixels[0]=128
    pixels[101]=128
    spikes=[P.rate_coded_pixel_indices(pixels,t) for t in range(25)]
    assert sum(0 in row for row in spikes)==(25*128)//255
    assert sum(101 in row for row in spikes)==(25*128)//255
    # Pixel indices 0 and 101 have different modulo-25 phase offsets.
    assert [t for t,row in enumerate(spikes) if 0 in row] != [
        t for t,row in enumerate(spikes) if 101 in row]
    assert spikes==[P.rate_coded_pixel_indices(pixels,t) for t in range(25)]

@pytest.mark.parametrize("bad,step",[
    ([0]*783,0),([0]*785,0),([0]*783+[256],0),([0]*783+[-1],0),
    ([0.0]*784,0),([0]*784,-1),([0]*784,26),
])
def test_event_encoder_refuses_malformed_samples(bad,step):
    with pytest.raises(ValueError):
        P.rate_coded_pixel_indices(bad,step)

def test_spike_readout_ties_and_valid_spike_counts():
    assert P.class_from_output_spike_counts([0]*10)==0
    assert P.class_from_output_spike_counts([1,4,3,4]+[0]*6)==1
    assert P.class_from_output_spike_counts([0]*9+[3])==9
    with pytest.raises(ValueError):
        P.class_from_output_spike_counts([0]*9)
    with pytest.raises(ValueError):
        P.class_from_output_spike_counts([0]*9+[-1])

@pytest.fixture(scope="module")
def real_compiled():
    from loihi_twin_v2.compiler import compile_network,MappingOptions
    return compile_network(M.make_synthetic_exploratory_network(32),
                           MappingOptions(max_logical_cores=1))

def test_real_v3_ingress_uses_784_distinct_allocated_destination_axons(real_compiled):
    packets=P.verified_external_packets(real_compiled,[255]*784,0)
    assert len(packets)==784
    assert all(p.target_timestep==0 and p.destination_core==0 for p in packets)
    assert len({p.destination_axon for p in packets})==784
    assert not P.verified_external_packets(real_compiled,[0]*784,0)
    assert not P.verified_external_packets(real_compiled,[255]*784,25)

def test_real_logical_chip_self_routing_is_next_step_not_analog_same_step(real_compiled):
    # This is the *existing v3 LogicalChip golden*, not FPGA bitstream execution.
    # A route-table entry is NOT itself a packet: only a neuron that actually
    # crosses its threshold generates a packet. This deterministic all-255
    # synthetic input leaves hidden neuron 1 subthreshold (1696 <= 2048).
    assert sum(M.dense_weights(src,1,784,32) for src in range(784))==1696
    expected_hidden_spikes=tuple(i for i in range(32) if i!=1)
    chip=real_compiled.build_chip()
    p=P.verified_external_packets(real_compiled,[255]*784,0)
    first=chip.step(p)
    assert first.algorithmic_timestep==0
    assert len(first.cores)==1
    first_core=first.cores[0]
    assert len(first_core.packet_in)==784
    assert first_core.spikes_out==expected_hidden_spikes
    assert len(first_core.packets_out)==len(expected_hidden_spikes)==31
    assert tuple(packet.source_compartment for packet in first_core.packets_out)==expected_hidden_spikes
    assert all(packet.target_timestep==1 and packet.source_timestep==0
               and packet.destination_core==0 for packet in first_core.packets_out)
    assert all(x.state.voltage==0 for x in first_core.compartment_state_after[32:])
    second=chip.step(())
    assert second.algorithmic_timestep==1
    second_core=second.cores[0]
    # NEXT-bank arrivals, not same-tick feedforward contributions.
    assert len(second_core.packet_in)==len(first_core.packets_out)
    assert {packet.logical_key for packet in second_core.packet_in}=={
        packet.logical_key for packet in first_core.packets_out
    }
    assert len(second_core.synaptic_contributions)==31*10
    assert all(32<=entry.target_compartment<42
               for entry in second_core.synaptic_contributions)
    assert any(i>=32 for i in second_core.spikes_out)


def test_allocated_routes_do_not_generate_spikes_without_threshold_crossing(real_compiled):
    # 32 physical route descriptors are *potential* routes. No event, no
    # hidden spike, no routed NEXT-bank traffic or downstream contribution.
    assert real_compiled.report()["static_route_estimate"]["total"]==32
    chip=real_compiled.build_chip()
    first=chip.step(P.verified_external_packets(real_compiled,[0]*784,0))
    assert first.cores[0].spikes_out==()
    assert first.cores[0].packets_out==()
    second=chip.step(())
    assert second.cores[0].packet_in==()
    assert second.cores[0].synaptic_contributions==()
