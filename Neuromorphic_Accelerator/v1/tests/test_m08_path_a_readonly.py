"""Path A Linux-managed KV260 discovery ONLY; CI never reaches a board."""
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
BOARD = ROOT / "scripts/m08_kv260_path_a_readonly.sh"
PC = ROOT / "scripts/run_m08_path_a_readonly_pc.sh"


class M08PathAReadOnlyTests(unittest.TestCase):
    def test_safe_command_contract(self):
        board = BOARD.read_text()
        pc = PC.read_text()
        operative = "\n".join(
            row for row in board.splitlines()
            if row.strip() and not row.lstrip().startswith("#")
        )
        for s in ("M08_PATH_A_LINUX_READ_ONLY_BEGIN",
                  "M08_PATH_A_LINUX_READ_ONLY_END_NO_FPGA_CHANGES",
                  "dfx-mgr", "fancontrol", "/sys/class/fpga_manager/",
                  "sudo -n xmutil listapps", "/proc/iomem",
                  "/sys/class/uio/", "/lib/firmware/xilinx"):
            self.assertIn(s, operative)
        for prohibited in ("xmutil unloadapp", "xmutil loadapp",
                           "program_hw_devices", "mwr ", "mrd ", "/dev/mem",
                           "devmem ", "fw_setenv", "flashcp ", "rm -rf",
                           "systemctl stop", "systemctl restart",
                           "systemctl disable", "fpgautil ", "sudo bash",
                           "bootgen ", "mount ", "dtc -I", "set_property"):
            self.assertNotIn(prohibited, operative)
        self.assertIn("StrictHostKeyChecking=ask", pc)
        self.assertIn("mktemp -d", pc)
        self.assertIn("04_evidence_sha256.txt", pc)
        self.assertIn("M08_PATH_A_READONLY_CAPTURED_NOT_DEPLOYMENT_APPROVAL", pc)
        for prohibited in ("xmutil unloadapp", "xmutil loadapp",
                           "program_hw_devices", "/dev/mem", "devmem ",
                           "flashcp ", "sudo ", "rm -rf",
                           "systemctl stop", "systemctl restart"):
            self.assertNotIn(prohibited, "\n".join(
                row for row in pc.splitlines()
                if row.strip() and not row.lstrip().startswith("#")
            ))

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_scripts_parse(self):
        for script in (BOARD, PC):
            p = subprocess.run(["bash", "-n", str(script)],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_reject_malformed_target_before_network_or_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            env = os.environ.copy()
            env["M08_EVIDENCE_BASE"] = td
            p = subprocess.run(["bash", str(PC), "ubuntu@kria;true"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 2)
            self.assertEqual(list(Path(td).iterdir()), [])

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_pc_capture_uses_mock_ssh_and_hashes_all_originals(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bindir = base / "bin"
            evidence = base / "evidence"
            bindir.mkdir()
            evidence.mkdir()
            fake = bindir / "ssh"
            fake.write_text(
                "#!/usr/bin/env bash\n"
                "cat >/dev/null\n"
                "echo M08_PATH_A_LINUX_READ_ONLY_BEGIN\n"
                "echo M08_PROBE_BEGIN\\|model | sed 's/\\\\\\\\|/|/'\n"
                "echo 'Kria K26'\n"
                "echo 'M08_PROBE_END|model|rc=0'\n"
                "echo M08_PATH_A_LINUX_READ_ONLY_END_NO_FPGA_CHANGES\n"
            )
            fake.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["M08_EVIDENCE_BASE"] = str(evidence)
            p = subprocess.run(["bash", str(PC), "ubuntu@kria"],
                               env=env, capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("NOT_DEPLOYMENT_APPROVAL", p.stdout)
            folders = list(evidence.iterdir())
            self.assertEqual(len(folders), 1)
            d = folders[0]
            self.assertIn("ssh_exit_status=0", (d / "03_exit_status.txt").read_text())
            self.assertIn("M08_PATH_A_LINUX_READ_ONLY_BEGIN",
                          (d / "01_board_stdout.log").read_text())
            p2 = subprocess.run(["sha256sum", "-c", "04_evidence_sha256.txt"],
                                cwd=d, capture_output=True, text=True)
            self.assertEqual(p2.returncode, 0, p2.stdout+p2.stderr)

    @unittest.skipUnless(shutil.which("bash"), "bash unavailable")
    def test_capture_failure_is_preserved_and_not_accepted(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            bindir = base / "bin"
            evidence = base / "evidence"
            bindir.mkdir()
            evidence.mkdir()
            fake = bindir / "ssh"
            fake.write_text("#!/usr/bin/env bash\nexit 12\n")
            fake.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(bindir) + os.pathsep + env["PATH"]
            env["M08_EVIDENCE_BASE"] = str(evidence)
            p = subprocess.run(["bash", str(PC), "ubuntu@kria"],
                               env=env, capture_output=True, text=True)
            self.assertNotEqual(p.returncode, 0)
            self.assertIn("CAPTURE_INCOMPLETE", p.stderr)
            folders = list(evidence.iterdir())
            self.assertEqual(len(folders), 1)
            self.assertIn("ssh_exit_status=12",
                          (folders[0] / "03_exit_status.txt").read_text())


if __name__ == "__main__":
    unittest.main()
