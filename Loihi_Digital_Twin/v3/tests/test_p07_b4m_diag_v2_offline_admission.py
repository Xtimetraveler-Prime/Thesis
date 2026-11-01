"""Build-only B4m V2 genuine ELF/source preflight. All fixtures are fake.

Mocks only external native Vitis artifact and freeze; source-copy comparison
uses real committed C/header bytes without accessing the KV260 or MNIST TEST.
"""
from __future__ import annotations

from pathlib import Path
import json
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b4m_diag_v2_offline_admission as gate

def fake_source_tree(tmp_path):
    contract=gate.import_build_contract()
    src=tmp_path/"source"
    src.mkdir()
    for name in (*contract.SOURCES,*contract.HEADERS):
        if name.endswith(".c"):
            p=ROOT/("software/p03" if name.startswith("p03_hw_") else "software/p07")/name
        else:
            p=ROOT/("software/p03/include" if name.startswith("p03_") else (
                "software/p05/include" if name=="p05_deployment.h" else
                "software/p07/include"))/name
        payload=p.read_bytes()
        if name=="p07_a2_sha256.c":
            payload=payload.replace(
                b'#include "include/p07_a2_sha256.h"',
                b'#include "p07_a2_sha256.h"'
            )
        if name=="p07_b2_packet.h":
            payload=payload.replace(
                b"#define P07_B2_MAX_ROUTE_BINDINGS 8192u",
                b"#define P07_B2_MAX_ROUTE_BINDINGS 10000u"
            )
        (src/name).write_bytes(payload)
    return src

def test_exact_v2_staged_source_matches_real_repository(tmp_path):
    src=fake_source_tree(tmp_path)
    digest=gate.verify_staged_source(src)
    assert "p07_b4m_full_board_diag.c" in digest
    assert "p03_hw_adapter.c" in digest
    assert "p07_b2_packet.h" in digest
    assert len(digest)==len(gate.import_build_contract().SOURCES)+len(
        gate.import_build_contract().HEADERS)
    assert len(set(digest.values()))>1

@pytest.mark.parametrize("filename",[
    "p07_b4m_full_board_diag.c",
    "p03_hw_adapter.c",
    "p07_b2_packet.h",
    "p07_b4m_full_inference.c",
])
def test_stage_mutation_rejected_before_board(tmp_path,filename):
    src=fake_source_tree(tmp_path)
    path=src/filename
    path.write_bytes(path.read_bytes()+b" \n")
    with pytest.raises(gate.DiagnosticAdmissionError,match="differs"):
        gate.verify_staged_source(src)

def test_v1_elf_identity_cannot_disguise_as_diagnostic():
    assert gate.IDENTITY!=gate.admission.ELF_ID
    assert gate.ELF_NAME!=gate.admission.ELF_NAME
    assert b"DIAGNOSTIC_V2" in gate.IDENTITY

def make_full(tmp_path,monkeypatch):
    build=tmp_path/"v2_build"
    build.mkdir()
    fake_source_tree(build)
    reports=tmp_path/"reports"
    reports.mkdir()
    (reports/"p03_2_ps_mmio.xsa").write_bytes(b"synthetic-not-real")
    (reports/"p03_2_post_route_metrics.txt").write_text("\n".join([
        "p03_hpm0_data_width_bits=128",
        "p03_hpm0_transport=smartconnect_width_protocol",
        "p03_mmio_slave_data_width_bits=32",
        "p03_ps_mmio_master=FPD",
        "p03_mmio_base=0xA4000000",
    ])+"\n")
    workspace=build/"vitis_workspace"
    workspace.mkdir()
    (workspace/gate.ELF_NAME).write_bytes(
        b"ELF_SYNTHETIC"+gate.IDENTITY+b"\0")
    frozen=tmp_path/"frozen"
    frozen.mkdir()
    routes=tmp_path/"routes"
    routes.mkdir()
    monkeypatch.setattr(gate.frozen27,"admit_freeze",lambda p:None)
    monkeypatch.setattr(gate.admission,"require_routes",lambda *args:{
        "input_routes":20384,
        "output_routes":1000,
        "registered_axons":21384,
        "staged_files_sha256":{},
    })
    original_sha=gate.sha
    monkeypatch.setattr(gate,"sha",lambda p:
                        gate.XSA_SHA if p.name.endswith(".xsa") else original_sha(p))
    def fake_elf(path,*,expected_name,expected_id):
        assert path.name==gate.ELF_NAME
        assert expected_name==gate.ELF_NAME
        assert expected_id==gate.IDENTITY
        return {"pt_load_memsz":1114112,
                "pt_load_end_exclusive":"0x00110000",
                "new_elf_sha256":"synthetic_not_real",
                "new_linker_map_sha256":"synthetic_not_real"}
    monkeypatch.setattr(gate.admission,"require_elf",fake_elf)
    return frozen,routes,build,reports

def test_v2_host_only_genuine_admission_contract_mocked_external_tools(
    tmp_path,monkeypatch
):
    frozen,routes,build,reports=make_full(tmp_path,monkeypatch)
    record=gate.admit(frozen=frozen,routes=routes,build=build,reports=reports)
    assert record["diagnostic_v2_physical_launch_authorized"] is False
    assert record["expanded_low_DDR_boot_firmware_exclusivity_independently_proven"] is False
    assert record["original_26tick_hardware_inference_accepted"] is False
    assert record["official_MNIST_TEST"]=="SEALED_NOT_ACCESSED"
    assert record["genuine_diagnostic_v2_elf"]["pt_load_memsz"]==1114112

def test_wrong_elf_memory_envelope_fails_closed(tmp_path,monkeypatch):
    frozen,routes,build,reports=make_full(tmp_path,monkeypatch)
    monkeypatch.setattr(gate.admission,"require_elf",lambda *args,**kwargs:{
        "pt_load_memsz":0x1100000
    })
    with pytest.raises(gate.DiagnosticAdmissionError,match="low DDR envelope"):
        gate.admit(frozen=frozen,routes=routes,build=build,reports=reports)

def test_v2_build_command_remains_offline_and_not_v1_launch():
    source=(ROOT/"scripts/p07_b4m_diag_v2_offline_admission.py").read_text()
    assert "xsdb" not in source and "hardware_server" not in source
    assert "diagnostic_v2_physical_launch_authorized" in source
    assert "original_26tick_hardware_inference_accepted" in source
    assert "p07_b4m_full_board_diag.c" in (ROOT/"scripts/build_p07_b4m_diag.sh").read_text()
