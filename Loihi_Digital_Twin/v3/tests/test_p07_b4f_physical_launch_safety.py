"""P07-B.4f offline real firmware launch-safety gate (synthetic fixtures only).

Every mocked ELF result here is NOT a genuine linked ELF or hardware
measurement. No test may invoke JTAG/XSDB, Vitis, Vivado or touch board.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import subprocess
import sys
from unittest import mock
import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4f_physical_launch_safety as gate

HEADER=(
    "ELF Header:\n"
    "  Class: ELF64\n"
    "  Data: 2's complement, little endian\n"
    "  Type: EXEC (Executable file)\n"
    "  Machine: AArch64\n"
    "  Entry point address: 0x0\n"
)
LOAD=(
    "  LOAD 0x010000 0x0000000000000000 0x0000000000000000 "
    "0x00e054 0x023a40 RWE 0x10000\n"
)
SYNTHETIC_ELF_GATE={
    "heap_stack_crosschecked_with_actual_allocated_ELF_sections":True,
    "ELF_heap_section":"0x1ea40:0x20a40",
    "ELF_stack_section":"0x20a40:0x23a40",
    "inference_authorized":False,
}


def synthetic(tmp:Path,monkeypatch,header=HEADER,load=LOAD,gate_override=None):
    folder=tmp/"vitis_local_build"/"vitis_workspace"
    folder.mkdir(parents=True)
    elf=folder/"p07_b4c_readonly_probe.elf"
    linker=folder/"p07_b4c_readonly_probe.map"
    elf.write_bytes(b"SYNTHETIC_NOT_ACTUAL_ELF")
    linker.write_bytes(b"SYNTHETIC_NOT_ACTUAL_MAP")
    xsa=tmp/"xsa"
    bit=tmp/"bit"
    ltx=tmp/"ltx"
    metrics=tmp/"metrics"
    for f in (xsa,bit,ltx,metrics):
        f.write_bytes(b"SYNTHETIC_ARCHIVE_ONLY")
    def fake_admission(*args,**kwargs):
        assert args[7:9]==("auto","auto")
        return {
            "sha256":{
                "elf":gate.digest(elf),"linker_map":gate.digest(linker),
                "xsa":gate.digest(xsa),"bit":gate.digest(bit),
                "ltx":gate.digest(ltx)},
            "elf_admission":SYNTHETIC_ELF_GATE | (gate_override or {}),
        }
    monkeypatch.setattr(gate,"admission_inputs",fake_admission)
    def fake_binutils(tool,args,path):
        if args==["-W","-h"]:return header
        if args==["-W","-l"]:return load
        raise AssertionError(args)
    monkeypatch.setattr(gate,"binutils",fake_binutils)
    return dict(
        build_dir=tmp/"vitis_local_build",
        xsa=xsa,bit=bit,ltx=ltx,route_metrics=metrics,
        xsa_sha256=gate.digest(xsa),bit_sha256=gate.digest(bit),
        elf_sha256=gate.digest(elf),map_sha256=gate.digest(linker),
        bit_provenance="observed",readelf="aarch64-none-elf-readelf",
        nm="aarch64-none-elf-nm"
    )


def test_real_shape_low_ddr_elf_must_never_grant_board_go(tmp_path,monkeypatch):
    kw=synthetic(tmp_path,monkeypatch)
    proof=gate.check(**kw)
    assert proof["user_local_real_elf_and_map_hash_matched"] is True
    assert proof["actual_ELF_entry"]=="0x0"
    assert proof["low_DDR_first_1MiB_overlap"] is True
    assert proof["low_DDR_start_zero"] is True
    assert proof["board_ELF_download_authorized"] is False
    assert proof["physical_inference_authorized"] is False
    assert proof["bit_independently_accepted"] is False
    assert proof["Linux_SMP_stopped_or_absent"]=="NOT_ESTABLISHED"
    assert proof["B2_official_MNIST_TEST"]=="SEALED"


def test_accepted_bit_pin_does_not_change_launch_go(tmp_path,monkeypatch):
    kw=synthetic(tmp_path,monkeypatch)
    kw["bit_provenance"]="independently_accepted"
    proof=gate.check(**kw)
    assert proof["bit_independently_accepted"] is True
    assert proof["board_ELF_download_authorized"] is False
    assert proof["physical_PL_bitstream_identity"]=="NOT_ESTABLISHED"


@pytest.mark.parametrize("issue,pattern",[
    ("elf","ELF SHA256 mismatch"),
    ("map","MAP SHA256 mismatch"),
    ("bit","BIT"),
    ("invalid_pin","64 hex"),
    ("no_elf","ELF missing"),
])
def test_corrupt_real_evidence_fails_before_tool_calls(tmp_path,monkeypatch,issue,pattern):
    kw=synthetic(tmp_path,monkeypatch)
    folder=kw["build_dir"]/"vitis_workspace"
    if issue=="elf":
        (folder/"p07_b4c_readonly_probe.elf").write_bytes(b"changed")
    elif issue=="map":
        (folder/"p07_b4c_readonly_probe.map").write_bytes(b"changed")
    elif issue=="bit":
        kw["bit_sha256"]="f"*64
        # Emulates admitted hash check, which must be performed by B4d gate.
        monkeypatch.setattr(gate,"admission_inputs",
                            lambda *a,**k: (_ for _ in ()).throw(
                                ValueError("BIT SHA256 mismatch")))
    elif issue=="invalid_pin":
        kw["map_sha256"]="not-a-64hex"
    else:
        (folder/"p07_b4c_readonly_probe.elf").unlink()
    with pytest.raises(ValueError,match=pattern):
        gate.check(**kw)


def test_elf_entry_must_be_inside_actual_load(tmp_path,monkeypatch):
    kw=synthetic(tmp_path,monkeypatch,
                 header=HEADER.replace("address: 0x0","address: 0x900000"))
    with pytest.raises(ValueError,match="outside all LOAD"):
        gate.check(**kw)


def test_p02_load_overlap_is_forbidden(tmp_path,monkeypatch):
    overlap=(
        " LOAD 0x010000 0x0000000040000000 0x0000000040000000 "
        "0x010000 0x023a40 RWE 0x10000\n"
    )
    kw=synthetic(tmp_path,monkeypatch,
                 header=HEADER.replace("address: 0x0","address: 0x40000000"),
                 load=overlap)
    with pytest.raises(ValueError,match="reserved DDR"):
        gate.check(**kw)


def test_missing_stack_or_false_inference_authorization_is_rejected(tmp_path,monkeypatch):
    kw=synthetic(tmp_path,monkeypatch,gate_override={
        "heap_stack_crosschecked_with_actual_allocated_ELF_sections":False})
    with pytest.raises(ValueError,match="heap/stack"):
        gate.check(**kw)
    kw=synthetic(tmp_path/"other",monkeypatch,gate_override={
        "inference_authorized":True})
    with pytest.raises(ValueError,match="unsafe ELF authorization"):
        gate.check(**kw)


def test_offline_module_contains_no_physical_actions():
    content=(ROOT/"scripts/p07_b4f_physical_launch_safety.py").read_text()
    assert "subprocess.run([tool,*args,str(path)]" in content
    assert "xsdb " not in content.lower()
    assert "vitis -s " not in content.lower()
    assert "mwr " not in content.lower()
    assert "dow " not in content.lower()
