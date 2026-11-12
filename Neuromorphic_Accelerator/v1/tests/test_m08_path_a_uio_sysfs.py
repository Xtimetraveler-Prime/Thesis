"""M08.2b read-only UIO sysfs inventory: synthetic metadata-only fixtures."""
from pathlib import Path
import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE = ROOT / "scripts/m08_path_a_uio_sysfs_readonly.py"
spec = importlib.util.spec_from_file_location("m08_uio_sysfs", MODULE)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def device(root: Path, index: int, name: str, base: int,
           size: int = 0x1000, map_index: int = 0) -> Path:
    path = root / f"uio{index}"
    maps = path / "maps" / f"map{map_index}"
    maps.mkdir(parents=True)
    (path / "name").write_text(name + "\n")
    (maps / "addr").write_text(f"0x{base:x}\n")
    (maps / "size").write_text(f"0x{size:x}\n")
    return path


class M08UIOSysfsDiscovery(unittest.TestCase):
    def test_baseline_performance_monitors_are_not_m08(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            device(root, 0, "axi-pmon", 0xFFA00000)
            device(root, 1, "axi-pmon", 0xFD0B0000)
            device(root, 2, "axi-pmon", 0xFD490000)
            device(root, 3, "axi-pmon", 0xFFA10000)
            result = mod.inventory(root)
            self.assertEqual(result["m08_bindings"], {})
            self.assertEqual(result["status"], "UIO_SYSFS_METADATA_INSPECTED_NO_MMIO")
            self.assertEqual(len(result["existing_devices"]), 4)
            with self.assertRaisesRegex(ValueError, "both separately mapped"):
                mod.inventory(root, expected="present")

    def test_two_m08_bindings_discovered_by_name_and_address_not_number(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            device(root, 0, "axi-pmon", 0xFFA00000)
            device(root, 12, "m08-page", 0xA0001000)
            device(root, 8, "m08-identity", 0xA0000000)
            result = mod.inventory(root, expected="present")
            self.assertEqual(result["m08_bindings"],
                             {"m08-identity": "uio8", "m08-page": "uio12"})
            self.assertEqual(result["register_readback"], "NOT_PERFORMED")
            with self.assertRaisesRegex(ValueError, "unexpectedly present"):
                mod.inventory(root, expected="absent")

    def test_fail_closed_wrong_name_address_size_duplicate_or_alias(self):
        for kind in ("wrong_name", "wrong_address", "wrong_size", "wrong_map",
                     "duplicate", "overlap"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                device(root, 7, "m08-identity", 0xA0000000)
                device(root, 8, "m08-page", 0xA0001000)
                if kind == "wrong_name":
                    (root / "uio7" / "name").write_text("axi-pmon\n")
                elif kind == "wrong_address":
                    (root / "uio8" / "maps" / "map0" / "addr").write_text("0xa0002000\n")
                elif kind == "wrong_size":
                    (root / "uio7" / "maps" / "map0" / "size").write_text("0x2000\n")
                elif kind == "wrong_map":
                    (root / "uio8" / "maps" / "map0").rename(
                        root / "uio8" / "maps" / "map1")
                elif kind == "duplicate":
                    device(root, 9, "m08-identity", 0xA0000000)
                elif kind == "overlap":
                    device(root, 6, "axi-pmon", 0xA0000800, size=0x1000)
                with self.assertRaises(ValueError):
                    mod.inventory(root, expected="present")

    def test_fail_closed_missing_sysfs_map_or_non_numeric_resource(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            path = device(root, 1, "axi-pmon", 0xFFA00000)
            (path / "maps" / "map0" / "size").write_text("garbage\n")
            with self.assertRaisesRegex(ValueError, "invalid numeric"):
                mod.inventory(root)
            (path / "maps" / "map0" / "size").unlink()
            with self.assertRaisesRegex(ValueError, "missing read-only"):
                mod.inventory(root)

    def test_command_line_only_prints_json_no_files_created(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            device(root, 2, "axi-pmon", 0xFFA00000)
            before = sorted(str(x) for x in root.rglob("*"))
            cmd = [sys.executable, str(MODULE), "--sysfs-root", str(root),
                   "--expected", "absent"]
            result = subprocess.run(cmd, capture_output=True, text=True,
                                    timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)["m08_bindings"], {})
            self.assertEqual(before, sorted(str(x) for x in root.rglob("*")))

    def test_no_device_open_mmap_driver_change_or_programming(self):
        text = MODULE.read_text()
        for dangerous in (
            "import mmap", "from mmap import", "subprocess.run(", "os.open(",
            "open('/dev/", 'open("/dev/', "modprobe", "xmutil loadapp",
            "xmutil unloadapp", "program_hw_devices", "write_bitstream",
            "flashcp", "devmem ",
        ):
            self.assertNotIn(dangerous, text)
        self.assertIn("REGIONS", text)
        self.assertIn("0xA0000000", text)
        self.assertIn("0xA0001000", text)
        self.assertIn('"NOT_PERFORMED"', text)


if __name__ == "__main__":
    unittest.main()
