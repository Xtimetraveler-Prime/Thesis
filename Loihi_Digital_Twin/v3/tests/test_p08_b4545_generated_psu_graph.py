"""B4.5.4.5: synthetic-only fail-closed original PS-source dependency tests."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b4545_generated_psu_graph as gate


C = """
static int psu_protection(void) { return psu_protection_data(); }
static int psu_protection_data(void) {
    psu_mask_write(0xFD010100, 0xffff, 0);
    psu_mask_write(DDR_XMPU_BASE, 0xffffffff, 0);
    return 0;
}
static int psu_protection_lock(void) {
    psu_mask_write(0xFD020104, 1, 1);
    return 0;
}
"""
H = "#define DDR_XMPU_BASE 0xFD000100\n#define DDR_XMPU_REGION_14 14\n"
T = "set psu_protection_data {DDR_XMPU_1 0xFD010100}\n"
HWH = "<root><module name='DDR_XMPU_1'/><port name='M_AXI_HPM0_FPD'/></root>"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def write_xsa(path: Path, *, c: str = C, h: str = H,
              t: str = T, include_hwh: bool = True,
              include_header: bool = True) -> None:
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("psu_init.c", c)
        z.writestr("psu_init.tcl", t)
        if include_header:
            z.writestr("psu_init.h", h)
        if include_hwh:
            z.writestr("system.hwh", HWH)


@pytest.fixture
def original(tmp_path: Path, monkeypatch):
    xsa = tmp_path / "original.xsa"
    write_xsa(xsa)
    c = tmp_path / "psu_init.c"
    h = tmp_path / "psu_init.h"
    t = tmp_path / "psu_init.tcl"
    c.write_text(C)
    h.write_text(H)
    t.write_text(T)
    prior = tmp_path / "b4544.json"
    accepted = {
        "schema": gate.previous.SCHEMA,
        "decision": "FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO",
        "BOOT_BIN_and_current_actual_fsbl_identity_proven": False,
        "physical_KV260_inference_authorized": False,
        "JTAG_DDR_register_or_boot_media_access": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "original_generated_psu_init_sha256": sha(c.read_bytes()),
        "xsa_to_original_psu_init_source_provenance": {
            "original_xsa_sha256": sha(xsa.read_bytes()),
            "standalone_psu_init_matches_XSA_exactly": True,
        },
    }
    prior.write_text(json.dumps(accepted))
    monkeypatch.setattr(gate, "ACCEPTED_PREVIOUS_SHA", sha(prior.read_bytes()))
    monkeypatch.setattr(gate, "EXPECTED_PSU_C_SHA", sha(c.read_bytes()))
    monkeypatch.setattr(gate.inventory, "ACCEPTED_P03_XSA_SHA", sha(xsa.read_bytes()))
    return {"prior_report": prior, "xsa": xsa, "psu_init": c,
            "psu_header": h, "psu_tcl": t}


def run_gate(inputs, out, artifacts=None):
    return gate.audit(**inputs, out=out, artifacts=artifacts)


def test_original_three_file_sha_and_source_dependencies(original, tmp_path):
    report = run_gate(original, tmp_path / "audit.json")
    assert report["schema"] == gate.SCHEMA
    g = report["source_call_graph_and_symbolic_register_inventory"]
    assert "psu_protection_data" in g["reachable_source_functions"]["psu_protection"]
    assert g["literal_ddr_xmpu_sites_by_port"]["1"] == 1
    assert g["literal_ddr_xmpu_sites_by_port"]["2"] == 1
    assert g["region_slot_priority_mask_register_semantics_proven"] is False
    assert report["original_p03_xsa"]["hwh_descriptors"][0]["xmpu_mentions"] == 1
    assert report["current_boot_bin_fsbl_elf_and_flags_bound_to_board"] is False
    assert report["decision"].endswith("NO_GO")
    with pytest.raises(gate.GeneratedSourceNoGo, match="no-overwrite"):
        run_gate(original, tmp_path / "audit.json")


@pytest.mark.parametrize("tamper", (
    "prior_file", "changed_C", "changed_H", "changed_T",
    "XSA_bytes", "XSA_missing_header", "XSA_missing_hwh",
    "prior_false_boot", "prior_false_approval", "prior_false_test",
))
def test_negative_original_files_and_prior_claims_rejected(original, tmp_path,
                                                           tamper):
    inputs = original
    if tamper == "prior_file":
        inputs["prior_report"].write_bytes(inputs["prior_report"].read_bytes()+b"x")
    elif tamper == "changed_C":
        inputs["psu_init"].write_text(C + "/* drift */")
    elif tamper == "changed_H":
        inputs["psu_header"].write_text(H + "#define MORE 1")
    elif tamper == "changed_T":
        inputs["psu_tcl"].write_text(T + "extra\n")
    elif tamper == "XSA_bytes":
        with inputs["xsa"].open("ab") as fd:
            fd.write(b"tampered archive")
    elif tamper == "XSA_missing_header":
        write_xsa(inputs["xsa"], include_header=False)
    elif tamper == "XSA_missing_hwh":
        write_xsa(inputs["xsa"], include_hwh=False)
    else:
        prior = json.loads(inputs["prior_report"].read_text())
        if tamper == "prior_false_boot":
            prior["BOOT_BIN_and_current_actual_fsbl_identity_proven"] = True
        elif tamper == "prior_false_approval":
            prior["physical_KV260_inference_authorized"] = True
        else:
            prior["official_MNIST_TEST"] = "UNSEALED"
        inputs["prior_report"].write_text(json.dumps(prior))
    with pytest.raises((gate.GeneratedSourceNoGo, gate.inventory.InventoryNoGo)):
        run_gate(inputs, tmp_path / "reject.json")
    assert not (tmp_path / "reject.json").exists()


def test_source_graph_missing_roots_duplicate_root_and_recursion_rejected():
    with pytest.raises(gate.GeneratedSourceNoGo, match="lock"):
        gate.graph_report(C.replace("psu_protection_lock", "not_a_lock"), H, T)
    with pytest.raises(gate.GeneratedSourceNoGo, match="duplicate"):
        gate.graph_report(C + "\n" + C, H, T)
    funcs = gate.function_definitions(C)
    assert "psu_protection_data" in funcs
    g = gate.graph_report(C.replace(
        "psu_mask_write(DDR_XMPU_BASE, 0xffffffff, 0);",
        "some_external_helper(DDR_XMPU_BASE);"), H, T)
    assert "some_external_helper" in g["unresolved_calls_include_macros_libc_or_external"]
    assert g["generated_security_policy_safe_to_enable"] is False


def test_optional_boot_files_do_not_prove_active_boot(original, tmp_path):
    fake_bin = tmp_path / "BOOT.BIN"
    fake_bin.write_bytes(b"not necessarily active")
    report = run_gate(original, tmp_path / "report.json", [fake_bin])
    entry = report["optional_existing_boot_artifacts"][0]
    assert entry["sha256"] == sha(fake_bin.read_bytes())
    assert entry["belongs_to_current_KV260_boot_medium_proven"] is False
    assert report["board_hardware_contact"] is False


def test_missing_duplicate_bad_extension_and_symlink_artifacts(original, tmp_path):
    good = tmp_path / "fsbl.elf"
    good.write_bytes(b"\x7fELFfake")
    linked = tmp_path / "alias.elf"
    linked.symlink_to(good)
    for paths in ([good, good], [tmp_path / "missing.bin"],
                  [linked], [tmp_path / "unapproved.sh"]):
        with pytest.raises((gate.GeneratedSourceNoGo, gate.inventory.InventoryNoGo)):
            run_gate(original, tmp_path / "reject.json", paths)
        assert not (tmp_path / "reject.json").exists()


def test_original_operator_frozen_sha_pins():
    assert gate.ACCEPTED_PREVIOUS_SHA == (
        "e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9")
    assert gate.EXPECTED_PSU_C_SHA == (
        "049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679")
