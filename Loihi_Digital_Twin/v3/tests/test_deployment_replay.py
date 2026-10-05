from __future__ import annotations

import json

import pytest

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
    run_deployment,
)


def lif() -> CompartmentConfig:
    return CompartmentConfig(
        current_decay=4096,
        voltage_decay=4096,
        threshold=5,
    )


def three_core_ring() -> Deployment:
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
    return Deployment((core2, core0, core1))


def spike_wave(result) -> tuple[tuple[int, int], ...]:
    observed: list[tuple[int, int]] = []
    for trace in result.traces:
        for core in trace.cores:
            if core.spikes_out:
                observed.extend((trace.algorithmic_timestep, core.logical_core_id) for _ in core.spikes_out)
    return tuple(observed)


def test_deployment_json_roundtrip_preserves_fingerprint_and_behavior(tmp_path):
    deployment = three_core_ring()
    path = deployment.write_json(tmp_path / "deployment.json")
    loaded = Deployment.read_json(path)

    assert loaded.fingerprint == deployment.fingerprint
    assert loaded.to_dict() == deployment.to_dict()

    schedule = {0: (SpikePacket(0, 0, 0),)}
    first = run_deployment(deployment, 4, external_schedule=schedule)
    second = run_deployment(loaded, 4, external_schedule=schedule)
    assert first.normalized() == second.normalized()
    assert first.trace_fingerprint == second.trace_fingerprint


def test_deployment_rejects_tampered_contents_when_fingerprint_is_present():
    payload = three_core_ring().to_dict()
    payload["cores"][0]["synapse_templates"][0]["entries"][0]["weight"] = 7

    with pytest.raises(ValueError, match="fingerprint"):
        Deployment.from_dict(payload)


def test_deployment_rejects_unknown_schema_version():
    payload = three_core_ring().to_dict()
    payload["version"] = "v9-unknown"

    with pytest.raises(ValueError, match="unsupported deployment version"):
        Deployment.from_dict(payload)


def test_multitimestep_ring_replay_is_service_order_invariant():
    deployment = three_core_ring()
    external = {0: (SpikePacket(0, 0, 0),)}
    forward = {t: (0, 1, 2) for t in range(4)}
    reverse = {t: (2, 1, 0) for t in range(4)}

    a = run_deployment(
        deployment,
        4,
        external_schedule=external,
        service_order_schedule=forward,
    )
    b = run_deployment(
        deployment,
        4,
        external_schedule=external,
        service_order_schedule=reverse,
        reverse_packet_drain_timesteps=frozenset(range(4)),
    )

    assert spike_wave(a) == ((0, 0), (1, 1), (2, 2), (3, 0))
    assert a.normalized() == b.normalized()
    assert a.trace_fingerprint == b.trace_fingerprint


def test_runtime_rejects_external_packet_scheduled_for_wrong_timestep():
    deployment = three_core_ring()
    with pytest.raises(ValueError, match="target_timestep"):
        run_deployment(
            deployment,
            2,
            external_schedule={0: (SpikePacket(1, 0, 0),)},
        )


def test_deployment_json_is_stable_for_equivalent_core_ordering():
    deployment = three_core_ring()
    shuffled = Deployment(tuple(reversed(deployment.core_configs)))
    assert json.loads(deployment.to_json()) == json.loads(shuffled.to_json())
    assert deployment.fingerprint == shuffled.fingerprint
