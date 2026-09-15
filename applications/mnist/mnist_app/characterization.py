from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CHARACTERIZATION_SCHEMA = "neuromorphic-twin-mnist-characterization-v1"
PROFILE_ORDER = ("cropped-dense", "native-sparse")

# Frozen application/core boundary.
OUTPUT_NEURONS = 10
CLOCK_HZ = 100_000_000
CONFIG_WORD_BITS = 128
STATE_WORD_BITS = 64
FORMAT_WORD_BITS = 16
SYNAPSE_WORD_BITS = 32
ROW_POINTER_BITS = 32

# M12.5 physically characterized no-route timing decomposition for FPGA-v1.
# For feed-forward workloads with no recurrent routes:
#   cycles/tick = 16 * neurons + 10 + 4 * input_events + 4 * synapse_visits
# MNIST-10 treats results computed from this relation as model-derived until a
# direct MNIST runtime characterization image confirms them physically.
BASE_CYCLES_PER_NEURON = 16
BASE_FIXED_CYCLES = 10
INPUT_EVENT_CYCLES = 4
SYNAPSE_VISIT_CYCLES = 4


def _read_json(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def static_profile_bits(*, input_axons: int, stored_synapses: int, formats: int = 2) -> int:
    """Logical frozen deployment bits attributable to one MNIST profile.

    This intentionally excludes fixed core-capacity buffers, debug/VIO logic,
    bitstream overhead, and the second profile in the shared MNIST-09 image.
    It is therefore a logical deployment-footprint metric, not FPGA BRAM use.
    """

    return (
        OUTPUT_NEURONS * CONFIG_WORD_BITS
        + OUTPUT_NEURONS * STATE_WORD_BITS
        + formats * FORMAT_WORD_BITS
        + stored_synapses * SYNAPSE_WORD_BITS
        + (input_axons + 1) * ROW_POINTER_BITS
        + (OUTPUT_NEURONS + 1) * ROW_POINTER_BITS  # empty route CSR rows
    )


def modeled_cycles_per_image(
    *,
    presentation_ticks: int,
    mean_input_events: float,
    mean_synaptic_visits: float,
    neurons: int = OUTPUT_NEURONS,
) -> float:
    base_per_tick = BASE_CYCLES_PER_NEURON * neurons + BASE_FIXED_CYCLES
    return (
        presentation_ticks * base_per_tick
        + INPUT_EVENT_CYCLES * mean_input_events
        + SYNAPSE_VISIT_CYCLES * mean_synaptic_visits
    )


def build_characterization_baseline(
    accepted_validation_path: str | Path,
    *,
    clock_hz: int = CLOCK_HZ,
) -> dict[str, Any]:
    accepted = _read_json(accepted_validation_path)
    if accepted.get("schema") != "neuromorphic-twin-mnist-accepted-validation-v1":
        raise ValueError("unsupported accepted-validation schema")
    profiles = accepted.get("profiles")
    if not isinstance(profiles, dict):
        raise ValueError("accepted validation is missing profiles")

    result_profiles: dict[str, Any] = {}
    for profile in PROFILE_ORDER:
        record = profiles[profile]
        checkpoint = record["checkpoint"]
        summary = record["summary"]
        ticks = int(checkpoint["presentation_ticks"])
        input_axons = int(checkpoint["input_axons"])
        stored_synapses = int(summary["deployment_stored_synapses"])
        mean_events = float(summary["golden_mean_input_events"])
        mean_visits = float(summary["golden_mean_synaptic_visits"])
        mean_spikes = float(summary["golden_mean_output_spikes"])
        modeled_cycles = modeled_cycles_per_image(
            presentation_ticks=ticks,
            mean_input_events=mean_events,
            mean_synaptic_visits=mean_visits,
        )
        latency_s = modeled_cycles / clock_hz
        logical_bits = static_profile_bits(
            input_axons=input_axons,
            stored_synapses=stored_synapses,
        )
        result_profiles[profile] = {
            "accuracy": {
                "golden": float(summary["golden_accuracy"]),
                "source": "accepted full 10,000-image FPGA-v1 golden evaluation",
                "status": "measured-software-golden",
            },
            "workload": {
                "images": int(summary["images"]),
                "presentation_ticks": ticks,
                "input_axons": input_axons,
                "output_neurons": OUTPUT_NEURONS,
                "stored_synapses": stored_synapses,
                "mean_input_events_per_image": mean_events,
                "mean_synaptic_visits_per_image": mean_visits,
                "mean_output_spikes_per_image": mean_spikes,
                "status": "measured-software-golden",
            },
            "logical_static_deployment_memory": {
                "bits": logical_bits,
                "bytes": logical_bits / 8.0,
                "kibibytes": logical_bits / 8.0 / 1024.0,
                "status": "derived-from-frozen-storage-schema",
                "scope": "profile-attributable config/state/format/synapse/CSR words only",
            },
            "architectural_timing_model": {
                "clock_hz": clock_hz,
                "mean_cycles_per_image": modeled_cycles,
                "mean_latency_ms": latency_s * 1000.0,
                "modeled_images_per_second": 1.0 / latency_s,
                "equation": "ticks*(16*neurons+10) + 4*input_events + 4*synapse_visits",
                "status": "model-derived-from-M12.5-physical-decomposition; direct-MNIST-spot-check-pending",
            },
        }

    cropped = result_profiles["cropped-dense"]
    native = result_profiles["native-sparse"]
    comparison = {
        "native_minus_cropped_accuracy_pp": 100.0
        * (native["accuracy"]["golden"] - cropped["accuracy"]["golden"]),
        "native_to_cropped_input_event_ratio": native["workload"]["mean_input_events_per_image"]
        / cropped["workload"]["mean_input_events_per_image"],
        "native_to_cropped_synaptic_visit_ratio": native["workload"]["mean_synaptic_visits_per_image"]
        / cropped["workload"]["mean_synaptic_visits_per_image"],
        "native_to_cropped_output_spike_ratio": native["workload"]["mean_output_spikes_per_image"]
        / cropped["workload"]["mean_output_spikes_per_image"],
        "native_to_cropped_modeled_cycle_ratio": native["architectural_timing_model"]["mean_cycles_per_image"]
        / cropped["architectural_timing_model"]["mean_cycles_per_image"],
        "native_to_cropped_logical_static_memory_ratio": native["logical_static_deployment_memory"]["bits"]
        / cropped["logical_static_deployment_memory"]["bits"],
    }

    return {
        "schema": CHARACTERIZATION_SCHEMA,
        "corpus": accepted["corpus"],
        "profiles": result_profiles,
        "comparison": comparison,
        "measurement_policy": {
            "architectural_time": "PL cycle count only; excludes JTAG/VIO/Python transport",
            "energy": "not claimed until a defensible board/chip measurement boundary is established",
            "loihi": "external Loihi figures are maintained separately with source-level provenance and comparability caveats",
        },
    }


def write_characterization_baseline(
    accepted_validation_path: str | Path,
    output_path: str | Path,
    *,
    clock_hz: int = CLOCK_HZ,
) -> Path:
    payload = build_characterization_baseline(accepted_validation_path, clock_hz=clock_hz)
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target
