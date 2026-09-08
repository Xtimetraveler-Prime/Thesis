from __future__ import annotations

from pathlib import Path

from neuromorphic_twin.fpga_broad_regression import (
    M12_BROAD_CASE_COUNT,
    M12_BROAD_CORPUS_SCHEMA,
    M12_BROAD_GENERATOR_VERSION,
    M12_BROAD_MASTER_SEED,
    build_m12_broad_cases,
    compare_m12_broad_capture,
    write_m12_broad_corpus,
)
from neuromorphic_twin.fpga_physical_trace import PhysicalFpgaTraceArtifact


def _by_name():
    return {case.name: case for case in build_m12_broad_cases()}


def test_m12_4_corpus_identity_is_frozen_and_dense() -> None:
    cases = build_m12_broad_cases()
    assert M12_BROAD_CASE_COUNT == 22
    assert len(cases) == 22
    assert sum(case.tick_count for case in cases) == 166
    assert tuple(case.case_id for case in cases) == tuple(range(22))
    assert len({case.name for case in cases}) == 22
    assert sum(case.source_kind == "seeded" for case in cases) == 16
    assert sum(case.source_kind == "stress" for case in cases) == 6
    assert all(case.generator_version == M12_BROAD_GENERATOR_VERSION for case in cases)
    assert M12_BROAD_MASTER_SEED == 0x4D31323456310001


def test_seeded_cases_vary_configuration_and_are_reproducible() -> None:
    first = build_m12_broad_cases()
    second = build_m12_broad_cases()
    assert tuple(case.seed for case in first) == tuple(case.seed for case in second)
    assert tuple(case.configuration_sha256 for case in first) == tuple(
        case.configuration_sha256 for case in second
    )
    assert tuple(case.workload.expected_ticks for case in first) == tuple(
        case.workload.expected_ticks for case in second
    )

    seeded = first[:16]
    assert len({case.configuration_sha256 for case in seeded}) == 16
    assert len({case.workload.neuron_count for case in seeded}) >= 4
    assert len({case.workload.storage.axon_count for case in seeded}) >= 4
    assert len({case.workload.tick_count for case in seeded}) >= 4
    assert all(case.workload.routes.route_count > 0 for case in seeded)


def test_stress_cases_hit_selected_physical_boundaries() -> None:
    cases = _by_name()

    multiplicity = cases["stress-external-multiplicity-1024"].workload
    assert len(multiplicity.external_schedule[0]) == 1024
    assert multiplicity.storage.synapse_count == 1

    dense = cases["stress-dense-fanin-256-synapses"].workload
    assert dense.neuron_count == 32
    assert dense.storage.synapse_count == 256
    assert len(dense.external_schedule[0]) == 32

    route = cases["stress-recurrent-fanout-256"].workload
    assert route.routes.route_count == 256
    assert route.storage.axon_count == 257
    assert len(route.expected_ticks[0].snapshot.routed_output_axons) == 256
    assert len(route.expected_ticks[1].snapshot.recurrent_input_axons) == 256

    population = cases["stress-neuron-population-128"].workload
    assert population.neuron_count == 128
    assert len(population.external_schedule[0]) == 128
    assert sum(population.expected_ticks[0].snapshot.spikes) == 128

    ring = cases["stress-recurrent-ring-32-ticks"].workload
    assert ring.neuron_count == 16
    assert ring.tick_count == 32
    assert ring.routes.route_count == 16
    assert all(sum(tick.snapshot.spikes) == 1 for tick in ring.expected_ticks)

    mixed = cases["stress-mixed-dense-history"].workload
    assert mixed.neuron_count == 32
    assert mixed.storage.axon_count == 64
    assert mixed.storage.synapse_count == 256
    assert mixed.routes.route_count == 128
    assert mixed.tick_count == 12


def test_every_configuration_hash_is_full_unique_sha256() -> None:
    hashes = [case.configuration_sha256 for case in build_m12_broad_cases()]
    assert len(set(hashes)) == len(hashes)
    assert all(len(value) == 64 for value in hashes)
    assert all(set(value) <= set("0123456789abcdef") for value in hashes)


def test_exact_comparator_accepts_all_python_expected_timelines() -> None:
    for case in build_m12_broad_cases():
        artifact = PhysicalFpgaTraceArtifact(
            scenario_id=case.name,
            transport="jtag-vio",
            device="test-device",
            ticks=case.workload.expected_ticks,
        )
        report = compare_m12_broad_capture(case, artifact)
        assert report.passed
        assert report.mismatches == ()


def test_manifest_and_per_case_artifacts_are_byte_deterministic(tmp_path: Path) -> None:
    left = tmp_path / "left"
    right = tmp_path / "right"
    manifest_left = write_m12_broad_corpus(left)
    manifest_right = write_m12_broad_corpus(right)
    assert manifest_left.read_bytes() == manifest_right.read_bytes()
    text = manifest_left.read_text(encoding="utf-8")
    assert f'"schema": "{M12_BROAD_CORPUS_SCHEMA}"' in text
    assert f'"generator_version": "{M12_BROAD_GENERATOR_VERSION}"' in text
    assert '"case_count": 22' in text
    assert '"total_ticks": 166' in text
    assert '"m12_2_directed_single_tick_cases": 16' in text
    assert '"m12_3_directed_multitick_cases": 10' in text

    for artifact in sorted(left.glob("*.golden.json")):
        assert artifact.read_bytes() == (right / artifact.name).read_bytes()
