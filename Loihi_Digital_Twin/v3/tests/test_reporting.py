from __future__ import annotations

import json

from loihi_twin_v2 import (
    CompartmentConfig,
    Deployment,
    InputAxonBinding,
    LogicalCoreConfig,
    SpikePacket,
    SynapseEntry,
    SynapseTemplate,
    deployment_report,
    trace_report,
)


def test_resource_and_trace_reports_are_json_serializable_and_include_headroom():
    config = LogicalCoreConfig(
        core_id=0,
        compartments=(CompartmentConfig(4096, 4096, 100),),
        input_axons=(InputAxonBinding(0, 0),),
        synapse_templates=(SynapseTemplate(0, (SynapseEntry(0, 2),)),),
    )
    deployment = Deployment((config,))
    resource = deployment_report(deployment)
    json.dumps(resource, sort_keys=True)
    assert resource["cores"][0]["resource_usage"]["compartments"] == 1
    assert resource["cores"][0]["headroom"]["compartments"] == 1023
    assert resource["cores"][0]["capacity"]["synapse_bytes"] == 128 * 1024

    trace = deployment.build_chip().step((SpikePacket(0, 0, 0),))
    payload = trace_report(trace)
    json.dumps(payload, sort_keys=True)
    assert payload["algorithmic_timestep"] == 0
    assert payload["cores"][0]["logical_core_id"] == 0
    assert payload["cores"][0]["packet_in"][0]["destination_axon"] == 0
