from neuromorphic_twin.fpga_broad_regression import build_m12_broad_cases
from neuromorphic_twin.fpga_core_capacity import (
    MAX_AXONS,
    MAX_EXTERNAL_EVENTS_PER_TICK,
    MAX_NEURONS,
    MAX_RECURRENT_EVENTS_PER_TICK,
    MAX_ROUTES,
    MAX_SYNAPSES,
)


def test_every_m12_4_case_fits_frozen_m11_5_physical_capacity() -> None:
    for case in build_m12_broad_cases():
        workload = case.workload
        assert workload.neuron_count <= MAX_NEURONS
        assert workload.storage.axon_count <= MAX_AXONS
        assert workload.storage.synapse_count <= MAX_SYNAPSES
        assert workload.routes.route_count <= MAX_ROUTES
        assert max(map(len, workload.external_schedule)) <= MAX_EXTERNAL_EVENTS_PER_TICK
        assert max(
            (len(tick.snapshot.recurrent_input_axons) for tick in workload.expected_ticks),
            default=0,
        ) <= MAX_RECURRENT_EVENTS_PER_TICK
        assert max(
            (len(tick.snapshot.routed_output_axons) for tick in workload.expected_ticks),
            default=0,
        ) <= MAX_RECURRENT_EVENTS_PER_TICK
