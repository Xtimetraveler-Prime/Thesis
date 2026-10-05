"""Logical synapse templates used by destination-side axon expansion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SynapseEntry:
    """One template-local synaptic contribution.

    ``target_compartment`` is added to an axon binding's ``target_offset``.
    Delay and tag are reserved from the start; v2.0 execution currently accepts
    only delay zero.
    """

    target_compartment: int
    weight: int
    delay: int = 0
    tag: int | None = None

    def __post_init__(self) -> None:
        if self.target_compartment < 0:
            raise ValueError("target_compartment cannot be negative")
        if isinstance(self.weight, bool) or not isinstance(self.weight, int):
            raise TypeError("weight must be an int")
        if self.delay < 0:
            raise ValueError("delay cannot be negative")


@dataclass(frozen=True, slots=True)
class SynapseTemplate:
    template_id: int
    entries: tuple[SynapseEntry, ...]
    encoding_profile: str = "effective-integer-v1-compatible"

    def __post_init__(self) -> None:
        if self.template_id < 0:
            raise ValueError("template_id cannot be negative")
        if not self.encoding_profile:
            raise ValueError("encoding_profile cannot be empty")
