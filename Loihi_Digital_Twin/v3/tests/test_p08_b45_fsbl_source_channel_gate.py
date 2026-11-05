"""P08-B4.5 C/FSBL vs Tcl/XSDB source and boot-artifact gate tests.

All inputs are synthetic. These tests NEVER contact or program a board.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b45_fsbl_source_channel_gate as gate

C = """
int psu_ddr_xmpu0_data(void) { return 1; }
int psu_ddr_xmpu1_data(void) { return 1; }
int psu_ddr_xmpu2_data(void) { return 1; }
int psu_ddr_xmpu3_data(void) { return 1; }
int psu_ddr_xmpu4_data(void) { return 1; }
int psu_ddr_xmpu5_data(void) { return 1; }
int psu_ddr_protection(void) {
  psu_ddr_xmpu0_data(); psu_ddr_xmpu1_data();
  psu_ddr_xmpu2_data(); psu_ddr_xmpu3_data();
  psu_ddr_xmpu4_data(); psu_ddr_xmpu5_data();
  return 1;
}
int psu_protection(void) { return psu_ddr_protection(); }
int psu_protection_lock_data(void) { return 1; }
int psu_protection_lock(void) { return psu_protection_lock_data(); }
"""
H = "#define DDR_XMPU0 0xfd000000\n"
T = """
proc psu_ddr_xmpu0_data {} { mwr 0xfd000100 0x01 }
proc psu_ddr_xmpu1_data {} { mwr 0xfd010100 0x02 }
set xmpu_config XMPU2
"""
HWH = "<module name='psu' ip='DDR_XMPU0'/>"


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def original_xsa(path: Path, *, source=C, tcl=T, hwh=True):
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("psu_init.c", source)
        z.writestr("psu_init.h", H)
        z.writestr("psu_init.tcl", tcl)
        if hwh:
            z.writestr("original.hwh", HWH)


@pytest.fixture
def files(tmp_path: Path, monkeypatch):
    xsa = tmp_path / "original.xsa"
    original_xsa(xsa)
    c = tmp_path / "psu_init.c"
    h = tmp_path / "psu_init.h"
    t = tmp_path / "psu_init.tcl"
    c.write_text(C)
    h.write_text(H)
    t.write_text(T)
    previous_graph = gate.previous.graph_report(C, H, T)
    prior = {
        "schema": gate.previous.SCHEMA,
        "decision": "GENERATED_PSU_SOURCE_GRAPH_ONLY_ACTIVE_BOOT_AND_XMPU_NO_GO",
        "physical_execution_authorized": False,
        "board_hardware_contact": False,
        "hardware_register_or_ddr_writes": False,
        "active_boot_medium_proven": False,
        "A53_read_only_backup_guard_enabled": False,
        "candidate_FSBL_full_protection_safe_to_enable": False,
        "actual_10_bit_AXI_master_IDs_proven": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "immutable_backup_bytes": 27*524288,
        "overprotected_adjacent_bytes": 524288,
        "original_backup_range": ["0x43000000", "0x43d80000"],
        "conservative_1mib_cover": ["0x43000000", "0x43e00000"],
        "original_p03_xsa": {"sha256": sha(xsa.read_bytes())},
        "original_generated_file_sha256": {
            "psu_init.c": sha(c.read_bytes()),
            "psu_init.h": sha(h.read_bytes()),
            "psu_init.tcl": sha(t.read_bytes()),
        },
        "source_call_graph_and_symbolic_register_inventory": previous_graph,
    }
    report = tmp_path / "accepted_b4545.json"
    report.write_text(json.dumps(prior, sort_keys=True))
    monkeypatch.setattr(gate, "ACCEPTED_B4545_REPORT_SHA", sha(report.read_bytes()))
    monkeypatch.setattr(gate, "ORIGINAL_PSU_C_SHA", sha(c.read_bytes()))
    monkeypatch.setattr(gate.previous.inventory,
                        "ACCEPTED_P03_XSA_SHA", sha(xsa.read_bytes()))
    return {
        "original_report": report, "original_xsa": xsa,
        "psu_c": c, "psu_h": h, "psu_tcl": t,
    }


def run_audit(inputs, result: Path, artifacts=None):
    return gate.audit(**inputs, out=result, artifacts=artifacts)


def test_valid_source_graph_stubs_vs_debugger_tcl(files, tmp_path):
    report = run_audit(files, tmp_path / "pass.json")
    c = report["source_channel_separation"]
    assert c["generated_C_used_for_FSBL_source_path"] is True
    assert c["tcl_is_not_automatically_executed_by_FSBL"] is True
    assert len(c["source_only_C_DDR_helpers"]) == 6
    p0 = c["source_only_C_DDR_helpers"][0]
    assert p0["c_has_no_obvious_write_call_or_named_callee"] is True
    assert p0["tcl_proc_declaration_seen"] is True
    assert p0["tcl_symbol_reference_lines"] == 1
    assert report["current_KV260_boot_medium_FSBL_ELF_and_build_flags_verified"] is False
    assert report["physical_16_or_1024_image_session_authorized"] is False
    assert report["decision"].endswith("NO_GO")
    assert report["original_generated_file_sha256"]["psu_init.c"] == sha(C.encode())
    with pytest.raises(gate.PhysicalReadinessNoGo, match="no-overwrite"):
        run_audit(files, tmp_path / "pass.json")


@pytest.mark.parametrize("reason", [
    "prior_sha", "prior_schema", "faked_phys_run", "faked_boot",
    "unsealed_test", "bad_backup_range", "bad_prior_c_sha",
    "bad_source_graph", "tamper_c", "tamper_h", "tamper_t",
    "corrupt_xsa", "xsa_c_mismatch",
])
def test_fail_closed_to_prior_or_original_source_tampering(files, tmp_path,
                                                          reason, monkeypatch):
    prior = json.loads(files["original_report"].read_text())
    if reason == "prior_sha":
        files["original_report"].write_bytes(
            files["original_report"].read_bytes() + b"bad")
    elif reason == "prior_schema":
        prior["schema"] = "fabricated"
    elif reason == "faked_phys_run":
        prior["physical_execution_authorized"] = True
    elif reason == "faked_boot":
        prior["active_boot_medium_proven"] = True
    elif reason == "unsealed_test":
        prior["official_MNIST_TEST"] = "UNSEALED"
    elif reason == "bad_backup_range":
        prior["conservative_1mib_cover"][1] = "0x43d80000"
    elif reason == "bad_prior_c_sha":
        prior["original_generated_file_sha256"]["psu_init.c"] = "0"*64
    elif reason == "bad_source_graph":
        prior["source_call_graph_and_symbolic_register_inventory"][
            "reachable_function_dependencies"]["psu_protection"]["defined_calls"] = []
    elif reason == "tamper_c":
        files["psu_c"].write_text(C + "\n// altered")
    elif reason == "tamper_h":
        files["psu_h"].write_text(H + "\n#define FAKE 1\n")
    elif reason == "tamper_t":
        files["psu_tcl"].write_text(T + "\nset hacked 1\n")
    elif reason == "corrupt_xsa":
        files["original_xsa"].write_bytes(b"not an XSA")
    elif reason == "xsa_c_mismatch":
        original_xsa(files["original_xsa"], source=C + "\n// altered")
    if reason in (
        "prior_schema", "faked_phys_run", "faked_boot", "unsealed_test",
        "bad_backup_range", "bad_prior_c_sha", "bad_source_graph"
    ):
        files["original_report"].write_text(json.dumps(prior))
        monkeypatch.setattr(
            gate, "ACCEPTED_B4545_REPORT_SHA",
            sha(files["original_report"].read_bytes()))
    with pytest.raises((gate.PhysicalReadinessNoGo,
                        gate.previous.GeneratedSourceNoGo,
                        gate.previous.inventory.InventoryNoGo,
                        KeyError)):
        run_audit(files, tmp_path / "reject.json")
    assert not (tmp_path / "reject.json").exists()


def test_no_ddr_c_function_cannot_be_silently_omitted(files, tmp_path, monkeypatch):
    modified = C.replace("int psu_ddr_xmpu5_data(void)", "int removed_port5(void)")
    original_xsa(files["original_xsa"], source=modified)
    files["psu_c"].write_text(modified)
    prior = json.loads(files["original_report"].read_text())
    prior["original_generated_file_sha256"]["psu_init.c"] = sha(modified.encode())
    prior["source_call_graph_and_symbolic_register_inventory"] = \
        gate.previous.graph_report(modified, H, T)
    prior["original_p03_xsa"]["sha256"] = sha(files["original_xsa"].read_bytes())
    files["original_report"].write_text(json.dumps(prior))
    monkeypatch.setattr(gate, "ORIGINAL_PSU_C_SHA", sha(modified.encode()))
    monkeypatch.setattr(gate, "ACCEPTED_B4545_REPORT_SHA",
                        sha(files["original_report"].read_bytes()))
    monkeypatch.setattr(gate.previous.inventory, "ACCEPTED_P03_XSA_SHA",
                        sha(files["original_xsa"].read_bytes()))
    with pytest.raises(gate.PhysicalReadinessNoGo, match="missing genuine"):
        run_audit(files, tmp_path / "no_port5.json")


def test_c_function_write_is_not_mistaken_for_noop(files, tmp_path, monkeypatch):
    changed = C.replace(
        "int psu_ddr_xmpu2_data(void) { return 1; }",
        "int psu_ddr_xmpu2_data(void) { Xil_Out32(0xfd020100, 0); return 1; }")
    original_xsa(files["original_xsa"], source=changed)
    files["psu_c"].write_text(changed)
    prior = json.loads(files["original_report"].read_text())
    prior["original_generated_file_sha256"]["psu_init.c"] = sha(changed.encode())
    prior["source_call_graph_and_symbolic_register_inventory"] = \
        gate.previous.graph_report(changed, H, T)
    prior["original_p03_xsa"]["sha256"] = sha(files["original_xsa"].read_bytes())
    files["original_report"].write_text(json.dumps(prior))
    monkeypatch.setattr(gate, "ORIGINAL_PSU_C_SHA", sha(changed.encode()))
    monkeypatch.setattr(gate, "ACCEPTED_B4545_REPORT_SHA",
                        sha(files["original_report"].read_bytes()))
    monkeypatch.setattr(gate.previous.inventory, "ACCEPTED_P03_XSA_SHA",
                        sha(files["original_xsa"].read_bytes()))
    report = run_audit(files, tmp_path / "candidate_write.json")
    p2 = report["source_channel_separation"]["source_only_C_DDR_helpers"][2]
    assert p2["c_has_no_obvious_write_call_or_named_callee"] is False
    assert p2["c_obvious_write_calls"] > 0
    assert p2["actual_XMPU_writes_in_live_boot_proven"] is False


def test_optional_local_boot_source_keyword_does_not_prove_active_boot(files, tmp_path):
    bif = tmp_path / "boot.bif"
    bif.write_text("the_ROM_image:\n{ [bootloader] fsbl.elf }\n")
    flags = tmp_path / "compile.rsp"
    flags.write_text("-DFSBL_PROT_BYPASS_EXCLUDE\n")
    r = run_audit(files, tmp_path / "candidate.json", [bif, flags])
    records = r["optional_host_existing_boot_candidates"]
    assert len(records) == 2
    assert records[0]["read_only_source_indicators"][
        "source_file_contains_bootloader_partition_keyword"] is True
    assert records[1]["read_only_source_indicators"][
        "source_file_contains_build_protection_exclude_macro"] is True
    assert not records[1]["read_only_source_indicators"][
        "running_board_used_this_boot_artifact"]
    assert r["hardware_or_boot_media_writes_authorized"] is False


def test_optional_bad_candidate_symlink_duplicate_or_missing(files, tmp_path):
    existing = tmp_path / "BOOt.BIN"
    existing.write_bytes(b"untrusted bytes")
    alias = tmp_path / "sym.BIN"
    alias.symlink_to(existing)
    for bad in ([existing, existing], [alias], [tmp_path / "missing.elf"]):
        with pytest.raises((gate.PhysicalReadinessNoGo,
                            gate.previous.GeneratedSourceNoGo,
                            gate.previous.inventory.InventoryNoGo)):
            run_audit(files, tmp_path / "blocked.json", bad)
        assert not (tmp_path / "blocked.json").exists()


def test_original_operator_report_pin_is_immutable_source_contract():
    assert gate.ACCEPTED_B4545_REPORT_SHA == (
        "2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0")
    assert gate.ORIGINAL_PSU_C_SHA == (
        "049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679")
