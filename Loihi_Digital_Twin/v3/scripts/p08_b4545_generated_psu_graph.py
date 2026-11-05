#!/usr/bin/env python3
"""B4.5.4.5: bounded, read-only P03 generated-PSU source dependency audit.

Source graph and candidate register references are NOT a C preprocessor,
compiled FSBL attestation, XMPU register readback, or physical permission.
Never runs a tool, touches devices, extracts XSA contents, or edits inputs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import p08_b4543_fsbl_boot_source_inventory as inventory
import p08_b4544_fsbl_protection_path as previous
import p08_b45_pair_elf_evidence as pair

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "p08-b4545-original-psu-generated-source-graph-pc-only-v1"
ACCEPTED_PREVIOUS_SHA = "e2c40e2c58a1a58d4c5611be7f95a58671b2c9e172a236323915dcb7368961a9"
EXPECTED_PSU_C_SHA = previous.P03_PSU_INIT_SHA
MAX_XSA = 2 * 1024 * 1024 * 1024
MAX_ARTIFACT = 512 * 1024 * 1024
MAX_MEMBER = 4 * 1024 * 1024
MAX_MEMBERS = 50000
MAX_BOOT_ARTIFACTS = 12
MAX_CALL_DEPTH = 24
INPUT_MEMBERS = ("psu_init.c", "psu_init.h", "psu_init.tcl")
CALL_RE = re.compile(r"\b([A-Za-z_]\w*)\s*\(")
HEX_RE = re.compile(r"\b0[xX][0-9a-fA-F]{6,8}\b")
WRITE_RE = re.compile(r"\b(psu_(?:mask_write|mask_poll)|Xil_Out32)\s*\(([^;]*?)\)\s*;", re.DOTALL)
IGNORED_CALLS = frozenset(("if", "for", "while", "switch", "return",
                           "sizeof", "defined", "do", "else"))
BOOT_EXTENSIONS = frozenset((".bin", ".bif", ".elf", ".map", ".json",
                             ".txt", ".log", ".rsp", ".cmd"))


class GeneratedSourceNoGo(ValueError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise GeneratedSourceNoGo("NO-GO: " + message)


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def read_xsa_members(path: Path) -> tuple[dict, dict]:
    digest = inventory.stream_sha(path, max_bytes=MAX_XSA)
    require(digest == inventory.ACCEPTED_P03_XSA_SHA,
            "original frozen P03 XSA hash differs")
    result = {}
    descriptors = []
    try:
        with zipfile.ZipFile(path) as z:
            infos = z.infolist()
            require(len(infos) <= MAX_MEMBERS, "XSA archive too many members")
            for name in INPUT_MEMBERS:
                matched = [i for i in infos if i.filename == name and not i.is_dir()]
                require(len(matched) == 1,
                        "original XSA must contain exactly one root " + name)
                info = matched[0]
                require(0 < info.file_size <= MAX_MEMBER,
                        "XSA member oversized/empty: " + name)
                require(info.compress_size > 0 and
                        info.file_size <= max(1000 * info.compress_size, 4096),
                        "XSA member decompression ratio invalid: " + name)
                result[name] = z.read(info)
                require(len(result[name]) == info.file_size,
                        "XSA member length drift: " + name)
            hwh = [i for i in infos if i.filename.lower().endswith(".hwh")
                   and not i.is_dir()]
            require(len(hwh) > 0, "original XSA has no HWH descriptor")
            for info in hwh:
                require(0 < info.file_size <= MAX_MEMBER,
                        "HWH member oversized/empty")
                raw = z.read(info)
                require(len(raw) == info.file_size, "HWH length mismatch")
                txt = raw.decode("utf-8", "replace")
                descriptors.append({
                    "member": info.filename, "bytes": info.file_size,
                    "sha256": sha(raw),
                    "xmpu_mentions": len(re.findall("XMPU", txt, re.I)),
                    "ps_axi_interface_mentions": len(
                        re.findall(r"\b(?:M_AXI|S_AXI|AXI_HP|AXI_HPC|AXI_ACP)\b", txt, re.I)),
                    "runtime_master_id_verified": False,
                })
    except (zipfile.BadZipFile, RuntimeError, EOFError, UnicodeError) as e:
        raise GeneratedSourceNoGo("invalid original XSA source archive") from e
    return result, {"sha256": digest, "hwh_descriptors": descriptors}


def read_original_source(path: Path, expected_raw: bytes, label: str,
                         *, expected_sha: str | None = None) -> str:
    dig, raw = inventory.hash_file(path, max_bytes=MAX_MEMBER)
    require(raw == expected_raw, label + " differs from exact original XSA")
    if expected_sha is not None:
        require(dig == expected_sha, label + " differs from frozen SHA pin")
    require(b"\x00" not in raw, label + " contains NUL")
    return raw.decode("utf-8", "replace")


def function_definitions(source: str) -> dict[str, str]:
    """Limited balanced-brace C source index; ambiguous functions rejected."""
    cleaned = inventory.remove_c_comments(source)
    pattern = re.compile(
        r"\b([A-Za-z_]\w*)\s*\([^;{}]*\)\s*\{", re.DOTALL)
    funcs: dict[str, str] = {}
    for match in pattern.finditer(cleaned):
        name = match.group(1)
        if name in IGNORED_CALLS:
            continue
        depth = 0
        end = None
        for i in range(match.end() - 1, len(cleaned)):
            if cleaned[i] == "{":
                depth += 1
            elif cleaned[i] == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    break
        require(end is not None, "unbalanced C function body: " + name)
        require(name not in funcs, "duplicate/ambiguous C definition: " + name)
        funcs[name] = cleaned[match.end()-1:end]
    return funcs


def graph_report(c_source: str, h_source: str, tcl_source: str) -> dict:
    funcs = function_definitions(c_source)
    require("psu_protection" in funcs and "psu_protection_lock" in funcs,
            "original generated protection and lock C definitions required")
    roots = ("psu_protection", "psu_protection_lock")
    graph = {}
    for name, body in funcs.items():
        calls = sorted({v for v in CALL_RE.findall(body) if v not in IGNORED_CALLS})
        # Do not misclassify C intrinsics, macros or function pointers as
        # resolved dependencies: only named definitions in this actual file.
        graph[name] = {
            "defined_calls": [v for v in calls if v in funcs and v != name],
            "unresolved_or_external_calls": [v for v in calls if v not in funcs],
            "self_recursive": name in calls,
            "source_body_bytes": len(body.encode()),
        }
    reach = {}
    for root in roots:
        visited = set()
        pending = [(root, 0)]
        while pending:
            name, depth = pending.pop()
            require(depth <= MAX_CALL_DEPTH, "generated function chain too deep")
            if name in visited:
                continue
            visited.add(name)
            pending.extend((x, depth+1) for x in graph[name]["defined_calls"])
        reach[root] = sorted(visited)
    touched = sorted(set(reach[roots[0]]) | set(reach[roots[1]]))
    operations = []
    for fname in touched:
        for match in WRITE_RE.finditer(funcs[fname]):
            argument = match.group(2).split(",", 1)[0].strip()
            literal = re.fullmatch(r"(?:\(?\s*)?(0[xX][0-9a-fA-F]{6,8})(?:\s*\)?)", argument)
            address = int(literal.group(1), 16) if literal else None
            port = ((address - 0xFD000000) // 0x10000
                    if address is not None and
                    0xFD000000 <= address < 0xFD060000 else None)
            operations.append({
                "source_function": fname, "source_call": match.group(1),
                "address_expression": argument[:160],
                "literal_address": f"0x{address:08x}" if address is not None else None,
                "candidate_ddr_xmpu_port": port,
                "actual_effective_register_write_proven": False,
            })
    header_words = sorted(set(re.findall(
        r"\b[A-Za-z_]*XMPU[A-Za-z_0-9]*\b", h_source, re.I)))[:250]
    tcl_words = sorted(set(re.findall(
        r"\b[A-Za-z_]*XMPU[A-Za-z_0-9]*\b", tcl_source, re.I)))[:250]
    per_port = {str(i): sum(v["candidate_ddr_xmpu_port"] == i
                             for v in operations) for i in range(6)}
    unresolved = sorted({call for name in touched
                         for call in graph[name]["unresolved_or_external_calls"]})
    return {
        "source_definition_count": len(funcs),
        "roots": list(roots),
        "reachable_source_functions": reach,
        "reachable_function_dependencies": {k: graph[k] for k in touched},
        "unresolved_calls_include_macros_libc_or_external": unresolved,
        "candidate_register_call_sites": operations[:1000],
        "candidate_register_site_truncated": len(operations) > 1000,
        "literal_ddr_xmpu_sites_by_port": per_port,
        "header_xmpu_symbol_names": header_words,
        "tcl_xmpu_symbol_names": tcl_words,
        "tcl_protection_data_mentions": len(re.findall(
            r"\bpsu_protection_data\b", tcl_source)),
        "tcl_numeric_hex_literals": len(HEX_RE.findall(tcl_source)),
        "region_slot_priority_mask_register_semantics_proven": False,
        "full_preprocessor_and_linked_compiler_call_graph_proven": False,
        "generated_security_policy_safe_to_enable": False,
    }


def artifact_inventory(paths: list[Path]) -> list[dict]:
    require(len(paths) <= MAX_BOOT_ARTIFACTS,
            "too many optional boot artifact paths")
    require(len(set(paths)) == len(paths), "duplicate artifact path")
    entries = []
    for path in paths:
        require(path.suffix.lower() in BOOT_EXTENSIONS,
                "unsupported optional boot-artifact extension: " + str(path))
        dig = inventory.stream_sha(path, max_bytes=MAX_ARTIFACT)
        entries.append({
            "path": str(path), "bytes": path.stat().st_size, "sha256": dig,
            "artifact_kind_extension_only": path.suffix.lower(),
            "belongs_to_current_KV260_boot_medium_proven": False,
            "source_to_elf_compile_flags_proven": False,
            "active_fsbl_proven": False,
        })
    return entries


def audit(*, prior_report: Path, xsa: Path, psu_init: Path,
          psu_header: Path, psu_tcl: Path, out: Path,
          artifacts: list[Path] | None = None) -> dict:
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not out.resolve().is_relative_to(ROOT),
            "fresh external no-overwrite report path required")
    previous_sha, _ = inventory.hash_file(prior_report, max_bytes=inventory.MAX_SOURCE)
    require(previous_sha == ACCEPTED_PREVIOUS_SHA,
            "accepted operator B4.5.4.4 evidence SHA drift")
    prev = pair.load_json(prior_report)
    require(prev.get("schema") == previous.SCHEMA and
            prev.get("decision") ==
              "FSBL_SOURCE_BYPASS_PATH_IDENTIFIED_REAL_BOOT_AND_XMPU_NO_GO" and
            prev.get("BOOT_BIN_and_current_actual_fsbl_identity_proven") is False and
            prev.get("physical_KV260_inference_authorized") is False and
            prev.get("JTAG_DDR_register_or_boot_media_access") is False and
            prev.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
            "prior source evidence is not the original physical NO-GO")
    require(prev.get("original_generated_psu_init_sha256") == EXPECTED_PSU_C_SHA and
            prev.get("xsa_to_original_psu_init_source_provenance", {}).get(
                "original_xsa_sha256") == inventory.ACCEPTED_P03_XSA_SHA and
            prev.get("xsa_to_original_psu_init_source_provenance", {}).get(
                "standalone_psu_init_matches_XSA_exactly") is True,
            "original P03 pin/provenance drift")
    members, xsa_evidence = read_xsa_members(xsa)
    c = read_original_source(psu_init, members["psu_init.c"], "psu_init.c",
                             expected_sha=EXPECTED_PSU_C_SHA)
    h = read_original_source(psu_header, members["psu_init.h"], "psu_init.h")
    t = read_original_source(psu_tcl, members["psu_init.tcl"], "psu_init.tcl")
    graph = graph_report(c, h, t)
    candidates = artifact_inventory(artifacts or [])
    data = {
        "schema": SCHEMA,
        "prior_operator_b4544_report_sha256": ACCEPTED_PREVIOUS_SHA,
        "original_p03_xsa": xsa_evidence,
        "original_generated_file_sha256": {
            n: sha(raw) for n, raw in members.items()},
        "source_call_graph_and_symbolic_register_inventory": graph,
        "optional_existing_boot_artifacts": candidates,
        "immutable_backup_bytes": 27 * 524288,
        "original_backup_range": ["0x43000000", "0x43d80000"],
        "conservative_1mib_cover": ["0x43000000", "0x43e00000"],
        "overprotected_adjacent_bytes": 524288,
        "physical_owner_of_extra_half_mib_proven": False,
        "active_boot_medium_proven": False,
        "current_boot_bin_fsbl_elf_and_flags_bound_to_board": False,
        "actual_10_bit_AXI_master_IDs_proven": False,
        "all_six_live_XMPU_ports_and_region_priorities_readback": False,
        "prelock_authenticated_original_context_staging_proven": False,
        "A53_read_only_backup_guard_enabled": False,
        "candidate_FSBL_full_protection_safe_to_enable": False,
        "board_hardware_contact": False,
        "hardware_register_or_ddr_writes": False,
        "physical_execution_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "decision": "GENERATED_PSU_SOURCE_GRAPH_ONLY_ACTIVE_BOOT_AND_XMPU_NO_GO",
    }
    with out.open("x", encoding="utf-8") as file:
        json.dump(data, file, indent=2, sort_keys=True)
        file.write("\n")
    return data


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--prior-report", type=Path, required=True)
    p.add_argument("--xsa", type=Path, required=True)
    p.add_argument("--psu-init", type=Path, required=True)
    p.add_argument("--psu-header", type=Path, required=True)
    p.add_argument("--psu-tcl", type=Path, required=True)
    p.add_argument("--artifact", type=Path, action="append", default=[])
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    try:
        result = audit(prior_report=a.prior_report, xsa=a.xsa,
                       psu_init=a.psu_init, psu_header=a.psu_header,
                       psu_tcl=a.psu_tcl, artifacts=a.artifact, out=a.out)
    except (GeneratedSourceNoGo, inventory.InventoryNoGo,
            previous.ProtectionSourceNoGo, pair.PairElfNoGo,
            OSError, ValueError, KeyError, TypeError) as e:
        print("P08_B4545_PC_ONLY_GENERATED_SOURCE_NO_GO=" + str(e),
              file=sys.stderr)
        return 3
    print("P08_B4545_ORIGINAL_XSA_C_H_TCL_BYTE_IDENTITY_PASS=1")
    print("P08_B4545_GENERATED_PROTECTION_SOURCE_GRAPH_RECORDED=1")
    print("P08_B4545_ACTIVE_BOOT_PROVEN=0")
    print("P08_B4545_XMPU_DDR_OWNERSHIP_OR_MASTER_IDS_PROVEN=0")
    print("P08_B4545_BOARD_JTAG_DDR_BOOT_WRITES_AUTHORIZED=0")
    print("P08_B4545_REPORT=" + str(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
