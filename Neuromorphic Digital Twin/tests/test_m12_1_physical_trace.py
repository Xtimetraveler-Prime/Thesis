from __future__ import annotations

import json

import pytest

from neuromorphic_twin.fpga_core_capacity import pack_neuron_state_word
from neuromorphic_twin.fpga_physical_trace import (
    FPGA_PHYSICAL_TRACE_SCHEMA,
    FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO,
    FpgaTraceReadSpace,
    PhysicalFpgaTickCapture,
    PhysicalFpgaTraceArtifact,
    read_physical_fpga_trace_json,
    write_physical_fpga_trace_json,
)
from neuromorphic_twin.fpga_trace_snapshot import FpgaTickTraceSnapshot
from neuromorphic_twin.model import NeuronState, Spike


def _snapshot() -> FpgaTickTraceSnapshot:
    before = (
        pack_neuron_state_word(NeuronState(current=10, voltage=-3, refractory_remaining=0)),
        pack_neuron_state_word(NeuronState(current=-7, voltage=5, refractory_remaining=2)),
    )
    after = (
        pack_neuron_state_word(NeuronState(current=14, voltage=0, refractory_remaining=1)),
        pack_neuron_state_word(NeuronState(current=-9, voltage=-4, refractory_remaining=1)),
    )
    return FpgaTickTraceSnapshot(
        committed_tick=7,
        external_input_axons=(4, 4, 1),
        recurrent_input_axons=(3, 2),
        synaptic_input=(11, -13),
        state_before_words=before,
        state_after_words=after,
        spikes=(True, False),
        routed_output_axons=(8, 7, 8),
    )


def _capture() -> PhysicalFpgaTickCapture:
    return PhysicalFpgaTickCapture(
        snapshot=_snapshot(),
        core_fault=False,
        core_fault_code=0,
        recurrent_current_bank=True,
        recurrent_current_count=3,
        recurrent_bank0_count=2,
        recurrent_bank1_count=3,
        consumed_recurrent_count=2,
        routed_recurrent_count=3,
        external_event_count=3,
    )


def _artifact() -> PhysicalFpgaTraceArtifact:
    return PhysicalFpgaTraceArtifact(
        scenario_id="m12.1.1-unit",
        transport=FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO,
        device="xck26-sfvc784-2LV-c",
        ticks=(_capture(),),
    )


def test_m12_1_read_space_selector_values_are_frozen() -> None:
    assert FPGA_PHYSICAL_TRACE_SCHEMA == "neuromorphic-twin-physical-fpga-trace-v1"
    assert {space.name: int(space) for space in FpgaTraceReadSpace} == {
        "STATE_BEFORE": 0,
        "STATE_AFTER": 1,
        "SYNAPTIC_INPUT": 2,
        "SPIKE": 3,
        "EXTERNAL_EVENT": 4,
        "RECURRENT_BANK0_EVENT": 5,
        "RECURRENT_BANK1_EVENT": 6,
    }


def test_physical_tick_metadata_is_consistent_with_snapshot() -> None:
    capture = _capture()
    assert capture.external_event_count == len(capture.snapshot.external_input_axons)
    assert capture.consumed_recurrent_count == len(capture.snapshot.recurrent_input_axons)
    assert capture.routed_recurrent_count == len(capture.snapshot.routed_output_axons)
    assert capture.recurrent_current_count == capture.recurrent_bank1_count


