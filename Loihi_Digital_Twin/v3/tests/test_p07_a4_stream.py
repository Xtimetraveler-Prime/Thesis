"""P07-A4.2a native Python/C11 parity: all payloads are SYNTHETIC.

No torch, no canonical MNIST TRAIN/TEST files, no hardware or FPGA claims.
Preserves accepted P07-A1/P07-A2 byte-level ABI.
"""
from __future__ import annotations

import ctypes
import json
import os
import sys
from pathlib import Path
import shutil
import struct
import subprocess
import zlib

import pytest

from loihi_twin_v2.p07_a1_ingress import decode_ingress, encode_ingress
from loihi_twin_v2 import p07_a4_stream as stream

ROOT = Path(__file__).resolve().parents[1]
MAPPING = tuple((i*73+17)%4096 for i in range(784))


class Descriptor(ctypes.Structure):
    _fields_ = [
        ("frame_count", ctypes.c_uint32),
        ("trace_frame", ctypes.c_uint32),
        ("image_crc32", ctypes.c_uint32),
        ("mapping_crc32", ctypes.c_uint32),
        ("descriptor_crc32", ctypes.c_uint32),
        ("ddr_sha256", ctypes.c_uint8*32),
        ("compiled_sha256", ctypes.c_uint8*32),
    ]


class Compact(ctypes.Structure):
    _fields_ = [
        ("image_index", ctypes.c_uint32),
        ("pixel_crc32", ctypes.c_uint32),
        ("committed_routes", ctypes.c_uint32),
        ("dropped_final_packets", ctypes.c_uint32),
        ("external_event_total", ctypes.c_uint32),
        ("cycles_low32", ctypes.c_uint32),
        ("output_spikes", (ctypes.c_uint8*10)*26),
    ]


def cbuf(raw: bytes):
    return (ctypes.c_uint8*len(raw)).from_buffer_copy(raw)


@pytest.fixture(scope="module")
def native(tmp_path_factory):
    cc = shutil.which("cc") or shutil.which("gcc") or shutil.which("clang")
    if not cc:
        pytest.skip("portable C11 compiler not available")
    lib = tmp_path_factory.mktemp("p07a4stream")/"libp07a4.so"
    cp = subprocess.run([
        cc, "-std=c11","-pedantic","-Werror","-Wall","-Wextra",
        "-O2","-fPIC","-shared",
        str(ROOT/"software/p07/p07_a4_stream.c"), "-o",str(lib),
    ], capture_output=True, text=True)
    assert cp.returncode == 0, cp.stderr
    api = ctypes.CDLL(str(lib))
    P = ctypes.POINTER(ctypes.c_uint8)
    api.p07_a4_validate_staging.argtypes = [
        P,ctypes.c_size_t,P,ctypes.c_size_t,P,ctypes.c_size_t,
        ctypes.POINTER(Descriptor),
    ]
    api.p07_a4_validate_staging.restype = ctypes.c_int
    api.p07_a4_make_ingress.argtypes = [
        ctypes.POINTER(Descriptor),P,ctypes.c_size_t,
        P,ctypes.c_size_t,ctypes.c_uint32,P,ctypes.c_size_t,
    ]
    api.p07_a4_make_ingress.restype = ctypes.c_int
    api.p07_a4_pack_result.argtypes = [
        ctypes.POINTER(Compact),P,ctypes.c_size_t,
    ]
    api.p07_a4_pack_result.restype = ctypes.c_int
    api.p07_a4_validate_result.argtypes = [
        P,ctypes.c_size_t,P,ctypes.c_size_t,ctypes.c_uint32,
    ]
    api.p07_a4_validate_result.restype = ctypes.c_int
    api.p07_a4_make_journal_header.argtypes = [
        P,ctypes.c_size_t,ctypes.c_uint32,ctypes.c_uint32,
        ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,ctypes.c_uint32,
    ]
    api.p07_a4_make_journal_header.restype = ctypes.c_int
    return api


