"""Frozen M13.3 common-subset and normalization interface.

This module translates deliberately restricted backend-neutral scenarios into
native plans for the M12 project baseline, Brian2Loihi 0.5.2, Catalyst's
synchronous CPU simulator, and Catalyst's RTL CUBA boundary.  It does not decide
whether different implementations are architecturally correct.  M13.4 consumes
these predeclared transforms and preserves native evidence beside normalized
traces.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from ..model import NeuronConfig, Synapse
from .brian2loihi_backend import run_brian2loihi_backend
from .io import write_trace_json
from .model import BackendTrace, ComparisonScenario
from .python_backend import run_python_backend

M13_3_SCHEMA = "neuromorphic-twin-m13-normalization-v1"
M13_COMMON_SCENARIO_SCHEMA = "neuromorphic-twin-m13-common-scenario-v1"
M13_NATIVE_PLAN_SCHEMA = "neuromorphic-twin-m13-native-plan-v1"
M13_NORMALIZED_TRACE_SCHEMA = "neuromorphic-twin-m13-normalized-trace-v1"
M13_CATALYST_NATIVE_TRACE_SCHEMA = "neuromorphic-twin-m13-catalyst-cpu-native-trace-v1"
M13_TRANSLATION_MANIFEST_SCHEMA = "neuromorphic-twin-m13-translation-smoke-v1"

_FIELD_CATEGORIES = {"exact", "transformed", "qualitative", "non_comparable"}
_INT16_MIN = -(1 << 15)
_INT16_MAX = (1 << 15) - 1


def _project_root() -> Path:
    return Path(__file__).resolve().parents[3]


def default_spec_path() -> Path:
    return _project_root() / "references" / "m13_3_normalization_spec.json"


class M13NormalizationError(ValueError):
    """Raised when a scenario cannot be represented by the frozen M13.3 rules."""


@dataclass(frozen=True, slots=True)
class M13CommonCase:
    name: str
    scenario_class: str
    question: str
    scenario: ComparisonScenario

    def __post_init__(self) -> None:
        if self.name != self.scenario.name:
            raise ValueError("common-case name and scenario name must match")


def load_normalization_spec(path: str | Path | None = None) -> dict[str, Any]:
    source = Path(path) if path is not None else default_spec_path()
    payload = json.loads(source.read_text(encoding="utf-8"))
    validate_normalization_spec(payload)
    return payload


def validate_normalization_spec(payload: Mapping[str, Any]) -> None:
    if payload.get("schema") != M13_3_SCHEMA:
        raise M13NormalizationError(
            f"unexpected M13.3 schema {payload.get('schema')!r}; expected {M13_3_SCHEMA!r}"
        )
    if payload.get("status") != "frozen":
        raise M13NormalizationError("M13.3 normalization specification is not frozen")
    if int(payload.get("version", 0)) != 1:
        raise M13NormalizationError("M13.3 normalization version must be 1")

    categories = set(payload.get("comparison_categories", {}))
    if categories != _FIELD_CATEGORIES:
        raise M13NormalizationError(
            f"comparison categories must be exactly {sorted(_FIELD_CATEGORIES)!r}"
        )

    field_policy = payload.get("field_policy")
    if not isinstance(field_policy, dict) or not field_policy:
        raise M13NormalizationError("field_policy must be a non-empty object")
    for field, participant_policy in field_policy.items():
        if not isinstance(participant_policy, dict) or not participant_policy:
            raise M13NormalizationError(f"field {field!r} has no participant policy")
        invalid = set(participant_policy.values()) - _FIELD_CATEGORIES
        if invalid:
            raise M13NormalizationError(
                f"field {field!r} contains invalid categories {sorted(invalid)!r}"
            )

    raw = json.dumps(payload, sort_keys=True)
    for forbidden in ("discrepancy_class", '"classification"', '"verdict"'):
        if forbidden in raw:
            raise M13NormalizationError(
                "M13.3 must freeze mapping only; discrepancy adjudication belongs to M13.6"
            )


def canonical_threshold_to_brian_mantissa(threshold: int) -> int:
    _validate_canonical_threshold(threshold)
    if threshold % 64:
        raise M13NormalizationError("Brian2Loihi threshold must be divisible by 64")
    mantissa = threshold // 64
    if not 0 <= mantissa <= 131071:
        raise M13NormalizationError("Brian2Loihi threshold mantissa is out of range")
    return mantissa


def canonical_threshold_to_catalyst(threshold: int) -> int:
    """Map strict canonical V>T to Catalyst's integer V>=threshold comparator."""

    _validate_canonical_threshold(threshold)
    native = threshold + 1
    _validate_int16(native, "Catalyst threshold")
    return native


