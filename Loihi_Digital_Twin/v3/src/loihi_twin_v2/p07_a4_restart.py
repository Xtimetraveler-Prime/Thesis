"""P07-A4.2c persistent validation128 independent cold-reboot evidence audit.

Read ONLY original physical XSDB evidence, preserving full 1MiB journal
and 64KiB selected trace. The committed A53 ELF, P03 bitstream, model,
test-population and firmware are unchanged. This module never accesses
canonical MNIST TEST or controls JTAG.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re

from .p07_a4_crosscheck import compare_prior_physical
from .p07_a4_stream import parse_journal, parse_stream, sha256

FRAMES = 128
ELF_SHA256 = "dcba738e0d9e78a6bf9fb61fba5ff23dcd1da68f8903fb1dbd33952b3dca38fb"
XSA_SHA256 = "52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
MASTER_SHA256 = "9617a822f74faa8723869bb576cf57b38af1a1a91ac81c47c246a9425d0dd955"
STAGE_FILES = (
    "p07_a4_descriptor_256.bin",
    "p07_a4_mapping_1568.bin",
    "p07_a4_pixels_raw.bin",
    "p07_a4_journal_initial_1m.bin",
    "p07_a4_2a_stage_manifest.json",
)
LOG_MARKERS = {
    "ps_width.log": ("P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",),
    "provision.log": ("P07_A4_2C_XSDB_PROVISION_PASS=1",),
    "program.log": (
        "PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released",
    ),
    "a53_run.log": (
        "P07_A4_2C_JOURNAL_STATUS=0x600D600D",
        "P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS",
    ),
    "verify.log": (
        "P07_A4_2C_PHYSICAL_FRAMES=128",
        "P07_A4_2C_PHYSICAL_ALL_OUTPUTS_EXACT=1",
        "P07_A4_2C_PHYSICAL_SELECTED_TRACE_26X42_EXACT=1",
        "P07_A4_2C_PHYSICAL_SEALED_VALIDATION_GATE_PASS=1",
        "P07_A4_OFFICIAL_TEST=SEALED",
    ),
}
HASH_LINE = re.compile(r"^([a-f0-9]{64})  (/.+)$")


@dataclass(frozen=True)
class RunEvidence:
    run_directory: str
    journal_sha256: str
    trace_sha256: str
    identity_sha256: str
    log_sha256: dict[str, str]
    bit_sha256: str
    ltx_sha256: str
    complete_frames: int


def _physical_identity(evidence: Path, stage: Path) -> dict[str, str]:
    path = evidence / "physical_identity.txt"
    text = path.read_text(encoding="utf-8")
    if ("phase=P07-A4.2c persistent A53 TRAIN-derived validation physical gate" not in
            text or "status=BOARD_NOT_YET_RUN" not in text):
        raise ValueError("A4.2c unrecognized prelaunch original physical identity")
    rows={}
    for line in text.splitlines():
        match=HASH_LINE.fullmatch(line)
        if match is None:
            continue
        digest,filename=match.groups()
        name=Path(filename).name
        if name in rows:
            raise ValueError(f"A4.2c duplicate physical provenance entry {name}")
        rows[name]=digest
        # Require preserved original locally accessible source bytes; do not
        # blindly trust a recorded SHA line detached from its file.
        if not Path(filename).is_file() or sha256(Path(filename).read_bytes())!=digest:
            raise ValueError(f"A4.2c original physical source hash changed: {filename}")
    for name,digest in (
        ("p07_a4_board.elf", ELF_SHA256),
        ("p03_2_ps_mmio.xsa", XSA_SHA256),
        ("core0_initial_p02_ddr_512k.bin", MASTER_SHA256),
    ):
        if rows.get(name)!=digest:
            raise ValueError(f"A4.2c wrong frozen physical artifact identity: {name}")
    if not rows.get("p03_2_ps_mmio.bit") or not rows.get("p03_2_ps_mmio.ltx"):
        raise ValueError("A4.2c original bitstream/ltx provenance missing")
    for name in STAGE_FILES:
        if rows.get(name)!=sha256((stage/name).read_bytes()):
            raise ValueError(f"A4.2c physical input staging SHA differs: {name}")
        # Identity hashes alone could point at an unrelated same-named file.
        found=[line for line in text.splitlines()
               if HASH_LINE.fullmatch(line) and line.endswith("/"+name)]
        if len(found)!=1:
            raise ValueError(f"A4.2c ambiguous physical staging file source: {name}")
        source=Path(HASH_LINE.fullmatch(found[0]).group(2))
        if source.resolve()!= (stage/name).resolve():
            raise ValueError(f"A4.2c different physical input staging path: {name}")
    return rows


def _read_run(stage: Path, evidence: Path, stream) -> RunEvidence:
    if not evidence.is_dir():
        raise ValueError("A4.2c missing original physical evidence directory: "+str(evidence))
    logs={}
    for filename,required in LOG_MARKERS.items():
        path=evidence/filename
        raw=path.read_bytes()
        lines=raw.decode("utf-8",errors="strict").splitlines()
        for marker in required:
            if marker not in lines:
                raise ValueError(
                    f"A4.2c {evidence.name}/{filename} missing physical gate marker {marker}"
                )
        logs[filename]=sha256(raw)
    hashes=_physical_identity(evidence,stage)
    # Confirm the original physical XSDB provision's actual *byte-for-byte*
    # readback files are preserved, not merely its terminal PASS assertion.
    identity_text=(evidence/"physical_identity.txt").read_text(encoding="utf-8")
    master_lines=[HASH_LINE.fullmatch(line) for line in identity_text.splitlines()]
    master_paths=[Path(m.group(2)) for m in master_lines
                  if m is not None and Path(m.group(2)).name==
                  "core0_initial_p02_ddr_512k.bin"]
    if len(master_paths)!=1:
        raise ValueError("A4.2c cannot resolve unique physical immutable master")
    exact_staging={
        0x43F00000:master_paths[0].read_bytes(),
        0x41000000:(stage/"p07_a4_pixels_raw.bin").read_bytes(),
        0x43FE0000:(stage/"p07_a4_descriptor_256.bin").read_bytes(),
        0x43FE0100:(stage/"p07_a4_mapping_1568.bin").read_bytes(),
        0x42000000:(stage/"p07_a4_journal_initial_1m.bin").read_bytes(),
        0x43FF0000:(evidence/"trace_zero_64k.bin").read_bytes(),
    }
    if len(exact_staging[0x43FF0000])!=65536 or any(exact_staging[0x43FF0000]):
        raise ValueError("A4.2c expected zero-initialized 64KiB full trace")
    for address,wanted in exact_staging.items():
        readback=evidence/"readback"/f"readback_{address:08X}.bin"
        if readback.read_bytes()!=wanted:
            raise ValueError(f"A4.2c physical staged DDR readback mismatch at 0x{address:08X}")
    journal=(evidence/"p07_a4_journal_1m.bin").read_bytes()
    trace=(evidence/"p07_a4_trace_64k.bin").read_bytes()
    results=parse_journal(journal,stream)
    if len(results)!=FRAMES:
        raise ValueError("A4.2c incomplete 128-image original physical journal")
    if len(trace)!=65536:
        raise ValueError("A4.2c physical selected trace truncated")
    return RunEvidence(
        str(evidence.resolve()),sha256(journal),sha256(trace),
        sha256((evidence/"physical_identity.txt").read_bytes()),
        logs,hashes["p03_2_ps_mmio.bit"],hashes["p03_2_ps_mmio.ltx"],
        len(results),
    )


def verify_cold_repeat(*, stage: Path, primary: Path,
                       a3_protocol: Path, a3_evidence: Path,
                       repeat: Path | None = None) -> dict:
    """Primary admission if repeat=None; else verify both true physical runs.

    This never asserts physical reboot was proven cryptographically:
    distinct run directories, original run logs, fresh staged readback,
    and user-declared reboot must all hold for research acceptance.
    """
    raw={
        "header":(stage/"p07_a4_descriptor_256.bin").read_bytes(),
        "mapping":(stage/"p07_a4_mapping_1568.bin").read_bytes(),
        "pixels":(stage/"p07_a4_pixels_raw.bin").read_bytes(),
    }
    stream=parse_stream(raw["header"],raw["mapping"],raw["pixels"])
    if stream.image_count!=FRAMES or stream.trace_index!=0:
        raise ValueError("A4.2c restart gate fixed at original 128 images, trace index 0")
    base_args=dict(
        a4_stage=stage,
        a3_protocol=a3_protocol,
        a3_evidence=a3_evidence,
    )
    first=_read_run(stage,primary,stream)
    old=compare_prior_physical(
        **base_args,
        a4_journal=primary/"p07_a4_journal_1m.bin",
        a4_trace=primary/"p07_a4_trace_64k.bin",
    )
    if old.frames!=FRAMES or not old.selected_trace_exact or old.prior_primary_batches!=8:
        raise AssertionError("A4.2c primary differs from old eight physical batches")
    result={
        "schema":"p07-a4-2c-128-cold-reboot-physical-v1",
        "official_mnist_test":"SEALED",
        "unique_train_validation_frames":FRAMES,
        "original_a3_primary_batches":8,
        "first_selected_trace_byte_exact_to_a3":True,
        "immutable_stage":{
            "descriptor_sha256":sha256(raw["header"]),
            "pixel_stream_sha256":sha256(raw["pixels"]),
            "mapping_sha256":sha256(raw["mapping"]),
        },
        "frozen_elf_sha256":ELF_SHA256,
        "frozen_xsa_sha256":XSA_SHA256,
        "primary":first.__dict__,
        "physical_restart_observation":"requires user independent JTAG-only reboot; not independently machine-attested",
        "status":"PRIMARY_ACCEPTED_REPEAT_PENDING",
    }
    if repeat is None:return result
    if repeat.resolve()==primary.resolve():
        raise ValueError("A4.2c second physical launch MUST use a distinct evidence directory")
    second=_read_run(stage,repeat,stream)
    if second.bit_sha256!=first.bit_sha256 or second.ltx_sha256!=first.ltx_sha256:
        raise ValueError("A4.2c cold repeat bitstream or LTX differs from accepted primary")
    # Full 1MiB / 64KiB equality, not merely output class predictions.
    if (primary/"p07_a4_journal_1m.bin").read_bytes()!=(
        repeat/"p07_a4_journal_1m.bin").read_bytes():
        raise AssertionError("A4.2c cold restart 1MiB physical journal differs")
    if (primary/"p07_a4_trace_64k.bin").read_bytes()!=(
        repeat/"p07_a4_trace_64k.bin").read_bytes():
        raise AssertionError("A4.2c cold restart 64KiB selected physical trace differs")
    again=compare_prior_physical(
        **base_args,
        a4_journal=repeat/"p07_a4_journal_1m.bin",
        a4_trace=repeat/"p07_a4_trace_64k.bin",
    )
    if again.frames!=FRAMES or again.prior_primary_batches!=8 or not again.selected_trace_exact:
        raise AssertionError("A4.2c cold repeat differs from old eight physical batches")
    result["repeat"]=second.__dict__
    result["physical_launches"]=2
    result["total_hardware_image_executions"]=2*FRAMES
    result["unique_train_validation_frames"]=FRAMES
    result["full_journal_1m_byte_exact"]=True
    result["selected_trace_64k_byte_exact"]=True
    result["status"]="PRIMARY_AND_COLD_REPEAT_VERIFIED_PENDING_LARGER_VALIDATION"
    return result
