"""P07-B.4d offline real-artifact contract and untrusted log guard tests.

All fake ELF/XSA/XSDB/UART contents below are synthetic negative fixtures.
No test connects to hardware, imports Vitis, programs PL or opens B2 TEST.
"""
from __future__ import annotations

from argparse import Namespace
import hashlib
from pathlib import Path
import re
import shutil
import sys

import pytest

V3=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(V3/"scripts"))
sys.path.insert(0,str(V3/"software/p07"))
import p07_b4d_readonly_evidence as gate
from build_p07_b4c import SOURCES, HEADERS

METRICS="\n".join(gate.METRICS)+"\n"
UART=(
    "Zynq MP Boot\n"
    "P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1\n"
    "P07_B4C_READONLY_ADMISSION_PROBE_PASS=1\n"
)
XSDB=(
    "P07_B4D_PHYSICAL_TARGET=PSU\n"
    "P07_B4D_FPD_RAW=0x00000A00\n"
    "P07_B4D_P03_ID=0x4C543302\n"
    "P07_B4D_P03_VERSION=0x00010000\n"
    "P07_B4D_P03_CAPABILITIES=0x0001031F\n"
    "P07_B4D_P03_GLOBAL_STATUS=0x00000000\n"
    "P07_B4D_P03_PAGE_PENDING=0x00000000\n"
    "P07_B4D_READONLY_PS_PL_SNAPSHOT_PASS=1\n"
    "P07_B4D_INFERENCE_AUTHORIZED=0\n"
)


def fixture(tmp_path, monkeypatch):
    build=tmp_path/"candidate"
    workspace=build/"vitis_workspace"
    stage=build/"source"
    workspace.mkdir(parents=True)
    stage.mkdir()
    for name in (*SOURCES,*HEADERS):
        original=V3/("software/p03" if name.startswith("p03_")
                     else "software/p07")/(
                         "" if name.endswith(".c") else "include")/name
        assert original.is_file()
        shutil.copyfile(original,stage/name)
    for name,data in (
        ("p07_b4c_readonly_probe.elf",b"FAKE_NOT_ELF"),
        ("p07_b4c_readonly_probe.map",b".text\n.bss\n"),
        ("p07_b4c_readonly_platform/export/p07_b4c_readonly_platform/"
         "p07_b4c_readonly_platform.xpfm",b"FAKE NOT XPFM"),
    ):
        dest=workspace/name;dest.parent.mkdir(exist_ok=True,parents=True)
        dest.write_bytes(data)
    artifact={}
    for name,body in (
        ("xsa",b"fake xsa"),("bit",b"fake bit"),
        ("ltx",b"fake ltx"),("route_metrics",METRICS.encode()),
    ):
        path=tmp_path/(name+".bin")
        path.write_bytes(body);artifact[name]=path
    monkeypatch.setattr(gate,"verify_elf",lambda *args,**kw: {
        "read_only_firmware_identity_present":True,
        "inference_authorized":False,
        "emulated_BINUTILS_ONLY_NOT_AN_ELF":True,
    })
    kw=dict(
        build_dir=build,xsa=artifact["xsa"],bit=artifact["bit"],
        ltx=artifact["ltx"],route_metrics=artifact["route_metrics"],
        xsa_sha256=gate.digest(artifact["xsa"]),
        bit_sha256=gate.digest(artifact["bit"]),
        stack="0x300000:0x310000",heap="0x320000:0x330000",
        readelf="aarch64-none-elf-readelf",nm="aarch64-none-elf-nm",
        out=tmp_path/"offline_evidence",
    )
    return Namespace(**kw)


def test_readonly_tcl_has_no_write_reset_download_or_cpu_stop():
    tcl=(V3/"vivado/p07_b4d_readonly_shell.tcl").read_text()
    assert "mrd -force -size w" in tcl
    assert "0xFD615000" in tcl and "0xA4000054" in tcl
    assert "P07_B4D_READONLY_PS_PL_SNAPSHOT_PASS=1" in tcl
    assert "P07_B4D_INFERENCE_AUTHORIZED=0" in tcl
    for cmd in ("dow","mwr","stop","rst","con","fpga","targets -stop",
                "disconnect -reset"):
        assert not re.search(r"(?m)^\s*"+re.escape(cmd)+r"\b",tcl),cmd


