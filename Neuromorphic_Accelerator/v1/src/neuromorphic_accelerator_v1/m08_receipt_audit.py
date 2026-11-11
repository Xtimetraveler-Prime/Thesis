"""M08.1 independent immutable capture SHA and scope-contract auditor.

An integrity-checked JSON is not proof of genuine KV260 hardware identity.
Never upgrade host-only or operator-text claims to valid physical DDR runs.
"""
from __future__ import annotations

import json
from pathlib import Path

from .m08_entry import SCHEMA, ARCHIVES, sha_file

HOST_COMMANDS = (
    "git rev-parse HEAD", "git status --porcelain=v1", "uname -a",
    "lsusb", "vivado -version", "vitis_hls -version",
)
BOARD_FILES = (
    "/proc/device-tree/model", "/proc/cmdline", "/proc/meminfo",
    "/etc/os-release", "/proc/version",
)


def audit_receipt(folder: Path) -> dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("M08 evidence must be an existing real folder")
    raw = folder / "m08_readonly_inventory.json"
    receipt = folder / "m08_readonly_inventory.sha256"
    if (raw.is_symlink() or receipt.is_symlink() or
            not raw.is_file() or not receipt.is_file()):
        raise ValueError("M08 JSON and SHA256 receipt must be regular files")
    expected_line = sha_file(raw) + "  m08_readonly_inventory.json\n"
    if receipt.read_text(encoding="ascii") != expected_line:
        raise ValueError("M08 receipt SHA256 mismatch or noncanonical format")
    data = json.loads(raw.read_text(encoding="utf-8"))
    if data.get("schema") != SCHEMA or data.get("mode") not in (
            "host", "board-local"):
        raise ValueError("M08 inventory schema/mode mismatch")
    for flag in ("kv260_programmed_by_this_tool",
                 "physical_dma_issued_by_this_tool",
                 "ready_for_physical_ddr"):
        if data.get(flag) is not False:
            raise ValueError("M08 inventory makes unauthorized physical assertion")
    readiness=data.get("physical_readiness")
    if (type(readiness) is not dict or
            readiness.get("ready_to_dma") is not False or
            readiness.get("physical_claim_accepted") is not False or
            readiness.get("physical_ddr_test_performed") is not False):
        raise ValueError("M08 source receipts cannot certify physical DDR")
    commands=data.get("commands")
    if type(commands) is not dict:
        raise ValueError("M08 command capture must be a map")
    if data["mode"]=="host":
        if set(commands) != set(HOST_COMMANDS):
            raise ValueError("host inventory is missing/adding read-only commands")
        if data.get("board_identity_observed") is not False:
            raise ValueError("host-only inventory cannot identify real KV260")
        hashes=data.get("source_sha256")
        if (type(hashes) is not dict or set(hashes)!={
            "src/neuromorphic_accelerator_v1/m08_entry.py",
            "scripts/m08_capture_readonly.py"} or
                not all(type(v) is str and len(v)==64 and
                        all(c in "0123456789abcdef" for c in v)
                        for v in hashes.values())):
            raise ValueError("M08 host source manifest invalid")
        archives=data.get("accepted_original_archive_inventory")
        if type(archives) is not dict:
            raise ValueError("missing M06 original artifact inventory")
        if archives.get("status")=="CHECKED":
            items=archives.get("items")
            if (type(items) is not list or len(items)!=len(ARCHIVES)
                    or any(item.get("name")!=name or
                           item.get("expected_sha256")!=sha for item,(name,sha)
                           in zip(items,ARCHIVES))):
                raise ValueError("accepted M06 archive list is not canonical")
            if archives.get("all_sha256_match") is True and not all(
                    x.get("status")=="MATCH" and
                    x.get("observed_sha256")==x.get("expected_sha256")
                    for x in items):
                raise ValueError("false accepted M06 SHA claim")
        elif archives.get("all_sha256_match") is not False:
            raise ValueError("nonchecked archives cannot be asserted verified")
    else:
        if set(commands) != {"uname -a"} or set(
                data.get("board_files",{}))!=set(BOARD_FILES):
            raise ValueError("board-local read-only capture incomplete/expanded")
        if data.get("accepted_original_archive_inventory",{}).get(
                "all_sha256_match") is not False:
            raise ValueError("board-local does not audit original owner ZIPs")
    return {
        "status":"RECEIPT_HASH_AND_SCHEMA_OK",
        "mode":data["mode"],
        "ready_for_physical_ddr":False,
        "physical_board_identity_authenticated":False,
        "physical_run_verified":False,
        "source_only_identity_attestation":True,
        "archive_scan_status":data["accepted_original_archive_inventory"]["status"],
        "receipt_sha256":sha_file(raw),
    }
