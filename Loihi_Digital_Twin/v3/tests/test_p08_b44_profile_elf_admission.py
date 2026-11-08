"""P08-B4.4.2 distinct A53 ELF64 image-only profiler no-JTAG negative tests."""
from __future__ import annotations
import hashlib
from pathlib import Path
import struct
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p08_b44_profile_elf_admission as gate

def sha(raw:bytes)->str:return hashlib.sha256(raw).hexdigest()

def fake_elf(marker:bytes,done:bytes=b"",physical_base:int=0x100000)->bytes:
    # SYNTHETIC ELF64 AArch64 for native admission fixture ONLY,
    # NEVER a real Vitis ELF and NEVER valid physical proof.
    ident=b"\x7fELF"+bytes([2,1,1])+bytes(9)
    header=struct.pack(gate.orig.ELF_HDR,ident,2,183,1,
        physical_base+0x100,64,0,0,64,56,1,64,0,0)
    phdr=struct.pack(gate.orig.PHDR,1,5,0x1000,
        physical_base,physical_base,0x1000,0x1000,0x1000)
    file=bytearray(0x2000)
    file[:64]=header
    file[64:64+56]=phdr
    file[0x1000:0x1000+len(marker)]=marker
    file[0x1100:0x1100+len(done)]=done
    return bytes(file)

@pytest.fixture
def pristine(tmp_path,monkeypatch):
    original=tmp_path/"original_signed_1024.elf"
    profile=tmp_path/"new_separate_profiler.elf"
    linker=tmp_path/"new_profiler.map"
    xsa=tmp_path/"original_p03.xsa"
    pins=tmp_path/"original27_SHA.h"
    original.write_bytes(fake_elf(gate.orig.IDENTITY))
    profile.write_bytes(fake_elf(gate.PROFILE_ID,gate.PROFILE_DONE))
    linker.write_bytes(b"Linker script and memory map\n.text .bss main p08_b44_profile_reset_image")
    xsa.write_bytes(b"ORIGINAL ROUTED P03 XSA SYNTHETIC ONLY")
    pins.write_bytes(b"ORIGINAL 27 CONTEXT PIN SYNTHETIC ONLY")
    monkeypatch.setattr(gate,"ORIGINAL_ELF_SHA",sha(original.read_bytes()))
    monkeypatch.setattr(gate,"ORIGINAL_XSA_SHA",sha(xsa.read_bytes()))
    monkeypatch.setattr(gate,"ORIGINAL_PINS_SHA",sha(pins.read_bytes()))
    return original,profile,linker,xsa,pins

def test_distinct_original_pinned_elf_profile_static_only(pristine,tmp_path):
    original,profile,linker,xsa,pins=pristine
    out=tmp_path/"external_profile_preflight.json"
    result=gate.audit(profile,linker,original,xsa,pins,out)
    assert result["schema"]==gate.SCHEMA
    assert result["distinct_embedded_profile_identity"]==gate.PROFILE_ID.decode()
    assert result["new_profile_sidecar_byte_count"]==262144
    assert result["original_immutable_B2_3_full1024_ELF_sha256"]==gate.ORIGINAL_ELF_SHA
    assert result["new_profile_ELF_sha256"]!=result[
        "original_immutable_B2_3_full1024_ELF_sha256"]
    assert result["new_image_actual_KV260_neural_FNV_parity_verified"] is False
    assert result["new_profile_sidecar_physical_readback_verified"] is False
    assert result["PS_FSBL_firmware_RPU_PL_DMA_DDR_owner_exclusivity_proven"] is False
    assert result["destructive_JTAG_launch_authorized"] is False
    with pytest.raises(gate.ProfileElfNoGo):
        gate.audit(profile,linker,original,xsa,pins,out)

@pytest.mark.parametrize("change",[
    "different_original","no_identity","no_terminal","wrong_linker_map",
    "wrong_xsa","wrong_pin_header","high_elf_segment","both_identities",
    "profile_is_original","bad_aarch64","bad_xsa_symlink",
])
def test_profile_elf_source_gate_negative(pristine,tmp_path,change):
    original,profile,linker,xsa,pins=pristine
    if change=="different_original":
        original.write_bytes(original.read_bytes()+b"changed")
    elif change=="no_identity":
        profile.write_bytes(fake_elf(b"NOT OUR PROFILER",gate.PROFILE_DONE))
    elif change=="no_terminal":
        profile.write_bytes(fake_elf(gate.PROFILE_ID))
    elif change=="wrong_linker_map":
        linker.write_text("main p08_b44_profile_reset_image")
    elif change=="wrong_xsa":
        xsa.write_bytes(b"OTHER XSA")
    elif change=="wrong_pin_header":
        pins.write_bytes(b"NEW UNAUTHORIZED PINS")
    elif change=="high_elf_segment":
        profile.write_bytes(fake_elf(gate.PROFILE_ID,gate.PROFILE_DONE,0x40001000))
    elif change=="both_identities":
        profile.write_bytes(fake_elf(gate.PROFILE_ID+gate.orig.IDENTITY,gate.PROFILE_DONE))
    elif change=="profile_is_original":
        profile.write_bytes(original.read_bytes())
    elif change=="bad_aarch64":
        data=bytearray(profile.read_bytes())
        data[18:20]=struct.pack("<H",62)
        profile.write_bytes(data)
    elif change=="bad_xsa_symlink":
        xsa.unlink()
        xsa.symlink_to(pins)
    out=tmp_path/"must_not_produce.json"
    with pytest.raises((gate.ProfileElfNoGo,gate.orig.ElfNoGo)):
        gate.audit(profile,linker,original,xsa,pins,out)
    assert not out.exists()

def test_original_production_static_pins_and_new_id_are_not_synthetic():
    # Actual source pins remain distinct from pytest monkeypatch fixture.
    import ast
    src=(ROOT/"scripts/p08_b44_profile_elf_admission.py").read_text()
    tree=ast.parse(src)
    constants={}
    for node in tree.body:
        if isinstance(node,ast.Assign) and len(node.targets)==1 and isinstance(node.targets[0],ast.Name):
            if isinstance(node.value,ast.Constant):
                constants[node.targets[0].id]=node.value.value
    assert constants["ORIGINAL_ELF_SHA"]==(
        "0c2de1656eff897e71d6d4fffe5575db9969baf7d3da7b82a2ec765447d36ee1")
    assert constants["PROFILE_ID"]==b"P08_B44_ORIGINAL_27CORE_RESET_PROFILE_1024_A53_V1"
    assert "import subprocess" not in src
    assert "import socket" not in src
    assert 'destructive_JTAG_launch_authorized":False' in src
