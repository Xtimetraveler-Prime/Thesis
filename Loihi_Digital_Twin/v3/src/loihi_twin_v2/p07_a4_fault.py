"""P07-A4.2c fail-closed PRE-DISPATCH injected descriptor fault gate.

Deliberately corrupt ONLY one reserved descriptor word in a disposable
staged SYNTHETIC ramp16 dataset *after* original byte-exact DDR XSDB
provisioning. Expect the unchanged accepted A53 ELF to refuse dataset
validation before ANY inference dispatch and record 0xDEAD0001,
completed=0, 1 error request slot, zero outputs/trace.

This NEVER reads official MNIST TEST or canonical TRAIN images, and
NEVER treats the expected negative terminal as successful inference.
"""
from __future__ import annotations

import json
from pathlib import Path
import struct

from .p07_a4_stream import (
    parse_stream, initial_journal, sha256, crc,
)
from .p07_a4_restart import (
    _physical_identity, ELF_SHA256, XSA_SHA256, MASTER_SHA256,
)

FAULT_WORD_OFFSET = 144
FAULT_WORD_ADDRESS = 0x43FE0090
FAULT_WORD_BYTES = b"\x01\x00\x00\x00"
EXPECTED_FAIL_STATUS = 0xDEAD0001
P07_A4_JOURNAL_SIZE = 1048576
P07_A4_TRACE_SIZE = 65536


def require_synthetic_ramp16(stage: Path):
    manifest=json.loads((stage/"p07_a4_2a_stage_manifest.json").read_text())
    if (manifest.get("scope")!="SYNTHETIC_RAMP" or
        manifest.get("frame_count")!=16 or
        manifest.get("trace_index")!=0 or
        manifest.get("official_mnist_test")!="SEALED" or
        manifest.get("physical_hardware")!="NOT_RUN" or
        manifest.get("schema")!="p07-a4-2a-persistent-ddr-stage-v1"):
        raise ValueError("A4.2c negative requires sealed, disposable synthetic ramp16 stage")
    files={
        "descriptor":(stage/"p07_a4_descriptor_256.bin").read_bytes(),
        "mapping":(stage/"p07_a4_mapping_1568.bin").read_bytes(),
        "pixels":(stage/"p07_a4_pixels_raw.bin").read_bytes(),
        "zero_journal_1m":(stage/"p07_a4_journal_initial_1m.bin").read_bytes(),
    }
    for key,value in files.items():
        if sha256(value)!=manifest.get("sha256",{}).get(key):
            raise ValueError("A4.2c negative staged input SHA mismatch: "+key)
    stream=parse_stream(files["descriptor"],files["mapping"],files["pixels"])
    if (stream.image_count!=16 or stream.trace_index!=0 or
        stream.images!=bytes(i%256 for i in range(784))*16 or
        files["zero_journal_1m"]!=initial_journal(stream)):
        raise ValueError("A4.2c negative source not exact expected synthetic ramp16")
    return stream


def check_fault_bytes(stage: Path, original: bytes, modified: bytes,
                      journal: bytes, trace: bytes) -> dict:
    """Only original descriptor[144..147] is allowed to change in physical DDR.

    The complete failure journal must be structurally and CRC exact, even
    though parse_journal() intentionally must REFUSE this error status.
    """
    stream=require_synthetic_ramp16(stage)
    if original!=stream.header:
        raise ValueError("A4.2c physical descriptor before fault != SHA-pinned staged descriptor")
    expected=bytearray(original)
    if any(expected[FAULT_WORD_OFFSET:FAULT_WORD_OFFSET+4]):
        raise ValueError("A4.2c intended reserved word already modified")
    expected[FAULT_WORD_OFFSET:FAULT_WORD_OFFSET+4]=FAULT_WORD_BYTES
    if modified!=bytes(expected):
        raise ValueError("A4.2c physical fault not EXACTLY one reserved word")
    if len(journal)!=P07_A4_JOURNAL_SIZE or len(trace)!=P07_A4_TRACE_SIZE:
        raise ValueError("A4.2c negative journal or trace physically truncated")
    if journal[:8]!=b"P07A4R01":
        raise ValueError("A4.2c negative physical journal magic wrong")
    values=struct.unpack_from("<9I",journal,8)
    wanted=(1,256,EXPECTED_FAIL_STATUS,1,0,0xFFFFFFFF,0,0,0)
    if values!=wanted:
        raise ValueError(f"A4.2c negative fail-closed header wrong: {values!r}")
    if (any(journal[44:252]) or
        struct.unpack_from("<I",journal,252)[0]!=crc(journal[:252]) or
        any(journal[256:])):
        raise ValueError("A4.2c negative failure journal CRC, reserved, or unexpected results")
    if any(trace):
        raise ValueError("A4.2c negative physical trace indicates unexpected inference dispatch")
    return {
        "status":"EXPECTED_PHYSICAL_PRE_DISPATCH_REFUSAL",
        "status_word":f"0x{EXPECTED_FAIL_STATUS:08X}",
        "complete_frames":0,"first_fault":0xFFFFFFFF,
        "initial_source_sha256":sha256(original),
        "one_word_corrupted_sha256":sha256(modified),
        "failure_journal_sha256":sha256(journal),
        "selected_trace_sha256":sha256(trace),
        "official_mnist_test":"SEALED",
    }


