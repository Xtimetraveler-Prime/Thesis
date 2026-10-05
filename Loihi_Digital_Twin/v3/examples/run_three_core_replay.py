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


def build_deployment() -> Deployment:
    template = SynapseTemplate(0, (SynapseEntry(0, 6),))
    core0 = LogicalCoreConfig(
        core_id=0,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(0, 0), InputAxonBinding(3, 0)),
        synapse_templates=(template,),
        output_routes=(OutputRouteEntry(0, (OutputRoute(1, 1),)),),
    )
    core1 = LogicalCoreConfig(
        core_id=1,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(1, 0),),
        synapse_templates=(template,),
        output_routes=(OutputRouteEntry(0, (OutputRoute(2, 2),)),),
    )
    core2 = LogicalCoreConfig(
        core_id=2,
        compartments=(lif(),),
        input_axons=(InputAxonBinding(2, 0),),
        synapse_templates=(template,),
        output_routes=(OutputRouteEntry(0, (OutputRoute(0, 3),)),),
    )
    return Deployment((core0, core1, core2))


def spike_wave(result) -> list[dict[str, int]]:
    wave: list[dict[str, int]] = []
    for trace in result.traces:
        for core in trace.cores:
            for compartment in core.spikes_out:
                wave.append(
                    {
                        "timestep": trace.algorithmic_timestep,
                        "core": core.logical_core_id,
                        "compartment": compartment,
                    }
                )
    return wave


def main() -> None:
    deployment = build_deployment()
    serialized = deployment.to_json()
    replay_deployment = Deployment.from_json(serialized)
    external = {0: (SpikePacket(0, 0, 0),)}

    forward = run_deployment(
        replay_deployment,
        4,
        external_schedule=external,
        service_order_schedule={t: (0, 1, 2) for t in range(4)},
    )
    reordered = run_deployment(
        replay_deployment,
        4,
        external_schedule=external,
        service_order_schedule={t: (2, 1, 0) for t in range(4)},
        reverse_packet_drain_timesteps=frozenset(range(4)),
    )

    output = {
        "deployment": deployment_report(replay_deployment),
        "deployment_roundtrip_fingerprint_match": (
            replay_deployment.fingerprint == deployment.fingerprint
        ),
        "forward_trace_fingerprint": forward.trace_fingerprint,
        "reordered_trace_fingerprint": reordered.trace_fingerprint,
        "schedule_invariant": forward.normalized() == reordered.normalized(),
        "spike_wave": spike_wave(forward),
    }
    print(json.dumps(output, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
