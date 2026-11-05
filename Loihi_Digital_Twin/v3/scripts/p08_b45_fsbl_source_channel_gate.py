#!/usr/bin/env python3
"""P08-B4.5 continuation: source-only FSBL(C) vs debugger(Tcl) protection audit.

Read-only original XSA/PSU sources and existing local build-artifact candidates.
No preprocessing, Tcl execution, Vitis, XSDB, MMIO, JTAG or board access.
This is a diagnostic/physical-readiness NO-GO, not XMPU provisioning.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys

import p08_b4545_generated_psu_graph as previous

SCHEMA = "p08-b45-source-channel-split-and-boot-candidate-pc-only-v1"
ACCEPTED_B4545_REPORT_SHA = (
    "2d6f9e079b3bf9845ebd07d69b2de4611b90dc821341b0c9ada6458b2daa74a0"
)
ORIGINAL_PSU_C_SHA = (
    "049ae8a025fab04526218d351b74d06313f7f163633dfcfde2cb5579e22b8679"
)
DDR_PORTS = {
    "0": ("0xfd000000", "RPU"),
    "1": ("0xfd010000", "CCI/APU path A"),
    "2": ("0xfd020000", "CCI/APU path B"),
    "3": ("0xfd030000", "HP0_FPD/DisplayPort"),
    "4": ("0xfd040000", "HP1-2_FPD"),
    "5": ("0xfd050000", "HP3_FPD/FPD DMA"),
}
FUNC_NAMES = tuple(f"psu_ddr_xmpu{i}_data" for i in range(6))
MAX_REPORT = 8 * 1024 * 1024
MAX_ARTIFACT_INSPECT = 1024 * 1024

AMD_SOURCES = (
    "https://docs.amd.com/r/en-US/pg201-zynq-ultrascale-plus-processing-system/Output-Generation",
    "https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances",
    "https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/XMPU-Register-Set-Overview",
    "https://github.com/Xilinx/embeddedsw/blob/xlnx_rel_v2025.2/lib/sw_apps/zynqmp_fsbl/src/xfsbl_hw.h",
)


class PhysicalReadinessNoGo(ValueError):
    pass


def require(ok: bool, message: str) -> None:
    if not ok:
        raise PhysicalReadinessNoGo("NO-GO: " + message)


def _validate_previous(path: Path) -> dict:
    digest, raw = previous.inventory.hash_file(path, max_bytes=MAX_REPORT)
    require(digest == ACCEPTED_B4545_REPORT_SHA,
            "original operator B4.5.4.5 JSON SHA changed")
    record = json.loads(raw)
    require(type(record) is dict and record.get("schema") == previous.SCHEMA,
            "prior original source report schema mismatch")
    require(record.get("decision") ==
            "GENERATED_PSU_SOURCE_GRAPH_ONLY_ACTIVE_BOOT_AND_XMPU_NO_GO",
            "prior source-only NO-GO decision missing")
    for flag in ("physical_execution_authorized", "board_hardware_contact",
                 "hardware_register_or_ddr_writes", "active_boot_medium_proven",
                 "A53_read_only_backup_guard_enabled",
                 "candidate_FSBL_full_protection_safe_to_enable",
                 "actual_10_bit_AXI_master_IDs_proven"):
        require(record.get(flag) is False,
                "prior report has false physical-readiness claim: " + flag)
    require(record.get("official_MNIST_TEST") == "SEALED_NOT_ACCESSED",
            "official TEST source contract changed")
    require(record.get("immutable_backup_bytes") == 27 * 524288 and
            record.get("overprotected_adjacent_bytes") == 524288 and
            record.get("original_backup_range") == ["0x43000000", "0x43d80000"] and
            record.get("conservative_1mib_cover") == ["0x43000000", "0x43e00000"],
            "original backup/overcoverage contract drift")
    require(record.get("original_p03_xsa", {}).get("sha256") ==
            previous.inventory.ACCEPTED_P03_XSA_SHA,
            "accepted P03 XSA source fingerprint drift")
    require(record.get("original_generated_file_sha256", {}).get("psu_init.c") ==
            ORIGINAL_PSU_C_SHA, "original P03 C SHA mismatch")
    source = record.get("source_call_graph_and_symbolic_register_inventory")
    require(type(source) is dict and source.get("roots") ==
            ["psu_protection", "psu_protection_lock"],
            "accepted C graph root mismatch")
    require(source.get("full_preprocessor_and_linked_compiler_call_graph_proven") is False and
            source.get("region_slot_priority_mask_register_semantics_proven") is False and
            source.get("generated_security_policy_safe_to_enable") is False,
            "prior source falsely claims effective protection")
    require(type(source.get("reachable_function_dependencies")) is dict,
            "accepted C call graph dependencies missing")
    return record


def source_channel_matrix(c: str, h: str, t: str, old_graph: dict) -> dict:
    """Binds exact original C source to prior graph. Never interprets Tcl as FSBL."""
    functions = previous.function_definitions(c)
    require(all(name in functions for name in
                ("psu_protection", "psu_protection_lock",
                 "psu_protection_lock_data", *FUNC_NAMES)),
            "missing genuine original DDR XMPU or protection lock function")
    reconstructed = previous.graph_report(c, h, t)
    require(reconstructed["reachable_function_dependencies"] ==
            old_graph["reachable_function_dependencies"] and
            reconstructed["reachable_source_functions"] ==
            old_graph["reachable_source_functions"] and
            reconstructed["literal_ddr_xmpu_sites_by_port"] ==
            old_graph["literal_ddr_xmpu_sites_by_port"],
            "real generated C does not match the original accepted C graph")
    rows = []
    for i, name in enumerate(FUNC_NAMES):
        body = functions[name]
        calls = sorted(set(previous.CALL_RE.findall(body)) -
                       previous.IGNORED_CALLS)
        # These tokens are a diagnostic: C macros, conditional compilation
        # and linked objects are NOT evaluated by this script.
        obvious_writes = len(re.findall(
            r"\b(?:PSU_Mask_Write|psu_mask_write|Xil_Out32|"
            r"EMIT_MASKWRITE|XMPU_REG_WRITE)\s*\(", body))
        assignment_candidate = bool(re.search(
            r"\*\s*(?:\([^;]*\))?\s*[A-Za-z_]\w*\s*=", body))
        token = re.compile(r"\b" + re.escape(name) + r"\b")
        lines = [line for line in t.splitlines() if token.search(line)]
        proc_seen = bool(re.search(r"(?m)^\s*proc\s+" +
                                  re.escape(name) + r"\b", t))
        rows.append({
            "port": i,
            "amd_control_register_base": DDR_PORTS[str(i)][0],
            "amd_documented_port_masters_category": DDR_PORTS[str(i)][1],
            "c_function": name,
            "c_body_source_bytes": len(body.encode()),
            "c_obvious_write_calls": obvious_writes,
            "c_named_calls_not_compiled": calls[:64],
            "c_pointer_assignment_heuristic": assignment_candidate,
            "c_has_no_obvious_write_call_or_named_callee":
                obvious_writes == 0 and not calls and not assignment_candidate,
            "tcl_symbol_reference_lines": len(lines),
            "tcl_proc_declaration_seen": proc_seen,
            "tcl_symbol_only_not_FSBL_execution": True,
            "actual_XMPU_writes_in_live_boot_proven": False,
            "effective_region_permissions_verified": False,
            "real_axi_master_ID_verified": False,
        })
    lock_body = functions["psu_protection_lock_data"]
    lock_calls = sorted(set(previous.CALL_RE.findall(lock_body)) -
                        previous.IGNORED_CALLS)
    return {
        "generated_C_used_for_FSBL_source_path": True,
        "generated_Tcl_used_for_XSDB_source_path": True,
        "tcl_is_not_automatically_executed_by_FSBL": True,
        "source_only_C_DDR_helpers": rows,
        "generated_C_lock_data": {
            "body_source_bytes": len(lock_body.encode()),
            "named_calls_not_compiled": lock_calls,
            "direct_obvious_write_calls": len(re.findall(
                r"\b(?:PSU_Mask_Write|psu_mask_write|Xil_Out32|"
                r"EMIT_MASKWRITE|XMPU_REG_WRITE)\s*\(", lock_body)),
            "lock_has_actually_been_applied": False,
        },
        "C_graph_recomputed_from_same_original_bytes": True,
        "tcl_subroutines_are_not_boot_permission_evidence": True,
        "C_macro_expansion_and_linking_proven": False,
        "effective_C_write_or_protection_execution_proven": False,
    }


def boot_artifacts(paths: list[Path]) -> list[dict]:
    rows = previous.artifact_inventory(paths)
    for row in rows:
        path = Path(row["path"])
        kind = path.suffix.lower()
        evidence = {
            "source_file_contains_build_protection_exclude_macro": False,
            "source_file_contains_bootloader_partition_keyword": False,
            "source_to_binary_compilation_reproduced": False,
            "running_board_used_this_boot_artifact": False,
        }
        if kind in (".bif", ".map", ".json", ".txt", ".log", ".rsp", ".cmd") and \
                row["bytes"] <= MAX_ARTIFACT_INSPECT:
            raw = path.read_bytes()
            require(len(raw) == row["bytes"] and
                    previous.sha(raw) == row["sha256"],
                    "optional boot-source candidate modified while reading")
            text = raw.decode("utf-8", "replace")
            evidence.update({
                "source_file_contains_build_protection_exclude_macro":
                    "FSBL_PROT_BYPASS_EXCLUDE" in text,
                "source_file_contains_bootloader_partition_keyword":
                    bool(re.search(r"\bbootloader\b", text, re.I)),
            })
        row.update({"read_only_source_indicators": evidence,
                    "artifact_presence_does_not_establish_boot_provenance": True})
    return rows


def audit(*, original_report: Path, original_xsa: Path, psu_c: Path,
          psu_h: Path, psu_tcl: Path, out: Path,
          artifacts: list[Path] | None = None) -> dict:
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not out.resolve().is_relative_to(previous.ROOT),
            "new, external no-overwrite report path required")
    accepted = _validate_previous(original_report)
    members, archive = previous.read_xsa_members(original_xsa)
    require(archive["sha256"] == accepted["original_p03_xsa"]["sha256"],
            "original accepted XSA SHA mismatch")
    for name, raw in members.items():
        require(previous.sha(raw) ==
                accepted["original_generated_file_sha256"][name],
                "original generated XSA source SHA mismatch: " + name)
    c = previous.read_original_source(
        psu_c, members["psu_init.c"], "psu_init.c",
        expected_sha=ORIGINAL_PSU_C_SHA)
    h = previous.read_original_source(
        psu_h, members["psu_init.h"], "psu_init.h")
    t = previous.read_original_source(
        psu_tcl, members["psu_init.tcl"], "psu_init.tcl")
    channels = source_channel_matrix(
        c, h, t, accepted["source_call_graph_and_symbolic_register_inventory"])
    candidates = boot_artifacts(artifacts or [])
    result = {
        "schema": SCHEMA,
        "accepted_operator_b4545_source_report_sha256": ACCEPTED_B4545_REPORT_SHA,
        "original_xsa_sha256": archive["sha256"],
        "original_generated_file_sha256":
            {k: previous.sha(v) for k, v in members.items()},
        "source_channel_separation": channels,
        "optional_host_existing_boot_candidates": candidates,
        "source_C_Tcl_paths_not_equivalent": True,
        "current_KV260_boot_medium_FSBL_ELF_and_build_flags_verified": False,
        "original_all_27_backup_records_trusted_staged_before_lock": False,
        "original_13p5MiB_backup_and_512KiB_overcoverage_owner_proven": False,
        "all_six_DDR_XMPU_port_lock_priority_ID_and_RW_readbacks_verified": False,
        "secure_boot_configuration_safe_to_enable": False,
        "trusted_continuing_A53_guard_proven": False,
        "real_board_access_performed": False,
        "physical_16_or_1024_image_session_authorized": False,
        "hardware_or_boot_media_writes_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "decision": "SOURCE_C_TCL_PATHS_RECONCILED_PHYSICAL_PROTECTION_NO_GO",
        "vendor_references": AMD_SOURCES,
    }
    with out.open("x", encoding="utf-8") as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write("\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--original-report", type=Path, required=True)
    parser.add_argument("--original-xsa", type=Path, required=True)
    parser.add_argument("--psu-c", type=Path, required=True)
    parser.add_argument("--psu-h", type=Path, required=True)
    parser.add_argument("--psu-tcl", type=Path, required=True)
    parser.add_argument("--artifact", type=Path, action="append", default=[])
    parser.add_argument("--out", type=Path, required=True)
    a = parser.parse_args()
    try:
        r = audit(original_report=a.original_report, original_xsa=a.original_xsa,
                  psu_c=a.psu_c, psu_h=a.psu_h, psu_tcl=a.psu_tcl,
                  artifacts=a.artifact, out=a.out)
    except (PhysicalReadinessNoGo, previous.GeneratedSourceNoGo,
            previous.inventory.InventoryNoGo, OSError, KeyError,
            TypeError, ValueError) as exc:
        print("P08_B45_FSBL_SOURCE_CHANNEL_PRECHECK_NO_GO=" + str(exc),
              file=sys.stderr)
        return 3
    print("P08_B45_ORIGINAL_C_H_TCL_AND_PREVIOUS_REPORT_MATCH=1")
    print("P08_B45_FSBL_C_VS_XSDB_TCL_CHANNELS_INVENTORIED=1")
    print("P08_B45_GENERATED_C_DDR_PORTS_RECONCILED=6")
    print("P08_B45_ACTIVE_BOOT_FSBL_PROTECTION_PROVEN=0")
    print("P08_B45_BOARD_OR_BOOT_MEDIA_WRITES_AUTHORIZED=0")
    print("P08_B45_REPORT=" + str(a.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