def test_physical_tick_rejects_count_or_bank_inconsistency() -> None:
    common = dict(
        snapshot=_snapshot(),
        core_fault=False,
        core_fault_code=0,
        recurrent_current_bank=True,
        recurrent_current_count=3,
        recurrent_bank0_count=2,
        recurrent_bank1_count=3,
        consumed_recurrent_count=2,
        routed_recurrent_count=3,
        external_event_count=3,
    )

    with pytest.raises(ValueError, match="external_event_count"):
        PhysicalFpgaTickCapture(**{**common, "external_event_count": 2})
    with pytest.raises(ValueError, match="consumed_recurrent_count"):
        PhysicalFpgaTickCapture(**{**common, "consumed_recurrent_count": 1})
    with pytest.raises(ValueError, match="routed_recurrent_count"):
        PhysicalFpgaTickCapture(**{**common, "routed_recurrent_count": 2})
    with pytest.raises(ValueError, match="selected physical bank"):
        PhysicalFpgaTickCapture(**{**common, "recurrent_bank1_count": 2})
    with pytest.raises(ValueError, match="post-commit recurrent current"):
        PhysicalFpgaTickCapture(
            **{
                **common,
                "snapshot": FpgaTickTraceSnapshot(
                    committed_tick=7,
                    external_input_axons=(4, 4, 1),
                    recurrent_input_axons=(3, 2),
                    synaptic_input=(11, -13),
                    state_before_words=_snapshot().state_before_words,
                    state_after_words=_snapshot().state_after_words,
                    spikes=(True, False),
                    routed_output_axons=(8, 7),
                ),
                "routed_recurrent_count": 2,
            }
        )


def test_artifact_round_trip_is_exact_and_reconstructs_tick_trace(tmp_path) -> None:
    artifact = _artifact()
    path = write_physical_fpga_trace_json(artifact, tmp_path / "capture.json")
    loaded = read_physical_fpga_trace_json(path)

    assert loaded == artifact
    assert path.read_text(encoding="utf-8").endswith("\n")
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["schema"] == FPGA_PHYSICAL_TRACE_SCHEMA
    assert payload["ticks"][0]["state_before_words"][0].startswith("0x")
    assert len(payload["ticks"][0]["state_before_words"][0]) == 18

    traces = loaded.to_tick_traces()
    assert len(traces) == 1
    trace = traces[0]
    assert trace.tick == 6
    assert trace.input_axons == (4, 4, 1, 3, 2)
    assert trace.synaptic_input == (11, -13)
    assert trace.spikes == (Spike(tick=6, neuron_id=0),)
    assert trace.routed_output_axons == (8, 7, 8)


def test_artifact_json_is_deterministic(tmp_path) -> None:
    artifact = _artifact()
    first = write_physical_fpga_trace_json(artifact, tmp_path / "a.json")
    second = write_physical_fpga_trace_json(artifact, tmp_path / "b.json")
    assert first.read_bytes() == second.read_bytes()


def test_reader_rejects_schema_bank_and_word_encoding_errors(tmp_path) -> None:
    payload = _artifact().to_dict()

    bad_schema = {**payload, "schema": "other"}
    path = tmp_path / "bad-schema.json"
    path.write_text(json.dumps(bad_schema), encoding="utf-8")
    with pytest.raises(ValueError, match="unsupported physical FPGA trace schema"):
        read_physical_fpga_trace_json(path)

    bad_bank = _artifact().to_dict()
    bad_bank["ticks"][0]["recurrent_current_bank"] = 2
    path = tmp_path / "bad-bank.json"
    path.write_text(json.dumps(bad_bank), encoding="utf-8")
    with pytest.raises(ValueError, match="must be 0 or 1"):
        read_physical_fpga_trace_json(path)

    bad_word = _artifact().to_dict()
    bad_word["ticks"][0]["state_after_words"][0] = "0x1"
    path = tmp_path / "bad-word.json"
    path.write_text(json.dumps(bad_word), encoding="utf-8")
    with pytest.raises(ValueError, match="16-digit hex"):
        read_physical_fpga_trace_json(path)


def test_artifact_requires_nonempty_identity_and_tick_list() -> None:
    with pytest.raises(ValueError, match="scenario_id"):
        PhysicalFpgaTraceArtifact("", "jtag-vio", "xck26", (_capture(),))
    with pytest.raises(ValueError, match="at least one tick"):
        PhysicalFpgaTraceArtifact("case", "jtag-vio", "xck26", ())
