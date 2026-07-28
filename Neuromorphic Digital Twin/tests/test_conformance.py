from dataclasses import replace

from neuromorphic_twin.comparison import (
    BackendTrace,
    run_python_backend,
    validate_brian2loihi_scenario,
)
from neuromorphic_twin.comparison.conformance import (
    build_directed_cases,
    format_suite_report,
    run_directed_suite,
)


def test_directed_cases_are_unique_and_adapter_compatible() -> None:
    cases = build_directed_cases()
    assert len(cases) == 12
    assert len({case.name for case in cases}) == len(cases)
    for case in cases:
        validate_brian2loihi_scenario(case.scenario)


def test_all_directed_scenarios_run_in_python_backend() -> None:
    for case in build_directed_cases():
        trace = run_python_backend(case.scenario)
        assert len(trace.ticks) == len(case.scenario.input_schedule)
        assert trace.neuron_count == len(case.scenario.neuron_configs)


def test_suite_passes_when_both_runners_are_identical() -> None:
    suite = run_directed_suite(
        reference_runner=run_python_backend,
        candidate_runner=run_python_backend,
    )
    assert suite.passed
    assert suite.pass_count == 12
    assert "pass=12" in format_suite_report(suite)


def test_suite_reports_a_precise_candidate_mismatch() -> None:
    case = build_directed_cases()[0]

    def mutated_candidate(scenario):
        trace = run_python_backend(scenario)
        first = trace.ticks[0]
        changed = replace(
            first,
            voltage_after=(first.voltage_after[0] + 1,),
        )
        return BackendTrace(
            backend="mutated-candidate",
            scenario=trace.scenario,
            ticks=(changed, *trace.ticks[1:]),
        )

    suite = run_directed_suite(
        [case],
        reference_runner=run_python_backend,
        candidate_runner=mutated_candidate,
    )
    assert not suite.passed
    result = suite.results[0]
    assert result.status == "FAIL"
    assert result.report is not None
    mismatch = result.report.mismatches[0]
    assert mismatch.tick == 0
    assert mismatch.field == "voltage_after"
    assert mismatch.neuron_id == 0
