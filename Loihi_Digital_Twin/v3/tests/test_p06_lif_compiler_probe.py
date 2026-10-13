"""Structural P06 LIF feasibility using real accepted compiler/FPGA packer.

No genuine MNIST samples, no inference, no synthetic paper checkpoint claims.
"""
from __future__ import annotations
import importlib.util
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location(
    "p06_lif_probe",ROOT/"scripts/p06_lif_compiler_probe.py")
assert SPEC and SPEC.loader
PROBE=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PROBE)

@pytest.fixture(scope="module")
def physical_packed_probe():
    return PROBE.probe_exploratory(32)

def test_synthetic_784_32_10_export_is_genuine_one_core_hardware_image(physical_packed_probe):
    r=physical_packed_probe
    image=r["actual_hardware_image"]
    assert r["weights_are_synthetic_and_have_no_MNIST_accuracy"] is True
    assert r["model_is_published_trained_checkpoint"] is False
    assert r["hardware_execution"] is False
    assert r["behavior_parity_snnTorch"] is False
    assert r["exploratory_project_architecture"]==[784,32,10]
    assert r["original_tutorial_architecture"]==[784,1000,10]
    assert image=={
        "compartment_count":42,
        "synapse_count":25408,
        "destination_axon_count":816,
        "route_count":32,
        "core_id":0,
    }
    assert r["logical_compiler_report"]["logical_core_count"]==1
    assert all(v>0 for v in r["logical_compiler_report"]["cores"][0]["headroom"].values())

def test_resident_worst_case_input_and_generated_events_fit(physical_packed_probe):
    c=physical_packed_probe["hard_capacities"]
    events=physical_packed_probe["theoretical_worst_case_events_per_step"]
    assert c["input_events_per_bank"]==4096
    assert events=={"all_pixels_external":784,"hidden_routed":32,
                   "conservative_combined":816}
    assert events["conservative_combined"]<c["input_events_per_bank"]

def test_accepted_fpga_resource_limits_are_from_actual_constants(physical_packed_probe):
    c=physical_packed_probe["hard_capacities"]
    assert c=={
        "compartments":1024,
        "input_axons":4096,
        "route_entries":4096,
        "synapse_entries":32768,
        "synapse_memory_bytes":131072,
        "input_events_per_bank":4096,
    }
    assert physical_packed_probe["actual_hardware_image"]["synapse_count"] < 32768

def test_original_published_1000_hidden_tutorial_cannot_fit_accepted_5x_ddr_without_redesign():
    p=PROBE.original_tutorial_limit()
    assert p["tutorial_architecture"]==[784,1000,10]
    assert p["dense_potential_synapse_entries"]==794000
    assert p["minimum_synapse_banks_without_compression"]==25
    assert p["max_dense_synapses_over_five_records"]==163840
    assert p["fits_accepted_five_record_hardware"] is False

def test_original_synthetic_weights_have_distinct_template_rows_and_are_not_a_real_checkpoint():
    n=PROBE.make_synthetic_exploratory_network(32)
    assert len(n.input_projections[0].connections)==784*32
    assert len(n.projections[0].connections)==32*10
    # Distinguish each source by at least two entry weights;
    # prevents false PASS by route-template sharing all dense weights.
    codes={(PROBE.dense_weights(src,0,784,32),
            PROBE.dense_weights(src,1,784,32)) for src in range(784)}
    assert len(codes)==784
    assert PROBE.dense_weights(0,0,784,32)!=PROBE.dense_weights(1,0,784,32)
    with pytest.raises(ValueError):
        PROBE.dense_weights(-1,0,784,32)
    with pytest.raises(ValueError):
        PROBE.dense_weights(0,32,784,32)

def test_exploratory_compartment_is_24bit_integer_lif_not_published_float_leaky():
    spec=PROBE.make_synthetic_exploratory_network(32)
    cfg=spec.populations[0].compartment
    assert cfg.current_decay==4096
    assert cfg.voltage_decay==205
    assert cfg.threshold==2048
    assert cfg.reset_voltage==0
    assert cfg.refractory_ticks==0
    assert (1-205/4096)!=0.95