def verify_physical_fault(*, stage: Path, evidence: Path) -> dict:
    """Read actual separately staged/provisioned physical negative evidence."""
    _=require_synthetic_ramp16(stage)
    if not evidence.is_dir():
        raise ValueError("A4.2c negative physical evidence directory absent")
    logs={
        "ps_width.log":("P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",),
        "provision.log":("P07_A4_2C_XSDB_PROVISION_PASS=1",),
        "program.log":("PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released",),
        "inject.log":("P07_A4_2C_DESCRIPTOR_ONE_WORD_PHYSICAL_FAULT_CONFIRMED=1",),
        "a53_run.log":(
            "P07_A4_2C_JOURNAL_STATUS=0xDEAD0001",
            "P07_A4_2C_KV260_STATUS=TERMINAL_FAILURE_INSPECT_JOURNAL",
        ),
    }
    for name,markers in logs.items():
        lines=(evidence/name).read_text(encoding="utf-8").splitlines()
        for marker in markers:
            if marker not in lines:
                raise ValueError(f"A4.2c negative original physical marker missing: {name}: {marker}")
        if any("FULL_PHYSICAL_GATE_PASS=1" in line for line in lines):
            raise ValueError("A4.2c negative must not appear as successful inference")

    hashes=_physical_identity(
        evidence,stage,
        phase="phase=P07-A4.2c SYNTHETIC ramp16 reserved-descriptor-negative gate",
    )
    if not hashes.get("p03_2_ps_mmio.bit") or not hashes.get("p03_2_ps_mmio.ltx"):
        raise ValueError("A4.2c negative hardware provenance missing")
    staging={
        0x43F00000:"core0_initial_p02_ddr_512k.bin",
        0x41000000:"p07_a4_pixels_raw.bin",
        0x43FE0000:"p07_a4_descriptor_256.bin",
        0x43FE0100:"p07_a4_mapping_1568.bin",
        0x42000000:"p07_a4_journal_initial_1m.bin",
        0x43FF0000:"trace_zero_64k.bin",
    }
    identity_lines=(evidence/"physical_identity.txt").read_text().splitlines()
    for address,name in staging.items():
        path=(evidence/"trace_zero_64k.bin") if name=="trace_zero_64k.bin" else stage/name
        if name=="core0_initial_p02_ddr_512k.bin":
            candidates=[Path(line.split("  ",1)[1]) for line in identity_lines
                        if "  " in line and line.endswith("/"+name)]
            if len(candidates)!=1 or sha256(candidates[0].read_bytes())!=MASTER_SHA256:
                raise ValueError("A4.2c negative failed immutable master staging provenance")
            path=candidates[0]
        if (evidence/"readback"/f"readback_{address:08X}.bin").read_bytes()!=path.read_bytes():
            raise ValueError(f"A4.2c negative original immutable DDR staging readback {address:#x}")
    result=check_fault_bytes(
        stage,
        (evidence/"descriptor_before_fault_256.bin").read_bytes(),
        (evidence/"descriptor_after_fault_256.bin").read_bytes(),
        (evidence/"p07_a4_journal_1m.bin").read_bytes(),
        (evidence/"p07_a4_trace_64k.bin").read_bytes(),
    )
    result["physical_evidence_dir"]=str(evidence.resolve())
    result["frozen_elf_sha256"]=ELF_SHA256
    result["frozen_xsa_sha256"]=XSA_SHA256
    result["original_log_sha256"]={
        name:sha256((evidence/name).read_bytes()) for name in logs
    }
    return result
