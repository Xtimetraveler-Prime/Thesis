"""SYNTHETIC-ONLY G3 AMD real IP evidence audit tests; no vendor execution.

The real runner requires actual Vivado 2025.2, creates a new scratch
project, and never edits original D3 or programs the board.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from m06_g3_amd_dwc_evidence_audit import audit, IPS, REQUIRED, SOURCE_NAMES


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(base: Path) -> Path:
    out = base / "m06_g3_real_amd_dwc_SYNTHETIC_ONLY"
    out.mkdir()
    (out / "vivado_version.txt").write_text("Vivado v2025.2 (64-bit)\n")
    (out / "01_vivado_amd_dwc.log").write_text(
        "Vivado v2025.2\nM06_G3_REAL_AMD_DWC_IP_GENERATED_NOT_CONNECTED\n")
    (out / "commit.txt").write_text("f"*40 + "\n")
    rows = [
        "status\tORIGINAL_AMD_IP_GENERATED_NOT_CONNECTED",
        "tool_version\t2025.2",
        "part\txck26-sfvc784-2LV-c",
    ]
    for ip, role in IPS.items():
        rows.append("ip\t"+ip)
        rows.append(ip+".CONFIG.READ_WRITE_MODE\t"+role)
        for key, val in REQUIRED.items():
            rows.append(ip+"."+key+"\t"+val)
        xci_expected = (out / "new_scratch_project" / "m06_g3_amd_dwc.srcs" /
                        "sources_1" / "ip" / ip / (ip+".xci"))
        rows.append(ip+".xci_source_path\t"+str(xci_expected))
    # The real tool prints one "ip" row per generated IP, but the audit
    # disallows duplicate keys. A unique row is enough for this fixture:
    rows = [row for row in rows if not row.startswith("ip\t")]
    rows += [
        "ip_count\t2",
        "original_smartconnect_connected\tFALSE",
        "generated_hls_connected\tFALSE",
        "physical_DDR\tNOT_ACCESSED",
        "m06_complete\tFALSE",
    ]
    (out / "02_amd_dwc_configuration.tsv").write_text("\n".join(rows)+"\n")
    project = out / "new_scratch_project"
    project.mkdir()
    xci = []
    for ip in IPS:
        path = (project / "m06_g3_amd_dwc.srcs" / "sources_1" /
                "ip" / ip / (ip+".xci"))
        path.parent.mkdir(parents=True)
        path.write_text("SYNTHETIC DATA, NOT AMD VIVADO IP\n")
        xci.append(path)
    sources = []
    for path in SOURCE_NAMES:
        digest=hashlib.sha256(path.encode()).hexdigest()
        sources.append(digest+"  "+path)
    original = "\n".join(sources)+"\n"
    (out / "source_before_sha256.txt").write_text(original)
    (out / "source_after_sha256.txt").write_text(original)
    (out / "result.txt").write_text("exit_status=0\n")
    (out / "03_real_amd_dwc_xci_paths.txt").write_text(
        "\n".join(str(p) for p in sorted(xci))+"\n")
    (out / "04_real_amd_dwc_xci_sha256.txt").write_text(
        "\n".join(sha(p)+"  "+str(p) for p in sorted(xci))+"\n")
    (out / "scope.txt").write_text("genuine_vendor_converter_status=GENERATED_ONLY\n")
    return out


class M06AMDDualConverterEvidenceSyntheticTests(unittest.TestCase):
    def test_positive_mock_only_never_connected_claim(self):
        with tempfile.TemporaryDirectory() as temp:
            output=fixture(Path(temp))
            report=audit(output)
            self.assertEqual(report["widths"],{"hls_si":32,"vendor_mi":256})
            self.assertEqual(report["address_width"],32)
            self.assertFalse(report["actual_amd_width_ip_xsim"])
            self.assertFalse(report["hls_generated_rtl_bound"])
            self.assertFalse(report["m06_complete"])
            self.assertFalse(report["pre_finalize_audit"])

    def test_positive_pre_finalize_before_exit_trap(self):
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            (out / "result.txt").unlink()
            (out / "source_after_sha256.txt").unlink()
            (out / "03_real_amd_dwc_xci_paths.txt").unlink()
            (out / "04_real_amd_dwc_xci_sha256.txt").unlink()
            result=audit(out,pre_finalize=True)
            self.assertTrue(result["pre_finalize_audit"])
            with self.assertRaises((OSError,ValueError)):
                audit(out)

    def test_negative_wrong_role_data_width_id_or_clock_part(self):
        for original, changed, message in (
            ("m06_g3_read_dwc.CONFIG.READ_WRITE_MODE\tREAD_ONLY",
             "m06_g3_read_dwc.CONFIG.READ_WRITE_MODE\tWRITE_ONLY", "role"),
            ("m06_g3_write_dwc.CONFIG.MI_DATA_WIDTH\t256",
             "m06_g3_write_dwc.CONFIG.MI_DATA_WIDTH\t128", "parameter"),
            ("m06_g3_read_dwc.CONFIG.SI_ID_WIDTH\t1",
             "m06_g3_read_dwc.CONFIG.SI_ID_WIDTH\t0", "parameter"),
            ("part\txck26-sfvc784-2LV-c",
             "part\tother-fpga", "target"),
        ):
            with tempfile.TemporaryDirectory() as temp, self.subTest(reason=message):
                out=fixture(Path(temp))
                p=out/"02_amd_dwc_configuration.tsv"
                p.write_text(p.read_text().replace(original,changed))
                with self.assertRaisesRegex(ValueError,message):
                    audit(out)

    def test_negative_missing_xci_or_modified_xci_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            (out/"new_scratch_project/m06_g3_amd_dwc.srcs/sources_1/ip/m06_g3_write_dwc/m06_g3_write_dwc.xci").unlink()
            with self.assertRaisesRegex(ValueError,"exactly two"):
                audit(out)
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            (out/"new_scratch_project/m06_g3_amd_dwc.srcs/sources_1/ip/m06_g3_write_dwc/m06_g3_write_dwc.xci").write_text("CHANGED\n")
            with self.assertRaisesRegex(ValueError,"digests altered"):
                audit(out)

    def test_negative_failed_runner_mutated_script_or_late_vendor_error(self):
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            (out/"result.txt").write_text("exit_status=1\n")
            with self.assertRaisesRegex(ValueError,"runner returned failure"):
                audit(out)
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            (out/"source_after_sha256.txt").write_text("TAMPERED\n")
            with self.assertRaisesRegex(ValueError,"mutated"):
                audit(out)
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            with (out/"01_vivado_amd_dwc.log").open("a") as log:
                log.write("ERROR: late vendor failure\n")
            with self.assertRaisesRegex(ValueError,"error or critical warning"):
                audit(out)

    def test_negative_xci_readback_cannot_point_to_old_original_d3(self):
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            p=out/"02_amd_dwc_configuration.tsv"
            original=(out/"new_scratch_project/m06_g3_amd_dwc.srcs/sources_1/"
                      "ip/m06_g3_read_dwc/m06_g3_read_dwc.xci")
            p.write_text(p.read_text().replace(
                str(original), str(out/"OLD_UNTRUSTED_D3.xci")))
            with self.assertRaisesRegex(ValueError, "XCI path readback"):
                audit(out)

    def test_pure_tcl_locator_rejects_missing_and_wrong_instance_without_vivado(self):
        if not shutil.which("tclsh"):
            self.skipTest("tclsh unavailable")
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            root=out/"new_scratch_project"
            script=Path(temp)/"test_real_locator_synthetic.tcl"
            locator=ROOT/"scripts/m06_g3_xci_path.tcl"
            script.write_text(
                "source {"+str(locator)+"}\n"
                "set base {"+str(root)+"}\n"
                "set expected [file join $base m06_g3_amd_dwc.srcs "
                    "sources_1 ip m06_g3_read_dwc m06_g3_read_dwc.xci]\n"
                "if {[m06_g3_xci_path $base m06_g3_read_dwc] ne "
                    "[file normalize $expected]} {exit 10}\n"
                "if {![catch {m06_g3_xci_path $base m06_g3_wrong_dwc}]} {exit 11}\n"
                "set wrong [file join $base m06_g3_amd_dwc.srcs "
                    "sources_1 ip m06_g3_write_dwc m06_g3_write_dwc.xci]\n"
                "file delete $wrong\n"
                "if {![catch {m06_g3_xci_path $base m06_g3_write_dwc}]} {exit 12}\n"
                "puts M06_G3_SYNTHETIC_REAL_XCI_PATH_PASS\n")
            run=subprocess.run(["tclsh",str(script)],capture_output=True,text=True,
                               timeout=15)
            self.assertEqual(run.returncode,0,run.stderr)
            self.assertIn("M06_G3_SYNTHETIC_REAL_XCI_PATH_PASS",run.stdout)

    def test_negative_run_status_cannot_claim_connected(self):
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            p=out/"02_amd_dwc_configuration.tsv"
            p.write_text(p.read_text().replace(
                "generated_hls_connected\tFALSE","generated_hls_connected\tTRUE"))
            with self.assertRaisesRegex(ValueError,"false integration"):
                audit(out)
        with tempfile.TemporaryDirectory() as temp:
            out=fixture(Path(temp))
            (out/"scope.txt").write_text("genuine_vendor_converter_status=CONNECTED\n")
            with self.assertRaisesRegex(ValueError,"false converter integration"):
                audit(out)

    def test_bash_syntax_only_does_not_run_vivado(self):
        result=subprocess.run(
            ["bash","-n",str(ROOT/"scripts/run_m06_g3_amd_dwc_ip.sh")],
            capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        # Tcl's info complete checks brace nesting; NOT Tcl execution.
        if shutil.which("tclsh"):

            check=subprocess.run(["tclsh",str(ROOT/"scripts/m06_g3_generate_amd_dwc.tcl")],
              capture_output=True,text=True,timeout=15)
            # This is an actual tclsh execution, which must reject
            # non-Vivado with an error rather than creating any project.
            self.assertNotEqual(check.returncode,0)


if __name__ == "__main__":
    unittest.main()