def catalyst_threshold_to_canonical(native_threshold: int) -> int:
    _validate_int16(native_threshold, "Catalyst threshold")
    threshold = native_threshold - 1
    _validate_canonical_threshold(threshold)
    return threshold


def canonical_refractory_to_catalyst(duration: int) -> int:
    if not 1 <= duration <= 64:
        raise M13NormalizationError("shared refractory duration must be in 1..64")
    return duration - 1


def canonical_effective_weight_to_brian_mantissa(weight: int) -> int:
    if weight % 64:
        raise M13NormalizationError("shared legacy effective weight must be divisible by 64")
    mantissa = weight // 64
    if not -256 <= mantissa <= 255:
        raise M13NormalizationError("shared legacy Brian2Loihi mantissa is out of range")
    return mantissa


def canonical_effective_weight_to_catalyst(weight: int) -> int:
    _validate_int16(weight, "Catalyst effective weight")
    return weight


def canonical_decay_to_catalyst_rtl(decay: int) -> int:
    if not 0 <= decay <= 4095:
        raise M13NormalizationError(
            "Catalyst RTL CUBA shared decay must fit its 12-bit 0..4095 field"
        )
    return decay


def catalyst_cuba_native_tick_for_canonical(canonical_tick: int) -> int:
    if canonical_tick < 0:
        raise M13NormalizationError("canonical tick cannot be negative")
    return canonical_tick + 1


def build_small_translation_corpus() -> tuple[M13CommonCase, ...]:
    """Return the frozen M13.3 translation-smoke corpus.

    These cases prove that the normalization interface can generate native plans.
    They are intentionally not the M13.4 differential-probe result set.
    """

    threshold = M13CommonCase(
        name="m13-3-threshold-boundary",
        scenario_class="cpu_direct_drive",
        question="Strict equality and just-over-threshold after Catalyst T+1 mapping.",
        scenario=ComparisonScenario.build(
            name="m13-3-threshold-boundary",
            neuron_configs=[_config(threshold=256, refractory_ticks=1)],
            synapses=[Synapse(0, 0, 256), Synapse(1, 0, 64)],
            input_schedule=[(0,), (1,)],
        ),
    )
    refractory = M13CommonCase(
        name="m13-3-refractory-release",
        scenario_class="cpu_direct_drive",
        question="Canonical three-tick refractory duration and first eligible tick.",
        scenario=ComparisonScenario.build(
            name="m13-3-refractory-release",
            neuron_configs=[_config(threshold=256, refractory_ticks=3)],
            synapses=[Synapse(0, 0, 320)],
            input_schedule=[(0,), (0,), (0,), (0,), ()],
        ),
    )
    signed_drive = M13CommonCase(
        name="m13-3-signed-drive",
        scenario_class="cpu_direct_drive",
        question="Positive and negative effective drive combine in canonical integer units.",
        scenario=ComparisonScenario.build(
            name="m13-3-signed-drive",
            neuron_configs=[_config(threshold=4096, refractory_ticks=1)],
            synapses=[Synapse(0, 0, 192), Synapse(1, 0, -64)],
            input_schedule=[(0, 1), ()],
        ),
    )
    cuba_decay = M13CommonCase(
        name="m13-3-isolated-cuba-decay",
        scenario_class="rtl_cuba_isolated_impulse",
        question="Isolated dual-state impulse with one Catalyst native staging tick.",
        scenario=ComparisonScenario.build(
            name="m13-3-isolated-cuba-decay",
            neuron_configs=[
                NeuronConfig(
                    current_decay=2048,
                    voltage_decay=2048,
                    threshold=8192,
                    bias=0,
                    reset_voltage=0,
                    refractory_ticks=1,
                )
            ],
            synapses=[Synapse(0, 0, 512)],
            input_schedule=[(0,), (), (), ()],
        ),
    )
    return (threshold, refractory, signed_drive, cuba_decay)


