"""M13.4 directed differential audit under the frozen M13.3 normalization.

The code in this module is audit infrastructure, not computational-core logic. It
preserves each implementation's native result and applies only transforms frozen
by M13.3 before the broad Catalyst outputs were observed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ..model import NeuronConfig, SpikeRoute, Synapse
from .brian2loihi_backend import run_brian2loihi_backend
from .m13_normalization import (
    M13CommonCase,
    backend_trace_to_normalized_payload,
    build_catalyst_cpu_native_plan,
    build_catalyst_rtl_cuba_native_plan,
    build_small_translation_corpus,
    catalyst_cpu_native_to_normalized_payload,
    catalyst_rtl_cuba_native_to_normalized_payload,
    load_normalization_spec,
    run_catalyst_cpu_native,
    scenario_to_payload,
)
from .model import ComparisonScenario
from .python_backend import run_python_backend
from .weight_conformance import build_weight_conformance_cases

M13_4_DIFFERENTIAL_SCHEMA = "neuromorphic-twin-m13-directed-differential-v1"
M13_4_CATALYST_CUBA_NATIVE_SCHEMA = "neuromorphic-twin-m13-catalyst-cuba-native-trace-v1"
M13_4_NORMALIZATION_MERGE = "32cc170ced02af834ed48b9533b245db1f65641d"
CATALYST_PIN = "1806bb4b4114d7671e5648fa75b7b83b3a8d5543"

_DISCREPANCY_CLASSES = {
    "A", "B", "C", "D", "E", "F", "G", "H"
}
_RESULT_STATUSES = {
    "agreement",
    "architectural_difference",
    "partial_scope",
    "non_comparable",
}
_CUBA_LINE = re.compile(
    r"^M13_4_CUBA\|case=(?P<case>[a-z]+)"
    r"\|native_tick=(?P<tick>\d+)"
    r"\|current=(?P<current>-?\d+)"
    r"\|voltage=(?P<voltage>-?\d+)"
    r"\|refractory=(?P<refractory>-?\d+)"
    r"\|spike=(?P<spike>[01])$"
)


@dataclass(frozen=True, slots=True)
class NormalizedComparison:
    equal: bool
    compared_values: int
    first_divergence: dict[str, Any] | None


def _config(
    *,
    current_decay: int = 4096,
    voltage_decay: int = 0,
    threshold: int = 4096,
    refractory_ticks: int = 1,
) -> NeuronConfig:
    return NeuronConfig(
        current_decay=current_decay,
        voltage_decay=voltage_decay,
        threshold=threshold,
        bias=0,
        reset_voltage=0,
        refractory_ticks=refractory_ticks,
    )


def build_m13_4_common_cases() -> dict[str, M13CommonCase]:
    """Return the M13.4 scenarios whose transforms were frozen by M13.3."""

    m13_3 = {case.name: case for case in build_small_translation_corpus()}
    cases = {
        "threshold": m13_3["m13-3-threshold-boundary"],
        "refractory": m13_3["m13-3-refractory-release"],
        "mixed_drive": m13_3["m13-3-signed-drive"],
        "cuba_positive": M13CommonCase(
            name="m13-4-cuba-positive-impulse",
            scenario_class="rtl_cuba_isolated_impulse",
            question="Positive isolated impulse under the frozen one-native-tick CUBA staging transform.",
            scenario=ComparisonScenario.build(
                name="m13-4-cuba-positive-impulse",
                neuron_configs=[
                    _config(
                        current_decay=2048,
                        voltage_decay=2048,
                        threshold=8192,
                    )
                ],
                synapses=[Synapse(0, 0, 512)],
                input_schedule=[(0,), (), (), ()],
            ),
        ),
        "cuba_negative": M13CommonCase(
            name="m13-4-cuba-negative-rounding",
            scenario_class="rtl_cuba_isolated_impulse",
            question="Negative fractional current decay under Catalyst raz_div4096 and the frozen CUBA staging transform.",
            scenario=ComparisonScenario.build(
                name="m13-4-cuba-negative-rounding",
                neuron_configs=[
                    _config(
                        current_decay=1025,
                        voltage_decay=0,
                        threshold=8192,
                    )
                ],
                synapses=[Synapse(0, 0, -64)],
                input_schedule=[(0,), (), ()],
            ),
        ),
        "negative_drive": M13CommonCase(
            name="m13-4-isolated-negative-drive",
            scenario_class="cpu_direct_drive",
            question="Whether isolated negative delivered current is retained below resting potential.",
            scenario=ComparisonScenario.build(
                name="m13-4-isolated-negative-drive",
                neuron_configs=[_config(threshold=4096)],
                synapses=[Synapse(0, 0, -128)],
                input_schedule=[(0,), ()],
            ),
        ),
        "simultaneous": M13CommonCase(
            name="m13-4-simultaneous-spike-set",
            scenario_class="cpu_direct_drive",
            question="Whether three independent neurons spike on the same committed tick after threshold normalization.",
            scenario=ComparisonScenario.build(
                name="m13-4-simultaneous-spike-set",
                neuron_configs=[_config(threshold=256)] * 3,
                synapses=[
                    Synapse(0, 0, 320),
                    Synapse(1, 1, 384),
                    Synapse(2, 2, 448),
                ],
                input_schedule=[(0, 1, 2), ()],
            ),
        ),
    }
    return cases


def parse_catalyst_cuba_log(path: str | Path) -> dict[str, dict[str, Any]]:
    """Parse the machine-readable lines emitted by the thesis-side Catalyst TB."""

    source = Path(path)
    text = source.read_text(encoding="utf-8")
    if "M13_4_CUBA_TIMEOUT" in text:
        raise ValueError("Catalyst CUBA native probe log contains timeout marker")
    if "M13_4_CUBA_DONE" not in text:
        raise ValueError("Catalyst CUBA native probe log lacks completion marker")

    grouped: dict[str, list[dict[str, Any]]] = {"positive": [], "negative": []}
    for line in text.splitlines():
        match = _CUBA_LINE.match(line.strip())
        if not match:
            continue
        name = match.group("case")
        if name not in grouped:
            raise ValueError(f"unknown Catalyst CUBA case {name!r}")
        grouped[name].append(
            {
                "native_tick": int(match.group("tick")),
                "current_after": [int(match.group("current"))],
                "voltage_after": [int(match.group("voltage"))],
                "refractory_after": [int(match.group("refractory"))],
                "spikes": [0] if match.group("spike") == "1" else [],
            }
        )

    expected = {"positive": 5, "negative": 4}
    result: dict[str, dict[str, Any]] = {}
    scenario_names = {
        "positive": "m13-4-cuba-positive-impulse",
        "negative": "m13-4-cuba-negative-rounding",
    }
    for name, ticks in grouped.items():
        if len(ticks) != expected[name]:
            raise ValueError(
                f"Catalyst CUBA case {name!r} has {len(ticks)} ticks; expected {expected[name]}"
            )
        if [tick["native_tick"] for tick in ticks] != list(range(expected[name])):
            raise ValueError(f"Catalyst CUBA case {name!r} tick sequence is not contiguous")
        result[name] = {
            "schema": M13_4_CATALYST_CUBA_NATIVE_SCHEMA,
            "backend": "catalyst_rtl_cuba",
            "profile": "isolated-impulse-one-tick-staging",
            "scenario": scenario_names[name],
            "catalyst_commit": CATALYST_PIN,
            "ticks": ticks,
        }
    return result


def compare_normalized_payloads(
    reference: Mapping[str, Any],
    candidates: Mapping[str, Mapping[str, Any]],
    *,
    fields: Sequence[str],
) -> NormalizedComparison:
    """Compare selected normalized fields by canonical tick against reference."""

    ref_ticks = {int(t["canonical_tick"]): t for t in reference["ticks"]}
    compared = 0
    for implementation, payload in candidates.items():
        cand_ticks = {int(t["canonical_tick"]): t for t in payload["ticks"]}
        if set(cand_ticks) != set(ref_ticks):
            return NormalizedComparison(
                False,
                compared,
                {
                    "implementation": implementation,
                    "field": "canonical_tick_set",
                    "reference": sorted(ref_ticks),
                    "candidate": sorted(cand_ticks),
                },
            )
        for tick_id in sorted(ref_ticks):
            for field in fields:
                ref_value = ref_ticks[tick_id].get(field)
                cand_value = cand_ticks[tick_id].get(field)
                if ref_value is None or cand_value is None:
                    continue
                compared += 1
                if cand_value != ref_value:
                    return NormalizedComparison(
                        False,
                        compared,
                        {
                            "implementation": implementation,
                            "canonical_tick": tick_id,
                            "field": field,
                            "reference": ref_value,
                            "candidate": cand_value,
                        },
                    )
    return NormalizedComparison(True, compared, None)


def _normalized_project_and_brian(case: M13CommonCase) -> tuple[dict[str, Any], dict[str, Any]]:
    project_trace = run_python_backend(case.scenario)
    brian_trace = run_brian2loihi_backend(case.scenario)
    return (
        backend_trace_to_normalized_payload(
            project_trace,
            implementation="project_fpga_v1",
            profile="comparison-scenario",
        ),
        backend_trace_to_normalized_payload(
            brian_trace,
            implementation="brian2loihi_0_5_2",
            profile="LoihiNetwork-point-neuron",
        ),
    )


def _run_cpu_case(case: M13CommonCase) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    project, brian = _normalized_project_and_brian(case)
    plan = build_catalyst_cpu_native_plan(case)
    native = run_catalyst_cpu_native(plan)
    catalyst = catalyst_cpu_native_to_normalized_payload(native)
    return project, brian, native, catalyst


def run_catalyst_graph_probe(
    *,
    name: str,
    canonical_thresholds: Sequence[int],
    refractory_durations: Sequence[int],
    edges: Sequence[tuple[int, int, int]],
    direct_current_schedule: Sequence[Sequence[int]],
) -> dict[str, Any]:
    """Execute a deterministic same-core Catalyst SDK graph probe.

    The graph uses Catalyst's actual compiler/adjacency and synchronous simulator.
    External currents are control stimuli; synaptic effects are delivered through
    Catalyst's pending-spike/adjacency path on following timesteps.
    """

    from .m13_normalization import (
        canonical_refractory_to_catalyst,
        canonical_threshold_to_catalyst,
    )

    try:
        import neurocore as nc
        from neurocore.constants import NEURONS_PER_CORE
    except Exception as exc:  # pragma: no cover - external pinned environment
        raise RuntimeError("pinned Catalyst neurocore SDK is required") from exc

    if len(canonical_thresholds) != len(refractory_durations):
        raise ValueError("threshold and refractory arrays must have equal length")
    n = len(canonical_thresholds)
    if any(len(row) != n for row in direct_current_schedule):
        raise ValueError("each direct-current row must match neuron count")

    network = nc.Network()
    pops = []
    for i, (threshold, refrac) in enumerate(zip(canonical_thresholds, refractory_durations, strict=True)):
        pops.append(
            network.population(
                1,
                params={
                    "threshold": canonical_threshold_to_catalyst(int(threshold)),
                    "leak": 0,
                    "resting": 0,
                    "refrac": canonical_refractory_to_catalyst(int(refrac)),
                },
                label=f"m13_4_n{i}",
            )
        )
    for src, tgt, weight in edges:
        network.connect(pops[src], pops[tgt], weight=int(weight), delay=0)

    sim = nc.Simulator(num_cores=1)
    sim.deploy(network)

    gid_for_pop: dict[int, int] = {}
    for pop in pops:
        core, neuron = sim._compiled.placement.neuron_map[(pop.id, 0)]
        gid_for_pop[pop.id] = int(core) * int(NEURONS_PER_CORE) + int(neuron)

    logical_gids = [gid_for_pop[pop.id] for pop in pops]
    gid_to_logical = {gid: logical for logical, gid in enumerate(logical_gids)}

    compiled_edges = []
    for src, tgt, requested_weight in edges:
        src_gid = gid_for_pop[pops[src].id]
        tgt_gid = gid_for_pop[pops[tgt].id]
        matches = [entry for entry in sim._adjacency.get(src_gid, []) if int(entry[0]) == tgt_gid]
        if len(matches) != 1:
            raise RuntimeError(
                f"Catalyst compiled graph expected one edge {src}->{tgt}; found {len(matches)}"
            )
        compiled_edges.append(
            {
                "source": src,
                "target": tgt,
                "requested_weight": int(requested_weight),
                "compiled_weight": int(matches[0][1]),
                "delay": int(matches[0][3]) if len(matches[0]) > 3 else 0,
            }
        )

    ticks = []
    for native_tick, currents in enumerate(direct_current_schedule):
        before = [int(sim._potential[gid]) for gid in logical_gids]
        ref_before = [int(sim._refrac[gid]) for gid in logical_gids]
        for neuron_id, current in enumerate(currents):
            if int(current):
                sim.inject(pops[neuron_id], int(current))
        result = sim.run(1)
        spikes = sorted(
            gid_to_logical[int(gid)]
            for gid in result.spike_trains
            if int(gid) in gid_to_logical
        )
        ticks.append(
            {
                "native_tick": native_tick,
                "direct_current": [int(v) for v in currents],
                "potential_before": before,
                "potential_after": [int(sim._potential[gid]) for gid in logical_gids],
                "refractory_before": ref_before,
                "refractory_after": [int(sim._refrac[gid]) for gid in logical_gids],
                "spikes": spikes,
            }
        )
    return {
        "schema": "neuromorphic-twin-m13-catalyst-graph-native-v1",
        "backend": "catalyst_cpu_sync",
        "scenario": name,
        "catalyst_commit": CATALYST_PIN,
        "logical_to_catalyst_gid": logical_gids,
        "compiled_edges": compiled_edges,
        "ticks": ticks,
    }


def run_brian2loihi_recurrent_probe() -> dict[str, Any]:
    """Measure native zero-delay recurrent timing without weakening generic guards."""

    try:
        import numpy as np
        from brian2 import prefs, start_scope
        from brian2_loihi import (
            LoihiNetwork,
            LoihiNeuronGroup,
            LoihiSpikeGeneratorGroup,
            LoihiSpikeMonitor,
            LoihiSynapses,
            synapse_sign_mode,
        )
    except Exception as exc:  # pragma: no cover - external comparison env
        raise RuntimeError("Brian2Loihi comparison runtime is required") from exc

    prefs.codegen.target = "numpy"
    start_scope()
    neurons = LoihiNeuronGroup(
        2,
        refractory=1,
        threshold_v_mant=4,
        decay_v=0,
        decay_I=4096,
    )
    generator = LoihiSpikeGeneratorGroup(1, [0], [0])
    external = LoihiSynapses(
        generator,
        neurons,
        w_exp=0,
        sign_mode=synapse_sign_mode.EXCITATORY,
        num_weight_bits=8,
    )
    external.connect(i=[0], j=[0])
    external.w = np.asarray([5], dtype=int)  # 5 * 64 = 320

    recurrent = LoihiSynapses(
        neurons,
        neurons,
        delay=0,
        w_exp=0,
        sign_mode=synapse_sign_mode.EXCITATORY,
        num_weight_bits=8,
    )
    recurrent.connect(i=[0], j=[1])
    recurrent.w = np.asarray([5], dtype=int)

    monitor = LoihiSpikeMonitor(neurons)
    network = LoihiNetwork(neurons, generator, external, recurrent, monitor)
    ticks = []
    for native_tick in range(4):
        spike_count = len(monitor.i)
        network.run(1)
        spikes = sorted(int(v) for v in monitor.i[spike_count:])
        ticks.append(
            {
                "native_tick": native_tick,
                "current_after": [int(round(float(v))) for v in neurons.I[:]],
                "voltage_after": [int(round(float(v))) for v in neurons.v[:]],
                "spikes": spikes,
            }
        )
    return {
        "schema": "neuromorphic-twin-m13-brian-recurrent-native-v1",
        "backend": "brian2loihi_0_5_2",
        "scenario": "m13-4-recurrent-one-hop",
        "external_effective_weight": int(external.w_act[0]),
        "recurrent_effective_weight": int(recurrent.w_act[0]),
        "ticks": ticks,
    }


def run_project_recurrent_probe() -> dict[str, Any]:
    scenario = ComparisonScenario.build(
        name="m13-4-recurrent-one-hop",
        neuron_configs=[_config(threshold=256)] * 2,
        synapses=[
            Synapse(0, 0, 320),
            Synapse(1, 1, 320),
        ],
        input_schedule=[(0,), (), (), ()],
        spike_routes=[SpikeRoute(source_neuron=0, target_axon=1)],
    )
    trace = run_python_backend(scenario)
    return {
        "schema": "neuromorphic-twin-m13-project-recurrent-native-v1",
        "backend": "project_fpga_v1",
        "scenario": scenario.name,
        "ticks": [
            {
                "native_tick": tick.tick,
                "current_after": list(tick.current_after),
                "voltage_after": list(tick.voltage_after),
                "spikes": list(tick.spikes),
                "recurrent_input_axons": list(tick.recurrent_input_axons),
            }
            for tick in trace.ticks
        ],
    }


def _spike_tick(native: Mapping[str, Any], neuron_id: int) -> int | None:
    for tick in native["ticks"]:
        if neuron_id in tick["spikes"]:
            return int(tick["native_tick"])
    return None


def _observe_catalyst_weights() -> dict[str, Any]:
    cases = build_weight_conformance_cases()
    representable = []
    out_of_envelope = []
    for case in cases:
        weight = int(case.encoding.effective_weight)
        if -32768 <= weight <= 32767:
            representable.append((case.name, weight))
        else:
            out_of_envelope.append((case.name, weight))

    if not representable:
        raise RuntimeError("M13.4 expected at least one Catalyst-representable encoded weight")

    # One independent source/target pair per weight keeps compiler observations unambiguous.
    n = len(representable) * 2
    thresholds = [32704] * n
    refracs = [1] * n
    edges = [(2 * i, 2 * i + 1, weight) for i, (_, weight) in enumerate(representable)]
    native = run_catalyst_graph_probe(
        name="m13-4-effective-weight-observation",
        canonical_thresholds=thresholds,
        refractory_durations=refracs,
        edges=edges,
        direct_current_schedule=[],
    )
    observations = []
    for (case_name, expected), compiled in zip(representable, native["compiled_edges"], strict=True):
        observations.append(
            {
                "case": case_name,
                "canonical_effective_weight": expected,
                "catalyst_compiled_weight": int(compiled["compiled_weight"]),
                "equal": expected == int(compiled["compiled_weight"]),
            }
        )
    return {
        "representable": observations,
        "out_of_catalyst_int16_envelope": [
            {"case": name, "canonical_effective_weight": weight}
            for name, weight in out_of_envelope
        ],
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _case_record(
    probe_id: str,
    *,
    status: str,
    discrepancy_classes: Sequence[str] = (),
    first_divergence: Mapping[str, Any] | None = None,
    observation: Mapping[str, Any] | None = None,
    applicable: Sequence[str] = (),
    non_comparable: Sequence[str] = (),
) -> dict[str, Any]:
    if status not in _RESULT_STATUSES:
        raise ValueError(f"invalid M13.4 status {status!r}")
    classes = list(discrepancy_classes)
    invalid = set(classes) - _DISCREPANCY_CLASSES
    if invalid:
        raise ValueError(f"invalid discrepancy classes: {sorted(invalid)}")
    return {
        "probe_id": probe_id,
        "status": status,
        "discrepancy_classes": classes,
        "first_divergence": dict(first_divergence) if first_divergence else None,
        "observation": dict(observation or {}),
        "applicable_implementations": list(applicable),
        "non_comparable_fields": list(non_comparable),
        "requires_m12_revalidation": bool({"A", "B"} & set(classes)),
    }


def write_m13_4_differential_bundle(
    output_dir: str | Path,
    *,
    catalyst_cuba_log: str | Path,
) -> Path:
    """Execute all applicable directed probes and write classified evidence."""

    spec = load_normalization_spec()
    if spec["schema"] != "neuromorphic-twin-m13-normalization-v1" or spec["status"] != "frozen":
        raise RuntimeError("M13.4 requires the frozen M13.3 normalization authority")

    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    cases = build_m13_4_common_cases()
    artifacts: list[Path] = []
    records: list[dict[str, Any]] = []

    # P01/P02/P03: Catalyst RTL CUBA, using only the predeclared isolated-impulse shift.
    cuba_native = parse_catalyst_cuba_log(catalyst_cuba_log)
    for label, case_key, probe_ids, fields in (
        ("positive", "cuba_positive", ("P01-current-impulse-decay", "P02-voltage-decay"), ("current_after", "voltage_after", "spikes")),
        ("negative", "cuba_negative", ("P03-negative-rounding",), ("current_after", "voltage_after", "spikes")),
    ):
        case = cases[case_key]
        project, brian = _normalized_project_and_brian(case)
        catalyst = catalyst_rtl_cuba_native_to_normalized_payload(cuba_native[label])
        case_dir = root / case.scenario.name
        artifacts += [
            _write_json(case_dir / "common-scenario.json", scenario_to_payload(case.scenario)),
            _write_json(case_dir / "project.normalized.json", project),
            _write_json(case_dir / "brian2loihi.normalized.json", brian),
            _write_json(case_dir / "catalyst.native.json", cuba_native[label]),
            _write_json(case_dir / "catalyst.normalized.json", catalyst),
            _write_json(case_dir / "catalyst.native-plan.json", build_catalyst_rtl_cuba_native_plan(case)),
        ]
        comparison = compare_normalized_payloads(
            project,
            {"brian2loihi_0_5_2": brian, "catalyst_rtl_cuba": catalyst},
            fields=fields,
        )
        for probe_id in probe_ids:
            records.append(
                _case_record(
                    probe_id,
                    status="agreement" if comparison.equal else "architectural_difference",
                    discrepancy_classes=() if comparison.equal else ("C",),
                    first_divergence=comparison.first_divergence,
                    observation={
                        "normalized_values_compared": comparison.compared_values,
                        "catalyst_profile": "catalyst_rtl_cuba",
                        "tick_transform": "canonical k <- Catalyst native k+1",
                    },
                    applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_rtl_cuba"),
                )
            )

    # P04/P05 and the mixed part of P06 use the frozen Catalyst CPU direct-drive transform.
    cpu_outputs: dict[str, tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]] = {}
    for key in ("threshold", "refractory", "mixed_drive", "negative_drive", "simultaneous"):
        case = cases[key]
        output = _run_cpu_case(case)
        cpu_outputs[key] = output
        project, brian, catalyst_native, catalyst = output
        case_dir = root / case.scenario.name
        artifacts += [
            _write_json(case_dir / "common-scenario.json", scenario_to_payload(case.scenario)),
            _write_json(case_dir / "project.normalized.json", project),
            _write_json(case_dir / "brian2loihi.normalized.json", brian),
            _write_json(case_dir / "catalyst.native-plan.json", build_catalyst_cpu_native_plan(case)),
            _write_json(case_dir / "catalyst.native.json", catalyst_native),
            _write_json(case_dir / "catalyst.normalized.json", catalyst),
        ]

    threshold_cmp = compare_normalized_payloads(
        cpu_outputs["threshold"][0],
        {"brian2loihi_0_5_2": cpu_outputs["threshold"][1], "catalyst_cpu_sync": cpu_outputs["threshold"][3]},
        fields=("voltage_after", "spikes"),
    )
    records.append(
        _case_record(
            "P04-threshold-boundary",
            status="agreement" if threshold_cmp.equal else "architectural_difference",
            discrepancy_classes=() if threshold_cmp.equal else ("C",),
            first_divergence=threshold_cmp.first_divergence,
            observation={"transform": "Catalyst native threshold = canonical T+1"},
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
        )
    )

    refractory_ticks = {
        "project_fpga_v1": [i for i, t in enumerate(cpu_outputs["refractory"][0]["ticks"]) if t["spikes"]],
        "brian2loihi_0_5_2": [i for i, t in enumerate(cpu_outputs["refractory"][1]["ticks"]) if t["spikes"]],
        "catalyst_cpu_sync": [i for i, t in enumerate(cpu_outputs["refractory"][3]["ticks"]) if t["spikes"]],
    }
    refractory_equal = len({tuple(v) for v in refractory_ticks.values()}) == 1
    records.append(
        _case_record(
            "P05-refractory-release",
            status="agreement" if refractory_equal else "architectural_difference",
            discrepancy_classes=() if refractory_equal else ("C", "D"),
            first_divergence=None if refractory_equal else {"field": "spike_ticks", "values": refractory_ticks},
            observation={"spike_ticks": refractory_ticks, "semantic": "next_eligible_tick"},
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
            non_comparable=("raw_refractory_register",),
        )
    )

    mixed_cmp = compare_normalized_payloads(
        cpu_outputs["mixed_drive"][0],
        {"brian2loihi_0_5_2": cpu_outputs["mixed_drive"][1], "catalyst_cpu_sync": cpu_outputs["mixed_drive"][3]},
        fields=("voltage_after", "spikes"),
    )
    negative_cmp = compare_normalized_payloads(
        cpu_outputs["negative_drive"][0],
        {"brian2loihi_0_5_2": cpu_outputs["negative_drive"][1], "catalyst_cpu_sync": cpu_outputs["negative_drive"][3]},
        fields=("voltage_after", "spikes"),
    )
    signed_difference = not negative_cmp.equal
    records.append(
        _case_record(
            "P06-signed-synaptic-drive",
            status="architectural_difference" if signed_difference else "agreement",
            discrepancy_classes=("C",) if signed_difference else (),
            first_divergence=negative_cmp.first_divergence,
            observation={
                "mixed_net_positive_agreement": mixed_cmp.equal,
                "isolated_negative_agreement": negative_cmp.equal,
                "interpretation": (
                    "Catalyst CPU simple-LIF returns sub-rest negative drive to resting=0; "
                    "project/Brian2Loihi retain negative membrane state."
                    if signed_difference else "All compared signed-drive cases agree."
                ),
            },
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
            non_comparable=("current_after_on_catalyst_cpu",),
        )
    )

    # P07: final effective weight is comparable; source encoding is not.
    weight_observation = _observe_catalyst_weights()
    weight_dir = root / "m13-4-effective-weight-observation"
    artifacts.append(_write_json(weight_dir / "catalyst.compiled-weights.json", weight_observation))
    weights_equal = all(item["equal"] for item in weight_observation["representable"])
    records.append(
        _case_record(
            "P07-weight-encoding-boundaries",
            status="partial_scope",
            discrepancy_classes=("C", "G"),
            first_divergence=None if weights_equal else {"field": "effective_weight", "detail": "Catalyst compiler changed a representable final weight"},
            observation={
                "representable_final_weights": len(weight_observation["representable"]),
                "representable_weights_equal": weights_equal,
                "out_of_int16_envelope": len(weight_observation["out_of_catalyst_int16_envelope"]),
                "project_brian_source_encoding_cases": 15,
            },
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
            non_comparable=("Catalyst mantissa/exponent/precision/sign-mode source encoding",),
        )
    )

    # P08: execute actual Catalyst graph fan-in and fan-out paths.
    fanin = run_catalyst_graph_probe(
        name="m13-4-catalyst-fanin",
        canonical_thresholds=(256, 256, 4096),
        refractory_durations=(1, 1, 1),
        edges=((0, 2, 128), (1, 2, 64)),
        direct_current_schedule=((320, 320, 0), (0, 0, 0)),
    )
    fanout = run_catalyst_graph_probe(
        name="m13-4-catalyst-fanout",
        canonical_thresholds=(256, 4096, 4096, 4096),
        refractory_durations=(1, 1, 1, 1),
        edges=((0, 1, 64), (0, 2, 128), (0, 3, 192)),
        direct_current_schedule=((320, 0, 0, 0), (0, 0, 0, 0)),
    )
    graph_dir = root / "m13-4-catalyst-connectivity"
    artifacts += [
        _write_json(graph_dir / "fanin.native.json", fanin),
        _write_json(graph_dir / "fanout.native.json", fanout),
    ]
    fanin_ok = fanin["ticks"][1]["potential_after"][2] == 192
    fanout_ok = fanout["ticks"][1]["potential_after"][1:4] == [64, 128, 192]
    records.append(
        _case_record(
            "P08-fanin-fanout",
            status="agreement" if fanin_ok and fanout_ok else "architectural_difference",
            discrepancy_classes=() if fanin_ok and fanout_ok else ("C",),
            first_divergence=None if fanin_ok and fanout_ok else {"field": "target_effective_drive", "fanin": fanin["ticks"][1]["potential_after"], "fanout": fanout["ticks"][1]["potential_after"]},
            observation={"fanin_target": fanin["ticks"][1]["potential_after"][2], "fanout_targets": fanout["ticks"][1]["potential_after"][1:4]},
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
        )
    )

    # P09: frozen M13.3 explicitly has no exact same-source duplicate-event transport.
    records.append(
        _case_record(
            "P09-event-multiplicity",
            status="non_comparable",
            discrepancy_classes=("G",),
            observation={
                "project_evidence": "M12.2 repeated-event-multiplicity and M12.3 same-target-recurrent-multiplicity",
                "reason": "Brian SpikeGeneratorGroup cannot encode two spikes from one source at one time; Catalyst external current is a per-neuron stimulus buffer rather than the same event-list boundary.",
            },
            applicable=("project_fpga_v1",),
            non_comparable=("same-source same-tick raw event multiplicity across all implementations",),
        )
    )

    # P10: execute logical one-hop recurrence on all three runnable implementations.
    project_rec = run_project_recurrent_probe()
    brian_rec = run_brian2loihi_recurrent_probe()
    catalyst_rec = run_catalyst_graph_probe(
        name="m13-4-recurrent-one-hop",
        canonical_thresholds=(256, 256),
        refractory_durations=(1, 1),
        edges=((0, 1, 320),),
        direct_current_schedule=((320, 0), (0, 0), (0, 0), (0, 0)),
    )
    rec_dir = root / "m13-4-recurrent-one-hop"
    artifacts += [
        _write_json(rec_dir / "project.native.json", project_rec),
        _write_json(rec_dir / "brian2loihi.native.json", brian_rec),
        _write_json(rec_dir / "catalyst.native.json", catalyst_rec),
    ]
    rec_lags = {}
    for name, native in (
        ("project_fpga_v1", project_rec),
        ("brian2loihi_0_5_2", brian_rec),
        ("catalyst_cpu_sync", catalyst_rec),
    ):
        src_tick = _spike_tick(native, 0)
        target_tick = _spike_tick(native, 1)
        rec_lags[name] = None if src_tick is None or target_tick is None else target_tick - src_tick
    lag_values = {value for value in rec_lags.values() if value is not None}
    rec_equal = len(lag_values) == 1 and None not in rec_lags.values()
    rec_classes: tuple[str, ...] = ()
    if not rec_equal:
        rec_classes = ("D",) if rec_lags["project_fpga_v1"] == rec_lags["catalyst_cpu_sync"] else ("C", "D")
    records.append(
        _case_record(
            "P10-recurrent-timing",
            status="agreement" if rec_equal else "architectural_difference",
            discrepancy_classes=rec_classes,
            first_divergence=None if rec_equal else {"field": "source_spike_to_target_spike_lag", "values": rec_lags},
            observation={"source_spike_to_target_spike_lag": rec_lags},
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
            non_comparable=("raw route/CSR addresses", "global FIFO ordering"),
        )
    )

    # P11: no M13.3 common overflow contract; preserve the physical project evidence.
    records.append(
        _case_record(
            "P11-state-saturation",
            status="non_comparable",
            discrepancy_classes=("E", "G"),
            observation={
                "project_evidence": "M12.2 positive-state-saturation and negative-state-saturation",
                "reason": "M13.3 intentionally excludes finite-width overflow from exact cross-implementation normalization; Catalyst exposes 24-bit internal state with 16-bit probes and published Loihi evidence does not justify a shared boundary here.",
            },
            applicable=("project_fpga_v1",),
            non_comparable=("finite-width saturation/overflow behavior",),
        )
    )

    # P12: compare spike set; ordering remains explicitly non-comparable.
    simultaneous_cmp = compare_normalized_payloads(
        cpu_outputs["simultaneous"][0],
        {"brian2loihi_0_5_2": cpu_outputs["simultaneous"][1], "catalyst_cpu_sync": cpu_outputs["simultaneous"][3]},
        fields=("spikes",),
    )
    records.append(
        _case_record(
            "P12-simultaneous-spikes",
            status="agreement" if simultaneous_cmp.equal else "architectural_difference",
            discrepancy_classes=() if simultaneous_cmp.equal else ("C", "D"),
            first_divergence=simultaneous_cmp.first_divergence,
            observation={"comparable_quantity": "per-tick spike set"},
            applicable=("project_fpga_v1", "brian2loihi_0_5_2", "catalyst_cpu_sync"),
            non_comparable=("global spike/event ordering",),
        )
    )

    by_probe = {record["probe_id"]: record for record in records}
    if len(by_probe) != 12:
        raise RuntimeError(f"M13.4 differential expected 12 probe records; got {len(by_probe)}")
    if any(record["requires_m12_revalidation"] for record in records):
        raise RuntimeError(
            "M13.4 found a candidate class-A/B discrepancy; stop before modifying the M12 baseline"
        )

    report = {
        "schema": M13_4_DIFFERENTIAL_SCHEMA,
        "status": "candidate_complete_pending_independent_validation",
        "normalization": {
            "schema": spec["schema"],
            "version": spec["version"],
            "status": spec["status"],
            "m13_3_merge_commit": M13_4_NORMALIZATION_MERGE,
        },
        "source_pins": {
            "project_m12": spec["source_pins"]["project_m12_baseline"],
            "brian2loihi": spec["source_pins"]["brian2loihi"],
            "catalyst_n1": CATALYST_PIN,
        },
        "probe_count": len(records),
        "results": sorted(records, key=lambda item: item["probe_id"]),
        "summary": {
            "agreement": sum(r["status"] == "agreement" for r in records),
            "architectural_difference": sum(r["status"] == "architectural_difference" for r in records),
            "partial_scope": sum(r["status"] == "partial_scope" for r in records),
            "non_comparable": sum(r["status"] == "non_comparable" for r in records),
            "class_A_or_B": sum(bool({"A", "B"} & set(r["discrepancy_classes"])) for r in records),
        },
    }
    report_path = _write_json(root / "directed-report.json", report)
    artifacts.append(report_path)

    manifest = {
        "schema": "neuromorphic-twin-m13-directed-differential-manifest-v1",
        "report": report_path.name,
        "artifacts": [
            {"path": p.relative_to(root).as_posix(), "sha256": _sha256(p)}
            for p in sorted(set(artifacts))
        ],
    }
    return _write_json(root / "manifest.json", manifest)
