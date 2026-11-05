#!/usr/bin/env python3
"""P08-B4.5.4.3 PC-only audit of original XSA and OPTIONAL local FSBL sources.

This is a FILE PROVENANCE / SOURCE ORDER scanner, not a hardware access
or active BOOT.BIN attestation. Does not generate code, extract archive
files, mutate originals, read hardware, or authorize execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

import p08_b45_pair_elf_evidence as pair

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = "p08-b4543-fsbl-xsa-source-inventory-host-only-v1"
ACCEPTED_POLICY_REPORT_SHA = "ba89166f826425bcd69c86ee7b249f70cd39f359382fa69bd331a366678899f2"
ACCEPTED_P03_XSA_SHA = "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
ACCEPTED_CANDIDATE_SHA = "7f78e7582e7fee12a06d83f14e45f1de1faf877ce1429af441dd83db3e851d2a"
MAX_SOURCE = 8 * 1024 * 1024
MAX_ELF = 64 * 1024 * 1024
MAX_ARCHIVE_MEMBERS = 50000
MAX_SELECTED_MEMBER = 2 * 1024 * 1024
MAX_SELECTED_TOTAL = 12 * 1024 * 1024
SOURCE_MARKERS = (
    "XFsbl_ProtectionConfig", "XFsbl_HookBeforeHandoff",
    "XFsbl_HookPsuInit", "psu_protection", "psu_init",
    "XMPU", "XPPU", "DDR_XMPU", "FSBL_PROT_BYPASS",
)
ARCHIVE_RELEVANT = re.compile(
    r"(?:^|/)(?:psu_(?:init|protection)[^/]*|xfsbl_[^/]*|"
    r"[^/]*(?:xmpu|xppu)[^/]*|[^/]*\.hwh|[^/]*\.bif)$",
    re.IGNORECASE,
)
AMD_HOOK_SOURCE_URL = (
    "https://github.com/Xilinx/embeddedsw/blob/master/"
    "lib/sw_apps/zynqmp_fsbl/src/xfsbl_handoff.c"
)


class InventoryNoGo(ValueError):
    pass


def require(allowed: bool, reason: str) -> None:
    if not allowed:
        raise InventoryNoGo("NO-GO: " + reason)


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path, *, max_bytes: int) -> tuple[str, bytes]:
    require(path.is_absolute() and path.is_file() and not path.is_symlink(),
            "file must be absolute and regular, not symlink: " + str(path))
    require(0 < path.stat().st_size <= max_bytes,
            "file size exceeds read-only bound or empty: " + str(path))
    data = path.read_bytes()
    require(len(data) == path.stat().st_size,
            "file changed during original SHA read: " + str(path))
    return sha_bytes(data), data


def remove_c_comments(data: str) -> str:
    """Parser used ONLY for source-call ordering, not C compilation."""
    data = re.sub(r"/\*.*?\*/", " ", data, flags=re.DOTALL)
    return re.sub(r"//[^\n]*", " ", data)


def handoff_order(source: str) -> dict:
    clean = remove_c_comments(source)
    # Extract the C function body, not prototypes or remarks anywhere else.
    pattern = re.compile(r"\bXFsbl_Handoff\s*\([^;{}]*\)\s*\{", re.DOTALL)
    functions = list(pattern.finditer(clean))
    if len(functions) != 1:
        return {"source_handoff_function_found": len(functions) == 1,
                "observed_call_order": "UNKNOWN",
                "protection_before_hook_in_this_file": False,
                "hook_before_protection_in_this_file": False}
    start = functions[0].end() - 1
    depth = 0
    end = len(clean)
    for i in range(start, len(clean)):
        if clean[i] == "{":
            depth += 1
        elif clean[i] == "}":
            depth -= 1
            if depth == 0:
                end = i + 1
                break
    require(depth == 0, "unclosed FSBL handoff function body")
    body = clean[start:end]
    # Allow one occurrence of each inside actual function; ambiguous
    # conditional/double call sequences cannot be trusted from regex.
    p = list(re.finditer(r"\bXFsbl_ProtectionConfig\s*\(", body))
    h = list(re.finditer(r"\bXFsbl_HookBeforeHandoff\s*\(", body))
    if len(p) != 1 or len(h) != 1:
        order = "UNKNOWN"
    else:
        order = ("PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK"
                 if p[0].start() < h[0].start() else
                 "HOOK_CALLED_BEFORE_PROTECTION_CONFIG")
    return {
        "source_handoff_function_found": True,
        "observed_call_order": order,
        "protection_before_hook_in_this_file":
            order == "PROTECTION_CONFIG_CALLED_BEFORE_BEFOREHANDOFF_HOOK",
        "hook_before_protection_in_this_file":
            order == "HOOK_CALLED_BEFORE_PROTECTION_CONFIG",
    }


def tokens(text: str) -> dict:
    return {name: len(re.findall(re.escape(name), text, re.IGNORECASE))
            for name in SOURCE_MARKERS}


def examine_source(path: Path | None, *, role: str) -> dict:
    if path is None:
        return {"role": role, "supplied": False,
                "active_board_fsbl_or_boot_image_proven": False,
                "call_order": "NOT_SUPPLIED"}
    digest, raw = hash_file(path, max_bytes=MAX_SOURCE)
    require(b"\0" not in raw, "text source contains NUL: " + role)
    text = raw.decode("utf-8", errors="replace")
    record = {"role": role, "supplied": True, "path": str(path),
              "sha256": digest, "bytes": len(raw),
              "marker_counts": tokens(text),
              "active_board_fsbl_or_boot_image_proven": False,
              "evidence_level": "LOCAL_FILE_ONLY_NOT_MATCHED_TO_BOOT_MEDIA"}
    if role == "fsbl_handoff":
        record.update(handoff_order(text))
    elif role == "boot_bif":
        record["observed_bif_text_flags_only"] = {
            "bootloader_attribute_seen": bool(re.search(
                r"\bbootloader\b", text, re.IGNORECASE)),
            "load_to_0x43000000_seen": bool(re.search(
                r"\bload\s*=\s*0x43000000\b", text, re.IGNORECASE)),
            "early_handoff_mentioned": bool(re.search(
                r"early.?handoff", text, re.IGNORECASE)),
            "authentication_attribute_seen": bool(re.search(
                r"\bauthentication\s*=", text, re.IGNORECASE)),
            "bif_is_proven_active": False,
        }
    return record


def examine_archive(xsa: Path) -> dict:
    digest, _ = hash_file(xsa, max_bytes=2 * 1024 * 1024 * 1024)
    require(digest == ACCEPTED_P03_XSA_SHA,
            "wrong original accepted routed P03 XSA bytes")
    try:
        with zipfile.ZipFile(xsa) as zf:
            all_members = zf.infolist()
            require(len(all_members) <= MAX_ARCHIVE_MEMBERS,
                    "unexpected huge XSA entry count")
            inspected = []
            total = 0
            for info in all_members:
                if not ARCHIVE_RELEVANT.search(info.filename):
                    continue
                if info.is_dir():
                    continue
                require(not info.filename.startswith("/") and
                        ".." not in Path(info.filename).parts and
                        "\\" not in info.filename,
                        "unsafe XSA member path (never extracted)")
                if info.file_size > MAX_SELECTED_MEMBER or (
                    total + info.file_size > MAX_SELECTED_TOTAL
                ):
                    inspected.append({
                        "member": info.filename, "bytes": info.file_size,
                        "sha256": None,
                        "status": "SKIPPED_OVERSIZE_NO_DECOMPRESSION",
                        "active_boot_image_identity_proven": False,
                    })
                    continue
                total += info.file_size
                raw = zf.read(info)
                require(len(raw) == info.file_size,
                        "XSA member length/CRC check failed")
                name = info.filename
                is_text = (b"\0" not in raw and
                           bool(re.search(r"\.(c|h|tcl|bif|txt|xml|hwh)$",
                                          name, re.IGNORECASE)))
                inspected.append({
                    "member": name, "bytes": len(raw),
                    "sha256": sha_bytes(raw),
                    "source_markers_if_text":
                        tokens(raw.decode("utf-8", errors="replace"))
                        if is_text else {},
                    "active_boot_image_identity_proven": False,
                })
    except (zipfile.BadZipFile, RuntimeError, EOFError) as exc:
        raise InventoryNoGo("accepted original XSA archive cannot be scanned") from exc
    return {"path": str(xsa), "sha256": digest,
            "type": "READ_ONLY_SIGNED_XSA_ZIP_METADATA_AND_BOUNDED_MEMBERS",
            "inspected_relevant_members": inspected,
            "count_relevant_members": len(inspected),
            "xsa_is_not_proof_of_active_boot_image": True,
            "active_fsbl_linkage_proven": False}


def audit(*, policy_report: Path, xsa: Path, out: Path,
          handoff: Path | None = None, hooks: Path | None = None,
          psu_init: Path | None = None, psu_protection: Path | None = None,
          boot_bif: Path | None = None, fsbl_elf: Path | None = None) -> dict:
    require(out.is_absolute() and out.parent.is_dir() and
            not out.exists() and not out.is_symlink() and
            not out.resolve().is_relative_to(ROOT),
            "new external PC-only no-overwrite JSON result required")
    original_sha, _ = hash_file(policy_report, max_bytes=MAX_SOURCE)
    require(original_sha == ACCEPTED_POLICY_REPORT_SHA,
            "original accepted B4.5.4.2 policy report SHA drift")
    report = pair.load_json(policy_report)
    require(report.get("schema") ==
            "p08-b4542-host-only-symbolic-xmpu-boot-policy-audit-v1" and
            report.get("candidate_file_sha256") == ACCEPTED_CANDIDATE_SHA and
            report.get("symbolic_transactions_tested") == 147456 and
            report.get("candidate_real_readers_authorized") is False and
            report.get("real_register_values_and_priority_readback_proven") is False and
            report.get("physical_KV260_contact") is False and
            report.get("physical_execution_authorized") is False,
            "previous accepted B4.5.4.2 policy report is not a physical NO-GO")
    archive = examine_archive(xsa)
    sources = [
        examine_source(handoff, role="fsbl_handoff"),
        examine_source(hooks, role="fsbl_hooks"),
        examine_source(psu_init, role="psu_init"),
        examine_source(psu_protection, role="psu_protection"),
        examine_source(boot_bif, role="boot_bif"),
    ]
    elf = {"supplied": False, "active_board_fsbl_proven": False}
    if fsbl_elf is not None:
        sha, raw = hash_file(fsbl_elf, max_bytes=MAX_ELF)
        require(raw.startswith(b"\x7fELF"), "optional FSBL executable is not ELF")
        elf = {"supplied": True, "path": str(fsbl_elf),
               "bytes": len(raw), "sha256": sha,
               "active_board_fsbl_proven": False,
               "source_to_executable_build_proven": False}
    hand = sources[0]
    data = {
        "schema": SCHEMA,
        "accepted_b4542_operator_policy_sha256": ACCEPTED_POLICY_REPORT_SHA,
        "accepted_p03_original_xsa": archive,
        "optional_source_files": sources,
        "optional_fsbl_elf": elf,
        "published_AMD_source_call_order":
            "XFsbl_ProtectionConfig BEFORE XFsbl_HookBeforeHandoff",
        "published_upstream_source_url": AMD_HOOK_SOURCE_URL,
        "local_handoff_source_order_if_supplied":
            hand.get("observed_call_order", "NOT_SUPPLIED"),
        "beforehandoff_hook_approved_for_secure_xmpu_reprogramming": False,
        "read_only_FSBL_and_Vivado_XSA_inventory_completed": True,
        "source_files_matched_to_actual_KV260_boot_image": False,
        "current_boot_image_provenance_independently_established": False,
        "true_protection_config_lock_timing_verified_on_active_boot": False,
        "source_ddr_xmpu_register_regions_readback_verified": False,
        "effective_per_port_AXI_reader_master_IDs_verified": False,
        "existing_region_slots_14_15_free_proven": False,
        "backup_extra_512KiB_exclusively_owned_proven": False,
        "trustworthy_FSBL_partition_load_before_lock_verified": False,
        "verified_nonsecure_A53_continuous_RO_attestation": False,
        "real_xmpu_registers_written": False,
        "board_contact": False,
        "physical_execution_authorized": False,
        "official_MNIST_TEST": "SEALED_NOT_ACCESSED",
        "decision": "READ_ONLY_SOURCE_INVENTORY_PASS_ACTIVE_BOOT_AND_PROTECTION_NOT_PROVEN",
    }
    with out.open("x", encoding="utf-8") as fd:
        json.dump(data, fd, indent=2, sort_keys=True)
        fd.write("\n")
    return data


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--policy-report", type=Path, required=True)
    p.add_argument("--xsa", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    for opt in ("fsbl-handoff", "fsbl-hooks", "psu-init",
                "psu-protection", "boot-bif", "fsbl-elf"):
        p.add_argument("--" + opt, type=Path)
    args = p.parse_args()
    try:
        result = audit(
            policy_report=args.policy_report, xsa=args.xsa, out=args.out,
            handoff=args.fsbl_handoff, hooks=args.fsbl_hooks,
            psu_init=args.psu_init, psu_protection=args.psu_protection,
            boot_bif=args.boot_bif, fsbl_elf=args.fsbl_elf,
        )
    except (InventoryNoGo, pair.PairElfNoGo, KeyError, TypeError,
            OSError, ValueError) as exc:
        print("P08_B4543_HOST_ONLY_INVENTORY_NO_GO=" + str(exc),
              file=sys.stderr)
        return 3
    print("P08_B4543_ACCEPTED_XSA_PC_ONLY_SOURCE_INVENTORY_PASS=1")
    print("P08_B4543_LOCAL_FSBL_HANDOFF_ORDER=" +
          result["local_handoff_source_order_if_supplied"])
    print("P08_B4543_ACTIVE_KV260_BOOT_FSBL_PROVEN=0")
    print("P08_B4543_PROTECTION_CONFIG_AND_MASTER_IDS_PROVEN=0")
    print("P08_B4543_FSBL_HOOK_APPROVED_FOR_XMPU_CHANGES=0")
    print("P08_B4543_KV260_BOARD_CONTACT=0")
    print("P08_B4543_BOARD_JTAG_DDR_EXECUTION_AUTHORIZED=0")
    print("P08_B4543_PC_ONLY_BOOT_SOURCE_REPORT=" + str(args.out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
