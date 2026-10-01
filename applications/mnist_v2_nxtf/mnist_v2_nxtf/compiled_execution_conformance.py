"""P08.4.2 exact compiled-deployment execution conformance.

This gate executes one deterministic official-test frame through the accepted
P06 compiled deployment and compares the packet-level logical/paged execution
against the source-recovered vectorized SNN semantics accepted in P08.3/P08.4.1.
The representative frame is fixed by index, not selected by classification
outcome, confidence, label, or accuracy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from loihi_twin_v2 import PagedVirtualizedLogicalChip
from loihi_twin_v2.compiler import CompiledDeployment

from .data import load_mnist
from .source_backend_reconstruction import _build_activity_simulator
from .source_recovered_conversion import (
    SOURCE_RECOVERED_COMPILED,
    SOURCE_RECOVERED_PARAMETERS,
)
from .source_recovered_validation import (
    ACCEPTED_INPUT_THRESHOLD,
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
    VALIDATION_TIMESTEPS,
    _load_accepted_conversion,
)

CONFORMANCE_SCHEMA = "p08-compiled-execution-conformance-v1"
CONFORMANCE_MANIFEST = "compiled_execution_conformance_manifest.json"
CONFORMANCE_VECTORS = "compiled_execution_conformance_vectors.npz"
REPRESENTATIVE_TEST_INDEX = 0
REPRESENTATIVE_SELECTION_RULE = "fixed_test_index_0_not_conditioned_on_result"
CONFORMANCE_TIMESTEPS = VALIDATION_TIMESTEPS
FORWARD_ORDER = (0, 1, 2, 3, 4)
REVERSE_ORDER = (4, 3, 2, 1, 0)


@dataclass(frozen=True, slots=True)
class ExecutionResult:
    mode: str
    trace_fingerprint: str
    final_evidence: tuple[int, ...]
    prediction: int
    ingress_packets: int
    internal_packet_traffic: int
    page_loads: int
    page_hits: int
    evictions: int


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def bias_input_spike_schedule(
    pixel_bias: np.ndarray,
    *,
    threshold: int = ACCEPTED_INPUT_THRESHOLD,
    timesteps: int = CONFORMANCE_TIMESTEPS,
) -> np.ndarray:
    """Reproduce the omitted NxTF BIAS input-neuron hard-reset spike train.

    Returns a boolean matrix with shape ``(timesteps, 784)``. The compiled graph
    begins at conv1, so source input spikes from tick ``t`` are injected into the
    compiled graph at algorithmic timestep ``t + 1``. Consequently the final
    source tick is generated for audit parity but is not consumed inside the
    fixed 100-timestep compiled horizon.
    """

    values = np.asarray(pixel_bias, dtype=np.int64)
    if values.shape == (28, 28, 1):
        values = values[..., 0]
    if values.shape != (28, 28):
        raise ValueError(f"pixel_bias must have shape (28,28) or (28,28,1); got {values.shape}")
    if np.any(values < 0) or np.any(values > 255):
        raise ValueError("pixel_bias must be in [0,255]")
    if threshold <= 0 or timesteps <= 0:
        raise ValueError("threshold and timesteps must be positive")

    flat = values.reshape(-1)
    voltage = np.zeros_like(flat, dtype=np.int64)
    spikes = np.zeros((timesteps, flat.size), dtype=bool)
    for tick in range(timesteps):
        candidate = voltage + flat
        emitted = candidate > threshold
        spikes[tick] = emitted
        voltage = np.where(emitted, 0, candidate)
    return spikes


def _trace_update(digest: "hashlib._Hash", trace) -> None:
    digest.update(repr(trace.normalized()).encode("utf-8"))
    digest.update(b"\n")


def _final_conv4_evidence(compiled: CompiledDeployment, chip) -> tuple[int, ...]:
    placements = [
        record
        for record in compiled.placement
        if record.population.startswith("conv4_c")
    ]
    placements = sorted(placements, key=lambda record: record.population)
    if len(placements) != 10 or any(record.neuron_index != 0 for record in placements):
        raise AssertionError("compiled conv4 placement no longer contains ten scalar output channels")
    return tuple(
        int(chip.cores[record.core_id].states[record.compartment_id].voltage)
        for record in placements
    )


def _run_compiled(
    compiled: CompiledDeployment,
    input_spikes: np.ndarray,
    *,
    mode: str,
) -> ExecutionResult:
    if input_spikes.shape != (CONFORMANCE_TIMESTEPS, 784):
        raise ValueError("input_spikes shape drifted")

    if mode == "unpaged_reference":
        chip = compiled.build_chip()
        service_order = None
        reverse_drain = False
        paged = False
    elif mode == "paged_forward":
        chip = PagedVirtualizedLogicalChip(
            compiled.logical_deployment.core_configs,
            resident_context_count=3,
        )
        service_order = FORWARD_ORDER
        reverse_drain = False
        paged = True
    elif mode == "paged_reverse":
        chip = PagedVirtualizedLogicalChip(
            compiled.logical_deployment.core_configs,
            resident_context_count=3,
        )
        service_order = REVERSE_ORDER
        reverse_drain = True
        paged = True
    else:
        raise ValueError(f"unknown execution mode {mode!r}")

    trace_digest = hashlib.sha256()
    ingress_packets = 0
    internal_packet_traffic = 0
    page_loads = 0
    page_hits = 0
    evictions = 0

    for timestep in range(CONFORMANCE_TIMESTEPS):
        # The omitted BIAS input neuron adds one algorithmic tick of latency.
        # At t=0 conv1 receives no external spike. At t>0 it receives input
        # spikes generated by the source input neuron at t-1.
        active = () if timestep == 0 else tuple(np.flatnonzero(input_spikes[timestep - 1]))
        external = compiled.external_packets(
            "pixels",
            active,
            target_timestep=timestep,
        )
        ingress_packets += len(external)

        if paged:
            trace = chip.step(
                external,
                service_order=service_order,
                reverse_packet_drain=reverse_drain,
            )
            if chip.last_page_schedule is None:
                raise AssertionError("paged execution did not record a page schedule")
            page_loads += chip.last_page_schedule.page_load_count
            page_hits += chip.last_page_schedule.page_hit_count
            evictions += chip.last_page_schedule.eviction_count
        else:
            trace = chip.step(external)

        internal_packet_traffic += len(trace.packet_traffic)
        _trace_update(trace_digest, trace)

    evidence = _final_conv4_evidence(compiled, chip)
    return ExecutionResult(
        mode=mode,
        trace_fingerprint=trace_digest.hexdigest(),
        final_evidence=evidence,
        prediction=int(np.argmax(np.asarray(evidence, dtype=np.int64))),
        ingress_packets=ingress_packets,
        internal_packet_traffic=internal_packet_traffic,
        page_loads=page_loads,
        page_hits=page_hits,
        evictions=evictions,
    )


def run_compiled_execution_conformance(
    conversion_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    root = Path(conversion_dir)
    parameters, conversion_manifest = _load_accepted_conversion(root)
    compiled_path = root / SOURCE_RECOVERED_COMPILED
    parameters_path = root / SOURCE_RECOVERED_PARAMETERS
    if not compiled_path.is_file() or not parameters_path.is_file():
        raise FileNotFoundError("accepted P08.3.5c compiled artifacts are missing")

    compiled = CompiledDeployment.read_json(compiled_path)
    if compiled.fingerprint != ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT:
        raise AssertionError("P08.4.2 compiled deployment fingerprint mismatch")
    if compiled.source_fingerprint != ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT:
        raise AssertionError("P08.4.2 compiled source/network fingerprint mismatch")
    if len(compiled.logical_deployment.core_configs) != 5:
        raise AssertionError("P08.4.2 requires the accepted five-logical-core deployment")

    dataset = load_mnist()
    if dataset.x_test.shape != (10_000, 28, 28):
        raise AssertionError("official MNIST test image shape drifted")
    if not 0 <= REPRESENTATIVE_TEST_INDEX < len(dataset.x_test):
        raise AssertionError("representative test index is out of range")

    raw_image = np.asarray(dataset.x_test[REPRESENTATIVE_TEST_INDEX], dtype=np.int32)
    label = int(dataset.y_test[REPRESENTATIVE_TEST_INDEX])
    # P08.4.1's full-corpus normalization has max=1 after /255 normalization,
    # therefore the accepted NxTF BIAS-domain frame equals the original uint8
    # pixel values exactly.
    pixel_bias = raw_image[..., np.newaxis]
    input_spikes = bias_input_spike_schedule(pixel_bias)

    simulator = _build_activity_simulator(parameters, CONFORMANCE_TIMESTEPS)
    totals_t, active_t, first_t, maxima_t, evidence_t = simulator(
        pixel_bias[np.newaxis, ...].astype(np.int32)
    )
    vector_evidence = tuple(int(value) for value in np.asarray(evidence_t.numpy())[0])
    vector_prediction = int(np.argmax(np.asarray(vector_evidence, dtype=np.int64)))
    vector_totals = tuple(int(value) for value in np.asarray(totals_t.numpy()))
    vector_active = tuple(int(value) for value in np.asarray(active_t.numpy()))

    runs = (
        _run_compiled(compiled, input_spikes, mode="unpaged_reference"),
        _run_compiled(compiled, input_spikes, mode="paged_forward"),
        _run_compiled(compiled, input_spikes, mode="paged_reverse"),
    )

    trace_fingerprints = {run.trace_fingerprint for run in runs}
    if len(trace_fingerprints) != 1:
        raise AssertionError(
            "accepted deployment normalized trace changed under legal paging/service order"
        )
    for run in runs:
        if run.final_evidence != vector_evidence:
            raise AssertionError(
                f"{run.mode} final evidence does not match source-recovered simulator: "
                f"{run.final_evidence} != {vector_evidence}"
            )
        if run.prediction != vector_prediction:
            raise AssertionError(f"{run.mode} prediction changed at the compiled boundary")

    if runs[1].page_loads <= 0 or runs[2].page_loads <= 0:
        raise AssertionError("paged conformance did not exercise context loads")
    if runs[1].evictions <= 0 or runs[2].evictions <= 0:
        raise AssertionError("paged conformance did not exercise context eviction")

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        output / CONFORMANCE_VECTORS,
        representative_test_index=np.asarray([REPRESENTATIVE_TEST_INDEX], dtype=np.int32),
        label=np.asarray([label], dtype=np.int32),
        pixel_bias=pixel_bias.astype(np.int16),
        input_spikes=input_spikes,
        vector_evidence=np.asarray(vector_evidence, dtype=np.int64),
    )

    manifest: dict[str, Any] = {
        "schema": CONFORMANCE_SCHEMA,
        "status": "P08_4_2_COMPILED_EXECUTION_REVIEW_PENDING",
        "representative_test_index": REPRESENTATIVE_TEST_INDEX,
        "representative_selection_rule": REPRESENTATIVE_SELECTION_RULE,
        "representative_label": label,
        "timesteps": CONFORMANCE_TIMESTEPS,
        "source_input_spikes_generated": int(np.count_nonzero(input_spikes)),
        "source_input_spikes_consumed": int(np.count_nonzero(input_spikes[:-1])),
        "source_input_final_tick_not_consumed_due_fixed_horizon": int(np.count_nonzero(input_spikes[-1])),
        "vector_stage_total_spikes": list(vector_totals),
        "vector_stage_active_examples": list(vector_active),
        "vector_final_evidence": list(vector_evidence),
        "vector_prediction": vector_prediction,
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "conversion_manifest_fingerprint": conversion_manifest["manifest_fingerprint"],
        "logical_core_count": 5,
        "resident_context_count": 3,
        "physical_engine_count": 1,
        "normalized_trace_invariant": True,
        "compiled_evidence_matches_source_simulator": True,
        "official_test_used_for_conformance": True,
        "model_or_conversion_selection_after_test": False,
        "runs": [
            {
                "mode": run.mode,
                "trace_fingerprint": run.trace_fingerprint,
                "final_evidence": list(run.final_evidence),
                "prediction": run.prediction,
                "ingress_packets": run.ingress_packets,
                "internal_packet_traffic": run.internal_packet_traffic,
                "page_loads": run.page_loads,
                "page_hits": run.page_hits,
                "evictions": run.evictions,
            }
            for run in runs
        ],
    }
    manifest["manifest_fingerprint"] = _json_fingerprint(manifest)
    (output / CONFORMANCE_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run P08.4.2 compiled execution conformance")
    parser.add_argument("--conversion-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = run_compiled_execution_conformance(args.conversion_dir, args.output_dir)
    run_map = {item["mode"]: item for item in manifest["runs"]}
    print(
        "PASS: P08.4.2 representative corpus "
        f"test_index={manifest['representative_test_index']} "
        f"label={manifest['representative_label']} timesteps={manifest['timesteps']} "
        f"source_input_spikes={manifest['source_input_spikes_generated']}"
    )
    print(
        "PASS: P08.4.2 source-vs-compiled evidence "
        f"prediction={manifest['vector_prediction']} "
        f"evidence={manifest['vector_final_evidence']} exact_match=true"
    )
    print(
        "PASS: P08.4.2 normalized trace invariance "
        f"fingerprint={run_map['unpaged_reference']['trace_fingerprint']} "
        "unpaged=paged_forward=paged_reverse"
    )
    print(
        "PASS: P08.4.2 paging exercise "
        f"forward_loads={run_map['paged_forward']['page_loads']} "
        f"forward_evictions={run_map['paged_forward']['evictions']} "
        f"reverse_loads={run_map['paged_reverse']['page_loads']} "
        f"reverse_evictions={run_map['paged_reverse']['evictions']}"
    )
    print(
        "PASS: P08.4.2 packet traffic "
        f"ingress={run_map['unpaged_reference']['ingress_packets']} "
        f"internal={run_map['unpaged_reference']['internal_packet_traffic']}"
    )
    print(
        "PASS: P08.4.2 artifact identities "
        f"parameters={manifest['parameter_fingerprint']} "
        f"network={manifest['network_fingerprint']} "
        f"compiled={manifest['compiled_fingerprint']}"
    )
    print(
        "PASS: P08.4.2 test-use boundary official_test_used_for_conformance=true "
        "model_or_conversion_selection_after_test=false"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
