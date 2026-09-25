"""Shared host/runtime protocol for the frozen MNIST FPGA deployments."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Sequence

import numpy as np

from .config import PRESENTATION_TICKS, get_profile
from .dataset import load_mnist
from .encoding import encode_event_schedule
from .inference import infer_image, load_deployment

RUNTIME_REQUEST_SCHEMA = "neuromorphic-twin-mnist-runtime-request-v1"
RUNTIME_RESULT_SCHEMA = "neuromorphic-twin-mnist-runtime-result-v1"
RUNTIME_APPEND_TRACE_SPACE = 7
PROFILE_ORDER = ("cropped-dense", "native-sparse")
PROFILE_ID = {name: index for index, name in enumerate(PROFILE_ORDER)}


@dataclass(frozen=True, slots=True)
class RuntimeRequest:
    profile: str
    profile_id: int
    mnist_test_index: int
    label: int
    external_schedule: tuple[tuple[int, ...], ...]
    golden_prediction: int
    golden_spike_counts: tuple[int, ...]

    @property
    def total_events(self) -> int:
        return sum(map(len, self.external_schedule))


def build_runtime_request(
    frozen_root: str | Path,
    *,
    profile: str,
    mnist_test_index: int,
) -> RuntimeRequest:
    """Build one arbitrary MNIST test request from the immutable deployment."""

    selected = get_profile(profile)
    if selected.name not in PROFILE_ID:
        raise ValueError(f"runtime profile is not frozen: {selected.name}")
    dataset = load_mnist()
    if not 0 <= mnist_test_index < len(dataset.x_test):
        raise ValueError("mnist_test_index is outside the official test split")

    image = np.asarray(dataset.x_test[mnist_test_index])
    label = int(dataset.y_test[mnist_test_index])
    deployment = Path(frozen_root) / "deployments" / selected.name / "deployment.json"
    runtime = load_deployment(deployment)
    result = infer_image(
        runtime.core,
        image,
        profile=runtime.profile,
        row_lengths=runtime.row_lengths,
    )
    schedule = encode_event_schedule(image, profile=runtime.profile)
    if len(schedule) != PRESENTATION_TICKS:
        raise AssertionError("runtime encoder did not produce the frozen 16 ticks")

    return RuntimeRequest(
        profile=selected.name,
        profile_id=PROFILE_ID[selected.name],
        mnist_test_index=mnist_test_index,
        label=label,
        external_schedule=tuple(tuple(events) for events in schedule),
        golden_prediction=result.prediction,
        golden_spike_counts=result.spike_counts,
    )


def write_runtime_request(request: RuntimeRequest, output_dir: str | Path) -> tuple[Path, Path]:
    """Write JSON metadata plus a simple Tcl-readable tick/event TSV."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "request.json"
    tsv_path = output / "events.tsv"

    json_path.write_text(
        json.dumps(
            {
                "schema": RUNTIME_REQUEST_SCHEMA,
                "profile": request.profile,
                "profile_id": request.profile_id,
                "mnist_test_index": request.mnist_test_index,
                "label": request.label,
                "presentation_ticks": len(request.external_schedule),
                "total_events": request.total_events,
                "events_per_tick": [len(events) for events in request.external_schedule],
                "golden_prediction": request.golden_prediction,
                "golden_spike_counts": list(request.golden_spike_counts),
            },
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )

    lines = ["tick\tevents"]
    for tick, events in enumerate(request.external_schedule):
        lines.append(f"{tick}\t{','.join(str(event) for event in events)}")
    tsv_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return json_path, tsv_path


def validate_runtime_result(
    request: RuntimeRequest,
    payload: dict[str, object],
) -> dict[str, object]:
    """Check one hardware classification result against request/golden metadata."""

    if payload.get("schema") != RUNTIME_RESULT_SCHEMA:
        raise ValueError("unsupported MNIST runtime result schema")
    spike_counts = tuple(int(value) for value in payload["spike_counts"])
    prediction = int(payload["prediction"])
    observed_ticks = int(payload["ticks"])
    observed_events = int(payload["total_events"])
    mismatches: list[str] = []
    if str(payload.get("profile")) != request.profile:
        mismatches.append("profile")
    if int(payload.get("mnist_test_index", -1)) != request.mnist_test_index:
        mismatches.append("mnist_test_index")
    if observed_ticks != PRESENTATION_TICKS:
        mismatches.append("ticks")
    if observed_events != request.total_events:
        mismatches.append("total_events")
    if spike_counts != request.golden_spike_counts:
        mismatches.append("spike_counts")
    if prediction != request.golden_prediction:
        mismatches.append("prediction")
    return {
        "passed": not mismatches,
        "mismatches": mismatches,
        "profile": request.profile,
        "mnist_test_index": request.mnist_test_index,
        "label": request.label,
        "golden_prediction": request.golden_prediction,
        "physical_prediction": prediction,
        "golden_spike_counts": list(request.golden_spike_counts),
        "physical_spike_counts": list(spike_counts),
    }


def parse_event_rows(path: str | Path) -> tuple[tuple[int, ...], ...]:
    """Read the runtime TSV format; primarily used by tests/tooling."""

    lines = Path(path).read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "tick\tevents":
        raise ValueError("runtime event TSV has an invalid header")
    rows: list[tuple[int, ...]] = []
    for expected_tick, line in enumerate(lines[1:]):
        fields = line.split("\t", 1)
        if len(fields) != 2 or int(fields[0]) != expected_tick:
            raise ValueError("runtime event TSV ticks must be dense and zero-based")
        rows.append(tuple(int(value) for value in fields[1].split(",") if value))
    if len(rows) != PRESENTATION_TICKS:
        raise ValueError("runtime event TSV must contain exactly 16 tick rows")
    return tuple(rows)
