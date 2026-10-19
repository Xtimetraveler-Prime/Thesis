"""P08-A5 native host-only CPU reference differential tests.

Synthetic CPU oracle fixtures NEVER claim physical FPGA evidence or MNIST TEST.
"""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from loihi_twin_v2.p06_input_contract import image_event_schedule
from loihi_twin_v2.p06_packed_replay import replay_p03_image
from loihi_twin_v2.p08_a5_cpu_reference import (
    prepare_cpu,preloaded_compute,image_to_class,assert_matches_original_packed,
    assert_matches_physical,CPUOutcome,
)
from loihi_twin_v2 import p08_a5_cpu_benchmark as bench

ROOT=Path(__file__).resolve().parents[1]


def synthetic_p03_image():
    # Synthetic only: pixel0 drives hidden0, hidden0 routes axon784 to output32.
    # The NEXT bank means output class 0 fires one tick AFTER hidden compartment.
    axons=[]
    for i in range(785):
        first,length,offset=(
            (0,1,0) if i==0 else (1,1,32) if i==784 else (0,0,0)
        )
        word=(1<<41) | first | (length<<15) | (offset<<31)
        axons.append(SimpleNamespace(index=i,word=word))
    config=(4096 | (4096<<13) | (8<<26))
    # Synapse encoded signed24=25, destination relative=0 in both cases.
    return SimpleNamespace(
        core_id=0,compartment_count=42,config_words=(config,)*42,
        state_words=(0,)*42,synapse_count=2,
        synapse_words=(25<<10,25<<10),
        axon_words=tuple(axons),route_count=1,
        route_words=(784<<7,),
        route_descriptor_words=(SimpleNamespace(index=0,word=(1<<25)|(1<<12)),),
    )


@pytest.mark.parametrize("pixel0", [0,64,128,255])
def test_cpu_core_and_full_match_original_p06_packed_oracle_all_26_ticks(pixel0):
    image=synthetic_p03_image()
    mapping=tuple(range(784))
    prepared=prepare_cpu(image,mapping)
    raw=bytes([pixel0])+bytes(783)
    oracle=replay_p03_image(image,mapping,raw)
    schedule=image_event_schedule(raw)
    core=preloaded_compute(prepared,schedule)
    full=image_to_class(prepared,raw)
    assert core==full
    assert len(core.output_spikes)==26
    assert core.external_events==sum(map(len,schedule))
    assert_matches_original_packed(core,oracle,schedule,0)
    assert_matches_original_packed(full,oracle,schedule,0)
    if pixel0==255:
        assert core.counts[0]==25
        assert core.output_spikes[0][0]==0
        assert core.output_spikes[1][0]==1
        assert core.output_spikes[25][0]==1
        assert core.routes==25
        assert core.discarded==0
    if pixel0==0:
        assert core.predicted==0 and core.all_silent is True


def test_rejects_wrong_encoder_frame_and_timestep_schedule():
    prepared=prepare_cpu(synthetic_p03_image(),tuple(range(784)))
    with pytest.raises(ValueError,match="784"):
        image_to_class(prepared,bytes(782))
    with pytest.raises(ValueError,match="26"):
        preloaded_compute(prepared,((),)*25)
    schedule=list(image_event_schedule(bytes(784)))
    schedule[25]=(0,)
    with pytest.raises(ValueError,match="empty drain"):
        preloaded_compute(prepared,tuple(schedule))
    schedule[25]=()
    schedule[0]=(0,0)
    with pytest.raises(ValueError,match="duplicate"):
        preloaded_compute(prepared,tuple(schedule))


def test_rejects_physical_mismatch_on_any_tick_or_count():
    prepared=prepare_cpu(synthetic_p03_image(),tuple(range(784)))
    cpu=image_to_class(prepared,bytes([255])+bytes(783))
    good=SimpleNamespace(**vars_as_dict(cpu))
    assert_matches_physical(cpu,good,17)
    bad=vars_as_dict(cpu)
    spikes=list(cpu.output_spikes)
    tick=list(spikes[12])
    tick[0]=1-tick[0]
    spikes[12]=tuple(tick)
    bad["output_spikes"]=tuple(spikes)
    with pytest.raises(AssertionError,match="frame=17"):
        assert_matches_physical(cpu,SimpleNamespace(**bad),17)


def vars_as_dict(outcome):
    return {name:getattr(outcome,name) for name in (
        "predicted","counts","output_spikes","routes",
        "discarded","external_events","all_silent"
    )}


def test_rejects_tampered_packed_axon_or_wrong_784_map():
    image=synthetic_p03_image()
    with pytest.raises(ValueError,match="784 distinct"):
        prepare_cpu(image,tuple(range(783))+(0,))
    broken=synthetic_p03_image()
    broken.axon_words=broken.axon_words+(
        SimpleNamespace(index=0,word=(1<<41)),)
    with pytest.raises(ValueError,match="duplicate packed axon"):
        prepare_cpu(broken,tuple(range(784)))


def test_exact_1024_host_two_endpoint_cpu_benchmark_bookkeeping(monkeypatch):
    out=CPUOutcome(0,(0,)*10,((0,)*10,)*26,0,0,0,True)
    monkeypatch.setattr(bench,"image_event_schedule",
                        lambda raw:((),)*26)
    monkeypatch.setattr(bench,"preloaded_compute",
                        lambda prepared,schedule:out)
    monkeypatch.setattr(bench,"image_to_class",
                        lambda prepared,raw:out)
    pixels=(bytes(784),)*1024
    row=SimpleNamespace(**vars_as_dict(out))
    data=bench.benchmark_cpu_two_endpoints(
        None,pixels,(row,)*1024,
        warmup=0,timer_environment={"synthetic_unit":"NO_REAL_CPU_BENCHMARK"},
    )
    assert data["unique_images"]==1024
    assert data["ordinary_images"]==1023
    assert data["benchmark_repeats"]==3
    assert data["fpga_service_scope_matched_exactly"] is False
    assert data["full_cpu_to_a53_fpga_speedup"].startswith("NOT_SUPPORTED")
    assert data["host_cpu_environment"]["synthetic_unit"]=="NO_REAL_CPU_BENCHMARK"
    assert data["all_1024_original_26tick_spike_traces_exact"]=="PASS"
    for name in ("preloaded_core_endpoint","full_raw_image_to_class_endpoint"):
        z=data[name]
        assert len(z["three_sequential_runs_ns"])==3
        assert all(len(sample)==1024 for sample in z["three_sequential_runs_ns"])
        assert all(sample>=0 for run in z["three_sequential_runs_ms"] for sample in run)
        assert len(z["ordinary_1023_per_image_median_across_three_runs_ms"])==1023
        assert z["ordinary_1023_aggregate_of_per_image_medians_ms"]["n"]==1023


def test_cpu_benchmark_rejects_wrong_frame_count_before_any_measurements():
    with pytest.raises(ValueError,match="1024"):
        bench.benchmark_cpu_two_endpoints(None,(bytes(784),)*16,(),warmup=0)


def test_cpu_benchmark_sources_have_no_hardware_or_test_corpus_access():
    source=(ROOT/"scripts/p08_a5_cpu_benchmark.py").read_text()
    assert "require_original_p07_oracle" in source
    assert "replay_p03_image" in source
    assert "assert_matches_original_packed" in source
    assert "official_mnist_test" in source.lower() or "P08_A5_OFFICIAL_TEST=SEALED" in source
    assert "physical_a21" in source
    assert "scripts/run_p08_a3_2_1024.sh" not in source
    assert "xsdb " not in source.lower()
    assert "vivado " not in source.lower()
