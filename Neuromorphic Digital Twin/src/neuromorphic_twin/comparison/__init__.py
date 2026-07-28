"""Backend-neutral verification harness for the neuromorphic twin."""

from .brian2loihi_backend import (
    BackendUnavailableError,
    Brian2LoihiMapping,
    UnsupportedScenarioError,
    effective_weight_to_mantissa,
    run_brian2loihi_backend,
    validate_brian2loihi_scenario,
)
from .compare import compare_traces, format_report
from .io import read_trace_json, write_report_json, write_trace_json
from .model import (
    BackendTick,
    BackendTrace,
    ComparisonReport,
    ComparisonScenario,
    TraceMismatch,
)
from .python_backend import run_python_backend

__all__ = [
    "BackendTick",
    "BackendTrace",
    "BackendUnavailableError",
    "Brian2LoihiMapping",
    "ComparisonReport",
    "ComparisonScenario",
    "TraceMismatch",
    "UnsupportedScenarioError",
    "compare_traces",
    "effective_weight_to_mantissa",
    "format_report",
    "read_trace_json",
    "run_brian2loihi_backend",
    "run_python_backend",
    "validate_brian2loihi_scenario",
    "write_report_json",
    "write_trace_json",
]
