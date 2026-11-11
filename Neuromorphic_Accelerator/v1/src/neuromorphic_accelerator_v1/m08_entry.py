"""M08.1 physical KV260 entry: read-only provenance, readiness and DDR guard.

Unlike M06/M07, M08 will eventually require actual on-board data. This
module does NOT claim board attendance or interrogate the board. Host-side
collection occurs separately in scripts/m08_capture_readonly.py.

Never infer physical PS DDR ownership from an AXI address map, from
/dev/mem, from a simulation memory image, or from a read-only firmware
inventory. Only a kernel-mediated isolated/coherent buffer with a verified
DMA-visible address, address width and device-tree/IOMMU matching is a
candidate for a later dedicated M08 DDR gate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

SCHEMA = "m08-kv260-readonly-entry-v1"
BOARD = "KV260"
PART = "xck26-sfvc784-2LV-c"
ARCHIVES = (
    ("M06_G3_3_M02_M03_PARITY_HLS_AMD_REVIEW_20261110T165556Z.zip",
     "c3c9c6c1b21989b11f2d632b306981b10261aa1c6aedd8e54f7cd1c88ed4eb6c"),
    ("M06_G4_FIRST_B_SLVERR_HLS_AMD_REVIEW_20261110T171436Z.zip",
     "11c2960d6a130e530ccfde345c42828e42626936e523a77f7b35bacffc87eaca"),
    ("M06_G4_FIRST_R_SLVERR_HLS_AMD_REVIEW_20261110T174333Z.zip",
     "55039df7443c0c0d6aba73d88d9eb80461a403684a46cf31ff0e736225a22d70"),
    ("M06_G4_STALLED_B_HLS_AMD_REVIEW_20261110T181903Z.zip",
     "263d0735a8319d92e79758299cbbaf01943052840faf2e35842ace94260d27b8"),
    ("M06_G4_DISCARD_RESTORE_HLS_AMD_REVIEW_20261110T182012Z.zip",
     "fa981f6dc18e750b863a81ffec1db8a0359b85f80fb7b178d197f1128dfa78af"),
)


def sha_file(p: Path) -> str:
    h = sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def archive_inventory(root: Path | None) -> dict:
    """Read accepted M06 ZIPs without copying, editing or pretending to rerun."""
    if root is None:
        return {"status": "NOT_SCANNED", "items": [],
                "all_sha256_match": False}
    if not root.is_dir() or root.is_symlink():
        raise ValueError("existing nonsymlink evidence directory required")
    items = []
    for name, expected in ARCHIVES:
        matches = list(root.rglob(name))
        # Never allow an ambiguous basename or symlinked evidence.
        if len(matches) != 1:
            items.append({"name": name, "status": (
                "MISSING" if not matches else "AMBIGUOUS"),
                "expected_sha256": expected, "observed_sha256": None})
            continue
        path = matches[0]
        if path.is_symlink() or not path.is_file():
            items.append({"name": name, "status": "INVALID_FILE",
                          "expected_sha256": expected, "observed_sha256": None})
            continue
        digest = sha_file(path)
        items.append({"name": name, "status": "MATCH" if digest == expected
                      else "SHA256_MISMATCH", "expected_sha256": expected,
                      "observed_sha256": digest})
    return {"status": "CHECKED", "items": items,
            "all_sha256_match": all(x["status"] == "MATCH" for x in items)}


@dataclass(frozen=True)
class PhysicalReadiness:
    """Independent operator evidence IDs only; not proof of actual silicon.

    A paper claim or even a matching file name does not establish hardware
    identity. Every later physical acceptance requires a separate audit.
    """
    actual_kv260_identity_evidence: str | None = None
    known_good_boot_or_recovery_evidence: str | None = None
    validated_k26_xsa_and_bitstream_evidence: str | None = None
    verified_linux_device_tree_and_driver_evidence: str | None = None
    kernel_owned_dma_buffer_evidence: str | None = None
    independent_neural_trace_evidence: str | None = None

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if value is not None and (
                type(value) is not str or not value.strip()
                or len(value) > 400 or any(c in value for c in "\x00\r\n")
            ):
                raise ValueError(f"{name} evidence ID must be nonempty one-line text")

    def assess(self) -> dict:
        self.validate()
        values = asdict(self)
        missing = [field for field, value in values.items() if value is None]
        return {
            "status": "INSUFFICIENT_EXTERNAL_EVIDENCE" if missing
                      else "AWAIT_INDEPENDENT_PHYSICAL_AUDIT",
            "missing": missing,
            "board_programming_performed": False,
            "physical_ddr_test_performed": False,
            "ready_to_dma": False,
            "physical_claim_accepted": False,
        }


def verify_dma_window(*, dma_addr: int, length: int,
                      dma_addr_bits: int, buffer_length: int,
                      allocator: str, buffer_owner: str,
                      device_dma_mask_bits: int, cpu_accessible: bool,
                      device_bound: bool, mappings_coherent: bool) -> dict:
    """PRECONDITION ONLY, never a driver or physical buffer allocation.

    The caller must independently establish these properties using a real
    Linux driver. Reject unowned or >address-width buffers before device use.
    """
    for field, val in (("dma_addr", dma_addr), ("length", length),
                       ("dma_addr_bits", dma_addr_bits),
                       ("buffer_length", buffer_length),
                       ("device_dma_mask_bits", device_dma_mask_bits)):
        if type(val) is not int or val < (0 if field == "dma_addr" else 1):
            raise ValueError(f"{field}: invalid integer")
    if type(allocator) is not str or allocator not in (
        "kernel_dma_alloc_coherent", "kernel_dma_buf_attached_mapped"
    ):
        raise ValueError("physical DMA requires kernel-owned, driver-mapped memory")
    if type(buffer_owner) is not str or not buffer_owner.strip():
        raise ValueError("nonempty unique Linux buffer owner evidence required")
    if (cpu_accessible is not True or device_bound is not True or
            mappings_coherent is not True):
        raise ValueError("buffer CPU/device mapping and ownership not established")
    if dma_addr_bits not in (32, 64) or device_dma_mask_bits < dma_addr_bits:
        raise ValueError("DMA address width mismatches verified device mask")
    if length > buffer_length or (dma_addr % 64) or (length % 64):
        raise ValueError("DMA extent outside owned allocation or not 64B aligned")
    if dma_addr + length > (1 << dma_addr_bits):
        raise ValueError("DMA extent exceeds address capability; no truncation")
    return {
        "shape_validation_only": True,
        "physical_allocation_verified": False,
        "dma_addr_bits": dma_addr_bits,
        "length_bytes": length,
        "does_not_authorize_address_arithmetic_or_mmio": True,
    }