def build_project_native_plan(case: M13CommonCase) -> dict[str, Any]:
    return {
        "schema": M13_NATIVE_PLAN_SCHEMA,
        "backend": "project_fpga_v1",
        "profile": "comparison-scenario",
        "scenario": scenario_to_payload(case.scenario),
        "normalization": {
            "tick": "identity",
            "state_unit": "identity",
            "logical_neuron_id": "identity",
        },
    }


def build_brian2loihi_native_plan(case: M13CommonCase) -> dict[str, Any]:
    scenario = case.scenario
    configs = scenario.neuron_configs
    if any(config != configs[0] for config in configs[1:]):
        raise M13NormalizationError(
            "current Brian2Loihi comparison adapter requires one shared neuron config"
        )
    config = configs[0]
    if config.bias != 0 or config.reset_voltage != 0:
        raise M13NormalizationError("Brian2Loihi common subset requires zero bias/reset")
    if not 1 <= config.refractory_ticks <= 64:
        raise M13NormalizationError("Brian2Loihi common refractory must be in 1..64")

    synapses = []
    for synapse in scenario.synapses:
        if synapse.encoding is None:
            mantissa = canonical_effective_weight_to_brian_mantissa(synapse.weight)
            sign_mode = "excitatory" if synapse.weight >= 0 else "inhibitory"
            synapses.append(
                {
                    "axon_id": synapse.axon_id,
                    "target_neuron": synapse.target_neuron,
                    "mantissa": mantissa,
                    "exponent": 0,
                    "num_weight_bits": 8,
                    "sign_mode": sign_mode,
                    "canonical_effective_weight": synapse.weight,
                }
            )
        else:
            enc = synapse.encoding
            fmt = enc.weight_format
            synapses.append(
                {
                    "axon_id": synapse.axon_id,
                    "target_neuron": synapse.target_neuron,
                    "mantissa": enc.requested_mantissa,
                    "exponent": fmt.exponent,
                    "num_weight_bits": fmt.num_weight_bits,
                    "sign_mode": fmt.sign_mode.value,
                    "canonical_effective_weight": enc.effective_weight,
                }
            )

    return {
        "schema": M13_NATIVE_PLAN_SCHEMA,
        "backend": "brian2loihi_0_5_2",
        "profile": "LoihiNetwork-point-neuron",
        "neuron": {
            "count": len(configs),
            "threshold_v_mant": canonical_threshold_to_brian_mantissa(config.threshold),
            "decay_I": config.current_decay,
            "decay_v": config.voltage_decay,
            "refractory": config.refractory_ticks,
            "reset_voltage": 0,
        },
        "synapses": synapses,
        "input_schedule": [list(tick) for tick in scenario.input_schedule],
        "normalization": {
            "threshold": "native_mantissa * 64",
            "effective_weight": "w_act",
            "tick": "committed LoihiNetwork step",
            "state_unit": "identity after existing effective-value adapter",
        },
    }


