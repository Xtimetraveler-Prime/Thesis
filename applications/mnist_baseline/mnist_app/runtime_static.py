"""Generate the two frozen static deployment images used by MNIST-09 runtime."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence

from .runtime import PROFILE_ID, PROFILE_ORDER


@dataclass(frozen=True, slots=True)
class RuntimeStaticProfile:
    profile: str
    profile_id: int
    config_words: tuple[int, ...]
    initial_state_words: tuple[int, ...]
    format_words: tuple[int, ...]
    synapse_words: tuple[int, ...]
    weight_rows: tuple[int, ...]
    route_rows: tuple[int, ...]
    route_targets: tuple[int, ...]

    @property
    def neuron_count(self) -> int:
        return len(self.config_words)

    @property
    def axon_count(self) -> int:
        return len(self.weight_rows) - 1

    @property
    def synapse_count(self) -> int:
        return len(self.synapse_words)

    @property
    def format_count(self) -> int:
        return len(self.format_words)

    @property
    def route_count(self) -> int:
        return len(self.route_targets)


def load_runtime_static_profiles(frozen_root: str | Path) -> tuple[RuntimeStaticProfile, ...]:
    from neuromorphic_twin import NeuronConfig, NeuronState, read_weight_storage_json
    from neuromorphic_twin.fpga_core_capacity import (
        pack_neuron_config_word,
        pack_neuron_state_word,
    )

    root = Path(frozen_root)
    profiles: list[RuntimeStaticProfile] = []
    for profile_name in PROFILE_ORDER:
        deployment = root / "deployments" / profile_name / "deployment.json"
        payload = json.loads(deployment.read_text(encoding="utf-8"))
        if payload.get("profile") != profile_name:
            raise ValueError("runtime frozen deployment profile mismatch")
        storage = read_weight_storage_json(deployment.parent / str(payload["weight_storage"]))
        configs = tuple(NeuronConfig(**row) for row in payload["neuron_configs"])
        profiles.append(
            RuntimeStaticProfile(
                profile=profile_name,
                profile_id=PROFILE_ID[profile_name],
                config_words=tuple(pack_neuron_config_word(config) for config in configs),
                initial_state_words=tuple(
                    pack_neuron_state_word(NeuronState()) for _ in configs
                ),
                format_words=tuple(storage.format_words),
                synapse_words=tuple(storage.synapse_words),
                weight_rows=tuple(storage.axon_row_pointers),
                route_rows=tuple(0 for _ in range(len(configs) + 1)),
                route_targets=(),
            )
        )
    return tuple(profiles)


def _pad(values: Sequence[int], count: int) -> tuple[int, ...]:
    values = tuple(int(value) for value in values)
    if len(values) > count:
        raise ValueError("runtime static image exceeds generated stride")
    return values + (0,) * (count - len(values))


def _hex(value: int, width: int) -> str:
    return f"{value & ((1 << width) - 1):0{(width + 3) // 4}x}"


def write_runtime_static_include(
    profiles: Sequence[RuntimeStaticProfile],
    output: str | Path,
) -> Path:
    selected = tuple(profiles)
    if tuple(profile.profile for profile in selected) != PROFILE_ORDER:
        raise ValueError("runtime static profiles must use frozen profile order")

    max_neurons = max(profile.neuron_count for profile in selected)
    max_axons = max(profile.axon_count for profile in selected)
    max_synapses = max(profile.synapse_count for profile in selected)
    max_formats = max(profile.format_count for profile in selected)
    max_routes = max(1, max(profile.route_count for profile in selected))

    lines = [
        "// Generated MNIST-09 dual-profile runtime image; do not edit.",
        "// Contains frozen static deployment data only. Runtime events arrive over VIO.",
        f"localparam int M12_3_CASE_COUNT = {len(selected)};",
        f"localparam int M12_3_MAX_NEURONS = {max_neurons};",
        f"localparam int M12_3_MAX_AXONS = {max_axons};",
        f"localparam int M12_3_MAX_SYNAPSES = {max_synapses};",
        f"localparam int M12_3_MAX_FORMATS = {max_formats};",
        f"localparam int M12_3_MAX_ROUTES = {max_routes};",
        "localparam int M12_3_MAX_TICKS = 16;",
        "localparam int M12_3_MAX_EXTERNAL_EVENTS = 4096;",
        "",
    ]

    def emit(name: str, width: int, values: Sequence[int]) -> None:
        words = tuple(int(value) for value in values)
        if not words:
            raise ValueError(f"cannot emit empty runtime array {name}")
        lines.append(
            f"localparam logic [{width - 1}:0] {name} [0:{len(words) - 1}] = '{{"
        )
        for index, word in enumerate(words):
            comma = "," if index + 1 < len(words) else ""
            lines.append(f"    {width}'h{_hex(word, width)}{comma}")
        lines.append("};")
        lines.append("")

    emit("M12_3_NEURON_COUNTS", 9, [p.neuron_count for p in selected])
    emit("M12_3_AXON_COUNTS", 11, [p.axon_count for p in selected])
    emit("M12_3_SYNAPSE_COUNTS", 13, [p.synapse_count for p in selected])
    emit("M12_3_FORMAT_COUNTS", 5, [p.format_count for p in selected])
    emit("M12_3_ROUTE_COUNTS", 13, [p.route_count for p in selected])
    emit("M12_3_TICK_COUNTS", 8, [16 for _ in selected])
    emit(
        "M12_3_CONFIG_WORDS",
        128,
        [word for p in selected for word in _pad(p.config_words, max_neurons)],
    )
    emit(
        "M12_3_INITIAL_STATE_WORDS",
        64,
        [word for p in selected for word in _pad(p.initial_state_words, max_neurons)],
    )
    emit(
        "M12_3_FORMAT_WORDS",
        16,
        [word for p in selected for word in _pad(p.format_words, max_formats)],
    )
    emit(
        "M12_3_SYNAPSE_WORDS",
        32,
        [word for p in selected for word in _pad(p.synapse_words, max_synapses)],
    )
    emit(
        "M12_3_WEIGHT_ROWS",
        32,
        [word for p in selected for word in _pad(p.weight_rows, max_axons + 1)],
    )
    emit(
        "M12_3_ROUTE_ROWS",
        32,
        [word for p in selected for word in _pad(p.route_rows, max_neurons + 1)],
    )
    emit(
        "M12_3_ROUTE_TARGETS",
        16,
        [word for p in selected for word in _pad(p.route_targets, max_routes)],
    )

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines), encoding="utf-8")
    return target
