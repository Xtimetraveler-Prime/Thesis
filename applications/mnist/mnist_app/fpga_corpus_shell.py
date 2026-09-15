"""Deterministic source adapters for reusing the M12.3 capture shell in MNIST-08.

The architectural core RTL remains untouched. MNIST-08 stages application-local
copies of the already validated M12.3 capture controller/Tcl and applies three
mechanical adaptations:

1. static load-image addressing uses the case's frozen profile ID, while the
   external schedule remains indexed by the 60-case application case ID;
2. packed external events use a row pointer plus one synthesis-safe ROM bank per
   profile rather than a single oversized or rectangular event array;
3. the existing four-bit capture-phase witness is compared with the low nibble
   of case IDs above 15. Exact external-event differential checking still proves
   that the complete selected case, not just its low nibble, executed.
"""

from __future__ import annotations

from pathlib import Path


_CONTROLLER_ANCHOR = "    capture_state_t state;\n    logic [7:0] active_case_id;\n"
_CONTROLLER_INSERT = """    capture_state_t state;
    logic [7:0] active_case_id;

    // MNIST-08 stores each frozen static deployment once and maps each of the
    // 60 dynamic cases to one of those two immutable profile images.
    logic [7:0] static_image_id;
    always_comb begin
        static_image_id = M12_3_CASE_PROFILE_IDS[active_case_id];
    end
"""

_STATIC_REPLACEMENTS = (
    ("active_case_id * M12_3_MAX_NEURONS", "static_image_id * M12_3_MAX_NEURONS", 2),
    ("active_case_id * M12_3_MAX_FORMATS", "static_image_id * M12_3_MAX_FORMATS", 1),
    ("active_case_id * M12_3_MAX_SYNAPSES", "static_image_id * M12_3_MAX_SYNAPSES", 1),
    (
        "active_case_id * (M12_3_MAX_AXONS + 1)",
        "static_image_id * (M12_3_MAX_AXONS + 1)",
        1,
    ),
    (
        "active_case_id * (M12_3_MAX_NEURONS + 1)",
        "static_image_id * (M12_3_MAX_NEURONS + 1)",
        1,
    ),
    ("active_case_id * M12_3_MAX_ROUTES", "static_image_id * M12_3_MAX_ROUTES", 1),
)

_EXTERNAL_RECTANGULAR = """M12_3_EXTERNAL_EVENTS[
                    (((active_case_id * M12_3_MAX_TICKS) + tick_index) *
                     M12_3_MAX_EXTERNAL_EVENTS) + load_index
                ]"""
_EXTERNAL_PROFILE_BANKED = """(static_image_id == 8'd0) ?
                    M12_3_EXTERNAL_EVENTS_PROFILE0[
                        M12_3_EXTERNAL_ROWS[
                            (active_case_id * M12_3_MAX_TICKS) + tick_index
                        ] + load_index
                    ] :
                    M12_3_EXTERNAL_EVENTS_PROFILE1[
                        M12_3_EXTERNAL_ROWS[
                            (active_case_id * M12_3_MAX_TICKS) + tick_index
                        ] + load_index
                    ]"""

_TCL_CASE_CHECK = """    if {$selected_case != $case_id} {
        error \"M12.3 case-select witness mismatch: requested=$case_id observed=$selected_case phase=$phase\"
    }"""
_TCL_NIBBLE_CHECK = """    set expected_case_nibble [expr {$case_id & 0xF}]
    if {$selected_case != $expected_case_nibble} {
        error \"M12.3 case-select witness mismatch: requested=$case_id expected_low_nibble=$expected_case_nibble observed=$selected_case phase=$phase\"
    }"""


def patch_capture_controller_text(text: str) -> str:
    if text.count(_CONTROLLER_ANCHOR) != 1:
        raise ValueError("unexpected M12.3 capture-controller active-case anchor")
    patched = text.replace(_CONTROLLER_ANCHOR, _CONTROLLER_INSERT, 1)

    for source, target, expected_count in _STATIC_REPLACEMENTS:
        actual_count = patched.count(source)
        if actual_count != expected_count:
            raise ValueError(
                f"unexpected M12.3 static-image occurrence count for {source!r}: "
                f"expected {expected_count}, got {actual_count}"
            )
        patched = patched.replace(source, target)

    if patched.count(_EXTERNAL_RECTANGULAR) != 1:
        raise ValueError("unexpected M12.3 rectangular external-event expression")
    patched = patched.replace(_EXTERNAL_RECTANGULAR, _EXTERNAL_PROFILE_BANKED, 1)

    if "M12_3_CASE_PROFILE_IDS[active_case_id]" not in patched:
        raise AssertionError("shared-profile selector was not inserted")
    if "M12_3_EXTERNAL_ROWS[" not in patched:
        raise AssertionError("packed external-event row lookup was not inserted")
    if "M12_3_EXTERNAL_EVENTS_PROFILE0[" not in patched:
        raise AssertionError("profile-banked external-event lookup was not inserted")
    if "M12_3_EXTERNAL_EVENTS_PROFILE1[" not in patched:
        raise AssertionError("profile-banked external-event lookup was not inserted")
    return patched


def patch_capture_tcl_text(text: str) -> str:
    if text.count(_TCL_CASE_CHECK) != 1:
        raise ValueError("unexpected M12.3 Tcl case-witness check")
    patched = text.replace(_TCL_CASE_CHECK, _TCL_NIBBLE_CHECK, 1)
    if "expected_case_nibble" not in patched:
        raise AssertionError("low-nibble case witness patch was not inserted")
    return patched


def write_patched_capture_controller(source: str | Path, output: str | Path) -> Path:
    source = Path(source)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        patch_capture_controller_text(source.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return output


def write_patched_capture_tcl(source: str | Path, output: str | Path) -> Path:
    source = Path(source)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        patch_capture_tcl_text(source.read_text(encoding="utf-8")),
        encoding="utf-8",
    )
    return output
