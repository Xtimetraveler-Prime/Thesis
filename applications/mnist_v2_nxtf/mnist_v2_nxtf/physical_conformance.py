"""P08.4.3b representative physical K26 conformance corpus.

The exhaustive 100-timestep paging proof belongs to P08.4.2. This module takes
that already-fixed execution and emits two exact late-timestep logical-core
snapshots for the physical K26 shell. The board harness dispatches them through
one physical slot in the fixed sequence core0 -> core4 -> core0, exercising two
real page replacements and one reload while comparing complete state/trace/
packet images against the Python architectural reference.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from loihi_twin_v2.compiler import CompiledDeployment
from loihi_twin_v2.hardware_p03 import (
    export_one_core_image,
    pack_compartment_state,
    pack_output_packet,
)

from .compiled_execution_conformance import (
    CONFORMANCE_MANIFEST,
    CONFORMANCE_SCHEMA,
    CONFORMANCE_TIMESTEPS,
    CONFORMANCE_VECTORS,
    REPRESENTATIVE_TEST_INDEX,
)
from .source_recovered_conversion import SOURCE_RECOVERED_COMPILED
from .source_recovered_validation import (
    ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
    ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
    ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
)

PHYSICAL_SCHEMA = "p08-physical-conformance-corpus-v1"
PHYSICAL_MANIFEST = "p08_4_3b_physical_manifest.json"
PHYSICAL_VECTORS_TCL = "p08_4_3b_physical_vectors.tcl"
PHYSICAL_TIMESTEP = CONFORMANCE_TIMESTEPS - 1
PHYSICAL_SLOT = 2
INGRESS_CORE_ID = 0
OUTPUT_CORE_ID = 4
INGRESS_NAME = "ingress_core0_t99"
OUTPUT_NAME = "output_core4_t99"
PHYSICAL_SEQUENCE = (INGRESS_NAME, OUTPUT_NAME, INGRESS_NAME)
EXPECTED_TEST_LABEL = 7
EXPECTED_PREDICTION = 7
EXPECTED_FINAL_EVIDENCE = (
    -284,
    -1203,
    104,
    109,
    -2253,
    -599,
    -2659,
    1446,
    -436,
    -63,
)


def _hex(value: int, bits: int) -> str:
    digits = (bits + 3) // 4
    return f"0x{value & ((1 << bits) - 1):0{digits}X}"


def _pair_list(entries: list[tuple[int, int]], bits: int) -> str:
    return "{" + " ".join(
        "{" + f"{index} {_hex(word, bits)}" + "}" for index, word in entries
    ) + "}"


def _word_list(words: list[int] | tuple[int, ...], bits: int) -> str:
    return "{" + " ".join(_hex(word, bits) for word in words) + "}"


def _int_list(values: list[int] | tuple[int, ...]) -> str:
    return "{" + " ".join(str(value) for value in values) + "}"


def _trace_word(before: int, synaptic_input: int, after: int, spike: bool) -> int:
    return (
        (before & ((1 << 64) - 1))
        | ((synaptic_input & ((1 << 64) - 1)) << 64)
        | ((after & ((1 << 64) - 1)) << 128)
        | ((1 if spike else 0) << 192)
    )


def _sha_words(words: list[int] | tuple[int, ...], *, bits: int) -> str:
    width = (bits + 7) // 8
    digest = hashlib.sha256()
    mask = (1 << bits) - 1
    for word in words:
        digest.update((int(word) & mask).to_bytes(width, "little", signed=False))
    return digest.hexdigest()


def _json_fingerprint(payload: dict[str, Any]) -> str:
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _context_record(compiled: CompiledDeployment, core_trace) -> tuple[dict[str, Any], dict[str, Any]]:
    logical_id = int(core_trace.logical_core_id)
    config_by_id = {
        int(config.core_id): config for config in compiled.logical_deployment.core_configs
    }
    config = config_by_id[logical_id]
    before_states = tuple(item.state for item in core_trace.compartment_state_before)
    image = export_one_core_image(config, initial_states=before_states)

    event_axons = [int(packet.destination_axon) for packet in core_trace.packet_in]
    metadata = (
        logical_id
        | (image.compartment_count << 7)
        | (image.synapse_count << 18)
        | (image.route_count << 34)
        | (len(event_axons) << 47)
    )

    delivered = [0] * image.compartment_count
    for contribution in core_trace.synaptic_contributions:
        delivered[int(contribution.target_compartment)] += int(contribution.weight)

    spike_set = {int(value) for value in core_trace.spikes_out}
    expected_states: list[int] = []
    expected_traces: list[int] = []
    for compartment_id in range(image.compartment_count):
        before = pack_compartment_state(core_trace.compartment_state_before[compartment_id].state)
        after = pack_compartment_state(core_trace.compartment_state_after[compartment_id].state)
        expected_states.append(after)
        expected_traces.append(
            _trace_word(
                before,
                delivered[compartment_id],
                after,
                compartment_id in spike_set,
            )
        )

    expected_packets = [pack_output_packet(packet) for packet in core_trace.packets_out]
    if logical_id == INGRESS_CORE_ID:
        name = INGRESS_NAME
    elif logical_id == OUTPUT_CORE_ID:
        name = OUTPUT_NAME
    else:
        raise AssertionError(f"unexpected P08.4.3b physical core {logical_id}")

    record = {
        "name": name,
        "logical_core_id": logical_id,
        "slot": PHYSICAL_SLOT,
        "timestep": PHYSICAL_TIMESTEP,
        "metadata": metadata,
        "event_count": len(event_axons),
        "spike_count": len(spike_set),
        "packet_count": len(expected_packets),
        "image": image,
        "events": event_axons,
        "expected_states": expected_states,
        "expected_traces": expected_traces,
        "expected_packets": expected_packets,
    }

    summary = {
        "name": name,
        "logical_core_id": logical_id,
        "slot": PHYSICAL_SLOT,
        "timestep": PHYSICAL_TIMESTEP,
        "compartment_count": image.compartment_count,
        "synapse_count": image.synapse_count,
        "route_count": image.route_count,
        "event_count": len(event_axons),
        "spike_count": len(spike_set),
        "packet_count": len(expected_packets),
        "events_fingerprint": _sha_words(event_axons, bits=32),
        "state_before_fingerprint": _sha_words(list(image.state_words), bits=64),
        "state_after_fingerprint": _sha_words(expected_states, bits=64),
        "trace_fingerprint": _sha_words(expected_traces, bits=256),
        "packet_fingerprint": _sha_words(expected_packets, bits=64),
    }
    return record, summary


def _context_tcl(record: dict[str, Any]) -> str:
    image = record["image"]
    axons = [(item.index, item.word) for item in image.axon_words]
    route_desc = [(item.index, item.word) for item in image.route_descriptor_words]
    lines = [
        "    {",
        f"        name {record['name']}",
        f"        logical_core_id {record['logical_core_id']}",
        f"        slot {record['slot']}",
        f"        timestep {record['timestep']}",
        f"        metadata {_hex(record['metadata'], 64)}",
        f"        compartment_count {image.compartment_count}",
        f"        synapse_count {image.synapse_count}",
        f"        route_count {image.route_count}",
        f"        event_count {record['event_count']}",
        f"        expected_spike_count {record['spike_count']}",
        f"        expected_packet_count {record['packet_count']}",
        f"        config_seeds {_pair_list(list(enumerate(image.config_words)), 128)}",
        f"        state_seeds {_pair_list(list(enumerate(image.state_words)), 64)}",
        f"        axon_seeds {_pair_list(axons, 64)}",
        f"        synapse_seeds {_pair_list(list(enumerate(image.synapse_words)), 64)}",
        f"        route_desc_seeds {_pair_list(route_desc, 32)}",
        f"        route_seeds {_pair_list(list(enumerate(image.route_words)), 32)}",
        f"        events {_int_list(record['events'])}",
        f"        expected_states {_word_list(record['expected_states'], 64)}",
        f"        expected_traces {_word_list(record['expected_traces'], 256)}",
        f"        expected_packets {_word_list(record['expected_packets'], 64)}",
        "    }",
    ]
    return "\n".join(lines)


def build_physical_corpus(
    conversion_dir: str | Path,
    conformance_dir: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    conversion_root = Path(conversion_dir)
    conformance_root = Path(conformance_dir)
    manifest_path = conformance_root / CONFORMANCE_MANIFEST
    vectors_path = conformance_root / CONFORMANCE_VECTORS
    compiled_path = conversion_root / SOURCE_RECOVERED_COMPILED
    for path in (manifest_path, vectors_path, compiled_path):
        if not path.is_file():
            raise FileNotFoundError(f"required P08.4.3b input is missing: {path}")

    p08_4_2 = json.loads(manifest_path.read_text(encoding="utf-8"))
    required = {
        "schema": CONFORMANCE_SCHEMA,
        "representative_test_index": REPRESENTATIVE_TEST_INDEX,
        "representative_label": EXPECTED_TEST_LABEL,
        "timesteps": CONFORMANCE_TIMESTEPS,
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "logical_core_count": 5,
        "resident_context_count": 3,
        "physical_engine_count": 1,
        "normalized_trace_invariant": True,
        "compiled_evidence_matches_source_simulator": True,
        "official_test_used_for_conformance": True,
        "model_or_conversion_selection_after_test": False,
        "vector_prediction": EXPECTED_PREDICTION,
        "vector_final_evidence": list(EXPECTED_FINAL_EVIDENCE),
    }
    for key, expected in required.items():
        if p08_4_2.get(key) != expected:
            raise AssertionError(
                f"P08.4.3b input manifest {key}={p08_4_2.get(key)!r}, expected {expected!r}"
            )

    compiled = CompiledDeployment.read_json(compiled_path)
    if compiled.fingerprint != ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT:
        raise AssertionError("P08.4.3b compiled deployment fingerprint mismatch")
    if compiled.source_fingerprint != ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT:
        raise AssertionError("P08.4.3b network fingerprint mismatch")

    with np.load(vectors_path, allow_pickle=False) as vectors:
        input_spikes = np.asarray(vectors["input_spikes"], dtype=bool)
    if input_spikes.shape != (CONFORMANCE_TIMESTEPS, 784):
        raise AssertionError("P08.4.3b input-spike schedule shape drifted")

    chip = compiled.build_chip()
    selected: dict[int, Any] = {}
    for timestep in range(CONFORMANCE_TIMESTEPS):
        active = () if timestep == 0 else tuple(np.flatnonzero(input_spikes[timestep - 1]))
        external = compiled.external_packets("pixels", active, target_timestep=timestep)
        trace = chip.step(external)
        if timestep == PHYSICAL_TIMESTEP:
            selected = {int(core.logical_core_id): core for core in trace.cores}

    if INGRESS_CORE_ID not in selected or OUTPUT_CORE_ID not in selected:
        raise AssertionError("P08.4.3b late-timestep physical core traces are missing")

    ingress_record, ingress_summary = _context_record(compiled, selected[INGRESS_CORE_ID])
    output_record, output_summary = _context_record(compiled, selected[OUTPUT_CORE_ID])

    placements = sorted(
        (item for item in compiled.placement if item.population.startswith("conv4_c")),
        key=lambda item: item.population,
    )
    if len(placements) != 10 or any(item.core_id != OUTPUT_CORE_ID for item in placements):
        raise AssertionError("P08.4.3b expects all ten scalar conv4 outputs on logical core 4")
    evidence_compartments = [int(item.compartment_id) for item in placements]
    evidence = [
        int(selected[OUTPUT_CORE_ID].compartment_state_after[index].state.voltage)
        for index in evidence_compartments
    ]
    if tuple(evidence) != EXPECTED_FINAL_EVIDENCE:
        raise AssertionError(
            f"P08.4.3b final evidence drifted: {evidence} != {list(EXPECTED_FINAL_EVIDENCE)}"
        )

    runs = {item["mode"]: item for item in p08_4_2["runs"]}
    reference_trace = runs["unpaged_reference"]["trace_fingerprint"]

    tcl_lines = [
        "# Generated by mnist_v2_nxtf.physical_conformance. Do not edit.",
        f"set P08_PARAMETER_FINGERPRINT {ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT}",
        f"set P08_NETWORK_FINGERPRINT {ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT}",
        f"set P08_COMPILED_FINGERPRINT {ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT}",
        f"set P08_P08_4_2_MANIFEST_FINGERPRINT {p08_4_2['manifest_fingerprint']}",
        f"set P08_NORMALIZED_TRACE_FINGERPRINT {reference_trace}",
        f"set P08_TEST_INDEX {REPRESENTATIVE_TEST_INDEX}",
        f"set P08_LABEL {EXPECTED_TEST_LABEL}",
        f"set P08_TIMESTEP {PHYSICAL_TIMESTEP}",
        f"set P08_RESIDENT_SLOT {PHYSICAL_SLOT}",
        f"set P08_EXPECTED_PREDICTION {EXPECTED_PREDICTION}",
        f"set P08_EXPECTED_EVIDENCE {_int_list(EXPECTED_FINAL_EVIDENCE)}",
        f"set P08_EVIDENCE_COMPARTMENTS {_int_list(evidence_compartments)}",
        f"set P08_SEQUENCE {{{' '.join(PHYSICAL_SEQUENCE)}}}",
        "set P08_CONTEXTS {",
        _context_tcl(ingress_record),
        _context_tcl(output_record),
        "}",
        "",
    ]

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    (output / PHYSICAL_VECTORS_TCL).write_text("\n".join(tcl_lines), encoding="utf-8")

    manifest: dict[str, Any] = {
        "schema": PHYSICAL_SCHEMA,
        "status": "P08_4_3B_PHYSICAL_REVIEW_PENDING",
        "representative_test_index": REPRESENTATIVE_TEST_INDEX,
        "representative_label": EXPECTED_TEST_LABEL,
        "selection_rule": "fixed_from_accepted_p08_4_2_no_model_or_conversion_selection",
        "physical_timestep": PHYSICAL_TIMESTEP,
        "physical_slot": PHYSICAL_SLOT,
        "dispatch_sequence": list(PHYSICAL_SEQUENCE),
        "physical_dispatch_count": len(PHYSICAL_SEQUENCE),
        "physical_page_replacements": 2,
        "reload_exercised": True,
        "parameter_fingerprint": ACCEPTED_P08_3_5C_PARAMETER_FINGERPRINT,
        "network_fingerprint": ACCEPTED_P08_3_5C_NETWORK_FINGERPRINT,
        "compiled_fingerprint": ACCEPTED_P08_3_5C_COMPILED_FINGERPRINT,
        "p08_4_2_manifest_fingerprint": p08_4_2["manifest_fingerprint"],
        "normalized_trace_fingerprint": reference_trace,
        "expected_final_evidence": list(EXPECTED_FINAL_EVIDENCE),
        "expected_prediction": EXPECTED_PREDICTION,
        "evidence_logical_core_id": OUTPUT_CORE_ID,
        "evidence_compartments": evidence_compartments,
        "logical_core_count": 5,
        "resident_context_count": 3,
        "physical_engine_count": 1,
        "official_test_used_for_physical_conformance": True,
        "model_or_conversion_selection_after_test": False,
        "contexts": [ingress_summary, output_summary],
    }
    manifest["manifest_fingerprint"] = _json_fingerprint(manifest)
    (output / PHYSICAL_MANIFEST).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate P08.4.3b physical conformance corpus")
    parser.add_argument("--conversion-dir", required=True)
    parser.add_argument("--conformance-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    manifest = build_physical_corpus(
        args.conversion_dir,
        args.conformance_dir,
        args.output_dir,
    )
    context_map = {item["logical_core_id"]: item for item in manifest["contexts"]}
    print(
        "PASS: P08.4.3b frozen corpus "
        f"test_index={manifest['representative_test_index']} label={manifest['representative_label']} "
        f"timestep={manifest['physical_timestep']} slot={manifest['physical_slot']}"
    )
    print(
        "PASS: P08.4.3b dispatch sequence "
        f"sequence={manifest['dispatch_sequence']} replacements={manifest['physical_page_replacements']} "
        "reload=true"
    )
    print(
        "PASS: P08.4.3b ingress context "
        f"core=0 events={context_map[0]['event_count']} spikes={context_map[0]['spike_count']} "
        f"packets={context_map[0]['packet_count']}"
    )
    print(
        "PASS: P08.4.3b output context "
        f"core=4 events={context_map[4]['event_count']} spikes={context_map[4]['spike_count']} "
        f"packets={context_map[4]['packet_count']}"
    )
    print(
        "PASS: P08.4.3b expected final evidence "
        f"prediction={manifest['expected_prediction']} evidence={manifest['expected_final_evidence']}"
    )
    print(
        "PASS: P08.4.3b identities "
        f"parameters={manifest['parameter_fingerprint']} network={manifest['network_fingerprint']} "
        f"compiled={manifest['compiled_fingerprint']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
