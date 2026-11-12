#!/usr/bin/env python3
"""M08.2b.3/.4 physical UIO: QUARANTINED after first AXI/RCU hang.

A Linux MMIO read or write can SIGBUS/hang if AXI does not respond. No Linux
UIO mmap can expose BRESP/RRESP. Do NOT run without independent cooling, serial
recovery, verified original firmware and explicit separate operator consent.
No firmware load/unload, /dev/mem, neural DISPATCH, or false attestation.
"""
from __future__ import annotations

import argparse
import ctypes
from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import platform
import re
import stat
import struct
import subprocess
import sys

from neuromorphic_accelerator_v1.m08_identity_client import inspect_identity
from neuromorphic_accelerator_v1.m08_uio_page_protocol import check_idle_pair, stage_and_compare

APP = "m08-v1-fan-page-uio-review"
STOCK = "k26-starter-kits"
BIT_SHA = "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b"
DTBO_SHA = "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed"
SHELL_SHA = "0377daaf2050b88df14de9a79d120144cf49381d00fa552402395a322cb7b1a3"
STOCK_BIT_SHA = "f9dfe95d14881a2768b2c0e6a36fc363635e8ae7882ecad9725d270490395d3e"
STOCK_DTBO_SHA = "1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1"
STOCK_SHELL_SHA = "2967ccbc1f75c8d4accd1b6fecc11b16a32a5d7992e56c6eebceb99a3410f777"
REGIONS = {"m08-identity": 0xA0000000, "m08-page": 0xA0001000}
LOGICAL_ID = 0x4D080201
ROOT = Path("/sys/class/uio")


class StopPhysicalTest(RuntimeError):
    pass


def demand(ok: bool, reason: str) -> None:
    if not ok:
        raise StopPhysicalTest(reason)


def digest(path: Path) -> str:
    h = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def check_installed_files() -> None:
    app = Path("/lib/firmware/xilinx") / APP
    stock = Path("/lib/firmware/xilinx") / STOCK
    originals = (
        (app / (APP + ".bit.bin"), BIT_SHA),
        (app / (APP + ".dtbo"), DTBO_SHA),
        (app / "shell.json", SHELL_SHA),
        (stock / "k26_starter_kits.bit.bin", STOCK_BIT_SHA),
        (stock / "k26_starter_kits.dtbo", STOCK_DTBO_SHA),
        (stock / "shell.json", STOCK_SHELL_SHA),
    )
    for path, expected in originals:
        demand(path.is_file() and not path.is_symlink() and digest(path) == expected,
               "installed original firmware/recovery SHA mismatch: " + str(path))
    demand(Path("/etc/dfx-mgrd/default_firmware").read_text().strip() == STOCK,
           "stock default firmware setting changed")


def check_live_platform() -> None:
    demand(platform.machine() == "aarch64", "live test requires KV260 aarch64")
    demand("KV260" in Path("/proc/device-tree/model").read_bytes().decode(errors="replace"),
           "wrong board model")
    demand(Path("/sys/class/fpga_manager/fpga0/state").read_text().strip() == "operating",
           "FPGA manager not operating")
    demand(Path("/sys/kernel/config/device-tree/overlays/" + APP + "_image_1").is_dir(),
           "M08 device-tree overlay is not loaded")
    for service in ("dfx-mgr", "fancontrol"):
        p = subprocess.run(["systemctl", "is-active", service],
                           capture_output=True, text=True, timeout=10)
        demand(p.returncode == 0 and p.stdout.strip() == "active", service + " not active")
    p = subprocess.run(["xmutil", "listapps"], capture_output=True, text=True, timeout=15)
    demand(p.returncode == 0, "xmutil listapps failed")
    rows = p.stdout.splitlines()
    m08 = [r for r in rows if re.match(r"^\s*" + APP + r"\s+PL_FLAT", r)]
    stock = [r for r in rows if re.match(r"^\s*k26-starter-kits\s+XRT_FLAT", r)]
    demand(len(m08) == 1 and re.search(r"0->0,?", m08[0]) is not None and
           len(stock) == 1 and "0->0" not in stock[0],
           "M08 PL_FLAT is not exclusive slot-0 owner")
    check_installed_files()


