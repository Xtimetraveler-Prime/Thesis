"""P08-B2.1 original 27-core image ingress, bounded DDR and native C tests."""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import zlib

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b2_stage_1024_ingress as stage
from loihi_twin_v2.p06_b13_streaming import B13_INGRESS_MAGIC, _pack_frame


def test_candidate_raw_memory_regions_are_disjoint_and_not_owner_proof():
    result=stage.validate_memory_ranges()
    assert result["static_disjoint_with_listed_regions"] is True
    assert result["physical_DDR_owner_exclusivity_proven"] is False
    assert result["new_Vitis_ELF_PT_LOAD_checked"] is False
    assert result["standalone_KV260_launch_authorized"] is False
    assert result["ranges"]["1024_raw_pixels_pool"] == [
        "0x42100000","0x421C4000"
    ]


def test_reject_overlapping_future_buffers():
    ranges=dict(stage.RANGES)
    ranges["new_sidecar_bad"]=(0x421A0000,0x421D0000)
    with pytest.raises(stage.B2NoGo):
        stage.validate_memory_ranges(ranges)


def test_reject_backup_sized_for_too_few_cores():
    ranges=dict(stage.RANGES)
    ranges["immutable_27_P02_backup_candidate"]=(0x43000000,0x43D00000)
    with pytest.raises(stage.B2NoGo):
        stage.validate_memory_ranges(ranges)


def test_reject_non_aligned_or_outside_aperture():
    ranges=dict(stage.RANGES)
    ranges["new_bad"]=(0x44000000,0x44000100)
    with pytest.raises(stage.B2NoGo):
        stage.validate_memory_ranges(ranges)
    ranges["new_bad"]=(0x42A00001,0x42A00100)
    with pytest.raises(stage.B2NoGo):
        stage.validate_memory_ranges(ranges)


def test_original_b13_format_bytewise_parity_with_reference():
    # Pure formatting fixture: synthetic route content cannot authenticate B2.4.
    routes=bytes((i*19+11)&255 for i in range(stage.ROUTE_BYTES))
    pixels=bytes((i*7+2)&255 for i in range(784))
    wire=stage.wire_from_pinned_route_bytes(routes,pixels)
    payload=routes+pixels
    fields=(1,128,len(payload),20384,27,784,25,26,6,784,0,0,0,0)
    expected=_pack_frame(B13_INGRESS_MAGIC,fields,
                         stage.b1.B24_COMPILED_SHA,
                         "82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498",
                         payload)
    assert wire==expected
    assert len(wire)==123216
    assert wire[128+20384*6:]==pixels
    assert struct.unpack_from("<I",wire,48)[0]==zlib.crc32(payload)
    header=bytearray(wire[:128])
    crc=struct.unpack_from("<I",header,52)[0]
    struct.pack_into("<I",header,52,0)
    assert zlib.crc32(header)==crc


def test_modified_raw_pixels_change_ingress_and_checksum():
    routes=bytes(stage.ROUTE_BYTES)
    a=bytes([0])*784
    b=bytes([0])*783+bytes([1])
    first=stage.wire_from_pinned_route_bytes(routes,a)
    second=stage.wire_from_pinned_route_bytes(routes,b)
    assert first!=second
    assert hashlib.sha256(first).digest()!=hashlib.sha256(second).digest()
    assert struct.unpack_from("<I",first,48)!=struct.unpack_from("<I",second,48)


@pytest.mark.parametrize("nr,npix",[
    (stage.ROUTE_BYTES-1,784),(stage.ROUTE_BYTES+1,784),
    (stage.ROUTE_BYTES,783),(stage.ROUTE_BYTES,785),
])
def test_invalid_route_or_pixel_dimensions_refused(nr,npix):
    with pytest.raises(stage.B2NoGo):
        stage.wire_from_pinned_route_bytes(bytes(nr),bytes(npix))


def test_route_pin_rejects_missing_or_symlink_source(tmp_path):
    p=tmp_path/stage.ROUTE_FILENAME
    with pytest.raises(stage.B2NoGo):
        stage.pinned_route_payload(p,None)
    good=tmp_path/"not_a_real_route.bin"
    good.write_bytes(bytes(0xE0000))
    p.symlink_to(good)
    with pytest.raises(stage.B2NoGo):
        stage.pinned_route_payload(p,None)
    p.unlink()
    p.write_bytes(bytes(0xE0000))
    with pytest.raises(stage.B2NoGo):
        stage.pinned_route_payload(p,None)


def test_native_c11_new_builder_compiles_and_rejects_unsigned_input(tmp_path):
    cc=shutil.which("cc")
    if not cc:
        pytest.fail("strict C11 compiler required")
    exe=tmp_path/"p08_b2_ingress_native"
    command=[
        cc,"-std=c11","-O2","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p08"),
        "-I",str(ROOT/"software/p07/include"),
        str(ROOT/"software/p08/p08_b2_ingress.c"),
        str(ROOT/"software/p07/p07_a2_sha256.c"),
        str(ROOT/"tests/native/p08_b2_ingress_native.c"),
        "-o",str(exe),
    ]
    subprocess.run(command,check=True,capture_output=True,text=True)
    result=subprocess.run([str(exe),"--reject-zeros"],check=True,
                          capture_output=True,text=True)
    assert "P08_B2_NATIVE_INVALID_ROUTES_REJECTED=1" in result.stdout
