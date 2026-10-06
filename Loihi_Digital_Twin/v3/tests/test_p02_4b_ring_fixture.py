from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile

from loihi_twin_v2.ddr_abi import P02_DDR_CONTEXT_STRIDE_BYTES


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "p02_4b_ring_fixture.py"
SPEC = importlib.util.spec_from_file_location("p02_4b_ring_fixture", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
fixture = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(fixture)


def test_p02_4b_workload_shape() -> None:
    configs = fixture.make_workload()
    assert tuple(config.core_id for config in configs) == (0, 1, 2, 3, 4)
    assert fixture.RESIDENT_SLOTS == 3
    assert fixture.TIMESTEPS == 7
    for core in configs:
        assert len(core.compartments) == 1
        assert len(core.input_axons) == 1
        assert len(core.output_routes) == 1


def test_p02_4b_generate_and_verify_expected_records() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture_dir = root / "fixture"
        dump_dir = root / "dumps"
        dump_dir.mkdir()

        manifest = fixture.generate(fixture_dir)

        assert manifest["logical_core_count"] == 5
        assert manifest["resident_context_count"] == 3
        assert manifest["physical_engine_count"] == 1
        assert manifest["dispatch_count"] == 35
        assert manifest["expected_packet_count_total"] == 30
        assert manifest["authoritative_backing"] == "k26-ddr"
        assert (
            manifest["trace_fingerprint"]
            == "9a925277fdeffbcce837954b6d44ce118d88e839f3a6b2d9d6e4956cf32747ac"
        )
        assert (
            manifest["manifest_fingerprint"]
            == "15288f1f6245c39a98167f610802d9146debfc6e3266981eb4bcd5245a1c975d"
        )

        for core_id in fixture.LOGICAL_CORES:
            initial = fixture_dir / f"core{core_id}_initial.bin"
            expected = fixture_dir / f"core{core_id}_expected.bin"
            assert initial.stat().st_size == P02_DDR_CONTEXT_STRIDE_BYTES
            assert expected.stat().st_size == P02_DDR_CONTEXT_STRIDE_BYTES
            (dump_dir / f"core{core_id}_after.bin").write_bytes(expected.read_bytes())

        result = fixture.verify(fixture_dir, dump_dir)
        assert set(result["records"]) == {"0", "1", "2", "3", "4"}


def test_p02_4b_final_expected_records_preserve_headers_and_static_banks() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        fixture.generate(root)

        for core_id in fixture.LOGICAL_CORES:
            initial = (root / f"core{core_id}_initial.bin").read_bytes()
            expected = (root / f"core{core_id}_expected.bin").read_bytes()

            assert initial[:0x1000] == expected[:0x1000]
            assert initial[0x6C000:] == expected[0x6C000:]
            for name in fixture.STATIC_BANKS:
                bank = fixture.BANKS[name]
                assert initial[bank.offset : bank.end] == expected[bank.offset : bank.end]
