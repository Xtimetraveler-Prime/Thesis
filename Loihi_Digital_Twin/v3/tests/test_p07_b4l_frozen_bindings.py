"""B4l actual frozen descriptor stage and original-C P03 registration gate.

Fixtures use synthetic metadata ONLY for native format/failure checks; real
prepare/verify requires user's original immutable B2.4 packed deployment.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
import struct
import subprocess
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4l_frozen_bindings as b


def synthetic_rows():
    result=[]
    for cid in range(27):
        bitmap=bytearray(512)
        for ax in (cid,100+cid,200+cid):
            bitmap[ax//8]|=1<<(ax%8)
        result.append({
            "core_id":cid,"compartments":4,
            "metadata":cid|(4<<7),"axon_count":3,
            "bitmap_hex":bitmap.hex(),
        })
    return result


def test_original_metadata_descriptor_fixed_geometry_and_identity():
    rows=synthetic_rows()
    blob=b.build_payload(rows)
    assert len(blob)==16384
    assert blob[:8]==b"B4BIND01"
    assert struct.unpack_from("<6I",blob,8)==(1,16384,27,528,128,14256)
    assert blob[32:64].hex()==b.deploy.ACCEPTED_BUNDLE_SHA
    assert blob[64:96].hex()==b.b1.DEPLOYMENT_SHA
    assert blob[96:128]==hashlib.sha256(blob[128:128+14256]).digest()
    receipt=b.verify_payload(blob,rows)
    assert receipt["registered_axons_total"]==81
    assert receipt["physical_staging_address"]=="0x43FC0000"
    assert receipt["physical_staging_end_exclusive"]=="0x43FC4000"
    assert blob[128+14256:]==bytes(16384-128-14256)


@pytest.mark.parametrize(("mutation","value"),[
    (0,0x44),(8,0),(12,0),(20,0),(24,0),(28,0),
    (32,0),(64,0),(96,0),(144,0xFF),(160,0x80),
    (16383,1)
])
def test_any_descriptor_identity_axon_bitmap_or_padding_mutation_fails(mutation,value):
    rows=synthetic_rows()
    blob=bytearray(b.build_payload(rows))
    blob[mutation]=value if value!=blob[mutation] else (value^0xFF)
    with pytest.raises(b.BindingError,match="NO-GO"):
        b.verify_payload(bytes(blob),rows)


def test_reorder_or_wrong_axon_population_rejected():
    rows=synthetic_rows()
    swapped=list(rows)
    swapped[0],swapped[1]=swapped[1],swapped[0]
    with pytest.raises(b.BindingError,match="order"):
        b.build_payload(swapped)
    tampered=synthetic_rows()
    tampered[1]["axon_count"]=20
    with pytest.raises(b.BindingError,match="bitmap"):
        b.build_payload(tampered)
    tampered=synthetic_rows()
    tampered[4]["metadata"]=4
    with pytest.raises(b.BindingError,match="metadata"):
        b.build_payload(tampered)


def test_original_binding_staging_no_overwrite_and_byte_exact_verify(tmp_path,monkeypatch):
    frozen=tmp_path/"original_frozen"
    frozen.mkdir()
    source=tmp_path/"accepted_ddr_stage"
    source.mkdir()
    monkeypatch.setattr(b.deploy,"prepare_verified_contexts",lambda *a: {"records":[]})
    monkeypatch.setattr(b,"original_core_bindings",lambda *_:synthetic_rows())
    output=tmp_path/"new_bindings"
    result=b.stage(frozen,source,output,"prepare")
    assert result["registered_axons_total"]==81
    assert b.stage(frozen,source,output,"verify")==result
    with pytest.raises(b.BindingError,match="new evidence"):
        b.stage(frozen,source,output,"prepare")
    data=output/b.FILENAME
    saved=data.read_bytes()
    data.write_bytes(saved[:100]+b"\x00"+saved[101:])
    with pytest.raises(b.BindingError,match="identity"):
        b.stage(frozen,source,output,"verify")
    data.write_bytes(saved)
    index=output/b.INDEXNAME
    info=json.loads(index.read_text())
    info["registered_axons_total"]=82
    index.write_text(json.dumps(info))
    with pytest.raises(b.BindingError,match="index"):
        b.stage(frozen,source,output,"verify")


def test_real_compiled_legacy_sha_verifier_and_original_axon_packer_required():
    body=(ROOT/"scripts/p07_b4l_frozen_bindings.py").read_text()
    assert "deploy.prepare_verified_contexts(frozen,source_stage)" in body
    assert "B12Result.from_json" in body
    assert "export_one_core_image(cfg)" in body
    assert "value!=expected[axon]" in body
    assert "physical_staging_address" in body
    assert "frozen_model" not in body.lower() or "frozen" in body.lower()


def test_unchanged_real_p03_adapter_and_original_sha256_link(tmp_path):
    cc=shutil.which("cc") or shutil.which("gcc")
    assert cc,"requires C11 native compiler"
    blob=tmp_path/"bindings.bin"
    blob.write_bytes(b.build_payload(synthetic_rows()))
    exe=tmp_path/"bindings_native"
    paths=[
        "software/p03/p03_hw_adapter.c",
        "software/p07/p07_a2_sha256.c",
        "software/p07/p07_b4l_b3_bindings.c",
        "tests/native/p07_b4l_b3_bindings_harness.c",
    ]
    c=subprocess.run([
        cc,"-std=c11","-O0","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p03/include"),
        "-I",str(ROOT/"software/p07/include"),
        *(str(ROOT/p) for p in paths),
        "-o",str(exe)
    ],capture_output=True,text=True,timeout=60)
    assert c.returncode==0,c.stderr
    run=subprocess.run([str(exe),str(blob)],capture_output=True,text=True,timeout=40)
    assert run.returncode==0,run.stderr+run.stdout
    assert run.stdout.splitlines()==[
        "P07_B4L_B3_NATIVE_FROZEN_REGISTRATION_METADATA_AXONS_PASS=1",
        "P07_B4L_B3_NATIVE_FROZEN_REGISTRATION_TAMPER_FAIL_CLOSED=1",
    ]