def build_catalyst_cpu_native_plan(case: M13CommonCase) -> dict[str, Any]:
    if case.scenario_class != "cpu_direct_drive":
        raise M13NormalizationError("Catalyst CPU direct-drive plan requires cpu_direct_drive class")
    scenario = case.scenario
    if scenario.spike_routes:
        raise M13NormalizationError("cpu_direct_drive does not normalize recurrent routes")

    native_params = []
    for config in scenario.neuron_configs:
        if config.current_decay != 4096:
            raise M13NormalizationError(
                "cpu_direct_drive requires canonical current_decay=4096"
            )
        if config.voltage_decay != 0:
            raise M13NormalizationError(
                "cpu_direct_drive requires canonical voltage_decay=0"
            )
        if config.bias != 0 or config.reset_voltage != 0:
            raise M13NormalizationError("cpu_direct_drive requires zero bias/reset")
        native_params.append(
            {
                "threshold": canonical_threshold_to_catalyst(config.threshold),
                "leak": 0,
                "resting": 0,
                "refrac": canonical_refractory_to_catalyst(config.refractory_ticks),
            }
        )

    schedule = collapse_external_drive(scenario)
    for tick, values in enumerate(schedule):
        for neuron_id, value in enumerate(values):
            _validate_int16(value, f"Catalyst direct current tick {tick} neuron {neuron_id}")

    return {
        "schema": M13_NATIVE_PLAN_SCHEMA,
        "backend": "catalyst_cpu_sync",
        "profile": "direct-current-equivalent",
        "scenario": scenario.name,
        "neuron_params": native_params,
        "direct_current_schedule": [list(values) for values in schedule],
        "required_settings": {
            "async_enable": False,
            "learn_enable": False,
            "graded_enable": False,
            "dendritic_enable": False,
            "noise_enable": False,
        },
        "normalization": {
            "threshold": "canonical T -> native T+1; native threshold normalized as T-1",
            "refractory": "canonical R -> native R-1; compare next_eligible_tick",
            "potential": "identity integer units",
            "current": "non_comparable",
            "external_transport": "canonical axon rows collapsed to per-target delivered current",
            "tick": "identity committed synchronous timestep",
        },
    }


def build_catalyst_rtl_cuba_native_plan(case: M13CommonCase) -> dict[str, Any]:
    if case.scenario_class != "rtl_cuba_isolated_impulse":
        raise M13NormalizationError(
            "Catalyst RTL CUBA plan requires rtl_cuba_isolated_impulse class"
        )
    scenario = case.scenario
    _validate_isolated_impulse_schedule(scenario)
    if scenario.spike_routes:
        raise M13NormalizationError("isolated CUBA plan does not include recurrent routes")

    native_params = []
    any_cuba_enable = False
    for config in scenario.neuron_configs:
        if config.bias != 0 or config.reset_voltage != 0:
            raise M13NormalizationError("RTL CUBA common subset requires zero bias/reset")
        decay_u = canonical_decay_to_catalyst_rtl(config.current_decay)
        decay_v = canonical_decay_to_catalyst_rtl(config.voltage_decay)
        any_cuba_enable = any_cuba_enable or decay_u != 0 or decay_v != 0
        native_params.append(
            {
                "threshold": canonical_threshold_to_catalyst(config.threshold),
                "resting": 0,
                "refrac_absolute": canonical_refractory_to_catalyst(
                    config.refractory_ticks
                ),
                "decay_v_param_id_16": decay_v,
                "decay_u_param_id_17": decay_u,
                "bias_cfg_param_id_18": 0,
            }
        )
    if not any_cuba_enable:
        raise M13NormalizationError(
            "Catalyst RTL enters CUBA mode only when decay_v, decay_u, or bias_cfg is nonzero"
        )

    schedule = collapse_external_drive(scenario)
    for tick, values in enumerate(schedule):
        for neuron_id, value in enumerate(values):
            _validate_int16(value, f"Catalyst RTL ext_current tick {tick} neuron {neuron_id}")

    return {
        "schema": M13_NATIVE_PLAN_SCHEMA,
        "backend": "catalyst_rtl_cuba",
        "profile": "isolated-impulse-one-tick-staging",
        "scenario": scenario.name,
        "neuron_params": native_params,
        "ext_current_schedule": [list(values) for values in schedule],
        "required_settings": {
            "scale_u_enable": False,
            "learn_enable": False,
            "graded_enable": False,
            "dendritic_enable": False,
            "noise_enable": False,
        },
        "probe_state_ids": {
            "potential_low16": 0,
            "refractory": 4,
            "current_low16": 13,
        },
        "normalization": {
            "threshold": "canonical T -> native T+1",
            "refractory": "canonical R -> native absolute counter R-1",
            "decay": "canonical d -> native 12-bit d, limited to 0..4095",
            "state_unit": "identity",
            "tick": "preserve native tick 0 as staging; canonical k <- native k+1",
            "warmup_native_ticks": 1,
        },
    }


