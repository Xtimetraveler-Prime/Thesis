"""Frozen application-level configuration for the MNIST deployment profiles."""

from __future__ import annotations

from dataclasses import dataclass

SOURCE_HEIGHT = 28
SOURCE_WIDTH = 28
OUTPUT_NEURONS = 10
PRESENTATION_TICKS = 16

# Both application profiles intentionally use the simplest already-validated
# neuron behavior: same-tick input, full current decay, persistent voltage,
# hard zero reset, zero bias, and no refractory hold.
CURRENT_DECAY = 4096
VOLTAGE_DECAY = 0
RESET_VOLTAGE = 0
REFRACTORY_TICKS = 0
FLOAT_THRESHOLD = 1.0

# Frozen K26 core-v1 implementation capacities audited in MNIST-01.
FPGA_MAX_NEURONS = 256
FPGA_MAX_AXONS = 1024
FPGA_MAX_SYNAPSES = 4096
FPGA_MAX_ROUTES = 4096
FPGA_MAX_EVENTS_PER_TICK = 4096
FPGA_MAX_WEIGHT_FORMATS = 16


@dataclass(frozen=True, slots=True)
class MnistProfile:
    """One frozen application mapping onto the common FPGA-v1 core."""

    name: str
    input_height: int
    input_width: int
    input_axons: int
    max_synapses: int
    crop_border: int | None

    @property
    def dense_synapses(self) -> int:
        return self.input_axons * OUTPUT_NEURONS

    @property
    def is_sparse(self) -> bool:
        return self.name == "native-sparse"


NATIVE_SPARSE = MnistProfile(
    name="native-sparse",
    input_height=28,
    input_width=28,
    input_axons=784,
    max_synapses=FPGA_MAX_SYNAPSES,
    crop_border=None,
)

CROPPED_DENSE = MnistProfile(
    name="cropped-dense",
    input_height=20,
    input_width=20,
    input_axons=400,
    max_synapses=4000,
    crop_border=4,
)

PROFILES = {
    NATIVE_SPARSE.name: NATIVE_SPARSE,
    CROPPED_DENSE.name: CROPPED_DENSE,
}

# Keep the previously implemented dense profile as the default for backwards
# compatibility; all new command-line flows expose --profile explicitly.
DEFAULT_PROFILE = CROPPED_DENSE


def get_profile(profile: str | MnistProfile = DEFAULT_PROFILE) -> MnistProfile:
    """Resolve a profile name while rejecting silent fallbacks."""

    if isinstance(profile, MnistProfile):
        return profile
    if not isinstance(profile, str):
        raise TypeError("profile must be a profile name or MnistProfile")
    try:
        return PROFILES[profile]
    except KeyError as exc:
        raise ValueError(
            f"unknown MNIST profile {profile!r}; expected one of {tuple(PROFILES)}"
        ) from exc


for _profile in PROFILES.values():
    if _profile.input_axons > FPGA_MAX_AXONS:
        raise RuntimeError(f"{_profile.name} exceeds FPGA axon capacity")
    if OUTPUT_NEURONS > FPGA_MAX_NEURONS:
        raise RuntimeError(f"{_profile.name} exceeds FPGA neuron capacity")
    if _profile.max_synapses > FPGA_MAX_SYNAPSES:
        raise RuntimeError(f"{_profile.name} exceeds FPGA synapse capacity")
    if _profile.input_axons > FPGA_MAX_EVENTS_PER_TICK:
        raise RuntimeError(f"{_profile.name} exceeds FPGA event capacity")

if CROPPED_DENSE.dense_synapses != 4000:
    raise RuntimeError("cropped-dense profile must contain exactly 4000 dense edges")
