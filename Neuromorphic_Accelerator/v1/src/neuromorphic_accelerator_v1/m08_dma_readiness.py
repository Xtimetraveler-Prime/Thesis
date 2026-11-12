"""M08.3.1 read-only Linux/DMA prerequisites; never authorizes device DMA.

No allocation, mmap, ioctl, sysfs write, kernel driver attach or JTAG.
An observed DMA heap or platform device is NOT proof of bound ownership.
The captured host /proc/sysfs trees cannot authenticate KV260 hardware.
"""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path

SCHEMA="m08_3_1_linux_dma_readiness_observation_v1"
FILES=(
    "proc/device-tree/model",
    "proc/version",
    "etc/os-release",
)
DIRECTORIES=(
    "sys/class/dma_heap",
    "sys/class/fpga_manager",
    "sys/bus/platform/devices",
    "sys/kernel/iommu_groups",
)
BLOCKERS=(
    "kernel_bound_pl_axi_device_not_verified",
    "device_dma_mask_not_verified",
    "dma_allocated_for_bound_device_not_verified",
    "buffer_dma_mapping_and_iommu_not_verified",
    "cache_coherency_and_sync_not_verified",
    "buffer_lifetime_and_quiesce_reset_not_verified",
    "physical_ps_pl_mapping_and_bitstream_not_verified",
)


def _valid_root(root:Path)->Path:
    if not root.is_dir() or root.is_symlink():
        raise ValueError("existing nonsymlink OS root required")
    return root


def _parent_is_safe(root:Path,path:Path)->bool:
    """Never follow a symlink out of a fixture or unexpectedly on a board."""
    current=path
    while current!=root:
        if current.is_symlink():
            return False
        current=current.parent
    return True


def read_allowlisted(root:Path,name:str,limit:int=4096)->dict:
    if name not in FILES:
        raise ValueError("file path not allowlisted")
    root=_valid_root(root)
    path=root/name
    if not _parent_is_safe(root,path):
        return {"status":"SYMLINK_REFUSED","text":""}
    try:
        if not path.is_file():
            return {"status":"MISSING","text":""}
        with path.open("rb") as f:
            value=f.read(limit+1)
    except OSError:
        return {"status":"UNREADABLE","text":""}
    if len(value)>limit:
        return {"status":"TOO_LARGE","text":""}
    return {"status":"OBSERVED","text":value.replace(b"\x00",b"\n").decode("utf-8",errors="replace")}


def list_allowlisted(root:Path,name:str,limit:int=128)->dict:
    if name not in DIRECTORIES:
        raise ValueError("directory path not allowlisted")
    root=_valid_root(root)
    path=root/name
    if not _parent_is_safe(root,path):
        return {"status":"SYMLINK_REFUSED","names":[]}
    try:
        if not path.is_dir():
            return {"status":"MISSING","names":[]}
        # Only names: no driver binds, device-node opens or recursive walks.
        names=sorted(p.name for p in path.iterdir())
    except OSError:
        return {"status":"UNREADABLE","names":[]}
    if len(names)>limit:
        return {"status":"TOO_MANY_ENTRIES","names":[]}
    return {"status":"OBSERVED","names":names}


def collect(root:Path=Path("/"))->dict:
    root=_valid_root(root)
    return {
        "schema":SCHEMA,
        "scope":"LOCAL_READ_ONLY_OS_OBSERVATION_NOT_HARDWARE_ATTESTATION",
        "tested_root_is_real_os":root==Path("/"),
        "kernel_files":{name:read_allowlisted(root,name) for name in FILES},
        "sysfs_names":{name:list_allowlisted(root,name) for name in DIRECTORIES},
        "candidate_dma_heaps_not_ownership":True,
        "verified_kernel_bound_pl_axi_device":False,
        "verified_device_dma_mask":False,
        "verified_device_dma_mapping":False,
        "verified_cache_coherency":False,
        "verified_quiesce_before_release":False,
        "allocated_or_mapped_dma_buffer":False,
        "opened_device_or_programmed_pl":False,
        "physical_dma_ready":False,
        "permitted_next_action":"REVIEW_READ_ONLY_EVIDENCE_ONLY",
        "blockers":list(BLOCKERS),
    }


