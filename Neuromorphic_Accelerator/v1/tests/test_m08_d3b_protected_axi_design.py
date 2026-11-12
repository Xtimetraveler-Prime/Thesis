"""M08 D3B PS-side admission policy and original D3A evidence gate tests.

Synthetic native receipts are only parser tests; the actual original owner
Vivado text SHAs are pinned in the separate source manifest and documentation.
No board, Vivado, PS registers, ATB, Linux MMIO, or firmware programs here.
"""
from __future__ import annotations

from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
GATE = ROOT / "scripts/m08_d3b_protected_axi_evidence_gate.py"
TB = ROOT / "rtl/m08/tb_m08_d3b_ps_linux_release_policy.sv"
spec = importlib.util.spec_from_file_location("m08_d3b_evidence_gate", GATE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
MARKERS = [
    "M08_D3B_EACH_MISSING_PREREQUISITE_BLOCKS_ACCESS_PASS",
    "M08_D3B_FIRST_TIMEOUT_STICKY_QUARANTINE_NO_RETRY_PASS",
    "M08_D3B_ONE_SUCCESSFUL_PROBE_PER_FULL_RESTART_PASS",
    "M08_D3B_READINESS_LOSS_LOCKS_UNTIL_RESTART_PASS",
    "M08_D3B_STOPPED_PS_CLOCK_IS_UNPROTECTED_NEGATIVE_PASS",
    "M08_D3B_OFFLINE_PS_LINUX_POLICY_ALL_PASS_NOT_HARDWARE_ATB_OR_MMIO_PROOF",
]


class M08D3BProtectedAXIOfflineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "contract.json"
        shutil.copy2(m.MANIFEST, self.manifest)

    def test_real_repo_manifest_cannot_authorize_programming(self):
        manifest, digest = m.audit_contract()
        self.assertEqual(manifest["phase"], "D3.2A_ARCHITECTURE_AND_OFFLINE_POLICY_MODEL")
        self.assertEqual(len(digest), 64)
        self.assertFalse(manifest["proposed_interconnect"]["physical_mmio_authorized"])
        self.assertEqual(manifest["evidence_status"]["D3B_PROTECTED_BITSTREAM"], "NOT_BUILT")
        self.assertTrue(manifest["evidence_status"]["original_m08_image_quarantined"])

    def test_bogus_protected_image_and_permission_rejected(self):
        obj = json.loads(self.manifest.read_text())
        obj["proposed_interconnect"]["physical_programming_authorized"] = True
        self.manifest.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.EvidenceRejected, "physical_programming_authorized"):
            m.audit_contract(self.manifest)
        obj["proposed_interconnect"]["physical_programming_authorized"] = False
        obj["evidence_status"]["D3B_PROTECTED_BITSTREAM"] = "BUILT"
        self.manifest.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.EvidenceRejected, "hardware approval"):
            m.audit_contract(self.manifest)

    def test_unsubstantiated_atb4_or_aib13_claim_rejected(self):
        obj = json.loads(self.manifest.read_text())
        obj["protection_requirements"]["ATB4_RESP_EN"] = "PASS"
        self.manifest.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.EvidenceRejected, "cannot claim"):
            m.audit_contract(self.manifest)
        obj["protection_requirements"]["ATB4_RESP_EN"] = "REQUIRES_BOOT_OWNERSHIP_AND_READBACK_PROOF"
        obj["proposed_interconnect"]["upstream_ps_isolation_block"] = "FPD_AIB_INSTANCE_12"
        self.manifest.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.EvidenceRejected, "upstream_ps_isolation_block"):
            m.audit_contract(self.manifest)

    def test_fake_synthesizable_ps_atb_model_rejected(self):
        obj = json.loads(self.manifest.read_text())
        obj["source_model"]["is_synthesizable_for_recovery"] = True
        self.manifest.write_text(json.dumps(obj))
        with self.assertRaisesRegex(m.EvidenceRejected, "model"):
            m.audit_contract(self.manifest)

    def fake_native_originals(self):
        """Synthetic test fixture; manifest expected SHAs patched to fake originals."""
        run = self.root / "m08_d3a_synthetic"
        run.mkdir()
        readback = {
            "schema": "m08-d3a-kv260-passive-fan-bd-v1",
            "candidate": "m08-d3a-passive-fan-v1",
            "vivado_version": "2025.2",
            "part": "xck26-sfvc784-2LV-c",
            "board_part": "xilinx.com:kv260_som:part0:1.4",
            "ps_preset": "YES",
            "ps_hpm0_fpd": "DISABLED", "ps_hpm1_fpd": "DISABLED",
            "ps_hpm0_lpd": "DISABLED",
            "smartconnect": "ABSENT", "identity_slave": "ABSENT",
            "page_slave": "ABSENT", "linux_uio_devices": "ZERO",
            "ps_pl0_native_frequency_hz": "99999001",
            "fan_pin": "A12", "fan_iostandard": "LVCMOS33",
            "validated_bd": "YES", "ps_atb4_configuration": "UNKNOWN",
            "ps_timeout_protection": "NOT_PROVEN",
            "physical_fan_cooling": "NOT_PROVEN",
            "synthesis": "NOT_RUN", "implementation": "NOT_RUN",
            "bitstream": "NOT_GENERATED", "hardware_programmed": "NO",
            "hardware_mmio_authorized": "NO",
        }
        documents = {
            "01_native_vivado.log": (
                "Vivado v2025.2\n"
                "INFO: [BD 5-1043] xilinx.com:inline_hdl:ilslice:1.0\n"
                "M08_D3A_PASSIVE_FAN_ONLY_BD_VALIDATED_NO_AXI_NO_BITSTREAM_NO_BOARD\n"
                "INFO: [Common 17-206] Exiting Vivado at synthetic time\n"
            ),
            "output/10_d3a_passive_bd_readback.txt": "".join(
                key + "=" + val + "\n" for key, val in readback.items()),
            "output/11_d3a_passive_bd_export.tcl": (
                "CONFIG.PSU__USE__M_AXI_GP0 {0}\n"
                "CONFIG.PSU__USE__M_AXI_GP1 {0}\n"
                "CONFIG.PSU__USE__M_AXI_GP2 {0}\n"
                "CONFIG.PSU__TTC0__WAVEOUT__IO {EMIO}\n"
                "M08_FAN_PWM m08_d3a_ttc0_fan_slice\n"
            ),
            "output/12_d3a_fan_a12.xdc": "\n".join(m.XDC_LINES) + "\n",
        }
        shas = {}
        for name, data in documents.items():
            path = run / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(data)
            shas[name] = sha256(data.encode()).hexdigest()
        (run / "99_evidence_sha256.txt").write_text(
            "".join(sha + "  " + name + "\n" for name, sha in shas.items()))
        obj = json.loads(self.manifest.read_text())
        obj["parent_d3a_native_evidence"]["sha256"] = shas
        self.manifest.write_text(json.dumps(obj))
        return run, obj

    def test_synthetic_d3a_receipt_carries_no_atb_proof(self):
        run, obj = self.fake_native_originals()
        record = m.audit_owner_run(run, obj)
        self.assertEqual(record["status"],
                         "D3A_NATIVE_OWNER_FILES_SHA256_AND_SEMANTICS_ACCEPTED")
        self.assertFalse(record["source_or_native_physical_atb4_proof"])

    def test_synthetic_receipt_rejects_file_change_and_bad_checksum(self):
        run, obj = self.fake_native_originals()
        path = run / "output/11_d3a_passive_bd_export.tcl"
        path.write_text(path.read_text() + "# changed\n")
        with self.assertRaisesRegex(m.EvidenceRejected, "SHA mismatch"):
            m.audit_owner_run(run, obj)
        path.write_text(path.read_text().replace("# changed\n", ""))
        receipt = run / "99_evidence_sha256.txt"
        receipt.write_text(receipt.read_text() + "0"*64 + "  fake\n")
        with self.assertRaisesRegex(m.EvidenceRejected, "unexpected"):
            m.audit_owner_run(run, obj)

    def test_synthetic_receipt_rejects_missing_or_symlinked_source(self):
        run, obj = self.fake_native_originals()
        file = run / "output/12_d3a_fan_a12.xdc"
        renamed = run / "output/other.xdc"
        file.rename(renamed)
        file.symlink_to(renamed)
        with self.assertRaisesRegex(m.EvidenceRejected, "symlinked"):
            m.audit_owner_run(run, obj)

    def test_policy_source_is_abstract_not_connected_to_hardware(self):
        src = TB.read_text()
        self.assertIn("ABSTRACT PS/LINUX release policy testbench ONLY", src)
        self.assertIn("No CDC, PS ATB4, AIB13, AXI hardware", src)
        self.assertIn("independent_prerequisites", src)
        self.assertIn("first normal", src)
        for illegal in ("/dev/mem", "/dev/uio", "program_hw_devices",
                        "write_bitstream", "xmutil ", "connect_bd_intf_net"):
            self.assertNotIn(illegal, src)
        gate = GATE.read_text()
        for illegal in ("subprocess.run", "os.system", "program_hw_devices",
                        "write_bitstream", "/dev/mem", "/dev/uio"):
            self.assertNotIn(illegal, gate)

    @unittest.skipUnless(shutil.which("iverilog") and shutil.which("vvp"),
                         "Icarus required: offline policy simulation must not silently PASS")
    def test_native_icarus_d3b_one_shot_release_policy_and_negative(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "d3b_policy.vvp"
            proc = subprocess.run(
                ["iverilog", "-g2012", "-s",
                 "tb_m08_d3b_ps_linux_release_policy",
                 "-o", str(target), str(TB)],
                capture_output=True, text=True, timeout=90, check=False)
            self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
            self.assertEqual(proc.stderr.strip(), "")
            run = subprocess.run(["vvp", str(target)],
                                 capture_output=True, text=True, timeout=30, check=False)
            self.assertEqual(run.returncode, 0, run.stdout + "\n" + run.stderr)
            self.assertEqual(run.stderr.strip(), "")
            self.assertNotIn("FATAL", run.stdout)
            for marker in MARKERS:
                self.assertEqual(run.stdout.splitlines().count(marker), 1,
                                 "missing/duplicate: " + marker + "\n" + run.stdout)


if __name__ == "__main__":
    unittest.main()
