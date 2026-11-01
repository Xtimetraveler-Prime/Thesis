"""P07-B.4m independent V3 real-run numerical audit: synthetic NO-BOARD tests."""
from __future__ import annotations
from pathlib import Path
import shutil
import struct
import subprocess
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_v3_train0_scalar_vs_physical as audit

def state(current=0,voltage=0,refractory_remaining=0):
    return SimpleNamespace(current=current,voltage=voltage,
                           refractory_remaining=refractory_remaining)

def test_signed_state_24_24_16_packing_matches_p03_wire_abi():
    s=state(-1,-2,0x1234)
    assert audit.state_word(s)==(0xFFFFFF|(0xFFFFFE<<24)|(0x1234<<48))
    with pytest.raises(audit.ParityNoGo):
        audit.state_word(state(1<<23))
    with pytest.raises(audit.ParityNoGo):
        audit.state_word(state(refractory_remaining=1<<16))

def test_native_little_endian_trace_fnv_words_and_26tick_reduction():
    words=[0x12345678,0xFFFFFFFF,0x01020304,0,0xABCDEF12,0,1,0]
    raw=struct.pack("<8I",*words)
    oracle_expected=audit.FNV_SEED
    for value in raw:
        oracle_expected=((oracle_expected^value)*1099511628211)&((1<<64)-1)
    assert audit.fnv_words(words)==oracle_expected
    assert audit.fnv_bytes(audit.FNV_SEED,raw)==oracle_expected
    with pytest.raises(audit.ParityNoGo):
        audit.fnv_words([-1])
    with pytest.raises(audit.ParityNoGo):
        audit.fnv_words([1<<32])

def test_all_1010_original_neurons_x_26_ticks_trace_fingerprint():
    # Deterministic standalone constructed oracle; no frozen or physical
    # evidence imported. Independently re-encode hardware trace layout.
    placements=[]
    for cid in range(27):
        size=10 if cid==26 else (39 if cid==0 else (
            39 if cid==1 else 40))
        # 39 + 39 + 24*40 + 10 = 1048; use exactly 1010 below instead.
        placements.extend((cid,comp,("h",cid*1000+comp))
                          for comp in range(size))
    placements=placements[:1010]
    # Include 10 terminal readout neurons at original core 26.
    placements=[(cid,c,key) for cid,c,key in placements if cid!=26]
    placements=placements[:1000]
    placements.extend((26,c,("r",c)) for c in range(10))
    assert len(placements)==1010
    place=[SimpleNamespace(core_id=cid,compartment_id=c,
                           population=key[0],neuron_index=key[1])
           for cid,c,key in placements]
    zeros=state()
    keys=[key for _,_,key in placements]
    ticks=[]
    for tick in range(26):
        spiked=(("r",1),) if tick%2 else ()
        before=tuple((key,zeros) for key in keys)
        inp=tuple((key,-12345 if key==("r",1) else 0) for key in keys)
        after=tuple((key,state(-1,-2,3) if key==("r",1) else zeros)
                    for key in keys)
        ticks.append(SimpleNamespace(tick=tick,before=before,
                                     synaptic_inputs=inp,after=after,
                                     spikes=spiked))
    h,per_tick=audit.trace_fingerprint(SimpleNamespace(ticks=ticks),place)
    assert len(per_tick)==26
    # Independent wire little-endian pack; this is different code from
    # the candidate 32bit-word streamer, tests ordering and signed bits.
    overall=audit.FNV_SEED
    expected_ticks=[]
    for tick in range(26):
        raw=bytearray()
        for cid,c,key in sorted(placements):
            b=0
            i=(-12345 if key==("r",1) else 0)&audit.MASK64
            a=audit.state_word(state(-1,-2,3)) if key==("r",1) else 0
            spike=int(key==("r",1) and tick%2==1)
            raw+=struct.pack("<QQQII",b,i,a,spike,0)
        t=audit.FNV_SEED
        for byte in raw:
            t=((t^byte)*audit.FNV_PRIME)&audit.MASK64
        expected_ticks.append(f"0x{t:016X}")
        for byte in t.to_bytes(8,"little"):
            overall=((overall^byte)*audit.FNV_PRIME)&audit.MASK64
    assert per_tick==expected_ticks
    assert h==f"0x{overall:016X}"
    assert h!=f"0x{audit.FNV_SEED:016X}"

