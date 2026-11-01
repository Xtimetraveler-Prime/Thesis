"""B5.3: original 256-bit hardware trace byte ABI / first-mismatch tests.

Pure synthetic oracle fixtures, NO physical board claims.
"""
from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import sys
from types import SimpleNamespace

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b5_raw_trace_reference as raw
import p07_b5_scaled_validation as b5

def st(c=0,v=0,r=0):
    return SimpleNamespace(current=c,voltage=v,refractory_remaining=r)

def fake_1010_x26():
    placement=[]
    for i in range(1000):
        placement.append(SimpleNamespace(
            core_id=i%26,compartment_id=i//26,
            population="hidden",neuron_index=i))
    for j in range(10):
        placement.append(SimpleNamespace(
            core_id=26,compartment_id=j,
            population="readout",neuron_index=j))
    keys=[(p.population,p.neuron_index) for p in placement]
    ticks=[]
    for t in range(26):
        ticks.append(SimpleNamespace(
            tick=t,
            before=[(key,st()) for key in keys],
            synaptic_inputs=[(key,-1 if key==("readout",1) else 0)
                             for key in keys],
            after=[(key,st(-7,5,2) if key==("readout",1) else st())
                   for key in keys],
            spikes=[("readout",1)] if t%2 else [],
        ))
    return SimpleNamespace(ticks=ticks),SimpleNamespace(placement=placement)

def test_840320_byte_hls_trace_exact_signed_state_and_spike_bit():
    run,compiled=fake_1010_x26()
    data,coords=raw.expected_raw_trace(run,compiled)
    assert len(data)==raw.TRACE_BYTES==840320
    assert len(coords)==26260
    assert coords[0][:3]==(0,0,0)
    assert coords[-1][:3]==(25,26,9)
    loc=next(i for i,item in enumerate(coords)
             if item[0]==1 and item[3]==("readout",1))
    chunk=data[loc*32:(loc+1)*32]
    assert chunk==struct.pack("<QQQII",
       0,(1<<64)-1,b5.baseline.state_word(st(-7,5,2)),1,0)
    whole=[]
    for t in range(26):
        span=data[t*1010*32:(t+1)*1010*32]
        whole.append(b5.baseline.fnv_bytes(b5.baseline.FNV_SEED,span))
    cumulative=b5.baseline.FNV_SEED
    for h in whole:
        cumulative=b5.baseline.fnv_bytes(cumulative,h.to_bytes(8,"little"))
    independently=b5.baseline.trace_fingerprint(run,compiled.placement)[0]
    assert independently==f"0x{cumulative:016X}"

@pytest.mark.parametrize("field_start,field_name",[
    (0,"before_state"),(8,"signed_64bit_synaptic_input"),
    (16,"after_state"),(24,"spike_bit"),(28,"reserved_bits"),
])
def test_diagnostic_first_exact_neuron_tick_and_field(field_start,field_name):
    run,compiled=fake_1010_x26()
    expected,coords=raw.expected_raw_trace(run,compiled)
    assert raw.first_mismatch(expected,expected,coords) is None
    idx=1010*3+41
    damaged=bytearray(expected)
    damaged[idx*32+field_start]^=1
    mismatch=raw.first_mismatch(expected,bytes(damaged),coords)
    assert mismatch is not None
    assert mismatch["tick"]==3
    assert mismatch["trace_word_index"]==idx
    assert mismatch["field"]==field_name
    assert mismatch["absolute_byte_offset"]==idx*32+field_start
    assert mismatch["population"]==coords[idx][3][0]
    assert mismatch["logical_core"]==coords[idx][1]
    assert mismatch["compartment"]==coords[idx][2]
    assert mismatch["expected_field_little_endian_hex"]!=mismatch["observed_field_little_endian_hex"]

def test_wrong_raw_size_cannot_be_truncated_to_false_full_pass():
    run,compiled=fake_1010_x26()
    data,coords=raw.expected_raw_trace(run,compiled)
    with pytest.raises(b5.ValidationNoGo,match="840320B"):
        raw.first_mismatch(data,data[:-1],coords)
    with pytest.raises(b5.ValidationNoGo,match="840320B"):
        raw.first_mismatch(data[:-1],data[:-1],coords)

def test_output_is_unauthenticated_until_separate_physical_sidecar():
    source=(ROOT/"scripts/p07_b5_raw_trace_reference.py").read_text()
    for token in (
        "direct_full_raw_26x1010_FPGA_trace_verified",
        "full_hardware_trace_capture_authenticated",
        "hardware_trace_source_authenticity_verified",
        "official_MNIST_TEST",
        "P07_B5_FULL_RAW_PHYSICAL_TRACE_AUTHENTICATED=0",
    ):
        assert token in source
    assert 'subprocess.run(["xsdb"' not in source
    assert "subprocess.run(" not in source
    assert "P07_B4M_A53_TRAIN_26_TICK_DIAGNOSTIC_V3" not in source
