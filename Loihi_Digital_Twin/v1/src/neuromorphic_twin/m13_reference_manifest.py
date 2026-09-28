"""M13.1 external-reference pinning and local checkout verification.

This module deliberately validates provenance and comparison methodology only.
It does not normalize Catalyst behavior, compare neuron equations, or change the
M10/M12 project baseline. Those activities belong to later M13 milestones.
"""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
import re
import subprocess
from typing import Any

M13_REFERENCE_MANIFEST_SCHEMA = "neuromorphic-twin-m13-reference-manifest-v1"
M13_CATALYST_COMMIT = "1806bb4b4114d7671e5648fa75b7b83b3a8d5543"
M13_CATALYST_TAG = "v2.3-paper"
M13_BRIAN2LOIHI_COMMIT = "d54676cb113e48dc886615a0b589bb0e4bccbca4"
M13_PROJECT_BASELINE_COMMIT = "80a502ec6dfc4c8d61372089b08c9a584ad65f85"
M13_DISCREPANCY_CLASSES = tuple("ABCDEFGH")
_SHA40 = re.compile(r"^[0-9a-f]{40}$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True, slots=True)
class CatalystCheckoutVerification:
    checkout: Path
    commit: str
    tags_at_commit: tuple[str, ...]
    required_files: tuple[str, ...]
    regression_testbenches: tuple[str, ...]
    clean: bool


def default_manifest_path() -> Path:
    return Path(__file__).resolve().parents[2] / "references" / "m13_1_reference_manifest.json"


def load_reference_manifest(path: str | Path | None = None) -> dict[str, Any]:
    manifest_path = Path(path) if path is not None else default_manifest_path()
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    validate_reference_manifest(data)
    return data


def validate_reference_manifest(data: dict[str, Any]) -> None:
    if data.get("schema") != M13_REFERENCE_MANIFEST_SCHEMA:
        raise ValueError(f"unexpected M13 reference manifest schema: {data.get('schema')!r}")

    project = _mapping(data, "project_baseline")
    catalyst = _mapping(data, "catalyst_n1")
    brian = _mapping(data, "brian2loihi")

    _require_sha40(project.get("commit"), "project baseline commit")
    _require_sha40(catalyst.get("commit"), "Catalyst commit")
    _require_sha40(brian.get("commit"), "Brian2Loihi commit")
    if project["commit"] != M13_PROJECT_BASELINE_COMMIT:
        raise ValueError("M13 project baseline is not the M12 closure merge")
    if catalyst["commit"] != M13_CATALYST_COMMIT:
        raise ValueError("Catalyst N1 commit differs from the frozen M13.1 pin")
    if catalyst.get("primary_tag") != M13_CATALYST_TAG:
        raise ValueError("Catalyst N1 primary tag differs from the frozen M13.1 pin")
    if catalyst.get("pin_kind") != "lightweight Git tags resolved directly to commit":
        raise ValueError("Catalyst N1 tag-kind provenance changed")
    if brian["commit"] != M13_BRIAN2LOIHI_COMMIT:
        raise ValueError("Brian2Loihi commit differs from the frozen project dependency")
    if brian.get("project_dependency") != "brian2-loihi==0.5.2":
        raise ValueError("Brian2Loihi project dependency must remain exactly 0.5.2")
    _require_sha256(brian.get("wheel_sha256"), "Brian2Loihi wheel SHA-256")

    native = _mapping(catalyst, "native_simulation")
    if native.get("testbench_count_in_script") != 25:
        raise ValueError("Catalyst native regression testbench count must be frozen at 25")
    if native.get("tool") != "Icarus Verilog" or native.get("tool_requirement") != ">=12":
        raise ValueError("Catalyst native simulation tool boundary changed")

    kria = _mapping(catalyst, "kria_k26_flow")
    expected_kria = {
        "target_part_in_script": "xczu5ev-sfvc784-2-i",
        "configured_cores": 2,
        "neurons_per_core": 256,
        "pool_depth_per_core": 4096,
        "clock_target_hz": 100_000_000,
        "clock_period_ns": 10.0,
    }
    for key, expected in expected_kria.items():
        if kria.get(key) != expected:
            raise ValueError(f"Catalyst K26 frozen field changed: {key}")

    for boundary in catalyst.get("key_source_boundaries", []):
        if not isinstance(boundary, dict) or not boundary.get("path"):
            raise ValueError("invalid Catalyst key source boundary")
        _require_sha40(boundary.get("blob_sha"), f"Catalyst blob {boundary.get('path')}")

    sdk = _mapping(catalyst, "sdk_reference")
    for key in ("simulator_blob_sha", "simulator_test_blob_sha", "setup_blob_sha"):
        _require_sha40(sdk.get(key), f"Catalyst SDK {key}")

    published = data.get("published_loihi")
    if not isinstance(published, list) or len(published) < 2:
        raise ValueError("M13.1 requires at least the two frozen published Loihi sources")
    dois = [entry.get("doi") for entry in published if isinstance(entry, dict)]
    if len(dois) != len(set(dois)) or any(not doi for doi in dois):
        raise ValueError("published Loihi DOI list must be populated and unique")

    evidence = data.get("evidence_types")
    evidence_ids = {entry.get("id") for entry in evidence or [] if isinstance(entry, dict)}
    required_evidence = {
        "published_documentation",
        "direct_observation",
        "implementation_inference",
        "project_interpretation",
    }
    if evidence_ids != required_evidence:
        raise ValueError("M13.1 evidence vocabulary changed")

    classes = data.get("discrepancy_classes")
    if not isinstance(classes, dict) or tuple(classes.keys()) != M13_DISCREPANCY_CLASSES:
        raise ValueError("M13 discrepancy classes A-H must be frozen in order")
    env = _mapping(data, "m13_1_validated_environment")
    if env.get("python") != "3.11.16" or not str(env.get("iverilog", "")).startswith("12.0"):
        raise ValueError("M13.1 exact closure-validation environment changed")
    if _mapping(env, "catalyst_rtl").get("result") != "25/25 native run_regression.sh testbenches passed":
        raise ValueError("M13.1 Catalyst RTL validation result changed")
    if _mapping(env, "catalyst_cpu").get("result") != "56/56 sdk/tests/test_simulator.py tests passed":
        raise ValueError("M13.1 Catalyst CPU validation result changed")

    change = _mapping(data, "change_control")
    if change.get("baseline_mutation_allowed_for") != ["A", "B"]:
        raise ValueError("only discrepancy classes A/B may alter the frozen baseline")
    if len(change.get("required_steps", [])) != 5:
        raise ValueError("M13 A/B change control must preserve all five required steps")


def verify_catalyst_checkout(
    checkout: str | Path,
    manifest: dict[str, Any] | None = None,
    *,
    require_clean: bool = True,
) -> CatalystCheckoutVerification:
    data = manifest if manifest is not None else load_reference_manifest()
    validate_reference_manifest(data)
    catalyst = _mapping(data, "catalyst_n1")
    root = Path(checkout).resolve()
    if not (root / ".git").exists():
        raise ValueError(f"Catalyst checkout is not a Git repository: {root}")

    head = _git(root, "rev-parse", "HEAD")
    if head != catalyst["commit"]:
        raise ValueError(f"Catalyst checkout commit mismatch: expected={catalyst['commit']} actual={head}")

    tags = tuple(sorted(filter(None, _git(root, "tag", "--points-at", "HEAD").splitlines())))
    required_tags = {catalyst["primary_tag"], catalyst["equivalent_tag"]}
    if not required_tags.issubset(tags):
        raise ValueError(f"Catalyst checkout is missing frozen tags at HEAD: required={sorted(required_tags)} actual={tags}")
    for tag in sorted(required_tags):
        if _git(root, "cat-file", "-t", tag) != "commit":
            raise ValueError(f"Catalyst frozen tag is no longer lightweight/direct-to-commit: {tag}")

    status = _git(root, "status", "--porcelain")
    clean = not bool(status.strip())
    if require_clean and not clean:
        raise ValueError("Catalyst checkout has local modifications; native evidence must start from a clean pin")

    required: dict[str, str] = {}
    for boundary in catalyst["key_source_boundaries"]:
        required[boundary["path"]] = boundary["blob_sha"]
    native = catalyst["native_simulation"]
    sdk = catalyst["sdk_reference"]
    kria = catalyst["kria_k26_flow"]
    required[native["rtl_regression_script"]] = native["rtl_regression_blob_sha"]
    required[sdk["simulator_path"]] = sdk["simulator_blob_sha"]
    required[sdk["simulator_test_path"]] = sdk["simulator_test_blob_sha"]
    required[sdk["setup_path"]] = sdk["setup_blob_sha"]
    required[kria["build_script"]] = kria["build_script_blob_sha"]
    required[kria["implementation_script"]] = kria["implementation_script_blob_sha"]
    required[kria["wrapper"]] = kria["wrapper_blob_sha"]

    for relative, expected_blob in required.items():
        path = root / relative
        if not path.is_file():
            raise ValueError(f"Catalyst pinned file is missing: {relative}")
        actual_blob = _git(root, "hash-object", "--", relative)
        if actual_blob != expected_blob:
            raise ValueError(
                f"Catalyst pinned file content mismatch: {relative} expected={expected_blob} actual={actual_blob}"
            )

    regression_text = (root / native["rtl_regression_script"]).read_text(encoding="utf-8")
    match = re.search(r"^for tb in (.+); do$", regression_text, flags=re.MULTILINE)
    if not match:
        raise ValueError("could not locate Catalyst native regression testbench list")
    testbenches = tuple(match.group(1).split())
    if len(testbenches) != native["testbench_count_in_script"]:
        raise ValueError(
            f"Catalyst native regression list changed: expected={native['testbench_count_in_script']} actual={len(testbenches)}"
        )

    build_text = (root / kria["build_script"]).read_text(encoding="utf-8")
    impl_text = (root / kria["implementation_script"]).read_text(encoding="utf-8")
    wrapper_text = (root / kria["wrapper"]).read_text(encoding="utf-8")
    required_fragments = (
        (build_text, f'set part        "{kria["target_part_in_script"]}"'),
        (impl_text, "create_clock -period 10.000 -name sys_clk"),
        (wrapper_text, "parameter NUM_CORES      = 2"),
        (wrapper_text, "parameter NUM_NEURONS    = 256"),
        (wrapper_text, "parameter POOL_DEPTH     = 4096"),
        (wrapper_text, ".CLK_FREQ       (100_000_000)"),
    )
    for text, fragment in required_fragments:
        if fragment not in text:
            raise ValueError(f"Catalyst frozen K26 boundary fragment not found: {fragment}")

    return CatalystCheckoutVerification(
        checkout=root,
        commit=head,
        tags_at_commit=tags,
        required_files=tuple(sorted(required)),
        regression_testbenches=testbenches,
        clean=clean,
    )


def _mapping(parent: dict[str, Any], key: str) -> dict[str, Any]:
    value = parent.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"M13 reference manifest field must be an object: {key}")
    return value


def _require_sha40(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _SHA40.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase 40-hex Git SHA")


def _require_sha256(value: Any, label: str) -> None:
    if not isinstance(value, str) or not _SHA256.fullmatch(value):
        raise ValueError(f"{label} must be a lowercase 64-hex SHA-256")


def _git(root: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *args],
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    return completed.stdout.strip()