def build_native_plan(case: M13CommonCase, backend: str) -> dict[str, Any]:
    if backend == "project_fpga_v1":
        return build_project_native_plan(case)
    if backend == "brian2loihi_0_5_2":
        return build_brian2loihi_native_plan(case)
    if backend == "catalyst_cpu_sync":
        return build_catalyst_cpu_native_plan(case)
    if backend == "catalyst_rtl_cuba":
        return build_catalyst_rtl_cuba_native_plan(case)
    raise M13NormalizationError(f"unknown M13.3 backend {backend!r}")


def collapse_external_drive(scenario: ComparisonScenario) -> tuple[tuple[int, ...], ...]:
    """Collapse canonical axon events to exact per-target delivered current sums."""

    rows: dict[int, list[Synapse]] = {}
    for synapse in scenario.synapses:
        rows.setdefault(synapse.axon_id, []).append(synapse)

    neuron_count = len(scenario.neuron_configs)
    schedule: list[tuple[int, ...]] = []
    for axons in scenario.input_schedule:
        values = [0] * neuron_count
        for axon_id in axons:
            for synapse in rows.get(axon_id, []):
                values[synapse.target_neuron] += synapse.weight
        schedule.append(tuple(values))
    return tuple(schedule)


def scenario_to_payload(scenario: ComparisonScenario) -> dict[str, Any]:
    synapses = []
    for synapse in scenario.synapses:
        payload: dict[str, Any] = {
            "axon_id": synapse.axon_id,
            "target_neuron": synapse.target_neuron,
            "effective_weight": synapse.weight,
        }
        if synapse.encoding is not None:
            enc = synapse.encoding
            fmt = enc.weight_format
            payload["encoding"] = {
                "requested_mantissa": enc.requested_mantissa,
                "quantized_mantissa": enc.quantized_mantissa,
                "exponent": fmt.exponent,
                "num_weight_bits": fmt.num_weight_bits,
                "sign_mode": fmt.sign_mode.value,
                "effective_weight_before_clip": enc.effective_weight_before_clip,
                "clipped": enc.clipped,
            }
        synapses.append(payload)

    return {
        "schema": M13_COMMON_SCENARIO_SCHEMA,
        "name": scenario.name,
        "neuron_configs": [
            {
                "current_decay": c.current_decay,
                "voltage_decay": c.voltage_decay,
                "threshold": c.threshold,
                "bias": c.bias,
                "reset_voltage": c.reset_voltage,
                "refractory_ticks": c.refractory_ticks,
            }
            for c in scenario.neuron_configs
        ],
        "synapses": synapses,
        "input_schedule": [list(tick) for tick in scenario.input_schedule],
        "spike_routes": [
            {
                "source_neuron": route.source_neuron,
                "target_axon": route.target_axon,
            }
            for route in scenario.spike_routes
        ],
    }


def backend_trace_to_normalized_payload(
    trace: BackendTrace,
    *,
    implementation: str,
    profile: str,
) -> dict[str, Any]:
    return {
        "schema": M13_NORMALIZED_TRACE_SCHEMA,
        "implementation": implementation,
        "profile": profile,
        "scenario": trace.scenario,
        "ticks": [
            {
                "canonical_tick": tick.tick,
                "native_tick": tick.tick,
                "current_after": list(tick.current_after),
                "voltage_after": list(tick.voltage_after),
                "refractory_after": None,
                "spikes": list(tick.spikes),
            }
            for tick in trace.ticks
        ],
    }


