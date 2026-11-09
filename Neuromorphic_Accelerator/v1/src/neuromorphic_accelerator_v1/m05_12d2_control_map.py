"""M05.12d.2b: *proposed*, uncommitted-to-hardware PS control address map.

Six DIFFERENT AXI4-Lite slaves need independently decoded apertures:
four AXI DMA register banks, the custom M05.11 shell and Vitis HLS control.
This is pure input validation, NOT Vivado address assignment, MMIO driver,
physical address discovery, DDR allocation, Linux /dev/mem, or coherency.

No default base addresses: an operator must eventually supply real Vivado
assign_bd_address + readback evidence and Linux resource ownership proof.
"""
from __future__ import annotations

from dataclasses import dataclass

BANKS = (
    "dma_neurons", "dma_synapses", "dma_external",
    "dma_trace", "shell", "hls",
)
DMA_MM2S = ("dma_neurons", "dma_synapses", "dma_external")
MIN_APERTURE_BYTES = 4096
MAX_APERTURE_BYTES = 1 << 20
MAX_PS_PHYS_EXCLUSIVE = 1 << 40  # upper bound only; does NOT prove an aperture is decodable

# PG021 direct/simple DMA registers and existing M05.11b VERSION register.
# HLS native regmap is still generated-IP-specific and must be independently
# confirmed from genuine HLS RTL. Checking hls offset0 is NOT HLS reg proof.
LAST_REQUIRED_OFFSET = {
    "dma_neurons": 0x28, "dma_synapses": 0x28, "dma_external": 0x28,
    "dma_trace": 0x58,
    "shell": 0x38, "hls": 0x00,
}
REGISTERS = {
    "dma_neurons": {"DMACR": 0x00, "DMASR": 0x04,
                    "SA_LOW": 0x18, "LENGTH": 0x28},
    "dma_synapses": {"DMACR": 0x00, "DMASR": 0x04,
                     "SA_LOW": 0x18, "LENGTH": 0x28},
    "dma_external": {"DMACR": 0x00, "DMASR": 0x04,
                     "SA_LOW": 0x18, "LENGTH": 0x28},
    "dma_trace": {"DMACR": 0x30, "DMASR": 0x34,
                  "DA_LOW": 0x48, "LENGTH": 0x58},
    "shell": {"CMD": 0x00, "STATE": 0x04, "VERSION": 0x38},
    "hls": {},
}


class AddressAdmissionError(ValueError):
    """Address map is not safe even as a proposed, offline control plan."""


@dataclass(frozen=True)
class ProposedAperture:
    """Not an actual validated PS physical region or registered kernel mapping."""

    bank: str
    base: int
    length_bytes: int = MIN_APERTURE_BYTES

    def __post_init__(self) -> None:
        if self.bank not in BANKS or type(self.bank) is not str:
            raise AddressAdmissionError("unknown PS/PL control slave")
        if type(self.base) is not int or self.base <= 0:
            raise AddressAdmissionError("explicit positive integer base required")
        if type(self.length_bytes) is not int:
            raise AddressAdmissionError("length must be explicit integer bytes")
        if not (MIN_APERTURE_BYTES <= self.length_bytes <= MAX_APERTURE_BYTES
                and self.length_bytes % MIN_APERTURE_BYTES == 0):
            raise AddressAdmissionError("control aperture must be 4KiB-granular")
        if self.base % MIN_APERTURE_BYTES:
            raise AddressAdmissionError("control base must be 4KiB-aligned")
        if self.base + self.length_bytes > MAX_PS_PHYS_EXCLUSIVE:
            raise AddressAdmissionError("candidate range exceeds 40-bit PS address bound")
        if LAST_REQUIRED_OFFSET[self.bank] + 4 > self.length_bytes:
            raise AddressAdmissionError("bank cannot fit minimum known register")

    @property
    def end_exclusive(self) -> int:
        return self.base + self.length_bytes


@dataclass(frozen=True)
class ProposedControlMap:
    """Immutable six-slave candidate only; cannot apply a Vivado/OS address map."""

    apertures: tuple[ProposedAperture, ...]

    def __post_init__(self) -> None:
        if type(self.apertures) is not tuple:
            raise AddressAdmissionError("immutable tuple of six apertures required")
        if (len(self.apertures) != len(BANKS)
                or any(type(x) is not ProposedAperture for x in self.apertures)):
            raise AddressAdmissionError("exactly six explicitly typed apertures required")
        names = tuple(item.bank for item in self.apertures)
        if len(set(names)) != len(BANKS) or set(names) != set(BANKS):
            raise AddressAdmissionError("all four DMA, shell and HLS banks must be independent")
        regions = sorted(self.apertures, key=lambda x: x.base)
        for prev, nxt in zip(regions, regions[1:]):
            if prev.end_exclusive > nxt.base:
                raise AddressAdmissionError(
                    f"overlapping proposed PS control apertures: {prev.bank}, {nxt.bank}"
                )

    def aperture(self, bank: str) -> ProposedAperture:
        if type(bank) is not str or bank not in BANKS:
            raise AddressAdmissionError("unknown bank")
        return next(item for item in self.apertures if item.bank == bank)

    def proposed_register_address(self, bank: str, register: str) -> int:
        """Candidate-only arithmetic. DOES NOT attest to actual PS decode or MMIO."""
        if type(register) is not str or register not in REGISTERS.get(bank, {}):
            raise AddressAdmissionError("unverified register or generated HLS offset")
        offset = REGISTERS[bank][register]
        target = self.aperture(bank)
        if offset + 4 > target.length_bytes:
            raise AddressAdmissionError("offset exceeds proposed aperture")
        return target.base + offset


def propose_control_map(apertures: tuple[ProposedAperture, ...]) -> ProposedControlMap:
    """No default address allocation and no physical memory operations."""
    return ProposedControlMap(apertures)