def validate_c(native, obj):
    desc = Descriptor()
    rc = native.p07_a4_validate_staging(
        cbuf(obj.header), len(obj.header),
        cbuf(obj.mapping_bytes),len(obj.mapping_bytes),
        cbuf(obj.images),len(obj.images),ctypes.byref(desc),
    )
    return rc, desc


@pytest.mark.parametrize("count", [1,16,128,10000])
def test_full_capacity_new_ddr_layout_python_c_exact(native, count):
    images = (bytes(range(256))*3 + bytes(range(16))) * count
    assert len(images) == count*784
    obj = stream.make_stream(images, MAPPING, trace_index=count-1)
    assert stream.parse_stream(obj.header,obj.mapping_bytes,obj.images) == obj
    rc, info = validate_c(native, obj)
    assert rc == 0
    assert info.frame_count == count and info.trace_frame == count-1
    assert info.descriptor_crc32 == struct.unpack_from("<I",obj.header,252)[0]
    assert bytes(info.ddr_sha256).hex() == stream.DDR_SHA256
    assert bytes(info.compiled_sha256).hex() == stream.COMPILED_FINGERPRINT
    # The new journal fits in the separate 1MiB DDR result reservation.
    assert stream.RESULT_HEADER_BYTES+count*stream.RESULT_RECORD_BYTES <= stream.RESULT_CAPACITY
    if count in (1,16,128):
        for idx in set((0,count-1)):
            raw = (ctypes.c_uint8*2480)()
            pixels = obj.image(idx)
            assert native.p07_a4_make_ingress(
                ctypes.byref(info),cbuf(obj.mapping_bytes),1568,
                cbuf(pixels),784,idx,raw,2480) == 0
            accepted = encode_ingress(pixels,MAPPING,
                ddr_sha256=stream.DDR_SHA256,
                deployment_fingerprint=stream.COMPILED_FINGERPRINT)
            assert bytes(raw) == accepted == obj.ingress(idx)
            assert decode_ingress(bytes(raw)).pixels == pixels


def mutated_header(obj, pos, value):
    head=bytearray(obj.header)
    head[pos]=value
    struct.pack_into("<I",head,252,zlib.crc32(head[:252]))
    return bytes(head)


def test_reject_noncanonical_layout_with_valid_recomputed_crc(native):
    obj=stream.make_stream(bytes(784*2),MAPPING,trace_index=1)
    for pos in (0,8,12,16,20,24,28,32,36,40,44,52,56,64,68,72,76,
                80,112,144,251):
        changed=mutated_header(obj,pos,obj.header[pos]^1)
        with pytest.raises(ValueError):
            stream.parse_stream(changed,obj.mapping_bytes,obj.images)
        desc=Descriptor()
        assert native.p07_a4_validate_staging(
            cbuf(changed),len(changed),cbuf(obj.mapping_bytes),1568,
            cbuf(obj.images),len(obj.images),ctypes.byref(desc)) != 0
    # Trace index is intentionally selectable; only OUT-OF-RANGE values
    # should be rejected after a valid CRC recomputation.
    head=bytearray(obj.header)
    struct.pack_into("<I",head,48,obj.image_count)
    struct.pack_into("<I",head,252,zlib.crc32(head[:252]))
    with pytest.raises(ValueError,match="trace"):
        stream.parse_stream(bytes(head),obj.mapping_bytes,obj.images)
    desc=Descriptor()
    assert native.p07_a4_validate_staging(
        cbuf(bytes(head)),256,cbuf(obj.mapping_bytes),1568,
        cbuf(obj.images),len(obj.images),ctypes.byref(desc)) != 0
    assert not any(obj.header[144:252])