def discover_uio(root: Path = ROOT, dev_root: Path = Path("/dev")) -> dict[str, str]:
    demand(root.is_dir(), "UIO sysfs missing")
    found: dict[str, str] = {}
    for item in root.iterdir():
        if re.fullmatch(r"uio\d+", item.name) is None:
            continue
        if not (item / "name").is_file():
            continue
        name = (item / "name").read_text().strip()
        if name not in REGIONS:
            for mp in (item / "maps").glob("map[0-9]*"):
                if not (mp / "addr").is_file() or not (mp / "size").is_file():
                    continue
                addr = int((mp / "addr").read_text(), 0)
                size = int((mp / "size").read_text(), 0)
                demand(not (addr < 0xA0002000 and addr + size > 0xA0000000),
                       "non-M08 UIO overlaps M08 region")
            continue
        demand(name not in found, "duplicate named M08 UIO device")
        maps = list((item / "maps").glob("map[0-9]*"))
        demand(len(maps) == 1 and maps[0].name == "map0", "M08 has extra UIO maps")
        addr = int((maps[0] / "addr").read_text(), 0)
        size = int((maps[0] / "size").read_text(), 0)
        demand(addr == REGIONS[name] and size == 4096, "incorrect M08 map")
        driver = item / "device" / "driver"
        demand(driver.is_symlink() and driver.resolve().name == "uio_pdrv_genirq",
               "M08 kernel driver is not uio_pdrv_genirq")
        node = dev_root / item.name
        demand(not node.is_symlink() and node.exists() and stat.S_ISCHR(node.stat().st_mode),
               "expected /dev/uio character device missing")
        expected_dev = tuple(int(x) for x in (item / "dev").read_text().strip().split(":"))
        actual_dev = (os.major(node.stat().st_rdev), os.minor(node.stat().st_rdev))
        demand(expected_dev == actual_dev, "UIO character device major/minor mismatch")
        found[name] = str(node)
    demand(set(found) == set(REGIONS), "both exact M08 Linux-owned devices required")
    return found


class Window:
    """4KiB kernel-owned UIO mapping, read-only unless explicit page transport."""
    def __init__(self, node: str, writable: bool):
        self.node = node
        self.writable = writable
        self.fd: int | None = None
        self.memory: mmap.mmap | None = None

    def __enter__(self):
        flags = os.O_CLOEXEC | os.O_NOFOLLOW | (os.O_RDWR if self.writable else os.O_RDONLY)
        self.fd = os.open(self.node, flags)
        try:
            prot = mmap.PROT_READ | (mmap.PROT_WRITE if self.writable else 0)
            self.memory = mmap.mmap(self.fd, 4096, flags=mmap.MAP_SHARED, prot=prot)
        except BaseException:
            os.close(self.fd)
            self.fd = None
            raise
        return self

    def __exit__(self, *_):
        if self.memory is not None:
            self.memory.close()
            self.memory = None
        if self.fd is not None:
            os.close(self.fd)
            self.fd = None

    @staticmethod
    def checked(offset: int) -> None:
        demand(type(offset) is int and 0 <= offset < 4096 and offset % 4 == 0,
               "unsafe or unaligned 32-bit MMIO register offset")

    def read32(self, offset: int) -> int:
        self.checked(offset)
        assert self.memory is not None
        if self.writable:
            return int(ctypes.c_uint32.from_buffer(self.memory, offset).value)
        return struct.unpack_from("<I", self.memory, offset)[0]

    def write32(self, offset: int, value: int) -> None:
        demand(self.writable, "no writes in read-only identity mode")
        self.checked(offset)
        demand(type(value) is int and 0 <= value <= 0xFFFFFFFF, "invalid MMIO write uint32")
        assert self.memory is not None
        # Aligned native word store, never mmap slice assignment/byte writes.
        ctypes.c_uint32.from_buffer(self.memory, offset).value = value


