from __future__ import annotations

import pytest

from loihi_twin_v2 import (
    export_compiled_fpga_image,
    export_paged_compiled_fpga_image,
)
from loihi_twin_v2.hardware_p03 import unpack_route_word
from mnist_v2_nxtf.structural import compile_structural_probe


def test_p08_2_frozen_structural_graph_exports_as_five_backing_three_resident_one_engine():
    compiled = compile_structural_probe()

    with pytest.raises(ValueError, match="resident P05 FPGA context count"):
        export_compiled_fpga_image(compiled)

    paged = export_paged_compiled_fpga_image(compiled)
    report = paged.report()

    assert paged.compiled_deployment_fingerprint == compiled.fingerprint
    assert paged.source_fingerprint == compiled.source_fingerprint
    assert report["logical_core_count"] == 5
    assert report["resident_context_count"] == 3
    assert report["physical_engine_count"] == 1
    assert report["requires_paging"] is True
    assert report["logical_capacity_changed"] is False
    assert paged.hardware_image.initial_resident_core_ids == (0, 1, 2)


def test_p08_2_backing_image_preserves_p06_resource_footprint_and_nonresident_route_identity():
    compiled = compile_structural_probe()
    compiled_report = compiled.report()
    paged = export_paged_compiled_fpga_image(compiled)

    expected_usage = tuple(
        (
            core["usage"]["compartments"],
            core["usage"]["input_axons"],
            core["usage"]["output_routes"],
            core["usage"]["synapse_bytes"],
            core["usage"]["shared_parameters"],
            core["usage"]["expanded_connections"],
        )
        for core in compiled_report["cores"]
    )
    assert expected_usage == (
        (900, 729, 2700, 12120, 2197, 22500),
        (900, 729, 2700, 16336, 3211, 22500),
        (900, 2745, 1210, 82360, 17181, 91584),
        (900, 2016, 729, 101024, 22680, 113400),
        (618, 3828, 521, 95464, 18966, 88896),
    )

    initial_resident = set(paged.hardware_image.initial_resident_core_ids)
    destinations_from_initial_page = {
        unpack_route_word(word)["destination_core"]
        for logical_core_id in initial_resident
        for word in paged.hardware_image.backing_by_logical_core[logical_core_id].image.route_words
    }

    assert destinations_from_initial_page - initial_resident
    assert destinations_from_initial_page <= set(range(5))


def test_p08_2_any_three_logical_cores_can_be_materialized_without_changing_backing_identity():
    paged = export_paged_compiled_fpga_image(compile_structural_probe())

    page = paged.hardware_image.resident_page((4, 1, 3))

    assert page.logical_core_ids == (4, 1, 3)
    assert page.logical_to_context_slot == {4: 0, 1: 1, 3: 2}
    assert page.contexts[0].image.core_id == 4
    assert page.contexts[1].image.core_id == 1
    assert page.contexts[2].image.core_id == 3
