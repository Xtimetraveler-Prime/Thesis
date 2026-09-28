from __future__ import annotations

from neuromorphic_twin.fpga_core_capacity import (
    FPGA_CORE_CAPACITY_SCHEMA,
    FPGA_CORE_CAPACITY_V1,
    estimate_fpga_core_storage_v1,
)


def main() -> None:
    capacity = FPGA_CORE_CAPACITY_V1
    estimate = estimate_fpga_core_storage_v1(capacity)

    print(f"schema={FPGA_CORE_CAPACITY_SCHEMA}")
    print(f"max_neurons={capacity.max_neurons}")
    print(f"max_axons={capacity.max_axons}")
    print(f"max_synapses={capacity.max_synapses}")
    print(f"max_weight_formats={capacity.max_weight_formats}")
    print(f"max_routes={capacity.max_routes}")
    print(
        "max_external_events_per_tick="
        f"{capacity.max_external_events_per_tick}"
    )
    print(
        "max_recurrent_events_per_tick="
        f"{capacity.max_recurrent_events_per_tick}"
    )
    print(f"storage_total_bits={estimate.total_bits}")
    print(f"bram36_capacity_lower_bound={estimate.bram36_lower_bound}")


if __name__ == "__main__":
    main()