def page_words() -> tuple[int, ...]:
    return tuple(((i * 0x9E3779B1) ^ (0xA5A55A5A + i * 0x101)) & 0xFFFFFFFF
                 for i in range(64))


def physical_identity(nodes: dict[str, str]) -> dict:
    with Window(nodes["m08-identity"], False) as identity:
        # Identity must match BEFORE even opening the second page slave.
        ident = inspect_identity(identity, require_nonzero_build_tag=False)
        with Window(nodes["m08-page"], False) as page:
            independently_checked = check_idle_pair(identity, page)
            offsets_id = list(range(0, 0x20, 4))
            offsets_page = [0, 4, 8, 12, 16, 24, 28]
            actual_id = [identity.read32(o) for o in offsets_id]
            actual_page = [page.read32(o) for o in offsets_page]
    demand(actual_id[:4] == [0x4D303831, 0x00010000, 0, 0],
           "identity register changed after duplicate reads")
    demand(actual_page[:4] == [0x4D303850, 0x00020002, 1, 0] and actual_page[-1] == 0,
           "page header/status/loaded count changed")
    return {
        "schema": "m08-first-physical-identity-read-v1",
        "status": "PHYSICAL_UIO_READ32_IDENTITY_AND_EMPTY_PAGE_MATCHED",
        "identity_offsets": [f"0x{o:03x}" for o in offsets_id],
        "identity_words": [f"0x{x:08x}" for x in actual_id],
        "page_offsets": [f"0x{o:03x}" for o in offsets_page],
        "page_words": [f"0x{x:08x}" for x in actual_page],
        "identity_build_tag_unprovisioned": ident.build_tag_hex == "0" * 32,
        "second_independent_protocol_check": independently_checked,
        "hardware_axi_response_codes_observed": False,
        "physical_bitstream_cryptographically_attested": False,
        "physical_register_reads_attempted": True,
        "physical_256byte_page_written": False,
        "neural_inference_tested": False,
    }


def verify_identity_evidence(path: Path, expected_sha: str) -> dict:
    demand(re.fullmatch(r"[0-9a-f]{64}", expected_sha or "") is not None,
           "SHA256 of separately reviewed original identity evidence required")
    demand(path.is_file() and not path.is_symlink() and digest(path) == expected_sha,
           "original identity evidence missing/changed")
    data = json.loads(path.read_text())
    demand(type(data) is dict and
           data.get("schema") == "m08-first-physical-identity-read-v1" and
           data.get("status") == "PHYSICAL_UIO_READ32_IDENTITY_AND_EMPTY_PAGE_MATCHED" and
           data.get("identity_words", [])[:4] ==
           ["0x4d303831", "0x00010000", "0x00000000", "0x00000000"] and
           data.get("page_words", [])[:4] ==
           ["0x4d303850", "0x00020002", "0x00000001", "0x00000000"] and
           data.get("physical_register_reads_attempted") is True and
           data.get("physical_256byte_page_written") is False,
           "original identity receipt is not an accepted identity-only result")
    return data


def physical_page(nodes: dict[str, str], identity_evidence: Path, evidence_sha: str) -> dict:
    prior = verify_identity_evidence(identity_evidence, evidence_sha)
    with Window(nodes["m08-identity"], False) as identity:
        inspect_identity(identity, require_nonzero_build_tag=False)
        with Window(nodes["m08-page"], True) as page:
            # This first-party protocol requires EMPTY, verifies all 64 readbacks
            # BEFORE COMMIT, checks 256B and READY, never issues DISPATCH.
            result = stage_and_compare(identity, page, page_words(), LOGICAL_ID,
                                       allow_transport_writes=True)
    wanted = sha256(b"".join(v.to_bytes(4, "little") for v in page_words())).hexdigest()
    demand(result.get("words_compared") == 64 and result.get("bytes_compared") == 256 and
           result.get("readback_sha256_little_endian") == wanted,
           "page transaction result does not match independent expected digest")
    return {
        "schema": "m08-first-physical-256byte-state-page-v1",
        "status": "PHYSICAL_UIO_64_WORD_READBACK_MATCHED_AND_COMMIT_READY",
        "prior_identity_receipt_sha256": evidence_sha,
        "prior_identity_status": prior["status"],
        "expected_pattern": "m08-page-64word-xor-golden-v1",
        "expected_pattern_little_endian_sha256": wanted,
        "transaction": result,
        "physical_uio_transport_exercised": True,
        "all_64_words_read_back_from_mapped_registers": True,
        "axi_rresp_bresp_directly_observed": False,
        "neural_inference_tested": False,
        "dispatch_attempted": False,
    }


