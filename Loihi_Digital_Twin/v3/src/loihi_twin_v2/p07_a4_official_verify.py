"""P07-A4.4 physical original-order 10000 exact neural numerical closeout.

This module may only be called AFTER official user unseal and accepted
physical fault gate. All official image/label reads are explicit, the
full 10k population and one full selected last-image trace were
precommitted before TEST unseal. No model retuning, sampling or substitutions.
"""
from __future__ import annotations

from pathlib import Path
import json
import re
import struct

from .p07_a4_official import (
    STAGE_FILES, MANIFEST_FILE, LEDGER_FILE, check_official_stage, full_score,
)
from .p07_a4_stream import parse_journal,sha256
from .p07_a4_restart import (
    ELF_SHA256, XSA_SHA256, MASTER_SHA256,
)
from .p07_a4_fault import verify_physical_fault

PHASE="phase=P07-A4.4 OFFICIAL canonical original10000 persistent A53 physical gate"
REQ_LOGS={
    "ps_width.log":("P03_2C_PS_FPD_HPM0_WIDTH_BITS=128",),
    "provision.log":("P07_A4_2C_XSDB_PROVISION_PASS=1",),
    "program.log":("PASS: P03.2c accepted PS-MMIO bitstream programmed and PL reset released",),
    "a53_run.log":(
        "P07_A4_2C_JOURNAL_STATUS=0x600D600D",
        "P07_A4_2C_KV260_STATUS=TERMINAL_SUCCESS_UNVERIFIED_NUMERICS",
    ),
}
LOG_SHA=re.compile(r"^([0-9a-f]{64})  (/.+)$")


def verify_original_physical_evidence(stage: Path,evidence: Path) -> dict:
    """Bind physical originals to accepted ELF/XSA, original test + readbacks."""
    path=evidence/"physical_identity.txt"
    text=path.read_text(encoding="utf-8")
    if PHASE not in text.splitlines() or "status=BOARD_NOT_YET_RUN" not in text.splitlines():
        raise ValueError("official TEST original physical provenance phase invalid")
    indexed={}
    for line in text.splitlines():
        match=LOG_SHA.fullmatch(line)
        if not match:continue
        digest,absolute=match.groups()
        file=Path(absolute)
        if not file.is_absolute() or file.name in indexed:
            raise ValueError("official TEST duplicate/nonabsolute physical source SHA row")
        if not file.is_file() or sha256(file.read_bytes())!=digest:
            raise ValueError("official TEST source hash differs from actual physical staged source: "+absolute)
        indexed[file.name]=(file,digest)
    wanted={
        "p07_a4_board.elf":ELF_SHA256,
        "p03_2_ps_mmio.xsa":XSA_SHA256,
        "core0_initial_p02_ddr_512k.bin":MASTER_SHA256,
    }
    for name,expected in wanted.items():
        if indexed.get(name,(None,None))[1]!=expected:
            raise ValueError("official TEST original physical accepted identity differs: "+name)
    for name in ("p03_2_ps_mmio.bit","p03_2_ps_mmio.ltx"):
        if name not in indexed:
            raise ValueError("official TEST original P03 bitstream/LTX identity missing")
    for name in [*STAGE_FILES.values(),MANIFEST_FILE]:
        if name not in indexed or indexed[name][0].resolve()!=(stage/name).resolve():
            raise ValueError("official TEST original staging path differs: "+name)
    logs={}
    for filename,expected in REQ_LOGS.items():
        data=(evidence/filename).read_bytes()
        lines=data.decode("utf-8").splitlines()
        for marker in expected:
            if marker not in lines:
                raise ValueError(f"official TEST original physical {filename} marker absent: {marker}")
        logs[filename]=sha256(data)
    zero_trace=(evidence/"trace_zero_64k.bin").read_bytes()
    if len(zero_trace)!=65536 or any(zero_trace):
        raise ValueError("official TEST original trace-zero physical staging invalid")
    originals={
        0x43F00000:indexed["core0_initial_p02_ddr_512k.bin"][0].read_bytes(),
        0x41000000:(stage/STAGE_FILES["pixels"]).read_bytes(),
        0x43FE0000:(stage/STAGE_FILES["descriptor"]).read_bytes(),
        0x43FE0100:(stage/STAGE_FILES["mapping"]).read_bytes(),
        0x42000000:(stage/STAGE_FILES["zero_journal_1m"]).read_bytes(),
        0x43FF0000:zero_trace,
    }
    for address,expected in originals.items():
        read=(evidence/"readback"/f"readback_{address:08X}.bin").read_bytes()
        if read!=expected:
            raise ValueError(f"official TEST original XSDB DDR readback differs: 0x{address:08X}")
    return {
        "original_physical_identity_sha256":sha256(path.read_bytes()),
        "original_hardware_logs_sha256":logs,
        "fpga_bitstream_sha256":indexed["p03_2_ps_mmio.bit"][1],
        "fpga_ltx_sha256":indexed["p03_2_ps_mmio.ltx"][1],
        "accepted_elf_sha256":ELF_SHA256,
        "accepted_xsa_sha256":XSA_SHA256,
        "accepted_master_sha256":MASTER_SHA256,
    }


