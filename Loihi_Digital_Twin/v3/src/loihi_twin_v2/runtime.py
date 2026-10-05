"""Deterministic multi-timestep execution and replay helpers for P02."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Mapping

from .mapping import Deployment
from .packet import SpikePacket
from .reporting import trace_report
from .trace import ChipTrace


@dataclass(frozen=True, slots=True)
class RunResult:
    """One complete logical run of a versioned deployment."""

    deployment_fingerprint: str
    traces: tuple[ChipTrace, ...]

    @property
    def trace_fingerprint(self) -> str:
        payload = json.dumps(
            [trace_report(trace) for trace in self.traces],
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def normalized(self) -> tuple:
        return tuple(trace.normalized() for trace in self.traces)


def run_deployment(
    deployment: Deployment,
    timesteps: int,
    *,
    external_schedule: Mapping[int, tuple[SpikePacket, ...]] | None = None,
    service_order_schedule: Mapping[int, tuple[int, ...]] | None = None,
    reverse_packet_drain_timesteps: frozenset[int] = frozenset(),
) -> RunResult:
    """Run a deployment for a fixed number of algorithmic timesteps.

    Scheduling knobs are intentionally explicit so P02 can prove that legal
    physical/service ordering choices do not alter normalized architecture
    behavior.
    """

    if timesteps < 0:
        raise ValueError("timesteps cannot be negative")

    external_schedule = external_schedule or {}
    service_order_schedule = service_order_schedule or {}

    for timestep in external_schedule:
        if not 0 <= timestep < timesteps:
            raise ValueError("external schedule contains a timestep outside the run")
    for timestep in service_order_schedule:
        if not 0 <= timestep < timesteps:
            raise ValueError("service-order schedule contains a timestep outside the run")
    for timestep in reverse_packet_drain_timesteps:
        if not 0 <= timestep < timesteps:
            raise ValueError("reverse-drain schedule contains a timestep outside the run")

    chip = deployment.build_chip()
    traces: list[ChipTrace] = []
    for timestep in range(timesteps):
        packets = tuple(external_schedule.get(timestep, ()))
        for packet in packets:
            if packet.target_timestep != timestep:
                raise ValueError(
                    "external packet target_timestep must match its schedule timestep"
                )
        traces.append(
            chip.step(
                external_packets=packets,
                service_order=service_order_schedule.get(timestep),
                reverse_packet_drain=timestep in reverse_packet_drain_timesteps,
            )
        )

    return RunResult(
        deployment_fingerprint=deployment.fingerprint,
        traces=tuple(traces),
    )
