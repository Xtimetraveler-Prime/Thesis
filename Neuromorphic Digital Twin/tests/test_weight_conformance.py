import json

from neuromorphic_twin.comparison.model import BackendTrace
from neuromorphic_twin.comparison.weight_conformance import (
    WeightBackendRun,
    build_weight_conformance_cases,
    format_weight_suite_report,
    run_python_weight_backend,
    run_weight_conformance_suite,
    write_weight_suite_report_json,
)


def test_weight_cases_are_unique_and_cover_m08_3_boundaries() -> None:
    cases = build_weight_conformance_cases()

    assert len(cases) == 15
    assert len({case.name for case in cases}) == len(cases)

    formats = {case.encoding.weight_format for case in cases}
    assert any(fmt.exponent == -2 for fmt in formats)
    assert any(fmt.exponent == 7 for fmt in formats)
    assert any(fmt.num_weight_bits == 0 for fmt in formats)
    assert any(fmt.num_weight_bits == 6 for fmt in formats)
    assert {fmt.sign_mode.value for fmt in formats} == {
        "mixed",
        "excitatory",
        "inhibitory",
    }
    assert any(case.encoding.clipped for case in cases)


def test_python_weight_cases_use_production_encoded_synapses() -> None:
    for case in build_weight_conformance_cases():
        synapse = case.scenario.synapses[0]
        assert synapse.is_encoded
        assert synapse.encoding == case.encoding
        assert synapse.weight == case.encoding.effective_weight

        run = run_python_weight_backend(case)
        assert run.effective_weight == case.encoding.effective_weight
        assert run.trace.ticks[0].current_after == (
            case.encoding.effective_weight,
        )
        assert run.trace.ticks[0].voltage_after == (
            case.encoding.effective_weight,
        )
        assert run.trace.ticks[0].spikes == ()

        assert len(run.trace.synapses) == 1
        descriptor = run.trace.synapses[0]
        fmt = case.encoding.weight_format
        assert descriptor.is_encoded
        assert descriptor.requested_mantissa == case.encoding.requested_mantissa
        assert descriptor.quantized_mantissa == case.encoding.quantized_mantissa
        assert descriptor.exponent == fmt.exponent
        assert descriptor.num_weight_bits == fmt.num_weight_bits
        assert descriptor.sign_mode == fmt.sign_mode.value
        assert (
            descriptor.effective_weight_before_clip
            == case.encoding.effective_weight_before_clip
        )
        assert descriptor.effective_weight == case.encoding.effective_weight
        assert descriptor.clipped == case.encoding.clipped


def test_weight_suite_passes_when_both_runners_are_identical() -> None:
    suite = run_weight_conformance_suite(
        reference_runner=run_python_weight_backend,
        candidate_runner=run_python_weight_backend,
    )

    assert suite.passed
    assert suite.pass_count == 15
    assert "pass=15" in format_weight_suite_report(suite)


def test_weight_suite_reports_direct_effective_weight_mismatch() -> None:
    case = build_weight_conformance_cases()[0]

    def mutated_reference(selected):
        run = run_python_weight_backend(selected)
        return WeightBackendRun(
            trace=BackendTrace(
                backend="mutated-reference",
                scenario=run.trace.scenario,
                ticks=run.trace.ticks,
                synapses=run.trace.synapses,
            ),
            effective_weight=run.effective_weight + 64,
        )

    suite = run_weight_conformance_suite(
        [case],
        reference_runner=mutated_reference,
        candidate_runner=run_python_weight_backend,
    )

    assert not suite.passed
    result = suite.results[0]
    assert result.status == "FAIL"
    assert result.report is not None
    mismatch = result.report.mismatches[0]
    assert mismatch.tick is None
    assert mismatch.field == "effective_weight"
    assert mismatch.reference == case.encoding.effective_weight + 64
    assert mismatch.candidate == case.encoding.effective_weight


def test_weight_suite_json_preserves_encoding_and_reference_values(
    tmp_path,
) -> None:
    case = build_weight_conformance_cases()[0]
    suite = run_weight_conformance_suite(
        [case],
        reference_runner=run_python_weight_backend,
        candidate_runner=run_python_weight_backend,
    )

    path = write_weight_suite_report_json(
        suite,
        tmp_path / "suite.json",
    )
    payload = json.loads(path.read_text(encoding="utf-8"))
    result = payload["results"][0]

    assert payload["schema"] == "neuromorphic-twin-weight-conformance-v1"
    assert result["encoding"]["requested_mantissa"] == 124
    assert result["encoding"]["candidate_effective_weight"] == 124 * 64
    assert result["reference_effective_weight"] == 124 * 64