def test_counters_from_signed_original_layout_not_physical_receipt():
    # Critical regression: use the ACTUAL frozen P06 B1.2 IngressRoute
    # dataclass, never synthetic source_input/source_index fields.
    from loihi_twin_v2.compiler import IngressRoute
    compiled=SimpleNamespace(
        ingress_routes=[
            IngressRoute("pixels",0,0,0),
            IngressRoute("pixels",0,1,3),
            IngressRoute("pixels",1,0,4),
        ],
        placement=[SimpleNamespace(population="h",neuron_index=0,
                                   core_id=0,compartment_id=0),
                   SimpleNamespace(population="r",neuron_index=1,
                                   core_id=26,compartment_id=1)],
        logical_deployment=SimpleNamespace(core_configs=[
            SimpleNamespace(core_id=0,output_routes=[
                SimpleNamespace(source_compartment=0,routes=[1,2,3])]),
            SimpleNamespace(core_id=26,output_routes=[]),
        ]))
    run=SimpleNamespace(ticks=[
            SimpleNamespace(spikes=(("h",0),)),
            SimpleNamespace(spikes=(("r",1),)),
        ],spike_count=2,predicted_class=1,readout_spike_counts=(0,1))
    expected=audit.expected_counters(run,((0,1),(0,)),compiled)
    assert expected=={
        "external_current_events":5,
        "source_spikes_from_P03_trace_bank7":2,
        "P03_packet_words_captured":3,
        "NEXT_packets_physically_inserted":3,
        "trained_readout_prediction":1,
        "readout_spike_counts":[0,1],
    }

def test_real_ingress_route_abi_rejects_invalid_external_population():
    from loihi_twin_v2.compiler import IngressRoute
    bad=SimpleNamespace(
        ingress_routes=[IngressRoute("not_pixels",0,0,0)],
        placement=[],logical_deployment=SimpleNamespace(core_configs=[]))
    fake=SimpleNamespace(ticks=(),spike_count=0,predicted_class=0,
                         readout_spike_counts=())
    with pytest.raises(audit.ParityNoGo,match="pixel input route"):
        audit.expected_counters(fake,(),bad)


def test_mismatch_never_counts_as_independent_parity():
    a={"trained_readout_prediction":1,"readout_spike_counts":[0,25],
       "external_current_events":31512,
       "source_spikes_from_P03_trace_bank7":1514,
       "P03_packet_words_captured":1489,
       "NEXT_packets_physically_inserted":1489,
       "all_26_tick_trace_hash":"0xB59CA8594D6E64AD"}
    expected={k:a[k] for k in a if k!="all_26_tick_trace_hash"}
    checks=audit.compare(a,expected,"0xB59CA8594D6E64AD")
    assert all(checks.values())
    checks=audit.compare(a,{**expected,"readout_spike_counts":[0,24]},
                         "0xB59CA8594D6E64AD")
    assert checks["readout_spike_counts"] is False
    checks=audit.compare(a,expected,"0x1111111111111111")
    assert checks["all_26_tick_trace_fingerprint"] is False
    assert not all(checks.values())

def test_frozen_physical_source_gate_never_treats_missing_files_as_proof(tmp_path):
    evidence=tmp_path/audit.EVIDENCE_NAME
    evidence.mkdir()
    with pytest.raises(audit.ParityNoGo,match="missing"):
        audit.check_physical(evidence,tmp_path,tmp_path,{})
    wrong=tmp_path/"some_previous_V2_run"
    wrong.mkdir()
    with pytest.raises(audit.ParityNoGo,match="require exact"):
        audit.check_physical(wrong,tmp_path,tmp_path,{})

def test_only_original_first_real_mailbox_and_sealed_test_contract():
    assert audit.MAILBOX_SHA=="5a2d9c9645b79144ef20f5ed7f26e5ed1ad3745aaf929713cf89fcb7f8718eda"
    assert audit.TRAIN0_SHA=="2aa772efd381805bab24fea145186d22f3550b156f155a9ab51dcef10e6d8126"
    source=(ROOT/"scripts/p07_b4m_v3_train0_scalar_vs_physical.py").read_text()
    assert "simulate_monolithic" in source
    assert "pixel_schedule_independent" in source
    assert "b23_validation_parity.json" in source
    assert '"strict_full_neuron_physical_numeric_parity_proven":False' in source
    assert "xsdb" not in source.lower()
    assert "official_MNIST_TEST" in source
    assert '"actual_board_access":False' in source
    assert '"all_26_tick_trace_fingerprint"' in source