def test_host_fake_prepare_records_hashes_and_cannot_claim_board(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    result=gate.prepare(args)
    assert result["actual_board_execution"]=="NOT_RUN"
    assert result["physical_acceptance"] is False
    assert result["inference_authorized"] is False
    assert len(result["source_sha256"])==len(SOURCES)+len(HEADERS)
    assert (args.out/"offline_preflight.json").is_file()
    assert (args.out/"offline_preflight.sha256").read_text().strip()==gate.digest(
        args.out/"offline_preflight.json")
    assert "NO board" in (args.out/"README_NO_BOARD_RUN.txt").read_text()
    with pytest.raises(ValueError,match="already exists"):
        gate.prepare(args)


@pytest.mark.parametrize("damage,expected",[
    ("xsa","XSA SHA256 mismatch"),
    ("bit","BIT SHA256 mismatch"),
    ("route_metrics","metrics missing"),
    ("staged","staged source drift"),
    ("elf","empty or symlinked input|missing, empty"),
])
def test_incorrect_or_modified_build_inputs_refuse_manifest(
    tmp_path,monkeypatch,damage,expected
):
    args=fixture(tmp_path,monkeypatch)
    if damage=="staged":
        (args.build_dir/"source"/SOURCES[0]).write_text("untrusted mutation")
    elif damage=="elf":
        (args.build_dir/"vitis_workspace/p07_b4c_readonly_probe.elf").unlink()
    elif damage=="route_metrics":
        args.route_metrics.write_text("p03_hpm0_data_width_bits=64\n")
    else:
        getattr(args,damage).write_bytes(b"tampered")
    with pytest.raises(ValueError,match=expected):
        gate.prepare(args)
    assert not args.out.exists()


def test_expected_sha_must_be_full_pin(tmp_path,monkeypatch):
    args=fixture(tmp_path,monkeypatch)
    args.xsa_sha256="0x1234"
    with pytest.raises(ValueError,match="64 hex"):
        gate.prepare(args)


def test_operator_log_parser_rejects_ambiguities_and_never_authorizes_inference():
    proof=gate.parse_observations(UART,XSDB)
    assert proof["fpd128_observed"] is True
    assert proof["logs_authenticity"]=="NOT_INDEPENDENTLY_ESTABLISHED"
    assert proof["board_physical_acceptance"] is False
    assert proof["inference_authorized"] is False
    defects=[
        (UART,XSDB.replace("0x00000A00","0x00000900"),"FPD128"),
        (UART,XSDB.replace("0x4C543302","0x00000000"),"P03_ID"),
        (UART,XSDB.replace("0x00000000","0x00000001",1),"P03_GLOBAL_STATUS"),
        (UART+"P07_B4C_READONLY_ADMISSION_PROBE_PASS=1\n",XSDB,"duplicate"),
        (UART.replace("P07_B4C_READONLY_ADMISSION_PROBE_PASS=1",
                      "P07_B4C_READONLY_ADMISSION_PROBE_FAIL=1"),
         XSDB,"explicit fail"),
        (UART,XSDB.replace("P07_B4D_PHYSICAL_TARGET=PSU",
                           "P07_B4D_PHYSICAL_TARGET=ARMHACK"),"target"),
        (UART,XSDB.replace("P07_B4D_P03_PAGE_PENDING=0x00000000",
                           "P07_B4D_P03_PAGE_PENDING=0x00000004"),"PAGE_PENDING"),
        (UART,XSDB.replace("P07_B4D_READONLY_PS_PL_SNAPSHOT_PASS=1",""),
         "missing/duplicate"),
        (UART,XSDB.replace("P07_B4D_INFERENCE_AUTHORIZED=0",
                           "P07_B4D_INFERENCE_AUTHORIZED=1"),"unexpected"),
    ]
    for u,x,why in defects:
        with pytest.raises(ValueError,match=why):
            gate.parse_observations(u,x)


def test_review_requires_unchanged_manifest_sources_and_logs(
    tmp_path,monkeypatch
):
    args=fixture(tmp_path,monkeypatch)
    gate.prepare(args)
    uart=tmp_path/"real-operator-uart.log"
    xsdb=tmp_path/"real-operator-xsdb.log"
    uart.write_text(UART);xsdb.write_text(XSDB)
    kwargs=Namespace(
        build_dir=args.build_dir,evidence_dir=args.out,
        uart=uart,xsdb=xsdb,
    )
    proof=gate.verify_logs(kwargs)
    assert proof["board_physical_acceptance"] is False
    assert proof["uart_sha256"]==gate.digest(uart)
    source=args.build_dir/"source"/SOURCES[0]
    source.write_text(source.read_text()+"\n/* mutated */\n")
    with pytest.raises(ValueError,match="source drift"):
        gate.verify_logs(kwargs)
    shutil.copyfile(
        V3/"software/p07"/SOURCES[0],source)
    xsa=args.xsa
    xsa.write_bytes(b"tamper after manifest")
    with pytest.raises(ValueError,match="artifact drift"):
        gate.verify_logs(kwargs)
    args.xsa.write_bytes(b"fake xsa")
    pre=args.out/"offline_preflight.json"
    pre.write_text(pre.read_text()+" ")
    with pytest.raises(ValueError,match="checksum drift"):
        gate.verify_logs(kwargs)


def test_real_verifier_is_not_fake_for_invalid_elf(tmp_path):
    from p07_b4c_verify_elf import verify
    elf=tmp_path/"invalid.elf"
    linker=tmp_path/"candidate.map"
    elf.write_bytes(b"FAKE_NOT_ELF")
    linker.write_text(".text\n.bss\n")
    with pytest.raises(ValueError,match="genuine ELF"):
        verify(elf,linker,"0x300000:0x310000","0x320000:0x330000")
