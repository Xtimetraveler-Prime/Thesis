from __future__ import annotations

import json

from loihi_twin_v2 import (
    CompartmentConfig,
    Deployment,
    InputAxonBinding,
    LogicalCoreConfig,
    OutputRoute,
    OutputRouteEntry,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
    deployment_report,
    run_deployment,
)


def lif() -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=5,
    )


def build_ring() -> Deployment:
    template = SynapseTemplate(0, (SynapseEntry(0, 6),))
    return Deployment(
        (
            LogicalCoreConfig(
                core_id=0,
                compartments=(lif(),),
                input_axons=(InputAxonBinding(0, 0), InputAxonBinding(3, 0)),
                synapse_templates=(template,),
                output_routes=(OutputRouteEntry(0, (OutputRoute(1, 1),)),),
            ),
            LogicalCoreConfig(
                core_id=1,
                compartments=(lif(),),
                input_axons=(InputAxonBinding(1, 0),),
                synapse_templates=(template,),
                output_routes=(OutputRouteEntry(0, (OutputRoute(2, 2),)),),
            ),
            LogicalCoreConfig(
                core_id=2,
                compartments=(lif(),),
                input_axons=(InputAxonBinding(2, 0),),
                synapse_templates=(template,),
                output_routes=(OutputRouteEntry(0, (OutputRoute(0, 3),)),),
            ),
        )
    )


def spike_wave(result) -> list[list[int]]:
    wave: list[list[int]] = []
    for trace in result.traces:
        for core in trace.cores:
            for compartment in core.spikes_out:
                wave.append(
                    [trace.algorithmic_timestep, core.logical_core_id, compartment]
                )
    return wave


def main() -> None:
    deployment = build_ring()
    reloaded = Deployment.from_json(deployment.to_json())
    external = {0: (SpikePacket(0, 0, 0),)}

    forward = run_deployment(
        reloaded,
        4,
        external_schedule=external,
        service_order_schedule={t: (0, 1, 2) for t in range(4)},
    )
    reordered = run_deployment(
        reloaded,
        4,
        external_schedule=external,
        service_order_schedule={t: (2, 1, 0) for t in range(4)},
        reverse_packet_drain_timesteps=frozenset(range(4)),
    )

    expected_wave = [[0, 0, 0], [1, 1, 0], [2, 2, 0], [3, 0, 0]]
    checks = {
        "deployment_roundtrip": reloaded.fingerprint == deployment.fingerprint,
        "logical_core_count": len(reloaded.core_configs) == 3,
        "expected_spike_wave": spike_wave(forward) == expected_wave,
        "normalized_schedule_invariance": (
            forward.normalized() == reordered.normalized()
        ),
        "trace_fingerprint_invariance": (
            forward.trace_fingerprint == reordered.trace_fingerprint
        ),
        "resource_headroom_nonnegative": all(
            value >= 0
            for core in deployment_report(reloaded)["cores"]
            for value in core["headroom"].values()
        ),
    }
    passed = all(checks.values())
    summary = {
        "p02_validation": "PASS" if passed else "FAIL",
        "checks": checks,
        "deployment_fingerprint": reloaded.fingerprint,
        "trace_fingerprint": forward.trace_fingerprint,
        "spike_wave": spike_wave(forward),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    if not passed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
