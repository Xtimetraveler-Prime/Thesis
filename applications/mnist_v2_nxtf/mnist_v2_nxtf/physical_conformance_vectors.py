"""Generate one frozen P08.4.3b K26 dispatch corpus from P08.4.2.

The corpus is intentionally representative rather than a second full 100-timestep
software execution. P08.4.2 already proves the complete five-logical-core paged
execution and paging-order invariance. P08.4.3b snapshots the final algorithmic
timestep before logical core 4 executes, then asks the physical K26 shell to load
that backing context into a resident slot and execute the exact same dispatch.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from loihi_twin_v2.compiler import CompiledDeployment
from loihi_twin_v2.hardware_p03 import (
    export_one_core_image,
    pack_compartment_state,
    pack_output_packet,
)

from .compiled_execution_conformance import (
    CONFORMANCE_MANIFEST,
    CONFORMANCE_TIMESTEPS,
    REPRESENTATIVE_TEST_INDEX,
    bias_input_spike_schedule,
)
from .data import load_mnist
from .source_recovered_conversion import SOURCE_RECOVERED_COMPILED
from .source_recovered_validation import ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT

PHYSICAL_TIMESTEP = CONFORMANCE_TIMESTEPS - 1
TARGET_LOGICAL_CORE = 4
TARGET_RESIDENT_SLOT = 0
DECOY_LOGICAL_CORE = 0


def _hex(value: int, bits: int) -> str:
    digits = (bits + 3) // 4
    return f"0x{value & ((1 << bits) - 1):0{digits}X}"


def _pairs(entries: list[tuple[int, int]], bits: int) -> str:
    return "{" + " ".join(
        "{" + f"{index} {_hex(word, bits)}" + "}" for index, word in entries
    ) + "}"


def _words(words: list[int] | tuple[int, ...], bits: int) -> str:
    return "{" + " ".join(_hex(int(word), bits) for word in words) + "}"


def _ints(values: list[int] | tuple[int, ...]) -> str:
    return "{" + " ".join(str(int(value)) for value in values) + "}"


def _trace_word(before: int, synaptic_input: int, after: int, spike: bool) -> int:
    return (
        (before & ((1 << 64) - 1))
        | ((synaptic_input & ((1 << 64) - 1)) << 64)
        | ((after & ((1 << 64) - 1)) << 128)
        | ((1 if spike else 0) << 192)
    )


def _image_fields(image) -> list[str]:
    return [
        f"compartment_count {image.compartment_count}",
        f"synapse_count {image.synapse_count}",
        f"route_count {image.route_count}",
        f"config_seeds {_pairs(list(enumerate(image.config_words)), 128)}",
        f"state_seeds {_pairs(list(enumerate(image.state_words)), 64)}",
        f"axon_seeds {_pairs([(seed.index, seed.word) for seed in image.axon_words], 64)}",
        f"synapse_seeds {_pairs(list(enumerate(image.synapse_words)), 64)}",
        f"route_desc_seeds {_pairs([(seed.index, seed.word) for seed in image.route_descriptor_words], 32)}",
        f"route_seeds {_pairs(list(enumerate(image.route_words)), 32)}",
    ]


def build_physical_vector(conversion_dir: Path, conformance_dir: Path) -> tuple[str, dict[str, object]]:
    manifest_path = conformance_dir / CONFORMANCE_MANIFEST
    if not manifest_path.is_file():
        raise FileNotFoundError(f"P08.4.2 manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("representative_test_index") != REPRESENTATIVE_TEST_INDEX:
        raise AssertionError("P08.4.2 representative index drifted")
    if manifest.get("compiled_fingerprint") != ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT:
        raise AssertionError("P08.4.2 compiled fingerprint drifted")
    if manifest.get("model_or_conversion_selection_after_test") is not False:
        raise AssertionError("P08.4.2 test-use boundary drifted")

    compiled_path = conversion_dir / SOURCE_RECOVERED_COMPILED
    compiled = CompiledDeployment.read_json(compiled_path)
    if compiled.fingerprint != ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT:
        raise AssertionError("accepted compiled deployment fingerprint drifted")

    dataset = load_mnist()
    raw_image = np.asarray(dataset.x_test[REPRESENTATIVE_TEST_INDEX], dtype=np.int32)
    input_spikes = bias_input_spike_schedule(raw_image[..., np.newaxis])

    chip = compiled.build_chip()
    target_trace = None
    for timestep in range(CONFORMANCE_TIMESTEPS):
        active = () if timestep == 0 else tuple(np.flatnonzero(input_spikes[timestep - 1]))
        external = compiled.external_packets("pixels", active, target_timestep=timestep)
        traces = chip.evaluate(external_packets=external)
        if timestep == PHYSICAL_TIMESTEP:
            target_trace = next(
                trace for trace in traces if trace.logical_core_id == TARGET_LOGICAL_CORE
            )
            break
        chip.drain_packets()
        chip.advance()

    if target_trace is None:
        raise AssertionError("failed to capture target physical dispatch")

    target_config = next(
        config for config in compiled.logical_deployment.core_configs
        if config.core_id == TARGET_LOGICAL_CORE
    )
    before_states = tuple(item.state for item in target_trace.compartment_state_before)
    target_image = export_one_core_image(target_config, before_states)

    decoy_config = next(
        config for config in compiled.logical_deployment.core_configs
        if config.core_id == DECOY_LOGICAL_CORE
    )
    decoy_image = export_one_core_image(decoy_config)

    input_events = [int(packet.destination_axon) for packet in target_trace.packet_in]
    expected_states = [pack_compartment_state(item.state) for item in target_trace.compartment_state_after]
    synaptic = [0] * len(target_trace.compartment_state_after)
    for contribution in target_trace.synaptic_contributions:
        synaptic[contribution.target_compartment] += contribution.weight
    spike_set = set(target_trace.spikes_out)
    expected_traces = []
    for index, (before, after) in enumerate(
        zip(target_trace.compartment_state_before, target_trace.compartment_state_after, strict=True)
    ):
        expected_traces.append(
            _trace_word(
                pack_compartment_state(before.state),
                synaptic[index],
                pack_compartment_state(after.state),
                index in spike_set,
            )
        )
    expected_packets = [pack_output_packet(packet) for packet in target_trace.packets_out]

    output_placements = sorted(
        [record for record in compiled.placement if record.population.startswith("conv4_c")],
        key=lambda record: record.population,
    )
    if len(output_placements) != 10:
        raise AssertionError("conv4 output placement drifted")
    evidence_compartments = [
        record.compartment_id for record in output_placements if record.core_id == TARGET_LOGICAL_CORE
    ]
    if len(evidence_compartments) != 10:
        raise AssertionError("P08.4.3b expects all ten conv4 outputs on logical core 4")
    evidence = [
        int(target_trace.compartment_state_after[index].state.voltage)
        for index in evidence_compartments
    ]
    if evidence != manifest["vector_final_evidence"]:
        raise AssertionError("physical snapshot evidence differs from accepted P08.4.2 evidence")

    metadata = (
        TARGET_LOGICAL_CORE
        | (target_image.compartment_count << 7)
        | (target_image.synapse_count << 18)
        | (target_image.route_count << 34)
        | (len(input_events) << 47)
    )

    # The decoy marker establishes that slot 0 held a different logical backing
    # image before the target image is materialized there. Static decoy tables do
    # not need to be transferred because the gate never computes on the decoy.
    decoy_marker = 0x0000000000000042

    lines = [
        "# Generated by mnist_v2_nxtf.physical_conformance_vectors. Do not edit.",
        f"set P08B_COMPILED_FINGERPRINT {compiled.fingerprint}",
        f"set P08B_TEST_INDEX {REPRESENTATIVE_TEST_INDEX}",
        f"set P08B_LABEL {int(dataset.y_test[REPRESENTATIVE_TEST_INDEX])}",
        f"set P08B_TIMESTEP {PHYSICAL_TIMESTEP}",
        f"set P08B_SLOT {TARGET_RESIDENT_SLOT}",
        f"set P08B_DECOY_LOGICAL_CORE {DECOY_LOGICAL_CORE}",
        f"set P08B_TARGET_LOGICAL_CORE {TARGET_LOGICAL_CORE}",
        f"set P08B_DECOY_MARKER {_hex(decoy_marker, 64)}",
        f"set P08B_METADATA {_hex(metadata, 64)}",
        f"set P08B_EVENT_READ_BANK {PHYSICAL_TIMESTEP & 1}",
        f"set P08B_INPUT_EVENTS {_ints(input_events)}",
        f"set P08B_EXPECTED_STATES {_words(expected_states, 64)}",
        f"set P08B_EXPECTED_TRACES {_words(expected_traces, 256)}",
        f"set P08B_EXPECTED_PACKETS {_words(expected_packets, 64)}",
        f"set P08B_EXPECTED_SPIKE_COUNT {len(target_trace.spikes_out)}",
        f"set P08B_EVIDENCE_COMPARTMENTS {_ints(evidence_compartments)}",
        f"set P08B_EXPECTED_EVIDENCE {_ints(evidence)}",
        "set P08B_TARGET_CONTEXT {" + " ".join(_image_fields(target_image)) + "}",
        "",
    ]

    summary: dict[str, object] = {
        "schema": "p08-4-3b-physical-dispatch-vector-v1",
        "compiled_fingerprint": compiled.fingerprint,
        "test_index": REPRESENTATIVE_TEST_INDEX,
        "label": int(dataset.y_test[REPRESENTATIVE_TEST_INDEX]),
        "timestep": PHYSICAL_TIMESTEP,
        "target_logical_core": TARGET_LOGICAL_CORE,
        "resident_slot": TARGET_RESIDENT_SLOT,
        "decoy_logical_core": DECOY_LOGICAL_CORE,
        "event_count": len(input_events),
        "compartment_count": target_image.compartment_count,
        "synapse_count": target_image.synapse_count,
        "route_count": target_image.route_count,
        "expected_spike_count": len(target_trace.spikes_out),
        "expected_packet_count": len(expected_packets),
        "expected_evidence": evidence,
        "accepted_vector_evidence": manifest["vector_final_evidence"],
        "selection_decisions_after_test": 0,
    }
    return "\n".join(lines), summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--conversion-dir", type=Path, required=True)
    parser.add_argument("--conformance-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--summary", type=Path, required=True)
    args = parser.parse_args()
    text, summary = build_physical_vector(args.conversion_dir, args.conformance_dir)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text, encoding="utf-8")
    args.summary.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        "PASS: P08.4.3b physical vector generated "
        f"test_index={summary['test_index']} timestep={summary['timestep']} "
        f"logical_core={summary['target_logical_core']} slot={summary['resident_slot']} "
        f"events={summary['event_count']} packets={summary['expected_packet_count']}"
    )
    print(
        "PASS: P08.4.3b expected evidence "
        f"evidence={summary['expected_evidence']} compiled={summary['compiled_fingerprint']}"
    )


if __name__ == "__main__":
    main()