def run_catalyst_cpu_native(plan: Mapping[str, Any]) -> dict[str, Any]:
    """Execute a prebuilt Catalyst CPU direct-drive plan if pinned SDK is importable."""

    if plan.get("backend") != "catalyst_cpu_sync":
        raise M13NormalizationError("Catalyst CPU runner received the wrong plan backend")
    try:
        import neurocore as nc
    except Exception as exc:  # pragma: no cover - exercised in pinned external env
        raise RuntimeError(
            "Catalyst neurocore SDK is not importable; place the pinned sdk directory on PYTHONPATH"
        ) from exc

    network = nc.Network()
    populations = []
    for neuron_id, params in enumerate(plan["neuron_params"]):
        populations.append(
            network.population(
                1,
                params={
                    "threshold": int(params["threshold"]),
                    "leak": int(params["leak"]),
                    "resting": int(params["resting"]),
                    "refrac": int(params["refrac"]),
                },
                label=f"m13_n{neuron_id}",
            )
        )

    simulator = nc.Simulator(num_cores=1)
    simulator.deploy(network)
    ticks = []
    for native_tick, currents in enumerate(plan["direct_current_schedule"]):
        potential_before = [int(value) for value in simulator._potential.tolist()]
        refractory_before = [int(value) for value in simulator._refrac.tolist()]
        for neuron_id, current in enumerate(currents):
            if int(current) != 0:
                simulator.inject(populations[neuron_id], int(current))
        result = simulator.run(1)
        spikes = sorted(int(neuron_id) for neuron_id in result.spike_trains)
        ticks.append(
            {
                "native_tick": native_tick,
                "direct_current": [int(value) for value in currents],
                "potential_before": potential_before,
                "refractory_before": refractory_before,
                "potential_after": [int(value) for value in simulator._potential.tolist()],
                "refractory_after": [int(value) for value in simulator._refrac.tolist()],
                "spikes": spikes,
            }
        )

    return {
        "schema": M13_CATALYST_NATIVE_TRACE_SCHEMA,
        "backend": "catalyst_cpu_sync",
        "profile": plan["profile"],
        "scenario": plan["scenario"],
        "ticks": ticks,
    }


def catalyst_cpu_native_to_normalized_payload(
    native: Mapping[str, Any],
) -> dict[str, Any]:
    if native.get("schema") != M13_CATALYST_NATIVE_TRACE_SCHEMA:
        raise M13NormalizationError("unexpected Catalyst CPU native-trace schema")
    return {
        "schema": M13_NORMALIZED_TRACE_SCHEMA,
        "implementation": "catalyst_cpu_sync",
        "profile": native["profile"],
        "scenario": native["scenario"],
        "ticks": [
            {
                "canonical_tick": int(tick["native_tick"]),
                "native_tick": int(tick["native_tick"]),
                "current_after": None,
                "voltage_after": [int(v) for v in tick["potential_after"]],
                "refractory_after": [int(v) for v in tick["refractory_after"]],
                "spikes": [int(v) for v in tick["spikes"]],
            }
            for tick in native["ticks"]
        ],
    }


def catalyst_rtl_cuba_native_to_normalized_payload(
    native: Mapping[str, Any],
) -> dict[str, Any]:
    """Normalize a future M13.4 Catalyst CUBA native trace using the frozen lag."""

    ticks = native.get("ticks")
    if not isinstance(ticks, Sequence) or len(ticks) < 2:
        raise M13NormalizationError("Catalyst CUBA trace requires warmup plus compared ticks")
    normalized_ticks = []
    for tick in ticks[1:]:
        native_tick = int(tick["native_tick"])
        normalized_ticks.append(
            {
                "canonical_tick": native_tick - 1,
                "native_tick": native_tick,
                "current_after": list(tick["current_after"]),
                "voltage_after": list(tick["voltage_after"]),
                "refractory_after": tick.get("refractory_after"),
                "spikes": list(tick.get("spikes", [])),
            }
        )
    return {
        "schema": M13_NORMALIZED_TRACE_SCHEMA,
        "implementation": "catalyst_rtl_cuba",
        "profile": "isolated-impulse-one-tick-staging",
        "scenario": native.get("scenario"),
        "ticks": normalized_ticks,
    }


