"""M13.4 directed architectural probe planning and pre-normalization evidence.

M13.4 is intentionally split into two boundaries:

* native/pre-normalization evidence may be produced from already validated shared
  project/Brian2Loihi scenarios; and
* normalized cross-implementation comparison is forbidden until M13.3 freezes
  the common behavioral subset and parameter/state transforms.

This prevents Catalyst-driven mappings from being invented after observing an
interesting output difference.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


M13_4_SCHEMA = "neuromorphic-twin-m13-directed-probe-catalog-v1"
M13_4_EVIDENCE_SCHEMA = "neuromorphic-twin-m13-pre-normalization-evidence-v1"
M13_4_BASELINE_COMMIT = "49ab7be6dfce427979622b585165b59bbbfbc2da"
M13_3_EXPECTED_SCHEMA = "neuromorphic-twin-m13-normalization-v1"

M13_4_REQUIRED_PROBE_CLASSES = {
    "impulse-response/current-decay sequences",
    "voltage-decay sequences",
    "negative-current rounding cases",
    "threshold equality and just-over-threshold behavior",
    "refractory entry, hold, countdown, and release",
    "positive/negative and mixed excitation/inhibition",
    "representative weight precision/exponent/sign-mode boundaries",
    "simultaneous fan-in and fan-out",
    "repeated event multiplicity",
    "recurrent-delivery timing and recurrent chains",
    "finite-width saturation/overflow boundaries",
}

_PARTICIPANTS = {"published_loihi", "brian2loihi", "project", "catalyst_n1"}
_PARTICIPATION_STATES = {
    "evidence_only",
    "runnable_existing",
    "runnable_new_native",
    "blocked_by_m13_3",
    "not_applicable",
}
_REUSE_KINDS = {"directed_cases", "weight_cases", "m12_physical_cases", "m12_multitick_cases"}


class M13NormalizationNotFrozen(RuntimeError):
    """Raised when normalized M13.4 work is requested before M13.3 exists."""


def default_probe_catalog_path() -> Path:
    return Path(__file__).resolve().parents[3] / "references" / "m13_4_probe_catalog.json"


def default_m13_3_spec_path() -> Path:
    return Path(__file__).resolve().parents[3] / "references" / "m13_3_normalization_spec.json"


def load_probe_catalog(path: str | Path | None = None) -> dict[str, Any]:
    target = Path(path) if path is not None else default_probe_catalog_path()
    with target.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    validate_probe_catalog(data)
    return data


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a mapping")
    return value


def validate_probe_catalog(data: Mapping[str, Any]) -> None:
    if data.get("schema") != M13_4_SCHEMA:
        raise ValueError("unexpected M13.4 probe-catalog schema")
    if data.get("baseline_commit") != M13_4_BASELINE_COMMIT:
        raise ValueError("M13.4 baseline commit changed")

    gate = _mapping(data.get("normalization_gate"), "normalization_gate")
    if gate.get("required_schema") != M13_3_EXPECTED_SCHEMA:
        raise ValueError("M13.4 normalization prerequisite schema changed")
    if gate.get("state") != "blocked_m13_3_not_frozen":
        raise ValueError("M13.4 catalog must remain blocked until M13.3 is frozen")
    if gate.get("normalized_comparison_allowed") is not False:
        raise ValueError("normalized comparison cannot be enabled by M13.4 itself")

    probes = data.get("probes")
    if not isinstance(probes, list) or not probes:
        raise ValueError("M13.4 probe catalog must be non-empty")

    ids: set[str] = set()
    covered: set[str] = set()
    for index, probe_value in enumerate(probes):
        probe = _mapping(probe_value, f"probes[{index}]")
        probe_id = str(probe.get("id", ""))
        if not probe_id or probe_id in ids:
            raise ValueError(f"missing/duplicate M13.4 probe id: {probe_id!r}")
        ids.add(probe_id)

        probe_class = str(probe.get("probe_class", ""))
        covered.add(probe_class)
        if not str(probe.get("question", "")).strip():
            raise ValueError(f"probe {probe_id} has no architectural question")
        rows = probe.get("crosswalk_rows")
        if not isinstance(rows, list) or not rows:
            raise ValueError(f"probe {probe_id} must cite M13.2 crosswalk rows")

        participation = _mapping(probe.get("participation"), f"{probe_id}.participation")
        if set(participation) != _PARTICIPANTS:
            raise ValueError(f"probe {probe_id} must define all four participants")
        for participant, state in participation.items():
            if state not in _PARTICIPATION_STATES:
                raise ValueError(f"probe {probe_id} has invalid {participant} state {state!r}")

        reuse = _mapping(probe.get("reuse"), f"{probe_id}.reuse")
        if set(reuse) != _REUSE_KINDS:
            raise ValueError(f"probe {probe_id} reuse map is incomplete")
        for kind, names in reuse.items():
            if not isinstance(names, list) or any(not isinstance(name, str) or not name for name in names):
                raise ValueError(f"probe {probe_id} reuse.{kind} must be a string list")

        if any(key in probe for key in ("discrepancy_class", "classification", "verdict")):
            raise ValueError(f"probe {probe_id} prematurely adjudicates a discrepancy")

    missing = M13_4_REQUIRED_PROBE_CLASSES - covered
    if missing:
        raise ValueError(f"M13.4 misses planned probe classes: {sorted(missing)}")

    summary = _mapping(data.get("summary"), "summary")
    if summary.get("probe_count") != len(probes):
        raise ValueError("M13.4 summary probe count is stale")
    if summary.get("required_probe_classes_covered") != len(M13_4_REQUIRED_PROBE_CLASSES):
        raise ValueError("M13.4 required-class summary is stale")


def require_frozen_m13_3(path: str | Path | None = None) -> dict[str, Any]:
    """Load the M13.3 normalization spec or refuse normalized M13.4 work."""

    target = Path(path) if path is not None else default_m13_3_spec_path()
    if not target.exists():
        raise M13NormalizationNotFrozen(
            f"M13.3 normalization spec is not frozen: expected {target}. "
            "Native probe capture may proceed, but normalized M13.4 comparison is blocked."
        )
    payload = json.loads(target.read_text(encoding="utf-8"))
    if payload.get("schema") != M13_3_EXPECTED_SCHEMA:
        raise M13NormalizationNotFrozen(
            f"unexpected M13.3 schema {payload.get('schema')!r}; expected {M13_3_EXPECTED_SCHEMA!r}"
        )
    if payload.get("status") != "frozen":
        raise M13NormalizationNotFrozen("M13.3 normalization spec exists but is not frozen")
    return payload


def pre_normalization_reuse_names(data: Mapping[str, Any]) -> dict[str, tuple[str, ...]]:
    """Return stable deduplicated case names that can be rerun before M13.3."""

    validate_probe_catalog(data)
    gathered: dict[str, list[str]] = {kind: [] for kind in _REUSE_KINDS}
    for probe in data["probes"]:
        for kind in _REUSE_KINDS:
            for name in probe["reuse"][kind]:
                if name not in gathered[kind]:
                    gathered[kind].append(name)
    return {kind: tuple(names) for kind, names in gathered.items()}


def _scenario_payload(scenario: Any) -> dict[str, Any]:
    neurons = [
        {
            "current_decay": int(cfg.current_decay),
            "voltage_decay": int(cfg.voltage_decay),
            "threshold": int(cfg.threshold),
            "reset_voltage": int(cfg.reset_voltage),
            "refractory_ticks": int(cfg.refractory_ticks),
        }
        for cfg in scenario.neuron_configs
    ]
    synapses = []
    for synapse in scenario.synapses:
        item: dict[str, Any] = {
            "axon_id": int(synapse.axon_id),
            "target_neuron": int(synapse.target_neuron),
            "effective_weight": int(synapse.weight),
        }
        if synapse.encoding is not None:
            enc = synapse.encoding
            fmt = enc.weight_format
            item["encoding"] = {
                "requested_mantissa": int(enc.requested_mantissa),
                "quantized_mantissa": int(enc.quantized_mantissa),
                "exponent": int(fmt.exponent),
                "num_weight_bits": int(fmt.num_weight_bits),
                "sign_mode": fmt.sign_mode.value,
                "effective_weight_before_clip": int(enc.effective_weight_before_clip),
                "effective_weight": int(enc.effective_weight),
                "clipped": bool(enc.clipped),
            }
        synapses.append(item)
    return {
        "name": scenario.name,
        "neuron_configs": neurons,
        "synapses": synapses,
        "input_schedule": [list(tick) for tick in scenario.input_schedule],
        "spike_routes": [
            {"source_neuron": int(route.source_neuron), "target_axon": int(route.target_axon)}
            for route in scenario.spike_routes
        ],
    }


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_pre_normalization_reuse(
    output_dir: str | Path,
    *,
    catalog_path: str | Path | None = None,
) -> Path:
    """Re-run already shared project/Brian2Loihi cases and preserve native evidence.

    This function intentionally does *not* execute Catalyst or normalize traces.
    Its artifacts are reusable input evidence for M13.4, not M13.4 discrepancy
    verdicts.
    """

    from .conformance import build_directed_cases, run_directed_suite
    from .io import write_report_json, write_trace_json
    from .weight_conformance import (
        build_weight_conformance_cases,
        run_weight_conformance_suite,
    )

    catalog = load_probe_catalog(catalog_path)
    names = pre_normalization_reuse_names(catalog)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)

    available_directed = {case.name: case for case in build_directed_cases()}
    unknown_directed = set(names["directed_cases"]) - set(available_directed)
    if unknown_directed:
        raise ValueError(f"catalog references unknown directed cases: {sorted(unknown_directed)}")
    directed_cases = tuple(available_directed[name] for name in names["directed_cases"])
    directed_suite = run_directed_suite(directed_cases)

    available_weights = {case.name: case for case in build_weight_conformance_cases()}
    unknown_weights = set(names["weight_cases"]) - set(available_weights)
    if unknown_weights:
        raise ValueError(f"catalog references unknown weight cases: {sorted(unknown_weights)}")
    weight_cases = tuple(available_weights[name] for name in names["weight_cases"])
    weight_suite = run_weight_conformance_suite(weight_cases)

    artifact_paths: list[Path] = []
    for result in directed_suite.results:
        case_dir = root / "directed" / result.case.name
        artifact_paths.append(_write_json(case_dir / "scenario.json", _scenario_payload(result.case.scenario)))
        if result.candidate is not None:
            artifact_paths.append(write_trace_json(result.candidate, case_dir / "project.native.json"))
        if result.reference is not None:
            artifact_paths.append(write_trace_json(result.reference, case_dir / "brian2loihi.native.json"))
        if result.report is not None:
            artifact_paths.append(write_report_json(result.report, case_dir / "project-vs-brian2loihi.report.json"))

    for result in weight_suite.results:
        case_dir = root / "weights" / result.case.name
        artifact_paths.append(_write_json(case_dir / "scenario.json", _scenario_payload(result.case.scenario)))
        if result.candidate is not None:
            artifact_paths.append(write_trace_json(result.candidate.trace, case_dir / "project.native.json"))
        if result.reference is not None:
            artifact_paths.append(write_trace_json(result.reference.trace, case_dir / "brian2loihi.native.json"))
        if result.report is not None:
            artifact_paths.append(write_report_json(result.report, case_dir / "project-vs-brian2loihi.report.json"))
        artifact_paths.append(
            _write_json(
                case_dir / "effective-weight.json",
                {
                    "project_effective_weight": (
                        result.candidate.effective_weight if result.candidate is not None else None
                    ),
                    "brian2loihi_effective_weight": (
                        result.reference.effective_weight if result.reference is not None else None
                    ),
                },
            )
        )

    manifest = {
        "schema": M13_4_EVIDENCE_SCHEMA,
        "catalog_schema": M13_4_SCHEMA,
        "baseline_commit": M13_4_BASELINE_COMMIT,
        "normalization_schema_required": M13_3_EXPECTED_SCHEMA,
        "normalized_comparison_performed": False,
        "catalyst_execution_performed": False,
        "purpose": (
            "Pre-normalization re-execution of already shared project/Brian2Loihi directed evidence. "
            "These results must not be interpreted as Catalyst or four-way discrepancy verdicts."
        ),
        "directed_summary": {
            "cases": len(directed_suite.results),
            "pass": directed_suite.pass_count,
            "fail": directed_suite.fail_count,
            "error": directed_suite.error_count,
            "ticks": directed_suite.total_ticks,
            "mismatches": directed_suite.mismatch_count,
        },
        "weight_summary": {
            "cases": len(weight_suite.results),
            "pass": weight_suite.pass_count,
            "fail": weight_suite.fail_count,
            "error": weight_suite.error_count,
            "ticks": weight_suite.total_ticks,
            "mismatches": weight_suite.mismatch_count,
        },
        "artifacts": [
            {"path": str(path.relative_to(root)), "sha256": _sha256(path)}
            for path in sorted(artifact_paths)
        ],
    }
    manifest_path = _write_json(root / "manifest.json", manifest)

    if not directed_suite.passed or not weight_suite.passed:
        raise RuntimeError(
            "pre-normalization project/Brian2Loihi evidence changed; inspect preserved artifacts"
        )
    return manifest_path
