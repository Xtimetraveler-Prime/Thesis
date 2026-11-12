"""Synthetic tests for pinned original DTS reader; NOT native Vivado/dtc runs."""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/m08_d2_verify_original_m08_decoded_overlay.py"
spec = importlib.util.spec_from_file_location("m08_d2_original_dtbo", SCRIPT)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

DTS = r"""/dts-v1/;

/ {

	fragment@0 {
		target = <0xffffffff>;

		__overlay__ {
			#address-cells = <0x02>;
			#size-cells = <0x02>;
			firmware-name = "m08-v1-fan-page-uio-review.bit.bin";
			resets = <0xffffffff 0x74 0xffffffff 0x75 0xffffffff 0x76 0xffffffff 0x77>;
		};
	};

	fragment@1 {
		target = <0xffffffff>;

		__overlay__ {
			#address-cells = <0x02>;
			#size-cells = <0x02>;

			m08-identity@a0000000 {
				compatible = "generic-uio";
				linux,uio-name = "m08-identity";
				reg = <0x00 0xa0000000 0x00 0x1000>;
				status = "okay";
			};

			m08-page@a0001000 {
				compatible = "generic-uio";
				linux,uio-name = "m08-page";
				reg = <0x00 0xa0001000 0x00 0x1000>;
				status = "okay";
			};
		};
	};

	__fixups__ {
		fpga_full = "/fragment@0:target:0";
		zynqmp_reset = "/fragment@0/__overlay__:resets:0\0/fragment@0/__overlay__:resets:8\0/fragment@0/__overlay__:resets:16\0/fragment@0/__overlay__:resets:24";
		amba = "/fragment@1:target:0";
	};
};
"""
# DTS is synthetic fixture text pasted from user-visible original. It is NOT
# asserted to be native without the user's SHA and matching native receipt.
WARNING = (
    "/original/12_m08.dts: Warning (resets_property): "
    "/fragment@0/__overlay__:resets: Could not get phandle node for (cell 1)\n"
)


class OriginalM08DecodedOwnerEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        (self.dir / "12_m08.dts").write_text(DTS)
        (self.dir / "22_m08_dtc_stderr.txt").write_text(WARNING)
        self.sha = sha256(DTS.encode()).hexdigest()
        review = {
            "schema": "m08-d2-owner-pc-dtbo-decompile-v1",
            "status": "ORIGINAL_M08_DTS_COPY_CREATED_STOCK_ABSENT_NO_BOARD",
            "m08_only": True,
            "stock_dtbo_compared": False,
            "originals_unchanged": True,
            "runtime_clock_reset_hpm0_afi_or_atb_verified": False,
            "hardware_retry_authorized": False,
            "original_quarantined_image_reloaded": False,
            "files": {"m08": {
                "original_sha256": m.ORIGINAL_M08_DTBO_SHA,
                "decompiled_sha256": self.sha,
                "original_verified_again_after_dtc": True,
                "dtc_exit_status": 0,
                "original_path": "/original/m08-v1-fan-page-uio-review.dtbo",
                "decompiled_file": "/original/12_m08.dts",
            }},
        }
        (self.dir / "00_review.json").write_text(json.dumps(review))
        self.pin = patch.object(m, "EXPECTED_DTS_SHA", self.sha)
        self.pin.start()
        self.addCleanup(self.pin.stop)

    def test_valid_synthetic_case_does_not_claim_runtime(self):
        result = m.inspect(self.dir)
        self.assertEqual(result["status"],
                         "ORIGINAL_M08_DEPLOYED_OVERLAY_VERIFIED_CLOCK_AFI_NOT_DECLARED")
        self.assertFalse(result["clock_afi"]["proves_failed_boot_clock_off"])
        self.assertFalse(result["stock_dtbo_present"])
        self.assertFalse(result["hardware_retest_authorized"])

    def test_changed_dts_rejected_sha(self):
        p = self.dir / "12_m08.dts"
        p.write_text(p.read_text().replace("0xa0001000", "0xa0002000"))
        with self.assertRaisesRegex(m.EvidenceRejected, "SHA"):
            m.inspect(self.dir)

    def test_changed_dtc_warning_rejected(self):
        p = self.dir / "22_m08_dtc_stderr.txt"
        p.write_text(WARNING + "Error: different problem\n")
        with self.assertRaisesRegex(m.EvidenceRejected, "warning"):
            m.inspect(self.dir)

    def test_fake_runtime_approval_rejected(self):
        p = self.dir / "00_review.json"
        r = json.loads(p.read_text())
        r["hardware_retry_authorized"] = True
        p.write_text(json.dumps(r))
        with self.assertRaisesRegex(m.EvidenceRejected, "metadata"):
            m.inspect(self.dir)

    def test_symlink_original_rejected(self):
        p = self.dir / "12_m08.dts"
        moved = self.dir / "other.dts"
        p.rename(moved)
        p.symlink_to(moved)
        with self.assertRaisesRegex(m.EvidenceRejected, "symlinked"):
            m.inspect(self.dir)

    def test_source_is_not_hardware_tool(self):
        src = SCRIPT.read_text()
        for forbidden in ("subprocess.run", "os.system", "mmap.mmap",
                          "open_checkpoint", "program_hw_devices",
                          "write_text(", "xmutil ", "socket.connect"):
            self.assertNotIn(forbidden, src)


if __name__ == "__main__":
    unittest.main()
