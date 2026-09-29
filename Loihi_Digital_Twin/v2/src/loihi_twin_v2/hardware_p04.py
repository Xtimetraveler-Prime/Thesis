"""P04 two-core physical validation-image contract.

P04 intentionally uses resource-scaled *physical* backing memories for its
directed two-endpoint K26 fixture because two complete P03 BRAM shells do not
fit simultaneously.  This module does not redefine Loihi logical capacity.
Logical validity is still enforced by :mod:`resources` and
:class:`LogicalCoreConfig`; the limits below only describe the retained address
space of the P04 directed hardware fixture.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core import LogicalCoreConfig
from .hardware_p03 import OneCoreHardwareImage, export_one_core_image

P04_PROFILE_NAME = "p04-k26-two-endpoint-directed-v1"

# Physical validation allocation.  These are deliberately much smaller than the
# logical Loihi limits and must never be reported as logical core capacities.
P04_PHYSICAL_COMPARTMENTS = 16
P04_PHYSICAL_INPUT_AXONS = 64
P04_PHYSICAL_SYNAPSE_ENTRIES = 256
P04_PHYSICAL_OUTPUT_ROUTES = 64
P04_PHYSICAL_INPUT_EVENTS = 64
P04_PHYSICAL_OUTPUT_PACKETS = 64


@dataclass(frozen=True, slots=True)
class TwoCoreValidationImage:
    profile: str
    core0: OneCoreHardwareImage
    core1: OneCoreHardwareImage

    @property
    def core_images(self) -> tuple[OneCoreHardwareImage, OneCoreHardwareImage]:
        return (self.core0, self.core1)


def _validate_physical_fixture_image(image: OneCoreHardwareImage) -> None:
    """Reject images that cannot be retained by the directed P04 fixture.

    This check is intentionally separate from logical resource validation.  A
    configuration can be perfectly valid architecturally yet too large for this
    temporary P04 physical test shell; P05 is where transparent full-context
    storage/scheduling is addressed.
    """

    if image.compartment_count > P04_PHYSICAL_COMPARTMENTS:
        raise ValueError(
            "P04 directed fixture compartment allocation exceeded; "
            "logical capacity is unchanged"
        )
    if image.synapse_count > P04_PHYSICAL_SYNAPSE_ENTRIES:
        raise ValueError(
            "P04 directed fixture synapse allocation exceeded; logical capacity is unchanged"
        )
    if image.route_count > P04_PHYSICAL_OUTPUT_ROUTES:
        raise ValueError(
            "P04 directed fixture route allocation exceeded; logical capacity is unchanged"
        )
    if any(seed.index >= P04_PHYSICAL_INPUT_AXONS for seed in image.axon_words):
        raise ValueError(
            "P04 directed fixture axon address allocation exceeded; logical capacity is unchanged"
        )
    if any(
        seed.index >= P04_PHYSICAL_COMPARTMENTS
        for seed in image.route_descriptor_words
    ):
        raise ValueError(
            "P04 directed fixture route-descriptor address allocation exceeded; "
            "logical capacity is unchanged"
        )


def export_two_core_validation_image(
    core_configs: tuple[LogicalCoreConfig, LogicalCoreConfig],
) -> TwoCoreValidationImage:
    """Pack exactly logical cores 0 and 1 for the P04 directed fixture."""

    if len(core_configs) != 2:
        raise ValueError("P04 directed hardware fixture requires exactly two cores")
    configs = {config.core_id: config for config in core_configs}
    if set(configs) != {0, 1}:
        raise ValueError("P04 directed hardware fixture requires logical core IDs 0 and 1")

    for config in configs.values():
        for route_entry in config.output_routes:
            for route in route_entry.routes:
                if route.destination_core not in (0, 1):
                    raise ValueError(
                        "P04 two-endpoint fixture cannot route to an uninstantiated core"
                    )
                if route.destination_axon >= P04_PHYSICAL_INPUT_AXONS:
                    raise ValueError(
                        "P04 routed destination axon exceeds directed fixture address space; "
                        "logical capacity is unchanged"
                    )

    core0 = export_one_core_image(configs[0])
    core1 = export_one_core_image(configs[1])
    _validate_physical_fixture_image(core0)
    _validate_physical_fixture_image(core1)
    return TwoCoreValidationImage(P04_PROFILE_NAME, core0, core1)
