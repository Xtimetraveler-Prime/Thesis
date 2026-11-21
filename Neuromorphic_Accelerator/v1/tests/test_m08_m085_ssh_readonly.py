"""M08.5 SSH-only read-only KV260 inventory: source policy and PC mock tests.

The subprocess is a MOCK SSH executable. No test connects to any board,
and a successful mock says nothing about live Linux ownership or DDR.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "scripts/run_m08_m085_ssh_readonly_pc.sh"
BOARD = ROOT / "scripts/m08_m085_ssh_linux_probe.sh"
TARGET = "ubuntu@10.42.0.135"


class M085SSHOnlyInventory(unittest.TestCase):
    def test_board_source_has_no_mutating_or_mmio_access(self):
        s = BOARD.read_text()
        self.assertIn("M08_5_SSH_READONLY_BEGIN", s)
        self.assertIn("M08_5_SSH_READONLY_END_NO_DMA_OR_BOARD_CHANGES", s)
        self.assertIn('[[ "$MODEL" == *KV260* ]]', s)
        for expected in (
            "/proc/device-tree/model", "/sys/class/dma_heap",
            "/sys/kernel/iommu_groups", "/sys/bus/platform/devices",
            "dma-ranges", "iommus", "driver_bound", "SECTION_END",
        ):
            if expected == "driver_bound":
                self.assertIn("DRIVER_UNBOUND_OR_UNKNOWN", s)
            else:
                self.assertIn(expected, s)
        executable = "\n".join(line for line in s.splitlines()
                               if not line.lstrip().startswith("#"))
        for forbidden in (
            "program_hw_devices", "xmutil", "modprobe ", "insmod ",
            "rmmod ", "sudo -", "/dev/mem", "/dev/uio", "fpgautil ",
            "systemctl restart", "systemctl stop", "dma_alloc_coherent(",
            "tee /sys/", "echo > /sys/", "reboot ",
        ):
            # The script's opening comments mention policy labels but not
            # dangerous command invocations.
            self.assertNotIn(forbidden, executable)

    def test_scripts_parse_and_pc_capture_ssh_is_strict(self):
        for p in (RUN, BOARD):
            cp = subprocess.run(["bash", "-n", str(p)],
                                capture_output=True, text=True, timeout=10)
            self.assertEqual(cp.returncode, 0, cp.stderr)
        s = RUN.read_text()
        for required in (
            "StrictHostKeyChecking=yes", "BatchMode=yes",
            "ConnectTimeout=12", "'bash -s'", "sha256sum",
            "mktemp -d", "timeout --signal=TERM",
            "M08_5_SSH_READONLY_CAPTURE_PASS_NOT_DMA_READY",
            "SECTION_END|dma_platform",
        ):
            self.assertIn(required, s)
        self.assertNotIn("StrictHostKeyChecking=no", s)
        self.assertNotIn("sshpass", s)
        self.assertNotIn("sudo ", s)

    def _invoke(self, mock_case: str, target: str = TARGET):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            evidence = root / "existing_parent"
            evidence.mkdir()
            mock_bin = root / "mockbin"
            mock_bin.mkdir()
            mock_ssh = mock_bin / "ssh"
            mock_ssh.write_text(
                "#!/bin/sh\n"
                "case \"$M085_TEST_SSH_CASE\" in\n"
                " success)\n"
                "  printf 'M08_5_SSH_READONLY_BEGIN\\n'\n"
                "  printf 'BOARD_MODEL=ZynqMP KV260 revB\\n'\n"
                "  printf 'SECTION_END|device_tree\\n'\n"
                "  printf 'SECTION_END|dma_platform\\n'\n"
                "  printf 'SECTION_END|safety_observation\\n'\n"
                "  printf 'M08_5_SSH_READONLY_END_NO_DMA_OR_BOARD_CHANGES\\n'\n"
                "  exit 0;;\n"
                " missing) printf 'M08_5_SSH_READONLY_BEGIN\\n'; exit 0;;\n"
                " wrong) printf 'M08_5_SSH_READONLY_BEGIN\\n"
                "BOARD_MODEL=Other\\n"
                "SECTION_END|device_tree\\n"
                "SECTION_END|dma_platform\\n"
                "SECTION_END|safety_observation\\n"
                "M08_5_SSH_READONLY_END_NO_DMA_OR_BOARD_CHANGES\\n'; exit 0;;\n"
                " failure) echo 'SSH session refused' >&2; exit 255;;\n"
                "esac\nexit 9\n"
            )
            mock_ssh.chmod(0o755)
            env = os.environ.copy()
            env["PATH"] = str(mock_bin) + os.pathsep + env.get("PATH", "")
            env["M08_EVIDENCE_BASE"] = str(evidence)
            env["M085_TEST_SSH_CASE"] = mock_case
            cp = subprocess.run(["bash", str(RUN), target], env=env,
                                capture_output=True, text=True, timeout=15)
            folders = list(evidence.glob("m08_m085_ssh_readonly_*"))
            if target != TARGET:
                self.assertEqual(folders, [])
                return cp, []
            self.assertEqual(len(folders), 1, cp.stdout + cp.stderr)
            out = folders[0]
            hashcheck = subprocess.run(
                ["sha256sum", "-c", "99_evidence_sha256.txt"],
                cwd=out, capture_output=True, text=True, timeout=10
            )
            self.assertEqual(hashcheck.returncode, 0, hashcheck.stdout + hashcheck.stderr)
            self.assertEqual(len((out / "99_evidence_sha256.txt").read_text().splitlines()), 5)
            self.assertIn("target="+TARGET, (out / "01_context.txt").read_text())
            self.assertTrue((out / "00_remote_source.sh").read_text().startswith("#!/usr/bin/env bash"))
            return cp, folders

    def test_successful_mock_capture_retains_originals_not_dma_authorization(self):
        cp, folders = self._invoke("success")
        self.assertEqual(cp.returncode, 0, cp.stderr)
        self.assertIn("CAPTURE_PASS_NOT_DMA_READY", cp.stdout)
        self.assertEqual(len(folders), 1)

    def test_bad_target_rejected_before_ssh(self):
        cp, _ = self._invoke("success", "ubuntu@192.0.2.10")
        self.assertEqual(cp.returncode, 2)
        self.assertNotIn("CAPTURE_PASS", cp.stdout)

    def test_missing_end_is_incomplete_preserves_original(self):
        cp, _ = self._invoke("missing")
        self.assertEqual(cp.returncode, 3)
        self.assertIn("INCOMPLETE_NOT_DMA_READY", cp.stderr)

    def test_wrong_board_metadata_is_incomplete(self):
        cp, _ = self._invoke("wrong")
        self.assertEqual(cp.returncode, 3)

    def test_ssh_failure_is_not_success_and_original_stderr_saved(self):
        cp, _ = self._invoke("failure")
        self.assertEqual(cp.returncode, 3)


if __name__ == "__main__":
    unittest.main()
