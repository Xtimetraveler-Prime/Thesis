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


def test_c_expected_route_sha_exactly_equals_pinned_original_b24():
    """Regression against silently hand-transcribing a signed 896KiB SHA wrong."""
    import re
    source=(ROOT/"software/p08/p08_b2_ingress.c").read_text(encoding="utf-8")
    match=re.search(
        r"static const uint8_t accepted_route_sha\[32\]\s*=\s*\{([^}]+)\};",
        source,re.DOTALL)
    assert match is not None
    expected=bytes(int(s,16) for s in
                   re.findall(r"0x([0-9a-fA-F]{2})",match.group(1)))
    assert len(expected)==32
    assert expected.hex()==stage.ROUTE_SHA256
    assert expected.hex()=="380268c5e8faa2664a31f993683c6759316239932d96b8e681ddb458c81574e8"


def test_strict_native_c11_full_1024_positive_encoder_with_synthetic_routes(tmp_path):
    """True positive path without private B2.4 files: temporary TEST-ONLY pin.

    A distinct, synthetic 896KiB image and matching synthetic SHA replace
    the one C source literal in a TEMP COPY ONLY. The repository C SHA pin
    is independently checked above and is NEVER modified or weakened.
    Byte-for-byte compare all 1,024 synthetic C encoded frames with Python
    B1.3 SHA. This is NOT acceptance of the real frozen B2.4 data.
    """
    import re
    cc=shutil.which("cc")
    assert cc, "strict native C11 compiler required"
    routes=bytes((i*17+83)&255 for i in range(stage.ROUTE_BYTES))
    orig=bytearray(0xE0000)
    struct.pack_into("<8s6I",orig,0,b"B4MING01",1,len(orig),27,
                     stage.ROUTES,6,128)
    orig[32:64]=bytes.fromhex(stage.b1.B24_COMPILED_SHA)
    orig[64:96]=bytes.fromhex(
        "82e9e6c11264c6092dbe94f17496332fae303ac9ef7dfaa01d0ec441869a9498")
    orig[128:128+stage.ROUTE_BYTES]=routes
    orig[96:128]=hashlib.sha256(orig[128:]).digest()
    source_sha=hashlib.sha256(orig).digest()
    source=(ROOT/"software/p08/p08_b2_ingress.c").read_text(encoding="utf-8")
    new_literal="static const uint8_t accepted_route_sha[32]={\n" + (
        "    "+",".join(f"0x{v:02x}" for v in source_sha) + "\n};")
    patched,changes=re.subn(
        r"static const uint8_t accepted_route_sha\[32\]\s*=\s*\{[^}]+\};",
        lambda _: new_literal,source,count=1,flags=re.DOTALL)
    assert changes==1
    assert stage.ROUTE_SHA256!=source_sha.hex(), "synthetic test pin not original"
    src=tmp_path/"p08_b2_test_only.c"
    src.write_text(patched,encoding="utf-8")
    exe=tmp_path/"native_c_positive"
    subprocess.run([
        cc,"-std=c11","-O2","-Wall","-Wextra","-Werror","-pedantic",
        "-I",str(ROOT/"software/p08"),
        "-I",str(ROOT/"software/p07/include"),
        str(src),
        str(ROOT/"software/p07/p07_a2_sha256.c"),
        str(ROOT/"tests/native/p08_b2_ingress_native.c"),
        "-o",str(exe),
    ],check=True,capture_output=True,text=True,timeout=60)
    source_file=tmp_path/"synthetic_not_B24.bin"
    source_file.write_bytes(orig)
    raw_file=tmp_path/"synthetic_1024_pixels.bin"
    all_raw=b"".join(bytes(((i+j*3)&255) for i in range(784))
                     for j in range(1024))
    raw_file.write_bytes(all_raw)
    expected_file=tmp_path/"synthetic_1024_expected_SHA.txt"
    expected_file.write_text(
        "".join(
            hashlib.sha256(stage.wire_from_pinned_route_bytes(
                routes,all_raw[i*784:(i+1)*784])).hexdigest()+"\n"
            for i in range(1024)
        ),encoding="ascii")
    test=subprocess.run([
        str(exe),"--verify",str(source_file),str(raw_file),str(expected_file)
    ],check=True,capture_output=True,text=True,timeout=120)
    assert "P08_B2_NATIVE_SOURCE_AUTHENTICATED=1" in test.stdout
    assert "P08_B2_NATIVE_ENCODED_FRAMES_EXACT=1024" in test.stdout
    assert "P08_B2_HARDWARE_EXECUTED=0" in test.stdout
    assert "P08_B2_NATIVE_BYTES_PER_FRAME=123216" in test.stdout

    # A changed original route image MUST fail, even when its B4MING01
    # header is structurally valid (the whole-file SHA is the authority).
    corrupted=bytearray(orig)
    corrupted[-1]^=0x01
    source_file.write_bytes(corrupted)
    rejected=subprocess.run([
        str(exe),"--verify",str(source_file),str(raw_file),str(expected_file)
    ],capture_output=True,text=True,timeout=120)
    assert rejected.returncode==4
    assert "P08_B2_NATIVE_ORIGINAL_896K_ROUTE_SHA_NO_GO" in rejected.stderr
