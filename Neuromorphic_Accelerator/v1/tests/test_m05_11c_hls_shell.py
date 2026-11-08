"""M05.11c host-only synthetic transcript tests; not generated HLS XSim."""
from __future__ import annotations

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from neuromorphic_accelerator_v1.m05_dma_frame import (
    build_fake_dma_packet_for_test
)
from neuromorphic_accelerator_v1.m05_trace_commit import RollingTraceRow
from m05_11c_replay import replay_real_xsim_log

SID0 = 0x0102030405060708
SID1 = 0x1020304050607080
PASS = ("PASS: M05.11c REAL HLS RTL + AXIL shell + 3 ingress + trace TLAST; "
        "success=24/status0; failure=8/status4; committed=24+0; "
        "output_stalls=200; HLS_output_stalls=190")


def expected_rows(run: int) -> tuple[RollingTraceRow, ...]:
    ticks = 12 if run == 0 else 4
    return tuple(
        RollingTraceRow(tick, neuron, 0,
                        int((tick == 0 and neuron == 0)
                            or (run == 0 and tick == 8 and neuron == 1)),
                        int((tick == 0 and neuron == 0)
                            or (run == 0 and tick == 8 and neuron == 1)),
                        int(tick == 0 or (run == 0 and tick == 8)))
        for tick in range(ticks) for neuron in range(2)
    )


def raw_log() -> str:
    transcript = []
    for run, sid, status in ((0, SID0, 0), (1, SID1, 4)):
        rows = expected_rows(run)
        pkt = build_fake_dma_packet_for_test(
            rows, status=status, session_id=sid
        )
        for offset in range(0, len(pkt), 32):
            raw = int.from_bytes(pkt[offset:offset+32], "little")
            last = int(offset + 32 == len(pkt))
            transcript.append(
                f"M05_11C_DMA run={run} data={raw:064x} "
                f"last={last} keep=ffffffff"
            )
        transcript.append(
            f"M05_11C_FINAL run={run} status={status} rows={len(rows)} "
            f"committed={len(rows) if status == 0 else 0} "
            f"session={sid:016x} tlast=1"
        )
        transcript.append(
            f"M05_11C_COMMIT run={run} "
            f"accepted_rows={len(rows) if status == 0 else 0}"
        )
    transcript.append(PASS)
    return "\n".join(transcript) + "\n"


