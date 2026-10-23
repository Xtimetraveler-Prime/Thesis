"""B4m offline-only source route + actual ELF shape admission.

All artifacts here are synthetic fixtures: never equate a fake ELF header or
a self-consistent route manifest with independently validated real board data.
"""
from pathlib import Path
import hashlib
import json
import struct
import zlib
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


def test_generic_gnu_readelf_is_valid_for_aarch64_elf(tmp_path,monkeypatch):
    elf=fake_elf(tmp_path,monkeypatch)
    looked_up=[]
    monkeypatch.setattr(
        gate.shutil,"which",
        lambda name: looked_up.append(name) or
            ("/usr/bin/readelf" if name=="readelf" else None),
    )
    captured=[]
    monkeypatch.setattr(
        gate.subprocess,"run",
        lambda cmd,**kwargs: (
            captured.append(cmd) or
            SimpleNamespace(returncode=0,stdout=READ_ELF)
        ),
    )
    report=gate.require_elf(elf)
    assert looked_up==[
        "aarch64-none-elf-readelf",
        "aarch64-linux-gnu-readelf",
        "readelf",
    ]
    assert captured[0][0]=="/usr/bin/readelf"
    assert report["pt_load_memsz"]==0x200000
    assert report["expanded_low_DDR_boot_firmware_exclusivity_independently_proven"] is False


def test_no_supported_elf_inspector_is_still_no_go(tmp_path,monkeypatch):
    elf=fake_elf(tmp_path,monkeypatch)
    monkeypatch.setattr(gate.shutil,"which",lambda name: None)
    with pytest.raises(gate.AdmissionError,match="GNU readelf unavailable"):
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


def _make_original_shape_stage(tmp_path,monkeypatch):
    """Use SOURCE-SHAPED but synthetic 20384+1000 topology. Not B2.4."""
    original=importlib.import_module("p07_b4m_frozen_inputs")
    rows=[]
    for core in range(27):
        n=39 if core<24 else 32 if core<26 else 10
        bitmap=bytearray(512)
        for axon in range(784 if core<26 else 1000):
            bitmap[axon//8]|=1<<(axon%8)
        rows.append({
            "core_id":core, "compartments":n,
            "axon_count":784 if core<26 else 1000,
            "bitmap_hex":bitmap.hex()
        })
    ins=[(pixel,core,pixel) for pixel in range(784) for core in range(26)]
    outs=[]
    destination_axon=0
    for core in range(26):
        for neuron in range(rows[core]["compartments"]):
            outs.append((core,neuron,26,destination_axon))
            destination_axon+=1
    assert len(ins)==20384 and len(outs)==1000
    output_bin,input_bin=original.pack_tables(rows,ins,outs)
    dirname=tmp_path/"synthetic_B2_shape_ONLY_NOT_FROZEN"
    dirname.mkdir()
    files={
        original.OUT_FILENAME:output_bin,
        original.IN_FILENAME:input_bin,
    }
    fake_images={}
    frame_rows={}
    for ordinal,index in gate.FRAME_IDX.items():
        img=bytes(((i+ordinal*17)%256 for i in range(784)))
        img_sha=hashlib.sha256(img).hexdigest()
        fake_images[ordinal]=img_sha
        payload=input_bin[128:128+len(ins)*6]+img
        wire=bytearray(128)
        struct.pack_into("<8s",wire,0,b"P06B13I1")
        for off,val in (
            (8,1),(12,128),(16,len(payload)),(20,len(ins)),
            (24,27),(28,784),(32,25),(36,26),(40,6),(44,784),
            (48,zlib.crc32(payload)),
        ):
            struct.pack_into("<I",wire,off,val)
        wire[64:96]=bytes.fromhex(original.PINNED_SHA)
        wire[96:128]=bytes.fromhex(original.CAP_SHA)
        struct.pack_into("<I",wire,52,zlib.crc32(wire))
        name=f"p07_b4m_original_TRAIN_validation_{ordinal}_ingress.bin"
        files[name]=bytes(wire)+payload
        frame_rows[str(ordinal)]={
            "original_TRAIN_idx":index,
            "raw_image_sha256":img_sha,
            "ingress_sha256":hashlib.sha256(files[name]).hexdigest(),
            "bytes":len(files[name]),
        }
    monkeypatch.setattr(original,"FRAME_SHA",fake_images)
    for name,data in files.items():
        (dirname/name).write_bytes(data)
    manifest={
        "schema":gate.SCHEMA,
        "official_MNIST_TEST":"SEALED",
        "hardware_executed":False,
        "frozen_snapshot_modified":False,
        "original_compiled_sha256":original.PINNED_SHA,
        "original_capacity_sha256":original.CAP_SHA,
        "compartment_count":1010,
        "output_route_count":1000,
        "input_route_count":20384,
        "spans":original_spans(),
        "files":{name:hashlib.sha256(data).hexdigest()
                 for name,data in files.items()},
        "frames":frame_rows,
    }
    (dirname/"p07_b4m_frozen_inputs_manifest.json").write_text(
        json.dumps(manifest,sort_keys=True,indent=2)+"\n"
    )
    return dirname,manifest


def original_spans():
    return {
        "output_routes":["0x43fc4000","0x43fd8000"],
        "input_routes":["0x41000000","0x410e0000"],
        "per_image_ingress":["0x41100000","0x411e0000"],
    }


def test_actual_B24_source_shaped_route_counts_pass_offline_without_test_access(
    tmp_path,monkeypatch
):
    stage,_=_make_original_shape_stage(tmp_path,monkeypatch)
    record=gate.require_routes(stage)
    assert record["input_routes"]==20384
    assert record["output_routes"]==1000
    assert record["registered_axons"]==21384


@pytest.mark.parametrize("field,value",[
    ("output_route_count",10000),
    ("output_route_count",999),
    ("input_route_count",20383),
    ("input_route_count",20385),
    ("compartment_count",1000),
])
def test_output_count_still_strictly_matches_real_frozen_topology(
    tmp_path,monkeypatch,field,value
):
    stage,manifest=_make_original_shape_stage(tmp_path,monkeypatch)
    manifest[field]=value
    (stage/"p07_b4m_frozen_inputs_manifest.json").write_text(
        json.dumps(manifest,sort_keys=True,indent=2)+"\n"
    )
    with pytest.raises(gate.AdmissionError,match="topology/count/identity"):
        gate.require_routes(stage)
