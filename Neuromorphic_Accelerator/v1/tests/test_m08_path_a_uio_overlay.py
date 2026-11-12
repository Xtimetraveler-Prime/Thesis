"""Source-only M08.2b Path A dual UIO overlay tests; NO live FPGA or MMIO.

All DT / board log examples below are SYNTHETIC, not owner evidence.
"""
from pathlib import Path
from hashlib import sha256
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FILE = ROOT / "scripts/m08_path_a_stage_uio_overlay.py"
spec = importlib.util.spec_from_file_location("m08_path_a_stage_uio_overlay", FILE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def synthetic_board() -> str:
    probes = [
        ("model", "ZynqMP KV260 revB\n"),
        ("os_release", 'VERSION_ID="24.04"\n'),
        ("cmdline", "uio_pdrv_genirq.of_id=generic-uio\n"),
        ("manager_service", "active\ninactive\nactive\n"),
        ("fpga_manager", "operating\n"),
        ("active_overlays", "k26-starter-kits_image_1\n"),
        ("m08_kernel_mmio_binding_readiness",
         "DRIVER_PRESENT=/sys/bus/platform/drivers/uio_pdrv_genirq\n"
         "uio_pdrv_genirq 16384 0\n"
         "EXISTING_UIO=/sys/class/uio/uio0:axi-pmon\n"
         "EXISTING_UIO=/sys/class/uio/uio1:axi-pmon\n"
         "EXISTING_UIO=/sys/class/uio/uio2:axi-pmon\n"
         "EXISTING_UIO=/sys/class/uio/uio3:axi-pmon\n"
         "M08_LINUX_ACCESSOR=NOT_YET_VALIDATED\n"),
        ("m08_live_dt_amba_fpga_symbols",
         "M08_DT_SYMBOL=amba|/axi\n"
         "M08_DT_SYMBOL=fpga_full|/fpga-full\n"
         "M08_DT_SYMBOL=zynqmp_reset|/firmware/zynqmp-reset\n"
         "M08_DT_CELL_HEX=amba|#address-cells|00000002\n"
         "M08_DT_CELL_HEX=amba|#size-cells|00000002\n"
         "M08_DT_SYMBOL_INSPECTION_NO_OVERLAY_WRITE\n"),
    ]
    return "M08_PATH_A_LINUX_READ_ONLY_BEGIN\n" + "".join(
        f"M08_PROBE_BEGIN|{name}\n{value}M08_PROBE_END|{name}|rc=0\n"
        for name, value in probes
    ) + "M08_PATH_A_LINUX_READ_ONLY_END_NO_FPGA_CHANGES\n"


def synthetic_dtc() -> str:
    return (
        "/dts-v1/;\n"
        "/ { fragment@0 { __overlay__ {\n"
        'firmware-name = "m08-v1-fan-page-uio-review.bit.bin";\n'
        "resets = <0xffffffff 0x74 0xffffffff 0x75 "
        "0xffffffff 0x76 0xffffffff 0x77>; };\n"
        "};\n"
        "fragment@1 { __overlay__ {\n"
        "m08-identity@a0000000 {\n"
        'compatible = "generic-uio";\n'
        'linux,uio-name = "m08-identity";\n'
        'reg = <0x00 0xa0000000 0x00 0x1000>;\n'
        'status = "okay";\n'
        "};\n"
        "m08-page@a0001000 {\n"
        'compatible = "generic-uio";\n'
        'linux,uio-name = "m08-page";\n'
        'reg = <0x00 0xa0001000 0x00 0x1000>;\n'
        'status = "okay";\n'
        "}; };\n"
        "};\n"
        '__fixups__ { amba = "/fragment@1:target:0";\n'
        'fpga_full = "/fragment@0:target:0";\n'
        'zynqmp_reset = "/fragment@0/__overlay__:resets:0"; };\n'
        "};\n"
    )


class TestM08PathADualUIO(unittest.TestCase):
    def test_two_exact_4k_windows_and_unique_uio_names(self):
        text = mod.DTS
        self.assertIn("&amba", text)
        self.assertIn("&fpga_full", text)
        self.assertIn("&zynqmp_reset", text)
        self.assertEqual(text.count('"generic-uio"'), 2)
        self.assertNotIn("/dev/mem", text)
        self.assertEqual(mod.REGISTERS, (
            ("m08-identity", 0xA0000000, 0x1000),
            ("m08-page", 0xA0001000, 0x1000),
        ))
        self.assertIn("m08-v1-fan-page-uio-review.bit.bin", text)
        self.assertEqual(mod.SHELL, {"shell_type": "PL_FLAT", "num_slots": "1"})
        self.assertEqual(mod.validate_dtbo(synthetic_dtc())["m08-page"]["bytes"], 4096)

    def test_synthetic_dtbo_rejects_wrong_address_name_dma_or_fixup(self):
        good = synthetic_dtc()
        for old, new in (
            ("0xa0001000", "0xa0002000"),
            ("0x1000", "0x2000"),
            ('linux,uio-name = "m08-identity";',
             'linux,uio-name = "axi-pmon";'),
            ('compatible = "generic-uio";', 'compatible = "my-bad-io";'),
            ("fpga_full = ", "not_fpga_full = "),
            ("zynqmp_reset = ", "reset_dummy = "),
            ("amba = ", "not_amba = "),
            ('status = "okay";', 'status = "disabled";'),
        ):
            with self.subTest(old=old), self.assertRaises(ValueError):
                mod.validate_dtbo(good.replace(old, new, 1))
        with self.assertRaises(ValueError):
            mod.validate_dtbo(good.replace(
                "}; };\n};", 'interrupts = <1 2 3>;\n}; };\n};', 1
            ).replace("linux,uio-name = \"m08-page\";",
                      "linux,uio-name = \"m08-page\";\n"
                      "dma-names = \"wrong\";", 1))

    def test_genuine_board_readiness_requires_live_symbols_and_driver(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            log = folder / "01_board_stdout.log"
            log.write_text(synthetic_board())
            (folder / "04_evidence_sha256.txt").write_text(
                sha256(log.read_bytes()).hexdigest()
                + "  01_board_stdout.log\n"
            )
            result = mod.validate_board(folder)
            self.assertEqual(result["kernel_of_id"], "generic-uio")
            for old, new in (
                ("M08_DT_SYMBOL=amba|/axi", "M08_DT_SYMBOL_MISSING=amba"),
                ("M08_DT_CELL_HEX=amba|#address-cells|00000002",
                 "M08_DT_CELL_HEX=amba|#address-cells|00000001"),
                ("uio_pdrv_genirq.of_id=generic-uio", "wrong-boot-args"),
                ("DRIVER_PRESENT=/sys/bus/platform/drivers/uio_pdrv_genirq",
                 "DRIVER_ABSENT=/sys/bus/platform/drivers/uio_pdrv_genirq"),
                ("k26-starter-kits_image_1", "OTHER_FPGA_LOADED"),
                ("M08_LINUX_ACCESSOR=NOT_YET_VALIDATED",
                 "M08_LINUX_ACCESSOR=ASSUMED"),
            ):
                with self.subTest(old=old):
                    log.write_text(synthetic_board().replace(old, new, 1))
                    (folder / "04_evidence_sha256.txt").write_text(
                        sha256(log.read_bytes()).hexdigest()
                        + "  01_board_stdout.log\n"
                    )
                    with self.assertRaises(ValueError):
                        mod.validate_board(folder)
            log.write_text(synthetic_board())
            with self.assertRaises(ValueError):
                mod.validate_board(folder)  # ledger now different

    def test_original_staging_package_must_be_SHA_pinned(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d) / "m08_2b_path_a_linux_package_REVIEW_ONLY_TEST"
            pkg = base / "m08-v1-fan-page"
            pkg.mkdir(parents=True)
            for name, content in (
                ("m08-v1-fan-page.bit.bin", b"fake bit data"),
                ("m08-v1-fan-page.dtbo", b"fake dtbo"),
                ("shell.json", json.dumps(mod.SHELL).encode()),
            ):
                (pkg / name).write_bytes(content)
            manifest = {
                "status": "OFFLINE_PACKAGE_STAGED_NO_BOARD_NO_MMIO_ACCESS",
                "original_verified_bit_sha256": mod.FAN_BIT_SHA,
                "bit_bin_sha256": mod.FAN_BIT_BIN_SHA,
                "bit_bin_bytes": mod.FAN_BIT_BIN_BYTES,
                "dtbo_sha256": mod.PRIOR_DTBO_SHA,
                "device_tree_mmio_nodes": "NONE_INTENTIONALLY",
                "linux_package_installed": False,
                "fpga_programmed": False,
            }
            (base / "05_package_review.json").write_text(json.dumps(manifest))
            (base / "98_status.txt").write_text("staging_status=success\n")
            originals = [
                pkg / "m08-v1-fan-page.bit.bin",
                pkg / "m08-v1-fan-page.dtbo",
                pkg / "shell.json",
                base / "05_package_review.json",
                base / "98_status.txt",
            ]
            (base / "99_evidence_sha256.txt").write_text(
                "".join(sha256(p.read_bytes()).hexdigest() + "  " +
                        str(p.relative_to(base)) + "\n" for p in originals)
            )
            with self.assertRaisesRegex(ValueError, "original bit.bin changed"):
                mod.validate_package(base)
            (pkg / "m08-v1-fan-page.bit.bin").write_bytes(b"tamper")
            with self.assertRaisesRegex(ValueError, "original evidence missing/changed"):
                mod.validate_package(base)

    def test_static_source_refuses_board_changes(self):
        source = FILE.read_text()
        for prohibited in (
            "subprocess.run([\"ssh\"", "subprocess.run([\"scp\"",
            "xmutil unloadapp", "xmutil loadapp", "program_hw_devices",
            "systemctl stop", "sudo cp", "devmem ",
            "modprobe uio_pdrv_genirq", "open(\"/dev/mem\"",
        ):
            self.assertNotIn(prohibited, source)
        self.assertIn("validate_board(board)", source)
        self.assertIn("validate_package(staged)", source)
        self.assertIn("validate_dtbo(result.stdout)", source)
        self.assertIn("99_evidence_sha256.txt", source)
        self.assertIn("OFFLINE_DUAL_UIO_CANDIDATE_NOT_INSTALLED", source)
        board_probe = (ROOT / "scripts/m08_kv260_path_a_readonly.sh").read_text()
        self.assertIn("m08_live_dt_amba_fpga_symbols", board_probe)
        self.assertIn("M08_DT_SYMBOL_INSPECTION_NO_OVERLAY_WRITE", board_probe)

    def test_cli_missing_original_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p = subprocess.run(
                [sys.executable, str(FILE), "--staged-dir", d,
                 "--board-evidence-dir", d, "--evidence-base", d],
                capture_output=True, text=True, timeout=10
            )
            self.assertEqual(p.returncode, 2)
            self.assertIn("DUAL_UIO_OFFLINE_REJECTED", p.stderr)
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_receipt_hashes_all_outputs_without_claiming_hardware(self):
        with tempfile.TemporaryDirectory() as d:
            folder = Path(d)
            (folder / "pkg").mkdir()
            (folder / "pkg" / "test.dtbo").write_bytes(b"SYNTHETIC")
            (folder / "98_status.txt").write_text("staging_status=success\n")
            mod.record_hashes(folder)
            content = (folder / "99_evidence_sha256.txt").read_text()
            self.assertIn("pkg/test.dtbo", content)
            self.assertNotIn("99_evidence_sha256.txt", content)


if __name__ == "__main__":
    unittest.main()
