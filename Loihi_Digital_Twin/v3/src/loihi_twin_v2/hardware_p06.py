"""FPGA image export from the P06 compiled deployment artifact."""

from __future__ import annotations

from dataclasses import dataclass

from .compiler import CompiledDeployment
from .hardware_p05 import (
    P05_MAX_RESIDENT_CONTEXTS,
    VirtualizedHardwareImage,
    export_virtualized_hardware_image,
)

P06_FPGA_PROFILE_NAME = "p06-compiled-p05-context-image-v1"


@dataclass(frozen=True, slots=True)
class CompiledFpgaImage:
    profile: str
    compiled_deployment_fingerprint: str
    source_fingerprint: str
    hardware_image: VirtualizedHardwareImage

    @property
    def logical_core_count(self) -> int:
        return self.hardware_image.logical_core_count

    @property
    def logical_to_context_slot(self) -> dict[int, int]:
        return self.hardware_image.logical_to_context_slot

    def report(self) -> dict[str, object]:
        return {
            "profile": self.profile,
            "compiled_deployment_fingerprint": self.compiled_deployment_fingerprint,
            "source_fingerprint": self.source_fingerprint,
            "logical_core_count": self.logical_core_count,
            "physical_engine_count": self.hardware_image.physical_engine_count,
            "logical_to_context_slot": self.logical_to_context_slot,
            "hardware": self.hardware_image.report(),
            "logical_capacity_changed": False,
        }


def export_compiled_fpga_image(compiled: CompiledDeployment) -> CompiledFpgaImage:
    """Export the exact compiled logical cores into the accepted P05 FPGA shell.

    The first physical P06 target intentionally reuses P05's three resident full
    contexts and one physical engine. Mapping itself can produce more logical
    cores; a larger deployment is rejected here rather than silently truncated.
    """

    core_configs = compiled.logical_deployment.core_configs
    if len(core_configs) > P05_MAX_RESIDENT_CONTEXTS:
        raise ValueError(
            "compiled deployment exceeds the currently resident P05 FPGA context count: "
            f"logical_cores={len(core_configs)} resident_contexts={P05_MAX_RESIDENT_CONTEXTS}"
        )
    hardware = export_virtualized_hardware_image(core_configs)
    return CompiledFpgaImage(
        profile=P06_FPGA_PROFILE_NAME,
        compiled_deployment_fingerprint=compiled.fingerprint,
        source_fingerprint=compiled.source_fingerprint,
        hardware_image=hardware,
    )
