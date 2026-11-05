"""B4.5.4.4 original FSBL conditional protection source analysis, all synthetic."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b4544_fsbl_protection_path as gate


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


HANDOFF = r"""
static u32 XFsbl_ProtectionConfig(void)
{
  u32 Status = 0;
#ifdef XFSBL_PROT_BYPASS
  psu_apply_master_tz();
  psu_ocm_protection();
#else
  Status = (u32)psu_protection();
  if (Status != XFSBL_SUCCESS) goto END;
  Status = (u32)psu_protection_lock();
#endif
END:
  return Status;
}
u32 XFsbl_Handoff(void) {
  XFsbl_PmInit();
  Status = XFsbl_ProtectionConfig();
  Status = XFsbl_HookBeforeHandoff(0);
  return Status;
}
"""

HW = """
#ifndef XFSBL_HW_H
#define XFSBL_HW_H
#if !defined(FSBL_PROT_BYPASS_EXCLUDE)
#define XFSBL_PROT_BYPASS
#endif
#endif
"""

PSU = """
void psu_protection(void) {
    psu_mask_write(0xFD01010C, 0xffffffff, 0x00);
    psu_mask_write(0xFD02010C, 0xffffffff, 0x00);
    psu_mask_write(0xFD03010C, 0xffffffff, 0x00);
}
void psu_protection_lock(void) {
    psu_mask_write(0xFD010000, 1, 1);
}
void psu_apply_master_tz(void) {}
void psu_ocm_protection(void) {}
"""


@pytest.fixture
def originals(tmp_path: Path, monkeypatch):
    root = tmp_path
    hand = root / "xfsbl_handoff.c"
    hand.write_text(HANDOFF)
    header = root / "xfsbl_hw.h"
    header.write_text(HW)
    generated = root / "psu_init.c"
    generated.write_text(PSU)
    xsa = root / "original_p03.xsa"
    with zipfile.ZipFile(xsa, "w") as archive:
        archive.writestr("psu_init.c", generated.read_bytes())
        archive.writestr("psu_init.tcl", "set psu_protection_data { }")
    info = {
        "schema": gate.prior.SCHEMA,
        "decision": "READ_ONLY_SOURCE_INVENTORY_PASS_ACTIVE_BOOT_AND_PROTECTION_NOT_PROVEN",
        "local_handoff_source_order_if_supplied":
            "PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK",
        "real_xmpu_registers_written": False,
        "physical_execution_authorized": False,
        "current_boot_image_provenance_independently_established": False,
        "accepted_p03_original_xsa": {
            "sha256": digest(xsa.read_bytes()),
        },
        "optional_source_files": [
            {"role": "fsbl_handoff", "sha256": digest(hand.read_bytes()),
             "supplied": True},
            {"role": "fsbl_hooks", "sha256": digest(b"synthetic hooks"),
             "supplied": True},
            {"role": "psu_init", "sha256": digest(generated.read_bytes()),
             "supplied": True},
        ],
    }
    report = root / "previous_accepted_source_inventory.json"
    report.write_text(json.dumps(info))
    monkeypatch.setattr(gate, "ACCEPTED_INVENTORY_SHA",
                        digest(report.read_bytes()))
    monkeypatch.setattr(gate, "HANDOFF_SHA", digest(hand.read_bytes()))
    monkeypatch.setattr(gate, "HOOKS_SHA", digest(b"synthetic hooks"))
    monkeypatch.setattr(gate, "P03_PSU_INIT_SHA", digest(generated.read_bytes()))
    monkeypatch.setattr(gate.prior, "ACCEPTED_P03_XSA_SHA",
                        digest(xsa.read_bytes()))
    return report, hand, header, generated, xsa


def review(inputs, out: Path):
    rep, hand, header, gen, xsa = inputs
    return gate.audit(prior_report=rep, handoff=hand,
                      hw_header=header, psu_init=gen,
                      xsa=xsa, out=out)


def test_source_both_paths_and_P03_psu_exact_XSA_match(originals, tmp_path):
    out = tmp_path / "source_review.json"
    r = review(originals, out)
    assert r["schema"] == gate.SCHEMA
    assert r["xsa_to_original_psu_init_source_provenance"][
        "standalone_psu_init_matches_XSA_exactly"] is True
    p = r["fsbl_protection_branch_cases"]
    assert p["bypass_path_skips_generated_psu_protection_and_lock"] is True
    assert p["full_path_calls_protection_before_lock"] is True
    assert r["fsbl_hw_header_compile_time_bypass"][
        "default_header_defines_protection_bypass_unless_excluded"] is True
    assert r["original_xsa_generated_psu_functions_and_literals"][
        "static_literal_xmpu_register_address_counts_by_port"]["1"] >= 1
    assert r["physical_KV260_inference_authorized"] is False
    assert r["original_A53_guard_enabled"] is False
    assert r["decision"].endswith("NO_GO")
    with pytest.raises(gate.ProtectionSourceNoGo, match="no-overwrite"):
        review(originals, out)


@pytest.mark.parametrize("corrupt", (
    "changed_prior_json", "changed_handoff", "changed_psu",
    "changed_xsa", "mismatched_xsa_member", "missing_psu_member",
    "bypass_grants_full_lock", "full_branch_skips_lock",
    "full_branch_reverses_lock", "no_bypass_define", "no_exclude_macro",
    "source_hook_before_protection",
    "fraudulent_real_boot", "fraudulent_physical_approval",
))
def test_frozen_source_and_protection_logic_rejects_change(
        originals, tmp_path, monkeypatch, corrupt):
    rep, hand, header, generated, xsa = originals
    report = json.loads(rep.read_text())
    if corrupt == "changed_prior_json":
        rep.write_bytes(rep.read_bytes() + b"tampered")
    elif corrupt == "changed_handoff":
        hand.write_bytes(hand.read_bytes() + b"tamper")
    elif corrupt == "changed_psu":
        generated.write_bytes(generated.read_bytes() + b"tamper")
    elif corrupt in ("changed_xsa", "mismatched_xsa_member", "missing_psu_member"):
        with zipfile.ZipFile(xsa, "w") as archive:
            if corrupt == "changed_xsa":
                archive.writestr("psu_init.c", PSU)
                archive.writestr("unapproved.txt", "new")
            elif corrupt == "mismatched_xsa_member":
                archive.writestr("psu_init.c", PSU + " changed")
            else:
                archive.writestr("no_psu.c", PSU)
        if corrupt != "changed_xsa":
            monkeypatch.setattr(gate.prior, "ACCEPTED_P03_XSA_SHA",
                                digest(xsa.read_bytes()))
    elif corrupt in ("bypass_grants_full_lock", "full_branch_skips_lock",
                     "full_branch_reverses_lock",
                     "source_hook_before_protection"):
        text = hand.read_text()
        if corrupt == "bypass_grants_full_lock":
            text = text.replace("  psu_ocm_protection();",
                                "  psu_ocm_protection(); psu_protection_lock();")
        elif corrupt == "full_branch_skips_lock":
            text = text.replace("Status = (u32)psu_protection_lock();",
                                "Status = 0;")
        elif corrupt == "full_branch_reverses_lock":
            text = text.replace(
                "Status = (u32)psu_protection();",
                "Status = (u32)psu_protection_lock();").replace(
                "Status = (u32)psu_protection_lock();\n#endif",
                "Status = (u32)psu_protection();\n#endif")
        else:
            text = text.replace(
                "Status = XFsbl_ProtectionConfig();\n  Status = XFsbl_HookBeforeHandoff(0);",
                "Status = XFsbl_HookBeforeHandoff(0);\n  Status = XFsbl_ProtectionConfig();")
        hand.write_text(text)
        monkeypatch.setattr(gate, "HANDOFF_SHA", digest(hand.read_bytes()))
        report["optional_source_files"][0]["sha256"] = digest(hand.read_bytes())
        rep.write_text(json.dumps(report))
        monkeypatch.setattr(gate, "ACCEPTED_INVENTORY_SHA", digest(rep.read_bytes()))
    elif corrupt in ("no_bypass_define", "no_exclude_macro"):
        if corrupt == "no_bypass_define":
            header.write_text(HW.replace("#define XFSBL_PROT_BYPASS", ""))
        else:
            header.write_text(HW.replace("FSBL_PROT_BYPASS_EXCLUDE",
                                         "UNRECOGNIZED_MACRO"))
    elif corrupt == "fraudulent_real_boot":
        report["current_boot_image_provenance_independently_established"] = True
        rep.write_text(json.dumps(report))
        monkeypatch.setattr(gate, "ACCEPTED_INVENTORY_SHA", digest(rep.read_bytes()))
    elif corrupt == "fraudulent_physical_approval":
        report["physical_execution_authorized"] = True
        rep.write_text(json.dumps(report))
        monkeypatch.setattr(gate, "ACCEPTED_INVENTORY_SHA", digest(rep.read_bytes()))
    with pytest.raises((gate.ProtectionSourceNoGo, gate.prior.InventoryNoGo)):
        review(originals, tmp_path / "NO_OUTPUT.json")
    assert not (tmp_path / "NO_OUTPUT.json").exists()


def test_real_operator_three_original_input_sha_pins():
    assert gate.ACCEPTED_INVENTORY_SHA == (
        "9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5")
    assert gate.HANDOFF_SHA == (
        "161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a")
    assert gate.P03_PSU_INIT_SHA == (
        "049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679")
    assert gate.HOOKS_SHA == (
        "35d0fe1f292166c36b09addb2aebb239c97583e66ceea3379a494689a4dd1f20")
