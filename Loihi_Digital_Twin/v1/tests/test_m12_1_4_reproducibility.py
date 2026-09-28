from __future__ import annotations

import json
from pathlib import Path

import pytest

from neuromorphic_twin.fpga_core_capacity import pack_neuron_state_word
from neuromorphic_twin.fpga_physical_trace import (
    FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO,
    PhysicalFpgaTickCapture,
    PhysicalFpgaTraceArtifact,
    write_physical_fpga_trace_json,
)
from neuromorphic_twin.fpga_physical_trace_reproducibility import (
    compare_physical_fpga_trace_files,
)
from neuromorphic_twin.fpga_trace_snapshot import FpgaTickTraceSnapshot
from neuromorphic_twin.model import NeuronState


ROOT = Path(__file__).resolve().parents[1]
RTL = ROOT / "rtl" / "core_v1"
CLOSURE_SH = RTL / "run_m12_1_4_reproducibility.sh"
COMPARE_CLI = ROOT / "examples" / "compare_m12_1_4_physical_captures.py"


def _artifact(*, voltage_after: int = 3) -> PhysicalFpgaTraceArtifact:
    before = pack_neuron_state_word(
        NeuronState(current=1, voltage=2, refractory_remaining=0)
    )
    after = pack_neuron_state_word(
        NeuronState(current=1, voltage=voltage_after, refractory_remaining=0)
    )
    snapshot = FpgaTickTraceSnapshot(
        committed_tick=1,
        external_input_axons=(),
        recurrent_input_axons=(),
        synaptic_input=(0,),
        state_before_words=(before,),
        state_after_words=(after,),
        spikes=(False,),
        routed_output_axons=(),
    )
    capture = PhysicalFpgaTickCapture(
        snapshot=snapshot,
        core_fault=False,
        core_fault_code=0,
        recurrent_current_bank=False,
        recurrent_current_count=0,
        recurrent_bank0_count=0,
        recurrent_bank1_count=0,
        consumed_recurrent_count=0,
        routed_recurrent_count=0,
        external_event_count=0,
    )
    return PhysicalFpgaTraceArtifact(
        scenario_id="m12.1.4-unit",
        transport=FPGA_PHYSICAL_TRACE_TRANSPORT_JTAG_VIO,
        device="xck26_0",
        ticks=(capture,),
    )


def test_exact_repeated_capture_comparison_returns_stable_hash(tmp_path) -> None:
    artifact = _artifact()
    first = write_physical_fpga_trace_json(artifact, tmp_path / "a.json")
    second = write_physical_fpga_trace_json(artifact, tmp_path / "b.json")

    result = compare_physical_fpga_trace_files(first, second)

    assert result.scenario_id == artifact.scenario_id
    assert result.device == artifact.device
    assert result.tick_count == 1
    assert result.byte_count == len(first.read_bytes())
    assert len(result.sha256_hex) == 64


def test_semantic_capture_difference_is_rejected(tmp_path) -> None:
    first = write_physical_fpga_trace_json(_artifact(), tmp_path / "a.json")
    second = write_physical_fpga_trace_json(
        _artifact(voltage_after=4), tmp_path / "b.json"
    )

    with pytest.raises(ValueError, match="semantic mismatch"):
        compare_physical_fpga_trace_files(first, second)


def test_semantically_equal_but_non_byte_stable_json_is_rejected(tmp_path) -> None:
    artifact = _artifact()
    first = write_physical_fpga_trace_json(artifact, tmp_path / "a.json")
    payload = artifact.to_dict()
    second = tmp_path / "b.json"
    second.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")

    with pytest.raises(ValueError, match="not byte-stable"):
        compare_physical_fpga_trace_files(first, second)


def test_m12_1_4_board_gate_runs_two_accepted_captures_and_compares_them() -> None:
    shell = CLOSURE_SH.read_text(encoding="utf-8")
    cli = COMPARE_CLI.read_text(encoding="utf-8")

    assert shell.count('bash "$M12_1_3_RUNNER"') == 2
    assert "m11_5_4_recurrent_chain_physical_trace_v1_run_a.json" in shell
    assert "m11_5_4_recurrent_chain_physical_trace_v1_run_b.json" in shell
    assert 'python3 "$COMPARE" "$CAPTURE_A" "$CAPTURE_B"' in shell
    assert "M12.1.4 repeated physical capture closure completed successfully." in shell

    assert "compare_physical_fpga_trace_files" in cli
    assert "M12.1.4 physical trace reproducibility passed:" in cli
