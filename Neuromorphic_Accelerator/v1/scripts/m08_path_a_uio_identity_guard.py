#!/usr/bin/env python3
"""M08.2b Linux UIO metadata preflight, optional *future* guarded ID read.

DEFAULT never opens /dev/uio or performs MMIO. The physical identity mode
MUST NOT be run until separately verified PL/fan/rollback and owner approval.
Source-only tests do NOT constitute Linux driver or PS AXI conformance.
UIO mmap does not expose AXI RRESP/BRESP, nor protect against a hung bus.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack
from hashlib import sha256
import json
import mmap
import os
from pathlib import Path
import platform
import re
import sys

from m08_path_a_uio_sysfs_readonly import inventory

FAN_BIT_BIN_SHA = "a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b"
UIO_DTBO_SHA = "2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed"
SYSFS_ROOT = Path("/sys/class/uio")
MODEL_FILE = Path("/proc/device-tree/model")
READ_FLAG = "M08_UIO_IDENTITY_READ_AUTHORIZED"
APPROVAL_FIELDS = {
    "schema": "m08-uio-physical-identity-approval-v1",
    "scope": "READ_IDENTITY_ONLY",
    "explicit_owner_authorization": "YES",
    "independent_cooling_during_pl_gap_verified": "YES",
    "rollback_to_starter_kit_verified": "YES",
    "m08_firmware_running_independently_verified": "YES",
    "linux_kernel_uio_ownership_verified": "YES",
    "bit_bin_sha256": FAN_BIT_BIN_SHA,
    "dtbo_sha256": UIO_DTBO_SHA,
}


class GuardRejected(RuntimeError):
    pass


def require(test: bool, reason: str) -> None:
    if not test:
        raise GuardRejected(reason)


def preflight(sysfs_root: Path, expected: str = "absent") -> dict:
    state = inventory(sysfs_root, expected=expected)
    return {
        "schema": "m08-uio-readonly-mapping-preflight-v1",
        "expected": expected,
        "uio_metadata": state,
        "device_node_opened": False,
        "linux_mmap_attempted": False,
        "physical_ps_axi_verified": False,
    }


def approve_identity_mode(*, sysfs_root: Path, approval_file: Path | None,
                          approval_sha256: str | None, cli_consent: bool,
                          environment: dict[str, str], machine: str,
                          board_model: str) -> dict:
    """Reject without independent operator record. Text cannot attest HW."""
    require(sysfs_root == SYSFS_ROOT, "physical mode demands exact live /sys/class/uio")
    require(machine == "aarch64" and "KV260" in board_model,
            "physical mode requires verified real KV260 Linux host")
    require(cli_consent is True and environment.get(READ_FLAG) == "YES",
            "physical mode requires separate CLI and environment owner consent")
    require(approval_file is not None and approval_sha256 is not None and
            re.fullmatch(r"[0-9a-f]{64}", approval_sha256) is not None,
            "physical mode requires exact review file and SHA256")
    require(approval_file.is_file() and not approval_file.is_symlink(),
            "approval record missing or symlinked")
    raw = approval_file.read_bytes()
    require(sha256(raw).hexdigest() == approval_sha256,
            "operator approval record SHA mismatch")
    try:
        record = json.loads(raw)
    except (UnicodeDecodeError, ValueError) as e:
        raise GuardRejected("invalid operator record JSON") from e
    require(type(record) is dict and record == APPROVAL_FIELDS,
            "operator record missing required exact reviewed assertions")
    return {"review_record_sha256": approval_sha256,
            "review_document_is_operator_assertion_not_physical_attestation": True}


def _check_linux_driver(sysfs_root: Path, bindings: dict[str, str]) -> None:
    for name in ("m08-identity", "m08-page"):
        dev = bindings[name]
        driver = sysfs_root / dev / "device" / "driver"
        require(driver.is_symlink() and driver.resolve().name == "uio_pdrv_genirq",
                "expected uio_pdrv_genirq platform driver not proven for " + name)


def identity_read_live(bindings: dict[str, str]) -> dict:
    """Only call after approval, Linux/sysfs/kernel binding and cooling review.

    O_RDONLY + PROT_READ; offsets are within a single verified map0 4KiB.
    A real inaccessible AXI slave could still SIGBUS or hang the OS.
    """
    def map_readonly(name: str, stack: ExitStack):
        idx = bindings[name]
        require(re.fullmatch(r"uio[0-9]+", idx) is not None, "invalid UIO node index")
        path = "/dev/" + idx  # derived from verified sysfs; never guessed
        fd = os.open(path, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW)
        stack.callback(os.close, fd)
        mapped = mmap.mmap(fd, 4096, flags=mmap.MAP_SHARED,
                           prot=mmap.PROT_READ, offset=0)
        stack.callback(mapped.close)
        return mapped

    def snapshot(mapped: mmap.mmap, offsets: tuple[int, ...]) -> list[int]:
        values = []
        for offset in offsets:
            require(0 <= offset <= 4092 and offset % 4 == 0,
                    "unaligned/out-of-range hardware read")
            values.append(int.from_bytes(mapped[offset:offset+4], "little"))
        return values

    with ExitStack() as stack:
        identity = map_readonly("m08-identity", stack)
        id_offsets = tuple(range(0, 0x20, 4))
        first_id = snapshot(identity, id_offsets)
        second_id = snapshot(identity, id_offsets)
        require(first_id == second_id, "unstable physical identity register values")
        require(first_id[:4] == [0x4D303831, 0x00010000, 0, 0],
                "identity magic/version/capability/reserved mismatch")
        # Only touch the second slave AFTER the first has matched.
        page = map_readonly("m08-page", stack)
        page_offsets = (0, 4, 8, 0x0c, 0x10, 0x18, 0x1c)
        first_page = snapshot(page, page_offsets)
        second_page = snapshot(page, page_offsets)
        require(first_page == second_page, "unstable physical page register values")
        require(first_page[:4] == [0x4D303850, 0x00020002, 1, 0] and first_page[-1] == 0,
                "page header/status/loaded bytes not in reset EMPTY state")
    return {
        "identity_register_offsets": [f"0x{x:03x}" for x in id_offsets],
        "identity_words": [f"0x{x:08x}" for x in first_id],
        "page_register_offsets": [f"0x{x:03x}" for x in page_offsets],
        "page_words": [f"0x{x:08x}" for x in first_page],
        "build_tag_unprovisioned": not any(first_id[4:]),
        "attempted_readonly_linux_uio_mmap": True,
        "uiommap_axi_rresp_observable": False,
        "physical_readback_independently_accepted": False,
        "page_write_attempted": False,
        "neural_inference_verified": False,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", choices=("preflight", "identity"), default="preflight")
    ap.add_argument("--sysfs-root", type=Path, default=SYSFS_ROOT)
    ap.add_argument("--expected", choices=("absent", "present"), default="absent")
    ap.add_argument("--review-file", type=Path)
    ap.add_argument("--review-sha256")
    ap.add_argument("--explicit-identity-read", action="store_true")
    args = ap.parse_args()
    try:
        if args.mode == "preflight":
            result = preflight(args.sysfs_root, args.expected)
        else:
            # HARD QUARANTINE after owner 2026-11-12 RCU stall on the first real
            # physical read: old consent flags/JSON cannot authorize this image.
            raise GuardRejected("M08_MMIO_QUARANTINED_AFTER_PHYSICAL_RCU_STALL")
            # No M08 live UIO mapping and no authorization exists today.
            require(args.expected == "present", "physical mode requires expected=present")
            info = approve_identity_mode(
                sysfs_root=args.sysfs_root, approval_file=args.review_file,
                approval_sha256=args.review_sha256,
                cli_consent=args.explicit_identity_read, environment=dict(os.environ),
                machine=platform.machine(),
                board_model=MODEL_FILE.read_bytes().decode(errors="replace").strip("\x00"),
            )
            state = inventory(SYSFS_ROOT, expected="present")
            _check_linux_driver(SYSFS_ROOT, state["m08_bindings"])
            result = {"schema": "m08-uio-identity-read-candidate-v1",
                      **info, **identity_read_live(state["m08_bindings"])}
    except (GuardRejected, OSError, ValueError, KeyError) as e:
        print("M08_UIO_IDENTITY_GUARD_REJECTED:", str(e), file=sys.stderr)
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
