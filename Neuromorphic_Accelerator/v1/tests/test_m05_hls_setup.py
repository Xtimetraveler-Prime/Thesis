"""M05 offline HLS manifest and runner contract tests; these DO NOT run Vitis."""
from __future__ import annotations

import re
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HLS = ROOT / "hls"
RUNNER = HLS / "m05_stream_eval/run_m05_offline_hls.sh"
CONFIGS = {
    "stream": (HLS / "m05_stream_eval/m05_hls_config.cfg",
               "m05_stream_eval"),
    "stateful": (HLS / "m05_stateful/m05_stateful_hls_config.cfg",
                 "m05_stateful_service"),
    "accumulator": (HLS / "m05_accumulator/m05_accum_hls_config.cfg",
                    "m05_event_accumulator"),
}


def parse_config(path):
    data = {}
    section = None
    for raw in path.read_text(encoding="utf8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].lower()
            continue
        key, value = line.split("=", 1)
        data.setdefault((section, key.strip()), []).append(value.strip())
    return data


class M05HLSSetupTests(unittest.TestCase):
    def test_three_isolated_k26_configs_have_documented_2025_2_keys(self):
        for name, (path, top) in CONFIGS.items():
            with self.subTest(kernel=name):
                data = parse_config(path)
                self.assertEqual(data[(None, "part")],
                                 ["xck26-sfvc784-2LV-c"])
                self.assertEqual(data[("hls", "syn.top")], [top])
                self.assertEqual(data[("hls", "package.output.format")], ["rtl"])
                self.assertEqual(data[("hls", "flow_target")], ["vivado"])
                self.assertEqual(data[("hls", "clock")], ["10ns"])
                self.assertEqual(data[("hls", "clock_uncertainty")], ["12%"])
                self.assertNotIn(("hls", "syn.output.format"), data)
                self.assertEqual(data[("hls", "relative_roots")], ["file/../.."])

    def test_configs_reference_real_sources_and_independent_benches(self):
        for name, (path, _) in CONFIGS.items():
            with self.subTest(kernel=name):
                data = parse_config(path)
                self.assertEqual(len(data[("hls", "tb.file")]), 1)
                self.assertTrue(data[("hls", "syn.file")])
                for source in data[("hls", "syn.file")] + data[("hls", "tb.file")]:
                    self.assertTrue((ROOT / source).is_file(),
                                    f"missing {source} for {name}")
                self.assertEqual(data[("hls", "csim.clean")], ["true"])

    def test_offline_runner_bash_syntax_help_and_bad_flags(self):
        ok = subprocess.run(["bash", "-n", str(RUNNER)], capture_output=True, text=True)
        self.assertEqual(ok.returncode, 0, ok.stderr)
        help_run = subprocess.run(["bash", str(RUNNER), "--help"],
                                  capture_output=True, text=True)
        self.assertEqual(help_run.returncode, 0)
        self.assertIn("--stateful", help_run.stdout)
        self.assertIn("--accumulator", help_run.stdout)
        self.assertIn("--cosim", help_run.stdout)
        for flags in (["--bad"], ["--stream", "--stateful"],
                      ["--cosim", "--synth"]):
            with self.subTest(flags=flags):
                fail = subprocess.run(["bash", str(RUNNER), *flags],
                                      capture_output=True, text=True)
                self.assertEqual(fail.returncode, 2)

    def test_offline_runner_never_invokes_board_or_old_v3_scripts(self):
        text = RUNNER.read_text(encoding="utf8")
        for operation in (r"\bxsdb\b", r"\bhw_server\b",
                          r"\bopen_hw\b", r"\bprogram_hw_devices\b",
                          r"\bbootgen\b", r"\bpetalinux-build\b",
                          r"run_synth_cosim\.sh", r"run_csim\.sh"):
            with self.subTest(operation=operation):
                self.assertNotRegex(text, operation)
        self.assertIn("mkdir \"$OUT\"", text)
        self.assertNotIn("rm -rf", text)
        self.assertIn("trap finish EXIT", text)
        self.assertIn("result.txt", text)
        self.assertIn("hls_effective_config.cfg", text)
        self.assertIn("prepare_hls_config.py", text)
        self.assertIn("--config \"$EFFECTIVE_CONFIG\"", text)

    def test_three_tops_are_distinct_and_syn_top_always_matches(self):
        source_stream = (HLS / "m05_stream_eval/m05_stream.cpp").read_text()
        source_state = (HLS / "m05_stateful/m05_stateful.cpp").read_text()
        self.assertIn("m05_stream_eval(", source_stream)
        self.assertNotIn("m05_stateful_service(", source_stream)
        self.assertIn("m05_stateful_service(", source_state)
        self.assertIn("BIND_STORAGE variable=voltages", source_state)
        self.assertIn("M05_MEM_DUPLICATE_TICK", source_state)
        source_acc = (HLS / "m05_accumulator/m05_accumulator.cpp").read_text()
        self.assertIn("m05_event_accumulator(", source_acc)
        self.assertIn("M05_ACC_EVENT_OVERFLOW", source_acc)
        runner = RUNNER.read_text()
        for _, top in CONFIGS.values():
            self.assertIn(f'TOP="{top}"', runner)


if __name__ == "__main__":
    unittest.main()
