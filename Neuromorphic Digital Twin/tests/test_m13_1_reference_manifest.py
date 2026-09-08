from __future__ import annotations

import json
from pathlib import Path

from neuromorphic_twin.m13_reference_manifest import (
    M13_BRIAN2LOIHI_COMMIT,
    M13_CATALYST_COMMIT,
    M13_CATALYST_TAG,
    M13_PROJECT_BASELINE_COMMIT,
    default_manifest_path,
    load_reference_manifest,
)


ROOT = Path(__file__).resolve().parents[1]


def test_m13_1_manifest_pins_all_four_evidence_columns() -> None:
    data = load_reference_manifest()
    assert data["project_baseline"]["commit"] == M13_PROJECT_BASELINE_COMMIT
    assert data["catalyst_n1"]["commit"] == M13_CATALYST_COMMIT
    assert data["catalyst_n1"]["primary_tag"] == M13_CATALYST_TAG
    assert data["brian2loihi"]["commit"] == M13_BRIAN2LOIHI_COMMIT
    assert len(data["published_loihi"]) >= 2
    assert {entry["doi"] for entry in data["published_loihi"]} >= {
        "10.1109/MM.2018.112130359",
        "10.1109/MC.2018.157113521",
    }


def test_m13_1_catalyst_pin_is_paper_tag_and_k26_boundary_is_frozen() -> None:
    data = load_reference_manifest()
    catalyst = data["catalyst_n1"]
    assert catalyst["primary_tag"] == "v2.3-paper"
    assert catalyst["equivalent_tag"] == "n1-final"
    assert catalyst["license"] == "Apache-2.0"
    assert catalyst["paper"]["doi"] == "10.5281/zenodo.18727094"
    assert catalyst["native_simulation"]["testbench_count_in_script"] == 25
    assert catalyst["native_simulation"]["tool_requirement"] == ">=12"
    kria = catalyst["kria_k26_flow"]
    assert kria["target_part_in_script"] == "xczu5ev-sfvc784-2-i"
    assert kria["configured_cores"] == 2
    assert kria["neurons_per_core"] == 256
    assert kria["pool_depth_per_core"] == 4096
    assert kria["clock_target_hz"] == 100_000_000
    assert "do not pin a Vivado version" in kria["vivado_version_status"]
    assert "Vivado 2025.2" in kria["vivado_version_status"]


def test_m13_1_brian2loihi_pin_matches_existing_project_dependency() -> None:
    data = load_reference_manifest()
    brian = data["brian2loihi"]
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    assert brian["project_dependency"] == "brian2-loihi==0.5.2"
    assert '"brian2-loihi==0.5.2"' in pyproject
    assert brian["tag"] == "v0.5.2"
    assert brian["wheel_sha256"] == "fc0bf66ea9e212a0c7d5003332b244fe02a47bc874382092b0bff6d83ebbd4d3"


def test_m13_1_evidence_and_discrepancy_vocabularies_are_frozen_before_comparison() -> None:
    data = load_reference_manifest()
    assert {item["id"] for item in data["evidence_types"]} == {
        "published_documentation",
        "direct_observation",
        "implementation_inference",
        "project_interpretation",
    }
    assert list(data["discrepancy_classes"]) == list("ABCDEFGH")
    assert data["change_control"]["baseline_mutation_allowed_for"] == ["A", "B"]
    assert len(data["change_control"]["required_steps"]) == 5
    independence = "\n".join(data["independence_rules"])
    assert "Do not copy Catalyst RTL" in independence
    assert "desire to make outputs agree" in independence


def test_m13_1_manifest_is_deterministic_json_and_source_controlled() -> None:
    path = default_manifest_path()
    raw = path.read_text(encoding="utf-8")
    parsed = json.loads(raw)
    assert parsed == load_reference_manifest(path)
    assert path.name == "m13_1_reference_manifest.json"
    assert raw.endswith("\n")


def test_m13_1_fetch_and_native_regression_scripts_never_modify_catalyst_sources() -> None:
    fetch = (ROOT / "scripts" / "fetch_m13_1_catalyst.sh").read_text(encoding="utf-8")
    regression = (ROOT / "scripts" / "run_m13_1_catalyst_rtl_regression.sh").read_text(encoding="utf-8")
    assert M13_CATALYST_COMMIT in fetch
    assert M13_CATALYST_TAG in fetch
    assert "checkout --detach --force" in fetch
    assert "clean -fdx" in fetch
    assert M13_CATALYST_COMMIT in regression
    assert "grep -m1 '^RTL=\"'" in regression
    assert "grep -m1 '^for tb in .*; do$'" in regression
    assert "${rtl_files[@]}" in regression
    assert "${testbenches[@]}" in regression
    for forbidden in ("sed -i", "perl -pi", "git apply", "patch "):
        assert forbidden not in regression
