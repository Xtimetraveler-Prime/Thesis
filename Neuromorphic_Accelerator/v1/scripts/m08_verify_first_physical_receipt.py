#!/usr/bin/env python3
"""Audit an original M08 first physical Linux deployment archive; PC ONLY.

Verifies original SHA receipt + specific observed Linux manager/UIO evidence.
Never SSHes, programs PL, opens /dev/uio, or infers PS AXI correctness.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import tarfile

ORIGINAL_CONTEXT = "source_head=b04cc15064f80bdea154f3182e90c688444d26b5"
EXPECTED_FILES = {
    "00_context.txt", "01_operator_ssh.log", "02_uio_sysfs_stdout.json",
    "03_uio_sysfs_stderr.log", "04_uio_exit.txt",
}
EXPECTED_MAPPINGS = {
    "m08-identity": (0xA0000000, 4096),
    "m08-page": (0xA0001000, 4096),
}
APP = "m08-v1-fan-page-uio-review"
ACTIVE_OVERLAY = "m08-v1-fan-page-uio-review_image_1"


class EvidenceRejected(ValueError):
    pass


def require(ok: bool, why: str) -> None:
    if not ok:
        raise EvidenceRejected(why)


def members_bytes(archive: Path) -> dict[str, bytes]:
    require(archive.is_file() and not archive.is_symlink(), "archive file absent or symlink")
    result = {}
    with tarfile.open(archive, mode="r:gz") as tar:
        for m in tar.getmembers():
            # Reject links, traversal, duplicate paths, unexpected files.
            path = m.name.removeprefix("./")
            require(path in EXPECTED_FILES | {"99_evidence_sha256.txt"} or
                    (path == "" and m.isdir()), "unexpected archive member: " + m.name)
            if m.isdir():
                require(path == "", "unexpected directory")
                continue
            require(m.isfile() and m.size < 1024 * 1024 and path not in result,
                    "nonregular, oversize or duplicate archived file: " + path)
            f = tar.extractfile(m)
            require(f is not None, "unreadable archived file")
            data = f.read()
            require(len(data) == m.size, "short original archive entry")
            result[path] = data
    require(set(result) == EXPECTED_FILES | {"99_evidence_sha256.txt"},
            "missing original physical evidence")
    return result


def verify_ledger(files: dict[str, bytes]) -> None:
    ledger = files["99_evidence_sha256.txt"].decode("ascii")
    covered = set()
    for line in ledger.splitlines():
        m = re.fullmatch(r"([0-9a-f]{64})  ([A-Za-z0-9_.]+)", line)
        require(m is not None, "invalid original ledger syntax")
        want, name = m.groups()
        require(name in EXPECTED_FILES and name not in covered,
                "duplicate or unrecognized original ledger entry")
        require(sha256(files[name]).hexdigest() == want, "SHA mismatch: " + name)
        covered.add(name)
    require(covered == EXPECTED_FILES, "original SHA coverage is incomplete")


def decode_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace").replace("\r", "")


def verify_log(text: str) -> dict:
    # The owner saved terminal control sequences; these output lines are not
    # expected to be immediately adjacent to one another or at known columns.
    require("STAGE_A_PASS_M08_REGISTERED_STOCK_STILL_RUNNING" in text,
            "firmware catalog registration not evidenced")
    require("remove from slot 0 returns: 0 (Ok)" in text,
            "successful stock unload not evidenced")
    proof = APP + ": Loaded with slot_handle 0"
    require(proof in text, "M08 load success not evidenced")
    after = text.rsplit(proof, 1)[1]
    require(re.search(r"\boperating\b", after) is not None,
            "postload FPGA manager operating not evidenced")
    require("ACTIVE_OVERLAY=/sys/kernel/config/device-tree/overlays/" +
            ACTIVE_OVERLAY in after, "active M08 DT overlay not evidenced")
    require("0->0," in after and APP in after and "k26-starter-kits" in after,
            "postload manager slot ownership not evidenced")
    require(re.search(r"\bactive\s+active\b", after) is not None,
            "two postload service-active observations not evidenced")
    values = re.findall(r"/sys/class/hwmon/hwmon\d+/temp\d+_input=([0-9]+)", after)
    require(len(values) >= 3 and all(0 < int(x) < 200000 for x in values),
            "postload telemetry missing/invalid")
    # Original root-visible resource inventory (but not exhaustive ownership proof).
    start = text.find("sudo cat /proc/iomem")
    end = text.find("Confirm independent fan", start)
    require(start >= 0 and end > start, "root-visible /proc/iomem review missing")
    ranges = re.findall(r"(?m)^\s*([0-9a-f]+)-([0-9a-f]+)\s+:", text[start:end])
    require(len(ranges) >= 15, "root-visible resource inventory implausibly incomplete")
    for low, high in ranges:
        a, b = int(low, 16), int(high, 16)
        require(not (a <= 0xA0001FFF and b >= 0xA0000000),
                "unexpected prior resource overlapping M08 physical windows")
    return {"stock_unload_reported_success": True,
            "m08_load_reported_success": True,
            "overlay_confirmed": True,
            "observed_postload_temperatures_millicelsius": [int(x) for x in values[:3]],
            "resource_inventory_nonoverlap_observed": True}


def verify_uio(data: dict) -> dict:
    require(data.get("schema") == "m08-kv260-uio-sysfs-discovery-v1" and
            data.get("status") == "UIO_SYSFS_METADATA_INSPECTED_NO_MMIO" and
            data.get("expected") == "present" and
            data.get("register_readback") == "NOT_PERFORMED" and
            data.get("driver_behavior") == "NOT_VERIFIED",
            "UIO metadata status inconsistent")
    bindings = data.get("m08_bindings")
    require(type(bindings) is dict and set(bindings) == set(EXPECTED_MAPPINGS),
            "both M08 UIO bindings required")
    devices = data.get("existing_devices")
    require(type(devices) is list, "missing sysfs device descriptors")
    found = {}
    for dev in devices:
        if dev.get("name") not in EXPECTED_MAPPINGS:
            continue
        name = dev["name"]
        require(name not in found and dev.get("uio") == bindings[name],
                "duplicate/mismatched named M08 UIO device")
        maps = dev.get("maps")
        require(type(maps) is list and len(maps) == 1 and maps[0].get("map_index") == 0,
                "unexpected extra M08 map")
        expected_base, expected_size = EXPECTED_MAPPINGS[name]
        require(int(maps[0].get("physical_base", "0"), 16) == expected_base and
                maps[0].get("bytes") == expected_size,
                "incorrect physical M08 map")
        found[name] = dev["uio"]
    require(set(found) == set(EXPECTED_MAPPINGS), "M08 UIO maps missing")
    return found


def review(archive: Path) -> dict:
    files = members_bytes(archive)
    verify_ledger(files)
    context = files["00_context.txt"].decode("ascii").strip()
    require(context == ORIGINAL_CONTEXT, "operator context ref mismatch")
    require(files["03_uio_sysfs_stderr.log"] == b"" and
            files["04_uio_exit.txt"] == b"exit_status=0\n",
            "UIO inspector failed or had stderr")
    status = verify_log(decode_text(files["01_operator_ssh.log"]))
    bindings = verify_uio(json.loads(files["02_uio_sysfs_stdout.json"]))
    return {
        "schema": "m08-first-physical-deployment-original-audit-v1",
        "status": "FIRST_PL_IMAGE_DEPLOYMENT_METADATA_ACCEPTED_NOT_PS_AXI",
        "source_commit": context.removeprefix("source_head="),
        "original_archive_sha256": sha256(archive.read_bytes()).hexdigest(),
        "original_sha_ledger_sha256": sha256(files["99_evidence_sha256.txt"]).hexdigest(),
        "ledger_covered_files_verified": 5,
        "m08_bindings": bindings,
        **status,
        "uart_log_independently_reviewed": False,
        "cooling_during_reconfiguration_instrumented": False,
        "operator_reports_fan_continuity": "SEPARATE_OWNER_OBSERVATION_NOT_IN_ARCHIVE",
        "rollback_to_stock_physically_exercised": False,
        "register_mmio_read_performed": False,
        "physical_axil_response_observed": False,
        "state_page_64word_verified": False,
        "neural_inference_verified": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = review(args.archive)
    except (EvidenceRejected, OSError, ValueError, UnicodeError,
            tarfile.TarError, KeyError, TypeError) as e:
        print("M08_FIRST_PHYSICAL_RECEIPT_REJECTED:", e, file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
