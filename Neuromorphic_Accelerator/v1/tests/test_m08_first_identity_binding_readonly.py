"""M08.2b.3 read-only live driver-ownership preflight; fake SSH only."""
from hashlib import sha256
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
PC = ROOT / "scripts/run_m08_identity_binding_readonly_pc.sh"
BOARD = ROOT / "scripts/m08_kv260_identity_binding_readonly.sh"


class TestM08IdentityBindingReadonly(unittest.TestCase):
    def test_bash_syntax_and_no_live_mmio_or_mutations(self):
        for file in (PC, BOARD):
            subprocess.run(["bash", "-n", str(file)], check=True, timeout=10)
        board = BOARD.read_text()
        pc = PC.read_text()
        for forbidden in (
            "xmutil loadapp", "xmutil unloadapp", "modprobe ",
            "systemctl stop", "systemctl restart", "program_hw_devices",
            "fpga_manager/fpga0/firmware", "dd if=", "/dev/mem",
            "devmem2", "mmap.mmap", "write32(",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, board + pc)
        self.assertIn('basename "$DRIVER"', board)
        self.assertIn("uio_pdrv_genirq", board)
        self.assertIn("M08_IDENTITY_BINDING_PREFLIGHT_PASS_NO_MMIO", board)
        self.assertIn("99_evidence_sha256.txt", pc)

    def test_wrong_target_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            env = {**os.environ, "M08_EVIDENCE_BASE": d}
            p = subprocess.run(["bash", str(PC), "ubuntu@192.0.2.1"],
                               env=env, cwd=ROOT, capture_output=True,
                               text=True, timeout=10)
            self.assertEqual(p.returncode, 2)
            self.assertIn("usage", p.stderr)
            self.assertEqual(list(Path(d).iterdir()), [])

    def fake_ssh(self, base: Path, success: bool) -> subprocess.CompletedProcess:
        bindir = base / "bin"
        bindir.mkdir()
        fake = bindir / "ssh"
        if success:
            payload = (
                "#!/bin/sh\n"
                "cat >/dev/null\n"
                "echo M08_IDENTITY_BINDING_PREFLIGHT_BEGIN_READ_ONLY\n"
                "echo 'M08_VERIFIED_BINDING|m08-identity|uio4|0xa0000000|0x1000|/kernel/uio_pdrv_genirq'\n"
                "echo 'M08_VERIFIED_BINDING|m08-page|uio5|0xa0001000|0x1000|/kernel/uio_pdrv_genirq'\n"
                "echo M08_IDENTITY_BINDING_PREFLIGHT_PASS_NO_MMIO\n"
            )
        else:
            payload = "#!/bin/sh\ncat >/dev/null\necho 'synthetic failure' >&2\nexit 255\n"
        fake.write_text(payload)
        fake.chmod(0o755)
        env = {**os.environ, "PATH": str(bindir) + os.pathsep + os.environ["PATH"],
               "M08_EVIDENCE_BASE": str(base)}
        return subprocess.run(
            ["bash", str(PC), "ubuntu@10.42.0.135"], env=env, cwd=ROOT,
            capture_output=True, text=True, timeout=15,
        )

    def test_success_preserves_five_original_facts_plus_sha_ledger(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = self.fake_ssh(base, True)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertIn("METADATA_CAPTURE_PASS_NOT_MMIO_APPROVAL", p.stdout)
            folder = Path(re.search(r"M08_IDENTITY_BINDING_EVIDENCE_DIR=(\S+)", p.stdout)[1])
            self.assertEqual(folder.parent, base)
            covered = set()
            for row in (folder / "99_evidence_sha256.txt").read_text().splitlines():
                digest, name = row.split("  ", 1)
                self.assertEqual(digest, sha256((folder / name).read_bytes()).hexdigest())
                covered.add(name)
            self.assertEqual(covered, {
                "00_board_probe_source.sh", "00_context.txt", "01_original_stdout.log",
                "02_original_stderr.log", "03_ssh_exit.txt",
            })
            self.assertEqual((folder / "03_ssh_exit.txt").read_text(), "exit_status=0\n")

    def test_failed_ssh_is_not_a_pass_and_keeps_original_logs(self):
        with tempfile.TemporaryDirectory() as d:
            base = Path(d)
            p = self.fake_ssh(base, False)
            self.assertEqual(p.returncode, 3)
            folder = Path(re.search(r"M08_IDENTITY_BINDING_EVIDENCE_DIR=(\S+)", p.stdout)[1])
            self.assertIn("synthetic failure", (folder / "02_original_stderr.log").read_text())
            self.assertEqual((folder / "03_ssh_exit.txt").read_text(), "exit_status=255\n")
            self.assertTrue((folder / "99_evidence_sha256.txt").is_file())


if __name__ == "__main__":
    unittest.main()