def test_reject_corrupt_pixels_mapping_and_duplicates(native):
    obj=stream.make_stream(bytes([12])*784*2,MAPPING)
    altered=bytearray(obj.images)
    altered[0] ^= 1
    with pytest.raises(ValueError,match="CRC"):
        stream.parse_stream(obj.header,obj.mapping_bytes,bytes(altered))
    desc=Descriptor()
    assert native.p07_a4_validate_staging(
        cbuf(obj.header),256,cbuf(obj.mapping_bytes),1568,
        cbuf(bytes(altered)),len(altered),ctypes.byref(desc)) != 0

    bad_map=bytearray(obj.mapping_bytes)
    bad_map[:2]=bad_map[2:4]
    head=bytearray(obj.header)
    struct.pack_into("<I",head,60,zlib.crc32(bad_map))
    struct.pack_into("<I",head,252,zlib.crc32(head[:252]))
    with pytest.raises(ValueError,match="784 distinct"):
        stream.parse_stream(bytes(head),bytes(bad_map),obj.images)
    assert native.p07_a4_validate_staging(
        cbuf(bytes(head)),256,cbuf(bytes(bad_map)),1568,
        cbuf(obj.images),len(obj.images),ctypes.byref(desc)) != 0
    with pytest.raises(ValueError):
        stream.make_stream(bytes(784*10001),MAPPING)
    with pytest.raises(ValueError):
        stream.make_stream(bytes(784),MAPPING,trace_index=1)
    with pytest.raises(ValueError):
        stream.make_stream(bytes(783),MAPPING)


def test_reconstruct_does_not_overwrite_on_failure(native):
    obj=stream.make_stream(bytes(784*2),MAPPING)
    rc, desc=validate_c(native,obj)
    assert rc == 0
    output=(ctypes.c_uint8*2480)(*([0xAA]*2480))
    wrong=bytearray(obj.mapping_bytes)
    wrong[3] ^= 1
    assert native.p07_a4_make_ingress(
        ctypes.byref(desc),cbuf(bytes(wrong)),1568,cbuf(obj.image(0)),784,
        0,output,2480) != 0
    assert bytes(output) == bytes([0xAA])*2480
    assert native.p07_a4_make_ingress(
        ctypes.byref(desc),cbuf(obj.mapping_bytes),1568,cbuf(obj.image(0)),784,
        2,output,2480) != 0
    assert bytes(output) == bytes([0xAA])*2480


def test_compact_result_spikes_counts_and_crc_exact(native):
    pixels=bytes(i%256 for i in range(784))
    ticks=tuple(tuple(int(cls==3 and t%2==0 or cls==9 and t%7==0)
                      for cls in range(10)) for t in range(26))
    result=Compact()
    result.image_index=4
    result.pixel_crc32=stream.crc(pixels)
    result.committed_routes=237
    result.dropped_final_packets=2
    result.external_event_total=930
    result.cycles_low32=0x12345
    for t in range(26):
        for cls in range(10):
            result.output_spikes[t][cls]=ticks[t][cls]
    out=(ctypes.c_uint8*96)()
    assert native.p07_a4_pack_result(ctypes.byref(result),out,96)==0
    expected=stream.encode_result(4,pixels,ticks,routes=237,discarded=2,
                                  input_events=930,cycles=0x12345)
    assert bytes(out)==expected
    assert native.p07_a4_validate_result(
        cbuf(expected),len(expected),cbuf(pixels),len(pixels),4)==0
    parsed=stream.parse_result(bytes(out),expected_index=4,pixels=pixels)
    assert parsed.predicted==3 and parsed.routes==237
    bad=bytearray(out)
    bad[32]^=1
    with pytest.raises(ValueError):
        stream.parse_result(bytes(bad),expected_index=4,pixels=pixels)
    assert native.p07_a4_validate_result(
        cbuf(bytes(bad)),96,cbuf(pixels),784,4)!=0


def test_result_mismatched_count_even_with_fixed_crc(native):
    pixels=bytes(784)
    spikes=tuple(tuple(0 for _ in range(10)) for _ in range(26))
    packed=stream.encode_result(0,pixels,spikes)
    assert stream.parse_result(packed,expected_index=0,pixels=pixels).all_silent
    tampered=bytearray(packed)
    struct.pack_into("<H",tampered,32,1)
    struct.pack_into("<I",tampered,92,zlib.crc32(tampered[:92]))
    with pytest.raises(ValueError,match="bit/count"):
        stream.parse_result(bytes(tampered),expected_index=0,pixels=pixels)
    assert native.p07_a4_validate_result(
        cbuf(bytes(tampered)),96,cbuf(pixels),784,0)!=0
    invalid=bytearray(packed)
    struct.pack_into("<I",invalid,84,1<<4)
    struct.pack_into("<I",invalid,92,zlib.crc32(invalid[:92]))
    with pytest.raises(ValueError,match="tail bits"):
        stream.parse_result(bytes(invalid),expected_index=0,pixels=pixels)
    assert native.p07_a4_validate_result(
        cbuf(bytes(invalid)),96,cbuf(pixels),784,0)!=0


