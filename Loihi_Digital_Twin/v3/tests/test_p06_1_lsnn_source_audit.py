"""Host-only P06.1 sMNIST upstream provenance/header fail-closed tests.

These SYNTHETIC .npy headers are parser tests, not official pretrained
weights. Never label these native tests an author's model reproduction.
"""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path
import struct
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
SRC=ROOT/"scripts/p06_1_lsnn_source_audit.py"
SPEC=importlib.util.spec_from_file_location("p06_source_audit",SRC)
assert SPEC is not None and SPEC.loader is not None
AUDIT=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)

def make_npy(shape=(240,80),descr="<i4",fortran=False,extra=b"")->bytes:
    hdr=repr({"descr":descr,"fortran_order":fortran,"shape":shape})
    # .npy v1 full header aligned to 16 bytes including prefix+len.
    data=(hdr+"\n").encode("latin1")
    padding=(-((10+len(data))%16))%16
    header=hdr.encode("latin1")+b" "*padding+b"\n"
    assert (10+len(header))%16==0
    size=shape[0]*shape[1]*4
    return b"\x93NUMPY\x01\x00"+struct.pack("<H",len(header))+header+bytes(size)+extra

def test_accept_correct_matrix_headers_without_numpy_dependency():
    shape={"w_in.npy":(240,80),"w_rec.npy":(240,240),"w_out.npy":(10,240)}
    for name,expected in shape.items():
        info=AUDIT.parse_npy_header(make_npy(shape=expected))
        assert tuple(info["shape"])==expected
        assert info["payload_elements"]==expected[0]*expected[1]
        assert info["descr"]=="<i4"
    assert sum(s[0]*s[1] for s in shape.values())==79200

def test_each_dtype_is_extracted_not_guessed():
    for dtype in ("<f4","<i4","<u4"):
        assert AUDIT.parse_npy_header(make_npy(descr=dtype))["descr"]==dtype

@pytest.mark.parametrize("bad",[
    "magic","truncated","size_mismatch","fortran","object","wrong_dtype",
])
def test_corrupt_or_unsafe_npy_never_parses(bad):
    data=bytearray(make_npy())
    if bad=="magic":data[0]=0
    elif bad=="truncated":data=data[:40]
    elif bad=="size_mismatch":data.extend(b"\0")
    elif bad=="fortran":data=bytearray(make_npy(fortran=True))
    elif bad=="object":data=bytearray(make_npy(descr="|O4"))
    elif bad=="wrong_dtype":data=bytearray(make_npy(descr="<f8"))
    with pytest.raises(ValueError):
        AUDIT.parse_npy_header(bytes(data))

def test_actual_weight_count_math_is_independent_of_github_size():
    header=AUDIT.parse_npy_header(make_npy((2,3),descr="<i4"))
    import struct
    raw=bytearray(make_npy((2,3),descr="<i4"))
    struct.pack_into("<6i",raw,header["header_bytes"],0,1,-2,0,300,-1)
    observed=AUDIT.measure_weight_payload(bytes(raw),header)
    assert observed["entries"]==6
    assert observed["nonzero_entries"]==4
    assert observed["zero_entries"]==2
    assert (observed["positive_entries"],observed["negative_entries"])==(2,2)
    assert (observed["min_value"],observed["max_value"])==(-2,300)
    assert observed["density_fraction"]==pytest.approx(4/6)


def test_unusable_nan_float_weight_fails_closed():
    import struct
    blob=bytearray(make_npy((2,3),descr="<f4"))
    header=AUDIT.parse_npy_header(blob)
    struct.pack_into("<f",blob,header["header_bytes"],float("nan"))
    with pytest.raises(ValueError,match="NaN or infinite"):
        AUDIT.measure_weight_payload(bytes(blob),header)


def test_paper_is_not_silently_frozen_and_source_blobs_are_pinned():
    m=json.loads(AUDIT.MANIFEST.read_text())
    assert m["status"]=="CANDIDATE_SOURCE_PIN_ONLY_NOT_FROZEN_OR_REPRODUCED"
    assert m["upstream"]["commit"]==AUDIT.EXPECTED_COMMIT
    assert m["freeze_status"].startswith("PROHIBITED")
    assert len(m["upstream"]["files"])==9
    weights=[r for r in m["upstream"]["files"] if r["path"].endswith(".npy")]
    assert len(weights)==3
    for row in m["upstream"]["files"]:
        assert len(row["git_blob"])==40
        assert row["size_bytes"]>128
    for name in AUDIT.EXPECTED_SHAPES:
        row=next(r for r in weights if r["path"].endswith(name))
        assert row["size_bytes"]==AUDIT.EXPECTED_BYTES[name]
        assert tuple(row["expected_shape"])==AUDIT.EXPECTED_SHAPES[name]
    assert m["paper_accuracy_for_THIS_specific_checkpoint"]=="NOT_YET_VERIFIED"
    assert "BLOCKED" in m["v3_single_compartment_compatibility"]

def test_missing_upstream_source_cannot_create_fake_pass(tmp_path):
    with pytest.raises((OSError,ValueError)):
        AUDIT.audit(tmp_path/"not_cloned")
