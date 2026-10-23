"""B4m offline-only source route + actual ELF shape admission.

All artifacts here are synthetic fixtures: never equate a fake ELF header or
a self-consistent route manifest with independently validated real board data.
"""
from pathlib import Path
import importlib
import sys
from types import SimpleNamespace

import pytest

SCRIPT=Path(__file__).resolve().parents[1]/"scripts"
sys.path.insert(0,str(SCRIPT))
gate=importlib.import_module("p07_b4m_offline_admission")

READ_ELF="""ELF Header:
  Class: ELF64
  Data: 2's complement, little endian
  Type: EXEC (Executable file)
  Machine: AArch64
  Entry point address: 0x0
Program Headers:
  Type           Offset   VirtAddr           PhysAddr           FileSiz  MemSiz   Flg Align
  LOAD           0x00010000 0x0000000000000000 0x0000000000000000 0x00020000 0x00200000 RWE 0x1000
Section Headers:
  [ 1] .text PROGBITS 0000000000001000 00010000 00002000 00 AX 0 0 4
  [ 2] .bss NOBITS 0000000000030000 00030000 00070000 00 WA 0 0 8
  [ 3] .heap NOBITS 00000000000A0000 000A0000 00040000 00 WA 0 0 16
  [ 4] .stack NOBITS 00000000000E0000 000E0000 00040000 00 WA 0 0 16
"""


def fake_elf(tmp_path,monkeypatch,readelf=READ_ELF):
    elf=tmp_path/gate.ELF_NAME
    elf.write_bytes(b"FAKE_NOBUILD "+gate.ELF_ID)
    elf.with_suffix(".map").write_text(
        "Linker script and memory map\n.text\n.bss\n.heap\n.stack\nmain\n"
    )
    monkeypatch.setattr(gate.shutil,"which",lambda _: "/fake/readelf")
    monkeypatch.setattr(gate.subprocess,"run",lambda *a,**k:
        SimpleNamespace(returncode=0,stdout=readelf))
    return elf


def test_valid_synthetic_elf_memory_shape_is_only_an_offline_candidate(tmp_path,monkeypatch):
    elf=fake_elf(tmp_path,monkeypatch)
    r=gate.require_elf(elf)
    assert r["pt_load_start"]=="0x00000000"
    assert r["pt_load_end_exclusive"]=="0x00200000"
    assert r["pt_load_memsz"]==0x200000
    assert r["expanded_low_DDR_boot_firmware_exclusivity_independently_proven"] is False


@pytest.mark.parametrize("edit",[
    lambda s:s.replace("0x0000000000000000 0x00020000",
                       "0x0000000040000000 0x00020000"),
    lambda s:s.replace("0x00200000 RWE","0x02000000 RWE"),
    lambda s:s.replace("0x00200000 RWE","0x00100000 RWE"),
    lambda s:s.replace("Entry point address: 0x0","Entry point address: 0x1000"),
    lambda s:s.replace(".stack NOBITS 00000000000E0000",".stack NOBITS 0000000000200000"),
    lambda s:s.replace(".stack NOBITS",".nosuch NOBITS"),
])
def test_unowned_or_corrupt_elf_refused(tmp_path,monkeypatch,edit):
    elf=fake_elf(tmp_path,monkeypatch,edit(READ_ELF))
    with pytest.raises(gate.AdmissionError):
        gate.require_elf(elf)


def test_wrong_name_unbuilt_elf_refused_before_tool_run(tmp_path):
    other=tmp_path/"p07_b4l_b3_first_epoch.elf"
    other.write_bytes(gate.ELF_ID)
    with pytest.raises(gate.AdmissionError):
        gate.require_elf(other)


def test_no_fake_stage_is_accepted(tmp_path):
    stage=tmp_path/"stage"
    stage.mkdir()
    with pytest.raises(gate.AdmissionError):
        gate.require_routes(stage)


def test_preflight_requires_actual_original_signed_B24_reconstruction():
    source=(SCRIPT/"p07_b4m_offline_admission.py").read_text()
    assert "b4l1.admit_freeze(args.frozen_dir)" in source
    assert "bindings.original_core_bindings(source_frozen)" in source
    assert "frozen.pack_tables(ordered,ins,outs)" in source
    assert "hashlib.sha256(data[-784:]).hexdigest()" in source
    assert "destructive_launch_authorized" in source
    assert "LOW_DDR_MAX_END" in source
