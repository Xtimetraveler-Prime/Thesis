"""Physical-FPGA trace capture schema for M12 validation.

M11.5.5 already froze the architectural contents of one post-commit FPGA
snapshot in :class:`FpgaTickTraceSnapshot`.  M12.1 adds the physical transport
metadata needed to prove that a trace came from a real board and to preserve
recurrent-queue/fault observations that are not part of the backend-neutral
``TickTrace`` itself.

This module is intentionally transport-neutral.  The first hardware transport
will be JTAG/VIO, but JSON artifacts produced by another transport must use the
same schema and reconstruct the same ``FpgaTickTraceSnapshot`` objects.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
import json
from pathlib import Path
from typing import Any, Mapping

from .fpga_core_capacity import (
    MAX_EXTERNAL_EVENTS_PER_TICK,
    MAX_RECURRENT_EVENTS_PER_TICK,
)
from .fpga_trace_snapshot import FpgaTickTraceSnapshot


FPGA_PHYSICAL_TRACE_SCHEMA = "neuromorphic-twin-physical-fpga-trace-v1"
FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO = "jtag-vio"


class FpgaTraceReadSpace(IntEnum):
    """Frozen M12.1 indexed debug-read selector values.

    M12.1.2 RTL and M12.1.3 VIO tooling must preserve these numeric values so
    the host capture path cannot silently reinterpret a hardware read.
    """

    STATE_BEFORE = 0
    STATE_AFTER = 1
    SYNAPTIC_INPUT = 2
    SPIKE = 3
    EXTERNAL_EVENT = 4
    RECURRENT_BANK0_EVENT = 5
    RECURRENT_BANK1_EVENT = 6


@dataclass(frozen=True, slots=True)
class PhysicalFpgaTickCapture:
    """One physically observed, post-commit FPGA tick.

    ``snapshot`` carries the lossless M10/M11 architectural trace fields.
    The remaining fields preserve hardware status and recurrent-bank metadata
    required to prove the observation window itself was coherent.
    """

    snapshot: FpgaTickTraceSnapshot
    core_fault: bool
    core_fault_code: int
    recurrent_current_bank: bool
    recurrent_current_count: int
    recurrent_bank0_count: int
    recurrent_bank1_count: int
    consumed_recurrent_count: int
    routed_recurrent_count: int
    external_event_count: int

    def __post_init__(self) -> None:
        if not isinstance(self.core_fault, bool):
            raise TypeError("core_fault must be bool")
        if not isinstance(self.recurrent_current_bank, bool):
            raise TypeError("recurrent_current_bank must be bool")
        _validate_uint("core_fault_code", self.core_fault_code, 8)
        _validate_count(
            "recurrent_current_count",
            self.recurrent_current_count,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )
        _validate_count(
            "recurrent_bank0_count",
            self.recurrent_bank0_count,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )
        _validate_count(
            "recurrent_bank1_count",
            self.recurrent_bank1_count,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )
        _validate_count(
            "consumed_recurrent_count",
            self.consumed_recurrent_count,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )
        _validate_count(
            "routed_recurrent_count",
            self.routed_recurrent_count,
            MAX_RECURRENT_EVENTS_PER_TICK,
        )
        _validate_count(
            "external_event_count",
            self.external_event_count,
            MAX_EXTERNAL_EVENTS_PER_TICK,
        )

        if self.external_event_count != len(self.snapshot.external_input_axons):
            raise ValueError("external_event_count does not match captured external events")
        if self.consumed_recurrent_count != len(self.snapshot.recurrent_input_axons):
            raise ValueError(
                "consumed_recurrent_count does not match captured recurrent inputs"
            )
        if self.routed_recurrent_count != len(self.snapshot.routed_output_axons):
            raise ValueError("routed_recurrent_count does not match captured routed events")

        selected_count = (
            self.recurrent_bank1_count
            if self.recurrent_current_bank
            else self.recurrent_bank0_count
        )
        if selected_count != self.recurrent_current_count:
            raise ValueError(
                "recurrent_current_count does not match the selected physical bank count"
            )
        if self.recurrent_current_count != self.routed_recurrent_count:
            raise ValueError(
                "post-commit recurrent current count must equal routed event count"
            )


@dataclass(frozen=True, slots=True)
class PhysicalFpgaTraceArtifact:
    """Machine-readable capture containing one or more physical FPGA ticks."""

    scenario_id: str
    transport: str
    device: str
    ticks: tuple[PhysicalFpgaTickCapture, ...]

    def __post_init__(self) -> None:
        for name, value in (
            ("scenario_id", self.scenario_id),
            ("transport", self.transport),
            ("device", self.device),
        ):
            if not isinstance(value, str):
                raise TypeError(f"{name} must be str")
            if not value.strip():
                raise ValueError(f"{name} must not be empty")
        if not isinstance(self.ticks, tuple):
            raise TypeError("ticks must be a tuple")
        if not self.ticks:
            raise ValueError("physical trace artifact must contain at least one tick")
        if any(not isinstance(tick, PhysicalFpgaTickCapture) for tick in self.ticks):
            raise TypeError("ticks entries must be PhysicalFpgaTickCapture values")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": FPGA_PHYSICAL_TRACE_SCHEMA,
            "scenario_id": self.scenario_id,
            "transport": self.transport,
            "device": self.device,
            "ticks": [_tick_to_dict(tick) for tick in self.ticks],
        }

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "PhysicalFpgaTraceArtifact":
        if not isinstance(payload, Mapping):
            raise TypeError("physical trace payload must be a mapping")
        if payload.get("schema") != FPGA_PHYSICAL_TRACE_SCHEMA:
            raise ValueError("unsupported physical FPGA trace schema")
        raw_ticks = payload.get("ticks")
        if not isinstance(raw_ticks, list):
            raise TypeError("physical trace ticks must be a JSON list")
        return cls(
            scenario_id=_required_str(payload, "scenario_id"),
            transport=_required_str(payload, "transport"),
            device=_required_str(payload, "device"),
            ticks=tuple(_tick_from_dict(item) for item in raw_ticks),
        )

    def to_tick_traces(self) -> tuple[Any, ...]:
        """Reconstruct the existing backend-neutral traces for comparison."""

        return tuple(tick.snapshot.to_tick_trace() for tick in self.ticks)


def write_physical_fpga_trace_json(
    artifact: PhysicalFpgaTraceArtifact,
    path: str | Path,
) -> Path:
    """Write a deterministic UTF-8 JSON artifact and return its path."""

    if not isinstance(artifact, PhysicalFpgaTraceArtifact):
        raise TypeError("artifact must be PhysicalFpgaTraceArtifact")
    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(artifact.to_dict(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output


def read_physical_fpga_trace_json(path: str | Path) -> PhysicalFpgaTraceArtifact:
    """Read and validate a physical-FPGA trace JSON artifact."""

    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    return PhysicalFpgaTraceArtifact.from_dict(payload)


def _tick_to_dict(capture: PhysicalFpgaTickCapture) -> dict[str, Any]:
    snapshot = capture.snapshot
    return {
        "committed_tick": snapshot.committed_tick,
        "core_fault": capture.core_fault,
        "core_fault_code": capture.core_fault_code,
        "external_event_count": capture.external_event_count,
        "consumed_recurrent_count": capture.consumed_recurrent_count,
        "routed_recurrent_count": capture.routed_recurrent_count,
        "recurrent_current_bank": int(capture.recurrent_current_bank),
        "recurrent_current_count": capture.recurrent_current_count,
        "recurrent_bank0_count": capture.recurrent_bank0_count,
        "recurrent_bank1_count": capture.recurrent_bank1_count,
        "external_input_axons": list(snapshot.external_input_axons),
        "recurrent_input_axons": list(snapshot.recurrent_input_axons),
        "routed_output_axons": list(snapshot.routed_output_axons),
        "synaptic_input": list(snapshot.synaptic_input),
        "state_before_words": [_format_u64(word) for word in snapshot.state_before_words],
        "state_after_words": [_format_u64(word) for word in snapshot.state_after_words],
        "spikes": list(snapshot.spikes),
    }


def _tick_from_dict(payload: Any) -> PhysicalFpgaTickCapture:
    if not isinstance(payload, Mapping):
        raise TypeError("physical trace tick must be a mapping")

    snapshot = FpgaTickTraceSnapshot(
        committed_tick=_required_int(payload, "committed_tick"),
        external_input_axons=_int_tuple(payload, "external_input_axons"),
        recurrent_input_axons=_int_tuple(payload, "recurrent_input_axons"),
        synaptic_input=_int_tuple(payload, "synaptic_input"),
        state_before_words=_u64_tuple(payload, "state_before_words"),
        state_after_words=_u64_tuple(payload, "state_after_words"),
        spikes=_bool_tuple(payload, "spikes"),
        routed_output_axons=_int_tuple(payload, "routed_output_axons"),
    )
    return PhysicalFpgaTickCapture(
        snapshot=snapshot,
        core_fault=_required_bool(payload, "core_fault"),
        core_fault_code=_required_int(payload, "core_fault_code"),
        recurrent_current_bank=bool(_required_bank(payload, "recurrent_current_bank")),
        recurrent_current_count=_required_int(payload, "recurrent_current_count"),
        recurrent_bank0_count=_required_int(payload, "recurrent_bank0_count"),
        recurrent_bank1_count=_required_int(payload, "recurrent_bank1_count"),
        consumed_recurrent_count=_required_int(payload, "consumed_recurrent_count"),
        routed_recurrent_count=_required_int(payload, "routed_recurrent_count"),
        external_event_count=_required_int(payload, "external_event_count"),
    )


def _required_str(payload: Mapping[str, Any], name: str) -> str:
    value = payload.get(name)
    if not isinstance(value, str):
        raise TypeError(f"{name} must be str")
    return value


def _required_int(payload: Mapping[str, Any], name: str) -> int:
    value = payload.get(name)
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    return value


def _required_bool(payload: Mapping[str, Any], name: str) -> bool:
    value = payload.get(name)
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be bool")
    return value


def _required_bank(payload: Mapping[str, Any], name: str) -> int:
    value = _required_int(payload, name)
    if value not in (0, 1):
        raise ValueError(f"{name} must be 0 or 1")
    return value


def _json_list(payload: Mapping[str, Any], name: str) -> list[Any]:
    value = payload.get(name)
    if not isinstance(value, list):
        raise TypeError(f"{name} must be a JSON list")
    return value


def _int_tuple(payload: Mapping[str, Any], name: str) -> tuple[int, ...]:
    values = _json_list(payload, name)
    result: list[int] = []
    for value in values:
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} entries must be ints")
        result.append(value)
    return tuple(result)


def _bool_tuple(payload: Mapping[str, Any], name: str) -> tuple[bool, ...]:
    values = _json_list(payload, name)
    if any(not isinstance(value, bool) for value in values):
        raise TypeError(f"{name} entries must be bools")
    return tuple(values)


def _u64_tuple(payload: Mapping[str, Any], name: str) -> tuple[int, ...]:
    values = _json_list(payload, name)
    result: list[int] = []
    for value in values:
        if not isinstance(value, str) or len(value) != 18 or not value.startswith("0x"):
            raise ValueError(f"{name} entries must be 0x-prefixed 16-digit hex words")
        try:
            parsed = int(value[2:], 16)
        except ValueError as exc:
            raise ValueError(f"{name} contains an invalid hex word") from exc
        if not 0 <= parsed < (1 << 64):
            raise ValueError(f"{name} entry does not fit 64 bits")
        result.append(parsed)
    return tuple(result)


def _format_u64(value: int) -> str:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("64-bit trace word must be int")
    if not 0 <= value < (1 << 64):
        raise ValueError("64-bit trace word is outside unsigned range")
    return f"0x{value:016x}"


def _validate_uint(name: str, value: int, bits: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if not 0 <= value < (1 << bits):
        raise ValueError(f"{name} must fit unsigned {bits} bits")


def _validate_count(name: str, value: int, maximum: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"{name} must be int")
    if not 0 <= value <= maximum:
        raise ValueError(f"{name} is outside physical event capacity")
