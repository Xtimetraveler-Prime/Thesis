#!/usr/bin/env python3
"""P08-B4.5.4.4: independently inspect REAL FSBL conditional protection source.

HOST-ONLY. Reads the accepted genuine XSA and user-selected Vitis
xfsbl_handoff.c/xfsbl_hw.h and original P03-generated psu_init.c.
Does not build boot media, write registers, connect to KV260 or claim
that host C sources were compiled into the currently active FSBL.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import zipfile

import p08_b4543_fsbl_boot_source_inventory as prior
import p08_b454_ddr_owner_preflight as owner
import p08_b45_pair_elf_evidence as pair

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "p08-b4544-host-fsbl-protection-conditional-branch-review-v1"
ACCEPTED_INVENTORY_SHA = "9c2a142bc62dc7bbfe73e5f85bd819adcf3854dfc3e02701ee18c9e7162667f5"
HANDOFF_SHA = "161ffc06037594fd14be856dce29ec6643eb97c8dcbe2872abc414b8c4d5d80a"
HOOKS_SHA = "35d0fe1f292166c36b09addb2aebb239c97583e66ceea3379a494689a4dd1f20"
P03_PSU_INIT_SHA = "049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679"
AMD_2025_2_HW_HEADER = (
    "https://raw.githubusercontent.com/Xilinx/embeddedsw/"
    "xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h"
)
AMD_2025_2_HANDOFF = (
    "https://raw.githubusercontent.com/Xilinx/embeddedsw/"
    "xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c"
)
DDR_XMPU_REGISTERS = tuple((0xFD000000 + i * 0x10000,
                             0xFD000000 + i * 0x10000 + 0x1000)
                            for i in range(6))


class ProtectionSourceNoGo(ValueError):
    pass


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise ProtectionSourceNoGo("NO-GO: " + reason)


def safe_source(path: Path, expected: str | None, label: str) -> str:
    sha, raw = prior.hash_file(path, max_bytes=prior.MAX_SOURCE)
    if expected is not None:
        require(sha == expected, label + " changed since operator accepted inventory")
    require(b"\x00" not in raw, label + " is binary instead of source")
    return raw.decode("utf-8", errors="replace")


def function_body(source: str, name: str) -> dict:
    """C token heuristic for SOURCE EVIDENCE ONLY; not a C compiler."""
    cleaned = prior.remove_c_comments(source)
    search = re.compile(
        r"\b" + re.escape(name) + r"\s*\([^;{}]*\)\s*\{",
        flags=re.DOTALL)
    matches = list(search.finditer(cleaned))
    if len(matches) != 1:
        return {"found_once": False, "body": "",
                "observed_definitions": len(matches)}
    start = matches[0].end() - 1
    braces = 0
    end = None
    for i in range(start, len(cleaned)):
        if cleaned[i] == "{":
            braces += 1
        elif cleaned[i] == "}":
            braces -= 1
            if braces == 0:
                end = i + 1
                break
    require(end is not None, name + " body is not balanced")
    return {"found_once": True, "body": cleaned[start:end],
            "observed_definitions": 1}


def protection_branches(handoff: str) -> dict:
    func = function_body(handoff, "XFsbl_ProtectionConfig")
    require(func["found_once"], "one actual XFsbl_ProtectionConfig function required")
    body = func["body"]
    m = re.search(
        r"^\s*#\s*ifdef\s+XFSBL_PROT_BYPASS\s*\n"
        r"(?P<bypass>.*?)"
        r"^\s*#\s*else\s*\n"
        r"(?P<normal>.*?)"
        r"^\s*#\s*endif\b",
        body, flags=re.MULTILINE | re.DOTALL)
    require(m is not None,
            "not the expected guarded 2025.2 FSBL protection source layout")
    bypass = m.group("bypass")
    normal = m.group("normal")
    b_calls = {x: bool(re.search(r"\b" + x + r"\s*\(", bypass))
               for x in ("psu_apply_master_tz", "psu_ocm_protection",
                         "psu_protection", "psu_protection_lock")}
    n_calls = {x: bool(re.search(r"\b" + x + r"\s*\(", normal))
               for x in ("psu_apply_master_tz", "psu_ocm_protection",
                         "psu_protection", "psu_protection_lock")}
    require(b_calls["psu_apply_master_tz"] and
            b_calls["psu_ocm_protection"] and
            not b_calls["psu_protection"] and
            not b_calls["psu_protection_lock"],
            "bypass branch must not be misrepresented as full XMPU protection")
    require(n_calls["psu_protection"] and
            n_calls["psu_protection_lock"] and
            not n_calls["psu_ocm_protection"],
            "full protection branch must call PSU config and locking")
    require(normal.find("psu_protection();") <
            normal.find("psu_protection_lock();"),
            "full protection must precede full lock")
    return {
        "source_bypass_branch_detected": True,
        "bypass_path_calls": b_calls,
        "bypass_path_skips_generated_psu_protection_and_lock": True,
        "source_full_protection_branch_detected": True,
        "full_protection_path_calls": n_calls,
        "full_path_calls_protection_before_lock": True,
        "actual_compiled_branch_proven": False,
    }


def header_default_condition(header: str) -> dict:
    cleaned = prior.remove_c_comments(header)
    result = re.search(
        r"#\s*if\s*!\s*defined\s*\(\s*FSBL_PROT_BYPASS_EXCLUDE\s*\)"
        r"\s*#\s*define\s+XFSBL_PROT_BYPASS\s*"
        r"#\s*endif",
        cleaned)
    require(result is not None,
            "Vitis xfsbl_hw.h default XMPU-bypass define not found")
    return {
        "default_header_defines_protection_bypass_unless_excluded": True,
        "required_build_exclusion_macro_for_full_psu_config":
            "FSBL_PROT_BYPASS_EXCLUDE",
        "build_defines_FSBL_PROT_BYPASS_EXCLUDE_PROVEN": False,
        "compile_configuration_and_active_boot_linkage_PROVEN": False,
    }


def generated_psu_summary(source: str, *, filename: str) -> dict:
    # No execution or public release of original generated code.
    # Count function definitions and XMPU-specific literal register
    # addresses for source review; no attempt to derive live XMPU state.
    functions = {}
    for name in ("psu_protection", "psu_protection_lock",
                 "psu_apply_master_tz", "psu_ocm_protection"):
        found = function_body(source, name)
        body = found["body"]
        functions[name] = {
            "definition_found_once": found["found_once"],
            "definition_count": found["observed_definitions"],
            "definition_body_bytes": len(body.encode()),
            "xmpu_symbol_mentions": len(re.findall(
                r"(?:DDR_XMPU|XMPU)", body, re.IGNORECASE)),
            "psu_mask_write_mentions": len(re.findall(
                r"\b(?:psu_mask_write|psu_mask_poll)\s*\(", body)),
            "static_source_function_only_not_hardware_proof": True,
        }
    register_addresses = []
    for m in re.finditer(r"\b0[xX]([0-9a-fA-F]{8})\b", source):
        addr = int(m.group(0), 16)
        port = next((idx for idx, (lo, hi) in
                     enumerate(DDR_XMPU_REGISTERS) if lo <= addr < hi), None)
        if port is not None:
            register_addresses.append({
                "ddr_xmpu_port": port,
                "symbolic_register_address": f"0x{addr:08x}",
            })
    unique = {(x["ddr_xmpu_port"], x["symbolic_register_address"])
              for x in register_addresses}
    by_port = {str(i): len([v for v in unique if v[0] == i])
               for i in range(6)}
    return {
        "label": filename,
        "functions": functions,
        "static_literal_xmpu_register_address_counts_by_port": by_port,
        "static_literal_xmpu_register_addresses_identified": sum(by_port.values()),
        "ddr_xmpu_mentions_total": len(re.findall(
            r"DDR_XMPU", source, re.IGNORECASE)),
        "psu_protection_named_references": len(re.findall(
            r"\bpsu_protection\b", source)),
        "active_boot_registers_programmed_or_readback": False,
        "effective_master_permissions_or_lock_state_proven": False,
    }


def xsa_source_match(xsa: Path, expected_sha: str) -> dict:
    observed_sha = prior.stream_sha(xsa, max_bytes=2 * 1024 * 1024 * 1024)
    require(observed_sha == prior.ACCEPTED_P03_XSA_SHA,
            "original accepted XSA SHA changed")
    try:
        with zipfile.ZipFile(xsa) as archive:
            names = [name for name in archive.namelist()
                     if name == "psu_init.c" and not name.startswith("/")]
            require(len(names) == 1, "XSA must include exactly one root psu_init.c")
            info = archive.getinfo(names[0])
            require(0 < info.file_size < prior.MAX_SELECTED_MEMBER,
                    "embedded PS init C source oversize")
            raw = archive.read(info)
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise ProtectionSourceNoGo("original XSA ZIP member invalid") from exc
    require(prior.sha_bytes(raw) == expected_sha,
            "provided Vivado-generated PS init differs from original XSA")
    return {"original_xsa_sha256": observed_sha,
            "embedded_generated_psu_init_sha256": prior.sha_bytes(raw),
            "standalone_psu_init_matches_XSA_exactly": True,
            "psu_init_is_proven_active_boot_firmware": False}


def audit(*, prior_report: Path, handoff: Path, hw_header: Path,
          psu_init: Path, xsa: Path, out: Path) -> dict:
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not out.resolve().is_relative_to(ROOT),
            "fresh external no-overwrite PC-only report path required")
    digest, _ = prior.hash_file(prior_report, max_bytes=prior.MAX_SOURCE)
    require(digest == ACCEPTED_INVENTORY_SHA,
            "operator accepted B4.5.4.3 source report SHA drift")
    previous = pair.load_json(prior_report)
    require(previous.get("schema") == prior.SCHEMA and
            previous.get("decision") ==
            "READ_ONLY_SOURCE_INVENTORY_PASS_ACTIVE_BOOT_AND_PROTECTION_NOT_PROVEN" and
            previous.get("local_handoff_source_order_if_supplied") ==
            "PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK" and
            previous.get("active_fsbl_linkage_proven", False) is False and
            previous.get("real_xmpu_registers_written") is False and
            previous.get("physical_execution_authorized") is False and
            previous.get("current_boot_image_provenance_independently_established") is False,
            "original accepted source inventory misrepresents active hardware")
    original = previous.get("optional_source_files")
    require(type(original) is list and len(original) >= 3,
            "original accepted source paths missing")
    expected = {"fsbl_handoff": HANDOFF_SHA, "fsbl_hooks": HOOKS_SHA,
                "psu_init": P03_PSU_INIT_SHA}
    for row in original:
        if row.get("role") in expected:
            require(row.get("sha256") == expected[row["role"]] and
                    row.get("supplied") is True,
                    "original operator source role SHA no longer matches "
                    + str(row.get("role")))
    require(previous.get("accepted_p03_original_xsa", {}).get("sha256")
            == prior.ACCEPTED_P03_XSA_SHA,
            "operator XSA fingerprint mismatch")
    h_text = safe_source(handoff, HANDOFF_SHA, "local Vitis xfsbl_handoff.c")
    g_text = safe_source(psu_init, P03_PSU_INIT_SHA, "original P03 psu_init.c")
    header_text = safe_source(hw_header, None, "local Vitis xfsbl_hw.h")
    xsa_link = xsa_source_match(xsa, P03_PSU_INIT_SHA)
    order = prior.handoff_order(h_text)
    require(order["observed_call_order"] ==
            "PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK",
            "expected actual local FSBL protection-then-handoff source order drifted")
    owner.source_contract()
    bs = protection_branches(h_text)
    header = header_default_condition(header_text)
    generated = generated_psu_summary(g_text, filename="original_XSA_psu_init.c")
    result = {
        "schema": SCHEMA,
        "accepted_operator_B4543_report_sha256": ACCEPTED_INVENTORY_SHA,
        "local_fsbl_handoff_sha256": HANDOFF_SHA,
        "installed_xfsbl_hw_header_sha256": pair.hex_sha(hw_header.read_bytes()),
        "original_generated_psu_init_sha256": P03_PSU_INIT_SHA,
        "xsa_to_original_psu_init_source_provenance": xsa_link,
        "installed_fsbl_call_order": order["observed_call_order"],
        "fsbl_protection_branch_cases": bs,
        "fsbl_hw_header_compile_time_bypass": header,
        "original_xsa_generated_psu_functions_and_literals": generated,
        "observed_source_only_no_live_register_capture": True,
        "BOOT_BIN_and_current_actual_fsbl_identity_proven": False,
        "FSBL_PROT_BYPASS_EXCLUDE_enabled_in_active_build_proven": False,
        "generated_psu_protection_lock_executed_in_real_boot_proven": False,
        "actual_R5_A53_PL_DDR_XMPU_port_master_ids_proven": False,
        "backup_13p5MiB_plus_extra_halfMiB_ownership_proven": False,
        "backup_immutable_after_boot_proven": False,
        "original_A53_guard_enabled": False,
        "new_A53_ELFs_or_FSBL_built": False,
        "recovery_media_and_boot_partition_proven": False,
        "JTAG_DDR_register_or_boot_media_access": False,
        "physical_KV260_inference_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "decision": "FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO",
        "research_sources": [AMD_2025_2_HW_HEADER, AMD_2025_2_HANDOFF,
            "https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Program-the-DDR-XMPUs"],
    }
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-report", type=Path, required=True)
    p.add_argument("--fsbl-handoff", type=Path, required=True)
    p.add_argument("--fsbl-hw-header", type=Path, required=True)
    p.add_argument("--psu-init", type=Path, required=True)
    p.add_argument("--xsa", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    try:
        r = audit(prior_report=a.prior_report,
                  handoff=a.fsbl_handoff,
                  hw_header=a.fsbl_hw_header,
                  psu_init=a.psu_init,
                  xsa=a.xsa, out=a.out)
    except (ProtectionSourceNoGo, prior.InventoryNoGo, pair.PairElfNoGo,
            OSError, KeyError, TypeError, ValueError) as exc:
        print("P08_B4544_HOST_FSBL_PROTECTION_SOURCE_NO_GO=" + str(exc),
              file=sys.stderr)
        return 3
    print("P08_B4544_ACTUAL_LOCAL_FSBL_TWO_BRANCHES_PARSED=1")
    print("P08_B4544_VITIS_HEADER_DEFAULT_PROTECTION_BYPASS=1")
    print("P08_B4544_XSA_TO_GENERATED_PSU_INIT_EXACT_SHA_MATCH=1")
    print("P08_B4544_REAL_FSBL_BUILD_COMPILE_FLAGS_PROVEN=0")
    print("P08_B4544_REAL_DDR_XMPU_PERMISSIONS_PROVEN=0")
    print("P08_B4544_BOARD_JTAG_BOOT_DDR_WRITES_AUTHORIZED=0")
    print("P08_B4544_SOURCE_REVIEW_REPORT=" + str(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