def check_trace(trace: bytes,base_image,oracle) -> None:
    """Selected image9999 26x42 full before/acc/after/spike state."""
    from .p07_a2_evidence import _state_word
    if len(trace)!=65536 or any(trace[26*42*32:]):
        raise ValueError("official TEST physical last-image full trace allocation/reserved changed")
    for tick,step in enumerate(oracle.ticks):
        for compartment in range(42):
            ptr=(tick*42+compartment)*32
            got=struct.unpack_from("<4Q",trace,ptr)
            wanted=(
                base_image.state_words[compartment] if tick==0 else
                _state_word(oracle.ticks[tick-1].states_after[compartment]),
                step.accumulators[compartment]&((1<<64)-1),
                _state_word(step.states_after[compartment]),
                int(compartment in step.fired_compartments),
            )
            if got!=wanted:
                raise AssertionError(
                    f"official TEST first full-compartment mismatch "
                    f"image=9999 tick={tick} compartment={compartment} "
                    f"hardware={got!r} oracle={wanted!r}")


def verify_full10000(*,stage: Path,evidence: Path,official,
                     candidate_dir: Path,fault_stage: Path,fault_evidence: Path):
    """Complete 10000/oracle/readback/trace gate, THEN and ONLY THEN score."""
    from .p06_a3_training import load_candidate,integer_weights_sha256
    from .p06_a4_snapshot import (
        compile_and_check_traces,require_pinned_training_candidate,
    )
    from .p07_a1_ingress import mapping_from_compiled
    from .p06_packed_replay import replay_p03_image
    from .p06_input_contract import image_event_schedule
    from .p07_a2_batch import COMPILED_FINGERPRINT
    physical_fault=verify_physical_fault(stage=fault_stage,evidence=fault_evidence)
    if physical_fault["status_word"]!="0xDEAD0001":
        raise ValueError("official TEST forbidden: physical fail-closed acceptance missing")
    stream,manifest,ledger=check_official_stage(stage,official)
    identities=verify_original_physical_evidence(stage,evidence)
    journal=(evidence/"p07_a4_journal_1m.bin").read_bytes()
    trace=(evidence/"p07_a4_trace_64k.bin").read_bytes()
    results=parse_journal(journal,stream) # all 10000 complete or STOP
    if len(results)!=10000:raise ValueError("official TEST full 10000 denominator missing")
    model,candidate=load_candidate(candidate_dir)
    require_pinned_training_candidate(candidate,integer_weights_sha256(model))
    image,compiled,check=compile_and_check_traces(model,())
    if check or image.core_id!=0 or compiled.fingerprint!=COMPILED_FINGERPRINT:
        raise ValueError("official TEST physical oracle changed frozen model")
    mapping=mapping_from_compiled(compiled)
    if mapping!=stream.mapping:
        raise ValueError("official TEST physical input map differs from frozen model")

    for i,result in enumerate(results):
        px=stream.image(i)
        oracle=replay_p03_image(image,mapping,px)
        for tick,step in enumerate(oracle.ticks):
            wanted=tuple(int(32+cls in step.fired_compartments) for cls in range(10))
            if result.output_spikes[tick]!=wanted:
                raise AssertionError(
                    f"official TEST FIRST physical numerical mismatch "
                    f"image={i} tick={tick} 10 output spikes")
        if (result.counts!=oracle.output_counts or
            result.predicted!=oracle.predicted_class or
            result.all_silent!=(sum(oracle.output_counts)==0)):
            raise AssertionError(f"official TEST FIRST physical mismatch image={i} class/count/silence")
        route_count=sum(len(step.next_packet_axons) for step in oracle.ticks[:-1])
        if (result.routes!=route_count or
            result.discarded!=len(oracle.dropped_boundary_packets) or
            result.external_events!=sum(len(t) for t in image_event_schedule(px))):
            raise AssertionError(f"official TEST FIRST physical mismatch image={i} ingress/route/discard")
        if i==9999:
            check_trace(trace,image,oracle)

    # Only AFTER every pixel, descriptor, journal, original device
    # readback, 26x10×10000 oracle and image9999 trace EXACT:
    report=full_score(results,official)
    report.update({
        "physical_numerical_parity":"10000/10000 EXACT 26x10 outputs and routes",
        "last_image_full_compartment_trace":"image9999 EXACT 26x42 (ONLY one selected)",
        "preunseal_physical_fail_closed":"0xDEAD0001 accepted",
        "physical_evidence_path":str(evidence.resolve()),
        "full_physical_journal_sha256":sha256(journal),
        "full_physical_selected_trace_sha256":sha256(trace),
        "official_stage_descriptor_sha256":manifest["sha256"]["descriptor"],
        "official_stage_image_bytes_sha256":manifest["sha256"]["pixels"],
        "canonical_archive_provenance":official.manifest,
        "preunseal_fault_evidence_sha256":physical_fault["failure_journal_sha256"],
        "physical_artifact_provenance":identities,
        "evaluation_status":"FULL10000_KV260_ORACLE_VERIFIED_AND_SCORED",
    })
    return report
