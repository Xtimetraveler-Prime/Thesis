"""M05.10 deterministic controller demo — explicitly SIMULATED, NO FPGA.

Run from Neuromorphic_Accelerator/v1:
  python3 scripts/m05_controller_native_demo.py

Demonstrates one failed/provisional transaction, explicit reset/flush fence,
then a successful independent run on the *model* of a finite transport.
Does not contact Vivado/Vitis, DMA, PS/PL or a physical K26.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from neuromorphic_accelerator_v1.m05_execution_controller import (
    ExecutionController, ExternalEvent, NeuronConfig, RunPlan
)
from neuromorphic_accelerator_v1.m05_execution_sim import (
    ScriptedRun, ScriptedTransport
)
from neuromorphic_accelerator_v1.m05_trace_commit import RollingTraceRow


def main() -> None:
    two_neurons = (NeuronConfig(0, 0, 5, 0),) * 2
    first = RunPlan(two_neurons, (), (ExternalEvent(0, 0, 5),), ticks=12)
    second = RunPlan(two_neurons, (), (ExternalEvent(1, 1, 5),), ticks=10)
    provisional = tuple(
        RollingTraceRow(t, n, 0, int(t == 0 and n == 0),
                        int(t == 0 and n == 0), int(t == 0))
        for t in range(4) for n in range(2)
    )
    accepted = tuple(
        RollingTraceRow(t, n, 0, int(t == 1 and n == 1),
                        int(t == 1 and n == 1), int(t == 1))
        for t in range(10) for n in range(2)
    )
    fake = ScriptedTransport((
        ScriptedRun(provisional, status=4, receive_stride=1,
                    completion_before_output_drained=False),
        ScriptedRun(accepted, status=0, input_consume_stride=3,
                    receive_stride=4, quiescent_delay=80),
    ))
    controller = ExecutionController(fake)
    report0 = controller.execute(first)
    assert not report0.result.accepted
    assert report0.result.status == 4
    assert report0.result.rows == ()
    assert controller.state.value == "faulted"
    print("SIMULATED run0: hardware_status=4, provisional=8, published=0, "
          "controller=FAULTED (explicit recovery required)")

    controller.recover()  # fake synchronous buffer purge, NOT real PL reset
    report1 = controller.execute(second)
    assert report1.result.accepted and len(report1.result.rows) == 20
    assert report1.result.rows[3].spike == 1
    assert report1.result.rows[17].delivered_count == 0
    print("SIMULATED run1: hardware_status=0, published=20, "
          "t1_neuron1_spike=1, stale_t8_deliveries=0")
    print("PASS: M05.10 controller HOST SIMULATION ONLY; "
          "nonblocking streams, fenced commit and explicit recovery")


if __name__ == "__main__":
    main()