def write_fresh(output_dir:Path,report:dict)->Path:
    if output_dir.exists() or output_dir.is_symlink():
        raise FileExistsError("immutable M08.3 output directory already exists")
    if not output_dir.parent.is_dir():
        raise ValueError("create evidence parent before capture")
    output_dir.mkdir(mode=0o700)
    report_path=output_dir/"m08_3_dma_readiness.json"
    with report_path.open("x",encoding="utf-8") as o:
        json.dump(report,o,indent=2,sort_keys=True)
        o.write("\n")
    digest=sha256(report_path.read_bytes()).hexdigest()
    with (output_dir/"m08_3_dma_readiness.sha256").open("x",encoding="ascii") as o:
        o.write(f"{digest}  m08_3_dma_readiness.json\n")
    return report_path


def audit(folder:Path)->dict:
    if folder.is_symlink() or not folder.is_dir():
        raise ValueError("original evidence folder missing or symlink")
    p=folder/"m08_3_dma_readiness.json"
    h=folder/"m08_3_dma_readiness.sha256"
    if p.is_symlink() or h.is_symlink():
        raise ValueError("symlinked M08.3 evidence not accepted")
    expected=sha256(p.read_bytes()).hexdigest()
    if h.read_text(encoding="ascii")!=f"{expected}  m08_3_dma_readiness.json\n":
        raise ValueError("M08.3 report SHA-256 mismatch")
    data=json.loads(p.read_text(encoding="utf-8"))
    if data.get("schema")!=SCHEMA or data.get("scope")!="LOCAL_READ_ONLY_OS_OBSERVATION_NOT_HARDWARE_ATTESTATION":
        raise ValueError("M08.3 wrong observation schema/scope")
    for name in FILES:
        obs=data.get("kernel_files",{}).get(name)
        if not isinstance(obs,dict) or obs.get("status") not in (
            "OBSERVED","MISSING","UNREADABLE","TOO_LARGE","SYMLINK_REFUSED"
        ) or not isinstance(obs.get("text"),str):
            raise ValueError("M08.3 missing/invalid kernel file observation")
    for name in DIRECTORIES:
        obs=data.get("sysfs_names",{}).get(name)
        if not isinstance(obs,dict) or obs.get("status") not in (
            "OBSERVED","MISSING","UNREADABLE","TOO_MANY_ENTRIES","SYMLINK_REFUSED"
        ) or not isinstance(obs.get("names"),list):
            raise ValueError("M08.3 missing/invalid sysfs observation")
    for key in (
        "verified_kernel_bound_pl_axi_device",
        "verified_device_dma_mask",
        "verified_device_dma_mapping",
        "verified_cache_coherency",
        "verified_quiesce_before_release",
        "allocated_or_mapped_dma_buffer",
        "opened_device_or_programmed_pl",
        "physical_dma_ready",
    ):
        if data.get(key) is not False:
            raise ValueError(f"M08.3 unsafe or unverified hardware claim: {key}")
    if data.get("permitted_next_action")!="REVIEW_READ_ONLY_EVIDENCE_ONLY":
        raise ValueError("M08.3 device access was incorrectly authorized")
    if data.get("blockers")!=list(BLOCKERS):
        raise ValueError("M08.3 required DMA ownership blockers absent")
    if data.get("candidate_dma_heaps_not_ownership") is not True:
        raise ValueError("M08.3 heap existence misrepresented as DMA ownership")
    if type(data.get("tested_root_is_real_os")) is not bool:
        raise ValueError("M08.3 capture-root provenance missing")
    return {
        "status":"M08_3_READONLY_OBSERVATION_INTEGRITY_PASS_NOT_DMA_READY",
        "report_sha256":expected,
        "physical_dma_ready":False,
        "scope":SCHEMA,
    }