def write_translation_smoke_bundle(
    output_dir: str | Path,
    *,
    execute_catalyst_cpu: bool = False,
) -> Path:
    """Generate the M13.3 small-corpus native/normalized evidence bundle.

    No cross-backend equality report is produced here.  This is an executable
    mapping/serialization gate only; M13.4 performs the differential probes.
    """

    spec = load_normalization_spec()
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    cases = build_small_translation_corpus()
    case_records = []

    for case in cases:
        case_dir = root / case.name
        case_dir.mkdir(parents=True, exist_ok=True)
        _write_json(
            case_dir / "common-scenario.json",
            {
                "schema": M13_COMMON_SCENARIO_SCHEMA,
                "scenario_class": case.scenario_class,
                "question": case.question,
                "scenario": scenario_to_payload(case.scenario),
            },
        )

        project_plan = build_project_native_plan(case)
        brian_plan = build_brian2loihi_native_plan(case)
        _write_json(case_dir / "project.native-plan.json", project_plan)
        _write_json(case_dir / "brian2loihi.native-plan.json", brian_plan)

        project_trace = run_python_backend(case.scenario)
        brian_trace = run_brian2loihi_backend(case.scenario)
        write_trace_json(project_trace, case_dir / "project.native.json")
        write_trace_json(brian_trace, case_dir / "brian2loihi.native.json")
        _write_json(
            case_dir / "project.normalized.json",
            backend_trace_to_normalized_payload(
                project_trace,
                implementation="project_fpga_v1",
                profile="comparison-scenario",
            ),
        )
        _write_json(
            case_dir / "brian2loihi.normalized.json",
            backend_trace_to_normalized_payload(
                brian_trace,
                implementation="brian2loihi_0_5_2",
                profile="LoihiNetwork-point-neuron",
            ),
        )

        catalyst_executed = False
        catalyst_backend = None
        if case.scenario_class == "cpu_direct_drive":
            catalyst_plan = build_catalyst_cpu_native_plan(case)
            catalyst_backend = "catalyst_cpu_sync"
            _write_json(case_dir / "catalyst.native-plan.json", catalyst_plan)
            if execute_catalyst_cpu:
                catalyst_native = run_catalyst_cpu_native(catalyst_plan)
                _write_json(case_dir / "catalyst.native.json", catalyst_native)
                _write_json(
                    case_dir / "catalyst.normalized.json",
                    catalyst_cpu_native_to_normalized_payload(catalyst_native),
                )
                catalyst_executed = True
        else:
            catalyst_plan = build_catalyst_rtl_cuba_native_plan(case)
            catalyst_backend = "catalyst_rtl_cuba"
            _write_json(case_dir / "catalyst.native-plan.json", catalyst_plan)

        case_records.append(
            {
                "name": case.name,
                "scenario_class": case.scenario_class,
                "project_executed": True,
                "brian2loihi_executed": True,
                "catalyst_backend": catalyst_backend,
                "catalyst_executed": catalyst_executed,
            }
        )

    artifacts = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name != "manifest.json"):
        artifacts.append(
            {
                "path": path.relative_to(root).as_posix(),
                "sha256": _sha256(path),
            }
        )

    manifest = {
        "schema": M13_TRANSLATION_MANIFEST_SCHEMA,
        "normalization_schema": spec["schema"],
        "normalization_status": spec["status"],
        "scenario_count": len(cases),
        "comparison_performed": False,
        "discrepancy_classification_performed": False,
        "catalyst_cpu_execution_requested": execute_catalyst_cpu,
        "cases": case_records,
        "artifacts": artifacts,
    }
    manifest_path = root / "manifest.json"
    _write_json(manifest_path, manifest)
    return manifest_path


def _config(*, threshold: int, refractory_ticks: int) -> NeuronConfig:
    return NeuronConfig(
        current_decay=4096,
        voltage_decay=0,
        threshold=threshold,
        bias=0,
        reset_voltage=0,
        refractory_ticks=refractory_ticks,
    )


def _validate_canonical_threshold(threshold: int) -> None:
    if isinstance(threshold, bool) or not isinstance(threshold, int):
        raise M13NormalizationError("canonical threshold must be an int")
    if not 64 <= threshold <= 32704 or threshold % 64:
        raise M13NormalizationError(
            "shared canonical threshold must be a multiple of 64 in 64..32704"
        )


def _validate_int16(value: int, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int):
        raise M13NormalizationError(f"{label} must be an int")
    if not _INT16_MIN <= value <= _INT16_MAX:
        raise M13NormalizationError(f"{label}={value} is outside signed int16")


def _validate_isolated_impulse_schedule(scenario: ComparisonScenario) -> None:
    if not scenario.input_schedule[0]:
        raise M13NormalizationError("isolated CUBA scenario requires a non-empty tick-0 impulse")
    if any(tick for tick in scenario.input_schedule[1:]):
        raise M13NormalizationError(
            "isolated CUBA normalization permits no external input after tick 0"
        )


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
