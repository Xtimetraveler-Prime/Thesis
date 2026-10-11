"""Offline guardrails for the board-only P03.2c ILA capture Tcl contract."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CAPTURE = ROOT / "vivado" / "p03_2c_ila_capture.tcl"
WRAPPER = ROOT / "scripts" / "run_p03_2c_ila_capture.sh"


def test_capture_arms_using_verified_reset_defaults_not_control_writes():
    source = CAPTURE.read_text(encoding="utf-8")
    arm = source.split("proc p03_arm_ila {ila trigger} {", 1)[1].split(
        "\nproc p03_export_ila", 1
    )[0]
    assert "reset_hw_ila $ila" in arm
    for key, value in (
        ("CONTROL.TRIGGER_MODE", "BASIC_ONLY"),
        ("CONTROL.TRIGGER_CONDITION", "AND"),
        ("CONTROL.CAPTURE_MODE", "ALWAYS"),
        ("CONTROL.WINDOW_COUNT", "1"),
    ):
        assert f"{key} {value}" in arm
    assert "get_property $property $ila" in arm
    assert "set_property CONTROL." not in arm
    assert 'set_property TRIGGER_COMPARE_VALUE "eq1\'b1" $trigger' in arm
    assert "run_hw_ila $ila" in arm


def test_capture_preserves_two_independent_read_channel_traces():
    source = CAPTURE.read_text(encoding="utf-8")
    wrapper = WRAPPER.read_text(encoding="utf-8")
    assert 'p03_ila_by_cell $device "system_ila"' in source
    assert 'p03_ila_by_cell $device "p03_mmio_native_ila"' in source
    assert source.index("p03_arm_ila $upstream") < source.index(
        'puts "P03_2C_ILA_ARMED=1"'
    )
    assert source.index("p03_arm_ila $downstream") < source.index(
        'puts "P03_2C_ILA_ARMED=1"'
    )
    for stem in ("p03_2c_hpm0_capture", "p03_2c_mmio_slave_capture"):
        assert stem in source
        for suffix in (".ila", ".csv", ".vcd"):
            assert f"{stem}{suffix}" in wrapper
    assert "P03_2C_ILA_NO_TRIGGER" in source


def test_capture_log_does_not_flood_with_synthesized_constant_probes():
    source = CAPTURE.read_text(encoding="utf-8")
    assert "IGNORED_CONSTANT_PROBES" in source
    assert "*<const0>*" in source
    assert "*<const1>*" in source
