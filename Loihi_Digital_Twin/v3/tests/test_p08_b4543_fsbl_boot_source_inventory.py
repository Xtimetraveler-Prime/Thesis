"""P08-B4.5.4.3 synthetic host-only original-XSA/FSBL file observations."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import p08_b4543_fsbl_boot_source_inventory as inv


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def mock_xsa(file: Path, *, member: str = "psu_init.c",
             body: bytes = b"void psu_protection(void){ /* DDR_XMPU */ }") -> None:
    with zipfile.ZipFile(file, "w") as archive:
        archive.writestr(member, body)
        archive.writestr("hw/design.hwh", "<hw> ZynqMP PS DDR </hw>")
        archive.writestr("design/system.bit", b"binary PL firmware")
        archive.writestr("junk.txt", b"unrelated")


@pytest.fixture
def corpus(tmp_path, monkeypatch):
    report = tmp_path / "original_operator_policy_report.json"
    data = {
        "schema": "p08-b4542-host-only-symbolic-xmpu-boot-policy-audit-v1",
        "candidate_file_sha256": "f" * 64,
        "symbolic_transactions_tested": 147456,
        "candidate_real_readers_authorized": False,
        "real_register_values_and_priority_readback_proven": False,
        "physical_KV260_contact": False,
        "physical_execution_authorized": False,
    }
    report.write_text(json.dumps(data))
    monkeypatch.setattr(inv, "ACCEPTED_POLICY_REPORT_SHA",
                        sha(report.read_bytes()))
    monkeypatch.setattr(inv, "ACCEPTED_CANDIDATE_SHA", "f" * 64)
    xsa = tmp_path / "original_p03.xsa"
    mock_xsa(xsa)
    monkeypatch.setattr(inv, "ACCEPTED_P03_XSA_SHA", sha(xsa.read_bytes()))
    return report, xsa


def audit(corpus, out: Path, **kw):
    return inv.audit(policy_report=corpus[0], xsa=corpus[1],
                     out=out, **kw)


def test_minimum_real_source_provenance_gap_is_permanently_no_go(corpus, tmp_path):
    out = tmp_path / "inventory.json"
    result = audit(corpus, out)
    assert result["schema"] == inv.SCHEMA
    assert result["accepted_p03_original_xsa"]["sha256"] == sha(
        corpus[1].read_bytes())
    assert result["accepted_p03_original_xsa"]["count_relevant_members"] >= 2
    assert result["local_handoff_source_order_if_supplied"] == "NOT_SUPPLIED"
    assert result["current_boot_image_provenance_independently_established"] is False
    assert result["beforehandoff_hook_approved_for_secure_xmpu_reprogramming"] is False
    assert result["board_contact"] is False
    assert result["physical_execution_authorized"] is False
    assert out.is_file()
    with pytest.raises(inv.InventoryNoGo, match="no-overwrite"):
        audit(corpus, out)


def test_actual_local_handoff_file_protection_call_precedes_hook(corpus, tmp_path):
    h = tmp_path / "xfsbl_handoff.c"
    h.write_text('''
    u32 XFsbl_Handoff(const XFsblPs *p, u32 part, u32 EarlyHandoff) {
      XFsbl_PmInit();
      Status = XFsbl_ProtectionConfig();
      if (Status) goto END;
      Status = XFsbl_HookBeforeHandoff(EarlyHandoff);
      END: return Status;
    }''')
    r = audit(corpus, tmp_path / "observed.json", handoff=h)
    assert r["local_handoff_source_order_if_supplied"] == (
        "PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK")
    assert r["optional_source_files"][0]["protection_before_hook_in_this_file"] is True
    assert r["optional_source_files"][0]["sha256"] == sha(h.read_bytes())
    assert r["source_files_matched_to_actual_KV260_boot_image"] is False


def test_reverse_handoff_order_is_not_false_proof_of_real_boot(corpus, tmp_path):
    h = tmp_path / "xfsbl_handoff.c"
    h.write_text('''
    u32 XFsbl_Handoff(u32 id) {
       XFsbl_HookBeforeHandoff(0);
       XFsbl_ProtectionConfig();
       return id;
    }''')
    r = audit(corpus, tmp_path / "report.json", handoff=h)
    assert r["local_handoff_source_order_if_supplied"] == (
        "HOOK_CALLED_BEFORE_PROTECTION_CONFIG")
    assert r["beforehandoff_hook_approved_for_secure_xmpu_reprogramming"] is False
    assert r["current_boot_image_provenance_independently_established"] is False


def test_comments_and_declarations_are_not_fsbl_call_order(corpus, tmp_path):
    h = tmp_path / "xfsbl_handoff.c"
    h.write_text('''
    /* XFsbl_ProtectionConfig(); XFsbl_HookBeforeHandoff(); */
    u32 XFsbl_ProtectionConfig(void);
    u32 XFsbl_Handoff(u32 id) {
       // XFsbl_ProtectionConfig();
       Status = XFsbl_HookBeforeHandoff(0);
       return id;
    }''')
    r = audit(corpus, tmp_path / "report.json", handoff=h)
    assert r["local_handoff_source_order_if_supplied"] == "UNKNOWN"
    assert r["beforehandoff_hook_approved_for_secure_xmpu_reprogramming"] is False


def test_optional_psu_bif_hooks_and_fsbl_binary_are_only_file_evidence(corpus, tmp_path):
    hooks = tmp_path / "xfsbl_hooks.c"
    hooks.write_text("u32 XFsbl_HookBeforeHandoff(u32 e) { return e; }")
    psu = tmp_path / "psu_init.c"
    psu.write_text("void psu_init(void){ psu_protection(); DDR_XMPU; }")
    protection = tmp_path / "psu_protection.c"
    protection.write_text("void protection(void){ /* DDR_XMPU */ }")
    bif = tmp_path / "boot.bif"
    bif.write_text("""the_ROM_image:
    {
      [bootloader] fsbl.elf
      [load=0x43000000] contexts.bin
      [authentication=rsa] bitstream.bit
    }""")
    elf = tmp_path / "fsbl.elf"
    elf.write_bytes(b"\x7fELF" + b"synthetic only")
    r = audit(corpus, tmp_path / "all.json",
              hooks=hooks, psu_init=psu, psu_protection=protection,
              boot_bif=bif, fsbl_elf=elf)
    assert r["optional_fsbl_elf"]["sha256"] == sha(elf.read_bytes())
    assert r["optional_fsbl_elf"]["active_board_fsbl_proven"] is False
    assert r["optional_source_files"][4]["observed_bif_text_flags_only"][
        "load_to_0x43000000_seen"] is True
    assert r["optional_source_files"][4]["observed_bif_text_flags_only"][
        "bif_is_proven_active"] is False
    assert r["optional_source_files"][2]["marker_counts"]["DDR_XMPU"] == 1


@pytest.mark.parametrize("tamper", (
    "wrong_policy_sha", "wrong_policy_candidate", "fake_physical_success",
    "fake_real_reader", "incorrect_model_transaction_count",
    "wrong_xsa_sha", "xsa_not_archive", "xsa_path_traversal",
    "source_is_symlink", "bad_fsbl_elf", "fsbl_source_binary",
    "source_larger_than_bound", "corrupted_zip_crc",
    "report_path_in_repo",
))
def test_hard_rejects_and_no_partial_external_report(
        corpus, tmp_path, monkeypatch, tamper):
    report, xsa = corpus
    h = None
    elf = None
    out = tmp_path / "must_not_exist.json"
    if tamper == "wrong_policy_sha":
        report.write_bytes(report.read_bytes() + b"tamper")
    elif tamper in ("wrong_policy_candidate", "fake_physical_success",
                    "fake_real_reader", "incorrect_model_transaction_count"):
        d = json.loads(report.read_text())
        if tamper == "wrong_policy_candidate":
            d["candidate_file_sha256"] = "e" * 64
        elif tamper == "fake_physical_success":
            d["physical_execution_authorized"] = True
        elif tamper == "fake_real_reader":
            d["candidate_real_readers_authorized"] = True
        else:
            d["symbolic_transactions_tested"] = 10
        report.write_text(json.dumps(d))
        monkeypatch.setattr(inv, "ACCEPTED_POLICY_REPORT_SHA",
                            sha(report.read_bytes()))
    elif tamper == "wrong_xsa_sha":
        xsa.write_bytes(xsa.read_bytes() + b"tamper")
    elif tamper == "xsa_not_archive":
        xsa.write_bytes(b"fake XSA nonzip")
        monkeypatch.setattr(inv, "ACCEPTED_P03_XSA_SHA", sha(xsa.read_bytes()))
    elif tamper == "xsa_path_traversal":
        mock_xsa(xsa, member="../bad/psu_init.c")
        monkeypatch.setattr(inv, "ACCEPTED_P03_XSA_SHA", sha(xsa.read_bytes()))
    elif tamper == "source_is_symlink":
        h = tmp_path / "h.c"
        real = tmp_path / "original_h.c"
        real.write_text("u32 XFsbl_Handoff(void){ return 1; }")
        h.symlink_to(real)
    elif tamper == "bad_fsbl_elf":
        elf = tmp_path / "fake.elf"
        elf.write_bytes(b"not ELF")
    elif tamper == "fsbl_source_binary":
        h = tmp_path / "xfsbl_handoff.c"
        h.write_bytes(b"bad\0binary")
    elif tamper == "source_larger_than_bound":
        h = tmp_path / "xfsbl_handoff.c"
        h.write_bytes(b"a" * (inv.MAX_SOURCE + 1))
    elif tamper == "corrupted_zip_crc":
        # ZIP truncated footer but pin adjusted to match corrupted archive.
        xsa.write_bytes(xsa.read_bytes()[:-16])
        monkeypatch.setattr(inv, "ACCEPTED_P03_XSA_SHA", sha(xsa.read_bytes()))
    elif tamper == "report_path_in_repo":
        out = ROOT / "docs" / "must_never_write.json"
    with pytest.raises((inv.InventoryNoGo, zipfile.BadZipFile)):
        audit(corpus, out, handoff=h, fsbl_elf=elf)
    assert not out.exists()


def test_xsa_oversized_text_is_not_decompressed(corpus, tmp_path, monkeypatch):
    mock_xsa(corpus[1], body=b"x" * (inv.MAX_SELECTED_MEMBER + 1))
    monkeypatch.setattr(inv, "ACCEPTED_P03_XSA_SHA", sha(corpus[1].read_bytes()))
    result = audit(corpus, tmp_path / "skipped.json")
    entries = result["accepted_p03_original_xsa"]["inspected_relevant_members"]
    assert any(e.get("status") == "SKIPPED_OVERSIZE_NO_DECOMPRESSION"
               and e["sha256"] is None for e in entries)
    assert result["source_files_matched_to_actual_KV260_boot_image"] is False


def test_original_b4542_policy_digest_is_full_64_hex():
    assert len(inv.ACCEPTED_POLICY_REPORT_SHA) == 64
    assert inv.ACCEPTED_POLICY_REPORT_SHA == (
        "ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2"
    )
    assert inv.ACCEPTED_P03_XSA_SHA == (
        "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
    )
    assert inv.ACCEPTED_CANDIDATE_SHA == (
        "7f78e7582e7fee12a06d83f14e45f1de1faf877ce1429af441dd83db3e851d2a"
    )
