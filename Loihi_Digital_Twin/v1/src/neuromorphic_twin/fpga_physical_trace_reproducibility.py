"""Reproducibility checks for repeated physical-FPGA trace captures.

M12.1.4 closes the physical trace-capture boundary by requiring two independent
board runs of the same deterministic workload to produce the same validated
physical artifact.  This module deliberately compares physical observations
only; Python-golden differential validation begins in M12.2.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from .fpga_physical_trace import read_physical_fpga_trace_json


@dataclass(frozen=True, slots=True)
class PhysicalTraceReproducibilityResult:
    """Summary of an exact repeated-capture comparison."""

    scenario_id: str
    device: str
    transport: str
    tick_count: int
    byte_count: int
    sha256_hex: str


def compare_physical_fpga_trace_files(
    first_path: str | Path,
    second_path: str | Path,
    *,
    require_byte_identical: bool = True,
) -> PhysicalTraceReproducibilityResult:
    """Require two physical trace artifacts to describe the exact same run.

    Parsed-artifact equality proves every typed physical observation is equal.
    Backend-neutral replay equality separately proves both files reconstruct the
    same M10/M12 ``TickTrace`` sequence.  By default, raw JSON bytes must also
    match so the capture artifact itself is deterministic rather than merely
    semantically equivalent after parsing.
    """

    first = Path(first_path)
    second = Path(second_path)
    first_bytes = first.read_bytes()
    second_bytes = second.read_bytes()

    first_artifact = read_physical_fpga_trace_json(first)
    second_artifact = read_physical_fpga_trace_json(second)

    if first_artifact != second_artifact:
        if first_artifact.scenario_id != second_artifact.scenario_id:
            raise ValueError(
                "physical capture scenario mismatch: "
                f"{first_artifact.scenario_id!r} != {second_artifact.scenario_id!r}"
            )
        if first_artifact.transport != second_artifact.transport:
            raise ValueError(
                "physical capture transport mismatch: "
                f"{first_artifact.transport!r} != {second_artifact.transport!r}"
            )
        if first_artifact.device != second_artifact.device:
            raise ValueError(
                "physical capture device mismatch: "
                f"{first_artifact.device!r} != {second_artifact.device!r}"
            )
        if len(first_artifact.ticks) != len(second_artifact.ticks):
            raise ValueError(
                "physical capture tick-count mismatch: "
                f"{len(first_artifact.ticks)} != {len(second_artifact.ticks)}"
            )
        for index, (first_tick, second_tick) in enumerate(
            zip(first_artifact.ticks, second_artifact.ticks, strict=True),
            start=1,
        ):
            if first_tick != second_tick:
                raise ValueError(
                    "physical capture semantic mismatch at artifact tick "
                    f"index {index}: committed_tick="
                    f"{first_tick.snapshot.committed_tick}/"
                    f"{second_tick.snapshot.committed_tick}"
                )
        raise ValueError("physical capture artifacts differ")

    first_replay = first_artifact.to_tick_traces()
    second_replay = second_artifact.to_tick_traces()
    if first_replay != second_replay:
        raise ValueError("physical capture TickTrace replay mismatch")

    if require_byte_identical and first_bytes != second_bytes:
        raise ValueError(
            "physical capture JSON is semantically equal but not byte-stable"
        )

    first_hash = sha256(first_bytes).hexdigest()
    second_hash = sha256(second_bytes).hexdigest()
    if require_byte_identical and first_hash != second_hash:
        raise AssertionError("byte-identical physical captures produced different hashes")

    return PhysicalTraceReproducibilityResult(
        scenario_id=first_artifact.scenario_id,
        device=first_artifact.device,
        transport=first_artifact.transport,
        tick_count=len(first_artifact.ticks),
        byte_count=len(first_bytes),
        sha256_hex=first_hash,
    )