class M0511CRealHLSBoundaryTests(unittest.TestCase):
    def test_full_synthetic_raw_dma_transcript(self):
        self.assertEqual(replay_real_xsim_log(raw_log()), (24, 0))

    def test_missing_tlast_is_rejected(self):
        src = raw_log()
        for run in (0, 1):
            footer = next(x for x in src.splitlines()
                          if x.startswith(f"M05_11C_DMA run={run} ")
                          and "last=1" in x)
            with self.subTest(run=run):
                with self.assertRaises(ValueError):
                    replay_real_xsim_log(src.replace(
                        footer, footer.replace("last=1", "last=0")))

    def test_wrong_session_footer_is_rejected(self):
        src = raw_log()
        with self.assertRaises(ValueError):
            replay_real_xsim_log(src.replace(
                f"session={SID1:016x}", f"session={SID0:016x}"))

    def test_failed_run_must_not_commit_partial_rows(self):
        with self.assertRaises(ValueError):
            replay_real_xsim_log(raw_log().replace(
                "M05_11C_COMMIT run=1 accepted_rows=0",
                "M05_11C_COMMIT run=1 accepted_rows=8"
            ))

    def test_missing_duplicate_or_early_final_rejected(self):
        src = raw_log()
        marker = next(x for x in src.splitlines()
                      if x.startswith("M05_11C_FINAL run=0"))
        for bad in (src.replace(marker + "\n", ""),
                    src.replace(marker, marker + "\n" + marker),
                    marker + "\n" + src):
            with self.subTest(bad=bad[-80:]):
                with self.assertRaises(ValueError):
                    replay_real_xsim_log(bad)

    def test_wrong_tkeep_and_trace_padding_rejected(self):
        src = raw_log()
        with self.assertRaises(ValueError):
            replay_real_xsim_log(src.replace(
                "keep=ffffffff", "keep=00ffffff", 1))
        first = src.splitlines()[0]
        raw = first.split("data=")[1][:64]
        corrupted = (int(raw, 16) | (1 << 192))
        with self.assertRaises(ValueError):
            replay_real_xsim_log(src.replace(
                first, first.replace(raw, f"{corrupted:064x}")
            ))

    def test_deleted_or_extra_256bit_handshake_is_rejected(self):
        lines = raw_log().splitlines()
        for bad in (lines[1:], [lines[0]] + lines):
            with self.assertRaises(ValueError):
                replay_real_xsim_log("\n".join(bad))

    def test_recurrent_spike_and_raw_hls_word_are_checked(self):
        src = raw_log()
        # Success run's tick8 neuron1 is at 8*2+1 == record index17.
        original = src.splitlines()[17].split("data=")[1][:64]
        corrupted = int(original, 16) ^ (1 << (128 + 8))
        with self.assertRaises(ValueError):
            replay_real_xsim_log(src.replace(
                original, f"{corrupted:064x}", 1
            ))

    def test_wrong_status_in_raw_terminal_beat_is_rejected(self):
        src = raw_log()
        final = next(x for x in src.splitlines()
                     if x.startswith("M05_11C_DMA run=0") and "last=1" in x)
        original = final.split("data=")[1][:64]
        corrupted = int(original, 16) | (4 << 96)
        with self.assertRaises(ValueError):
            replay_real_xsim_log(src.replace(
                original, f"{corrupted:064x}", 1
            ))

    def test_missing_sim_pass_or_fatal_is_rejected(self):
        src = raw_log()
        for bad in (src.replace(PASS, ""),
                    src + "Fatal: M05_11C_FAIL injected\n",
                    src + PASS + "\n"):
            with self.assertRaises(ValueError):
                replay_real_xsim_log(bad)

    def test_cli_reads_only_and_never_mutates_logs(self):
        with tempfile.TemporaryDirectory(prefix="m05_11c_native_") as td:
            p = Path(td) / "04_xsim.log"
            src = raw_log()
            p.write_text(src)
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/m05_11c_replay.py"),
                 "--xsim-log", str(p)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("accepted=24+0", result.stdout)
            self.assertEqual(p.read_text(), src)

    def test_cli_missing_real_log_fails_closed(self):
        with tempfile.TemporaryDirectory(prefix="m05_11c_native_") as td:
            result = subprocess.run(
                [sys.executable, str(ROOT / "scripts/m05_11c_replay.py"),
                 "--xsim-log", str(Path(td) / "missing")],
                capture_output=True, text=True,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("ERROR: M05.11c real XSim", result.stderr)

    def test_operator_script_uses_real_hls_source_and_ram_assets(self):
        src = (ROOT / "scripts/run_m05_11c_hls_shell_xsim.sh").read_text()
        for term in (
            "xck26-sfvc784-2LV-c", "m05_rolling_replay.v",
            "hls/m05_rolling/m05_rolling.cpp", "source_sha256.txt",
            "m05_axis_regmap.py", "m05_rtl_meminit.py",
            "tb_m05_11c_real_hls_shell.sv", "m05_11_stream_shell.v",
            "m05_11c_replay.py", "05_dma_frame_replay.log",
            "M05_11C_FAIL", "result.txt", "--onfinish quit",
        ):
            with self.subTest(term=term):
                self.assertIn(term, src)
        self.assertNotIn("program_hw_devices", src)
        self.assertNotIn("vitis-run --mode hls", src)

    def test_sv_connects_two_real_axi_banks_without_modifying_hls(self):
        sv = (ROOT / "rtl/m05_11/tb_m05_11c_real_hls_shell.sv").read_text()
        for term in (
            "m05_rolling_replay hls_dut",
            "m05_11_stream_shell shell_dut",
            "SID_SUCCESS", "SID_FAILURE", "M05_11C_DMA",
            "M05_11C_FINAL", "setup_bridge(SID_FAILURE,3)",
            "if(hw_status!==4)", "c_write(8'h00,4,2)",
            "trace_dma_tlast", "s2mm_stall_cycles", "prior_stall",
        ):
            with self.subTest(term=term):
                self.assertIn(term, sv)


if __name__ == "__main__":
    unittest.main()