def test_initial_and_completed_journal_native_header_parity(native):
    obj=stream.make_stream(bytes(784*2),MAPPING,trace_index=1)
    staged=stream.initial_journal(obj)
    assert len(staged)==stream.RESULT_CAPACITY
    header=(ctypes.c_uint8*256)()
    desc_crc=struct.unpack_from("<I",obj.header,252)[0]
    assert native.p07_a4_make_journal_header(
        header,256,2,1,desc_crc,0,0,stream.NO_FAILURE)==0
    assert bytes(header)==staged[:256]
    with pytest.raises(ValueError,match="not entirely completed"):
        stream.parse_journal(staged,obj)
    assert native.p07_a4_make_journal_header(
        header,256,2,1,desc_crc,stream.SUCCESS,2,stream.NO_FAILURE)==0
    good=[stream.encode_result(i,obj.image(i),
         tuple(tuple(0 for _ in range(10)) for _ in range(26)))
         for i in range(2)]
    result=bytes(header)+b"".join(good)
    journal=result+bytes(stream.RESULT_CAPACITY-len(result))
    decoded=stream.parse_journal(journal,obj)
    assert len(decoded)==2 and all(x.predicted==0 and x.all_silent for x in decoded)
    assert native.p07_a4_make_journal_header(
        header,256,2,1,desc_crc,stream.SUCCESS,1,stream.NO_FAILURE)!=0
    wrong=bytearray(journal)
    wrong[256+96+4]^=1
    with pytest.raises(ValueError):
        stream.parse_journal(bytes(wrong),obj)


def test_offline_staging_inspector_accepts_synthetic_and_rejects_mutation(tmp_path):
    obj=stream.make_stream(bytes([255])*784*16,MAPPING,trace_index=4)
    staged=tmp_path/"staged"
    staged.mkdir()
    raw={
        "descriptor":("p07_a4_descriptor_256.bin",obj.header),
        "mapping":("p07_a4_mapping_1568.bin",obj.mapping_bytes),
        "pixels":("p07_a4_pixels_raw.bin",obj.images),
        "zero_journal_1m":("p07_a4_journal_initial_1m.bin",
                           stream.initial_journal(obj)),
    }
    for filename,payload in raw.values():
        (staged/filename).write_bytes(payload)
    manifest={
        "schema":"p07-a4-2a-persistent-ddr-stage-v1",
        "scope":"SYNTHETIC_WHITE", "frame_count":16, "trace_index":4,
        "official_mnist_test":"SEALED", "physical_hardware":"NOT_RUN",
        "sha256":{key:stream.sha256(contents) for key,(_,contents) in raw.items()},
    }
    (staged/"p07_a4_2a_stage_manifest.json").write_text(json.dumps(manifest))
    script=ROOT/"scripts/p07_a4_2_check.py"
    command=[sys.executable,str(script),"--stage-dir",str(staged)]
    env={**os.environ,"PYTHONPATH":str(ROOT/"src")}
    result=subprocess.run(command,env=env,capture_output=True,text=True)
    assert result.returncode==0,result.stderr
    assert "P07_A4_2A_STAGING_CHECK_PASS=1" in result.stdout
    assert "P07_A4_OFFICIAL_TEST=SEALED" in result.stdout
    pixels=staged/"p07_a4_pixels_raw.bin"
    wrong=bytearray(pixels.read_bytes())
    wrong[75]^=1
    pixels.write_bytes(wrong)
    result=subprocess.run(command,env=env,capture_output=True,text=True)
    assert result.returncode!=0
    assert "SHA256 mismatch" in result.stderr
