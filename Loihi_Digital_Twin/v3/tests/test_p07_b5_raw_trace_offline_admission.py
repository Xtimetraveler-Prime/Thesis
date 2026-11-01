"""B5.3.2 new Vitis source/map/XSA offline admission contract (PC ONLY)."""
from __future__ import annotations
import hashlib
from pathlib import Path
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import p07_b5_raw_trace_offline_admission as gate

@pytest.fixture()
def prepared_stage(tmp_path):
    stage=tmp_path/"external_B5_vitis_source"
    stage.mkdir()
    manifest=gate.builder()
    for name in (*manifest.SOURCES,*manifest.HEADERS):
        if name.endswith(".c"):
            original=ROOT/("software/p03" if name.startswith("p03_hw_")
                           else "software/p07")/name
        elif name.startswith("p03_"):
            original=ROOT/"software/p03/include"/name
        elif name=="p05_deployment.h":
            original=ROOT/"software/p05/include"/name
        else:
            original=ROOT/"software/p07/include"/name
        raw=original.read_bytes()
        if name=="p07_a2_sha256.c":
            raw=raw.replace(b'#include "include/p07_a2_sha256.h"',
                            b'#include "p07_a2_sha256.h"')
        if name=="p07_b2_packet.h":
            raw=raw.replace(b'#define P07_B2_MAX_ROUTE_BINDINGS 8192u',
                            b'#define P07_B2_MAX_ROUTE_BINDINGS 10000u')
        (stage/name).write_bytes(raw)
    return stage,manifest

def test_isolated_new_build_contract_rejects_missing_or_extra_file(prepared_stage):
    stage,manifest=prepared_stage
    manifest.check_stage(stage)
    assert len(manifest.SOURCES)>15
    assert "p07_b4m_full_board_diag_v3.c" not in manifest.SOURCES
    assert "p07_b4m_spike_trace.c" not in manifest.SOURCES
    assert "p07_b5_raw_capture.c" in manifest.SOURCES
    assert "p07_b5_spike_trace.c" in manifest.SOURCES
    assert "p07_b5_trace_hook.h" in manifest.HEADERS
    (stage/"p07_b5_raw_capture.c").unlink()
    with pytest.raises(ValueError):
        manifest.check_stage(stage)

def test_original_repository_exact_source_sha_binding_and_mutation_rejection(prepared_stage):
    stage,manifest=prepared_stage
    recorded=gate.verify_source(stage)
    assert set(recorded)==set(manifest.SOURCES+manifest.HEADERS)
    assert recorded["p07_b5_raw_capture.c"]==hashlib.sha256(
        (stage/"p07_b5_raw_capture.c").read_bytes()).hexdigest()
    target=stage/"p07_b5_spike_trace.c"
    target.write_bytes(target.read_bytes()+b"\n/* unauthorized modification */")
    with pytest.raises(gate.AdmissionNoGo,match="differs"):
        gate.verify_source(stage)

def test_original_p03_and_frozen_source_contract_fail_closed(prepared_stage):
    stage,_=prepared_stage
    target=stage/"p03_hw_adapter.c"
    target.write_text("int forged_mmio_adapter(void){return 0;}\n")
    with pytest.raises(gate.AdmissionNoGo,match="differs"):
        gate.verify_source(stage)

def test_exact_proposed_trace_and_new_mailbox_ranges_are_disjoint_not_authorized():
    bounds=gate.boundaries()
    assert bounds["raw_trace_exact_bytes"]==840320
    assert bounds["trace_candidate_address_range_hex"]==[
        "0x42000000","0x420cd280"]
    assert bounds["new_B5_mailbox_candidate_address_range_hex"]==[
        "0x43ff0100","0x43ff0200"]
    assert bounds["known_original_software_ranges_disjoint"] is True
    assert bounds["actual_DDR_physical_ownership_independently_proven"] is False
    assert bounds["boot_firmware_low_DDR_exclusivity_independently_proven"] is False

def test_no_fabricated_build_or_elf_admission(tmp_path):
    with pytest.raises(gate.AdmissionNoGo):
        gate.admit(frozen=tmp_path/"none",routes=tmp_path/"none",
                   build=tmp_path/"missing",reports=tmp_path/"none")

def test_new_B5_source_print_identity_does_not_include_previous_V3():
    source=(ROOT/"software/p07/p07_b5_full_board_raw_trace_v1.c").read_bytes()
    assert source.count(gate.IDENTITY)==2
    for legacy in gate.LEGACY_FIRMWARE_IDENTITIES:
        assert legacy not in source


def test_offline_legacy_firmware_identifier_guard_rejects_stale_printf():
    good=gate.IDENTITY+b"\x00synthetic_native_test_only"
    gate.reject_legacy_firmware_identity(good)
    for legacy in gate.LEGACY_FIRMWARE_IDENTITIES:
        with pytest.raises(gate.AdmissionNoGo,match="original firmware identity"):
            gate.reject_legacy_firmware_identity(good+b"\x00"+legacy)


def test_new_shell_build_does_not_use_old_V3_programming_or_elf():
    shell=(ROOT/"scripts/build_p07_b5_raw_trace.sh").read_text()
    code=(ROOT/"software/p07/build_p07_b5_raw_trace.py").read_text()
    assert "software/p07/build_p07_b5_raw_trace.py" in shell
    assert "p07_b5_raw_trace_v1.elf" in shell
    assert "P07_B5_RAW_REAL_BOARD_RUN_AUTHORIZED=0" in shell
    assert "P07_B5_RAW_SIDECAR_DDR_OWNERSHIP_INDEPENDENTLY_PROVEN=0" in shell
    assert "p07_b4m_diag_v3_26tick.elf" not in shell
    assert "xsdb" not in shell and "program_hw_devices" not in shell
    assert "USER_LINK_OTHER_FLAGS" in code
    assert "p07_b5_raw_trace_v1" in code