def save_original(path: Path, result: dict, mode: str) -> str:
    demand(path.is_absolute() and path.name == mode + ".json" and
           re.fullmatch(r"/home/ubuntu/m08_2b_tests_[a-zA-Z0-9]+/" +
                        re.escape(mode) + r"\.json", str(path)) is not None,
           "original physical evidence must use exact owner home test folder")
    payload = (json.dumps(result, sort_keys=True, indent=2) + "\n").encode()
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW | os.O_CLOEXEC,
                 0o644)
    with os.fdopen(fd, "wb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    return sha256(payload).hexdigest()


def reject_quarantined_mmio_mode(mode: str) -> None:
    """Hard interlock after 2026-11-12 physical RCU stall.

    No command-line flags or environment variables may bypass quarantine.
    Requires a separately reviewed NEW hardware/software release and source
    change before any direct MMIO is authorized. Metadata-only preflight stays.
    """
    demand(mode == "preflight",
           "M08_IDENTITY_AND_PAGE_MMIO_QUARANTINED_AFTER_KV260_RCU_STALL;"
           " do not rerun identity/page on the original bitstream")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("preflight", "identity", "page"), default="preflight")
    parser.add_argument("--acknowledge-axi-read-risk", action="store_true")
    parser.add_argument("--acknowledge-axi-write-risk", action="store_true")
    parser.add_argument("--acknowledge-rollback-not-yet-exercised", action="store_true")
    parser.add_argument("--identity-evidence", type=Path)
    parser.add_argument("--identity-evidence-sha256")
    parser.add_argument("--output-file", type=Path)
    args = parser.parse_args()
    try:
        reject_quarantined_mmio_mode(args.mode)  # BEFORE any hardware checks/accesses
        demand(os.geteuid() == 0, "authenticated root required on live KV260")
        check_live_platform()
        nodes = discover_uio()
        if args.mode == "preflight":
            result = {
                "schema": "m08-physical-uio-preflight-v1",
                "status": "LIVE_KERNEL_AND_INSTALLED_FIRMWARE_READY_NO_MMIO",
                "bindings": nodes,
                "registers_read": False,
                "page_written": False,
            }
        else:
            demand(args.acknowledge_axi_read_risk and
                   args.acknowledge_rollback_not_yet_exercised and
                   os.environ.get("M08_EXPLICIT_PHYSICAL_TEST_APPROVED") == "YES",
                   "explicit AXI read risk, unexercised rollback and environment consent required")
            demand(args.output_file is not None and not args.output_file.exists(),
                   "new original owner evidence filename required; no overwrites")
            if args.mode == "identity":
                demand(not args.acknowledge_axi_write_risk,
                       "identity mode must not authorize physical writes")
                result = physical_identity(nodes)
            else:
                demand(args.acknowledge_axi_write_risk and
                       os.environ.get("M08_EXPLICIT_PAGE_WRITE_APPROVED") == "YES",
                       "SEPARATE physical page write consent required")
                demand(args.identity_evidence is not None and
                       args.identity_evidence_sha256 is not None,
                       "reviewed SHA-pinned physical identity receipt required")
                result = physical_page(nodes, args.identity_evidence,
                                       args.identity_evidence_sha256)
            record_sha = save_original(args.output_file, result, args.mode)
            result["original_record_sha256"] = record_sha
        print(json.dumps(result, sort_keys=True, indent=2))
        return 0
    except (StopPhysicalTest, OSError, ValueError, KeyError, RuntimeError,
            subprocess.TimeoutExpired) as error:
        print("M08_PHYSICAL_UIO_STOP_NO_RETRY:", str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
