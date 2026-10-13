"""Original author sMNIST SNIP I/O semantics; NOT AHP/NxSDK hardware parity."""
from __future__ import annotations
import importlib.util
from pathlib import Path

import pytest

ROOT=Path(__file__).resolve().parents[1]
SCRIPT=ROOT/"scripts/p06_1_lsnn_io_contract.py"
spec=importlib.util.spec_from_file_location("lsnn_p06_source_io",SCRIPT)
assert spec is not None and spec.loader is not None
IO=importlib.util.module_from_spec(spec)
spec.loader.exec_module(IO)

def blank(pixel=0):return [pixel]*784

def test_original_author_threshold_array_is_numpy_equivalent():
    np=pytest.importorskip("numpy")
    upstream=np.floor(np.linspace(0,255,40)).astype(int)
    assert list(IO.THRESHOLDS)==upstream.tolist()
    assert len(IO.THRESHOLDS)==40
    assert (IO.THRESHOLDS[0],IO.THRESHOLDS[-1])==(0,255)

def test_rising_and_falling_crossing_uses_next_pixel_not_previous():
    img=blank()
    img[0]=0
    img[1]=30
    img[2]=0
    p0=IO.spike_ports(img,1)
    p1=IO.spike_ports(img,2)
    assert p0==(2,4,6,8)
    assert p1==(3,5,7,9)
    # Source indexes threshold 0? No. Ports 0 and 1 are UNTOUCHED.
    assert not ({0,1}&set(p0+p1))
    assert IO.spike_ports(img,3)==()

def test_last_pixel_cannot_look_across_images_but_can_fire_touch():
    img=blank()
    img[783]=255
    assert IO.spike_ports(img,784)==(78,)
    assert IO.spike_ports(img,783)==tuple(2*t for t in range(1,39))
    assert IO.spike_ports(img,785)==(79,)
    assert IO.spike_ports(img,840)==(79,)

def test_output_cue_repeats_for_56_steps_and_never_injects_during_pixel_loop():
    schedule=IO.stream_sparse_ports(blank())
    assert len(schedule)==56
    assert min(schedule)==785 and max(schedule)==840
    assert set(schedule.values())=={(79,)}

def test_constant_255_emits_touch_each_image_pixel_but_no_false_transitions():
    img=blank(255)
    schedule=IO.stream_sparse_ports(img)
    assert len(schedule)==840
    assert [schedule[t] for t in range(1,785)]==[(78,)]*784
    assert [schedule[t] for t in range(785,841)]==[(79,)]*56

def test_argmax_reads_nonspiking_membrane_V_not_output_spikes():
    assert IO.classify_output_membrane_voltages([0]*10)==0
    assert IO.classify_output_membrane_voltages([-20]*9+[99])==9
    assert IO.classify_output_membrane_voltages([123,45,123]+[-7]*7)==0
    assert IO.classify_output_membrane_voltages([-8388608]*10)==0

@pytest.mark.parametrize("item,step",[
    ([0]*783,1),([0]*785,1),([0]*784,0),([0]*784,841),
    ([0]*783+[256],4),([0]*783+[-1],4),
    ([0.0]*784,1),
])
def test_input_invalid_duration_dtype_range_fails(item,step):
    with pytest.raises(ValueError):
        IO.spike_ports(item,step)

def test_invalid_non_24bit_output_membrane_readout_fails():
    for values in ([0]*9,[0]*11,[-(1<<23)-1]+[0]*9,
                   [(1<<23)]+[0]*9,[0.0]*10):
        with pytest.raises(ValueError):
            IO.classify_output_membrane_voltages(values)
