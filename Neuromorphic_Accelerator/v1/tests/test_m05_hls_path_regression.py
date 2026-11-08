"""Regression for 2026-11-08 Vitis HLS 200-627 missing C testbench.

All tests run WITHOUT Vitis or board: the subprocess 'vitis-run' is a STUB
that chdirs into an evidence work directory and validates the effective INI.
No STUB PASS is an actual HLS simulation, synthesis or RTL result.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HLS = ROOT / "hls"
sys.path.insert(0, str(HLS / "m05_stream_eval"))
from prepare_hls_config import prepare  # noqa: E402


CONFIGS = {
    "stream": ("m05_stream_eval/m05_hls_config.cfg", "m05_stream_eval"),
    "stateful": ("m05_stateful/m05_stateful_hls_config.cfg", "m05_stateful_service"),
    "accumulator": ("m05_accumulator/m05_accum_hls_config.cfg", "m05_event_accumulator"),
    "integrated": ("m05_integrated/m05_integrated_hls_config.cfg",
                   "m05_integrated_replay"),
}

STUB = r"""#!/usr/bin/env python3
# STUB ONLY. Tests Vitis-like chdir, not design behavior.
import os
from pathlib import Path
import shlex
import sys

args = sys.argv[1:]
if "--version" in args:
    print("vitis-run v2025.2 STUB ONLY")
    sys.exit(0)
try:
    config = Path(args[args.index("--config") + 1])
    workdir = Path(args[args.index("--work_dir") + 1])
    part = args[args.index("--part") + 1]
    assert part == "xck26-sfvc784-2LV-c"
    assert config.is_absolute() and config.is_file()
    workdir.parent.mkdir(parents=True, exist_ok=True)
    os.chdir(workdir.parent)  # CRITICAL Vitis behavior: not project cwd.
    lines = config.read_text().splitlines()
    keys = {}
    for line in lines:
        if not line.strip() or line.startswith("#") or line.startswith("["):
            continue
        k, v = line.split("=", 1)
        keys.setdefault(k, []).append(v)
    assert keys["package.output.format"] == ["rtl"]
    assert "syn.output.format" not in keys
    assert keys["relative_roots"][0].startswith("/")
    assert len(keys["tb.file"]) == 1
    assert len(keys["syn.file"]) >= 1
    for name in ("tb.file", "syn.file"):
        for fname in keys[name]:
            p = Path(fname)
            assert p.is_absolute() and p.is_file(), fname
    for name in ("syn.cflags", "syn.csimflags", "tb.cflags"):
        for flags in keys.get(name, []):
            for flag in shlex.split(flags):
                assert flag.startswith("-I"), flag
                p = Path(flag[2:])
                assert p.is_absolute() and p.is_dir(), flag
except Exception as error:
    print(f"MOCK_TOOL_ERROR: {error}", file=sys.stderr)
    sys.exit(81)
print("STUB_ONLY PASS: effective config source and include paths resolve after chdir")
"""


class M05RealWorldPathRegressionTests(unittest.TestCase):
    def test_all_three_effective_configs_resolve_from_unrelated_directory(self):
        for kernel, (relative_cfg, top) in CONFIGS.items():
            with self.subTest(kernel=kernel), tempfile.TemporaryDirectory() as temp:
                dest = Path(temp) / "evidence/hls_effective_config.cfg"
                template = HLS / relative_cfg
                old_bytes = template.read_bytes()
                result = prepare(ROOT, template, dest, top)
                self.assertTrue(dest.is_file())
                self.assertEqual(result["top"], top)
                self.assertEqual(template.read_bytes(), old_bytes)
                self.assertIn("package.output.format=rtl", dest.read_text())
                self.assertIn("relative_roots=" + str(ROOT.resolve()), dest.read_text())
                # Demonstrate exactly the old failure: change out of v1 and
                # resolve ALL original config source paths under the NEW cwd.
                old_files = [line.split("=", 1)[1] for line in
                             template.read_text().splitlines()
                             if line.startswith(("syn.file=", "tb.file="))]
                self.assertTrue(all(not (Path(temp) / path).exists()
                                    for path in old_files))
                source_paths = result["sources"]
                self.assertTrue(all(Path(s).is_absolute() and Path(s).exists()
                                    for s in source_paths))

    def test_absolute_config_is_exclusive_and_fails_on_missing_input(self):
        with tempfile.TemporaryDirectory() as temp:
            src = Path(temp) / "source"
            cfg = src / "hls/template.cfg"
            cfg.parent.mkdir(parents=True)
            (src / "hls/top.cpp").write_text("void top() {}\n")
            cfg.write_text(
                "part=xck26-sfvc784-2LV-c\n"
                "[hls]\nrelative_roots=file/..\nclock=10ns\n"
                "package.output.format=rtl\nsyn.top=m05_stream_eval\n"
                "syn.file=hls/top.cpp\ntb.file=hls/missing_testbench.cpp\n",
                encoding="utf-8"
            )
            with self.assertRaises(FileNotFoundError):
                prepare(src, cfg, Path(temp) / "config.ini", "m05_stream_eval")
            (src / "hls/missing_testbench.cpp").write_text("int main() {}\n")
            out = Path(temp) / "config.ini"
            prepare(src, cfg, out, "m05_stream_eval")
            with self.assertRaises(FileExistsError):
                prepare(src, cfg, out, "m05_stream_eval")
            self.assertNotIn("syn.output.format", out.read_text())

    def test_offline_runner_three_kernels_survive_vitis_chdir_with_stub(self):
        runner = HLS / "m05_stream_eval/run_m05_offline_hls.sh"
        with tempfile.TemporaryDirectory(prefix="m05_hls_path_stub_") as temp:
            t = Path(temp)
            bin_dir = t / "fake_tools"
            bin_dir.mkdir()
            fake_tool = bin_dir / "vitis-run"
            fake_tool.write_text(STUB)
            fake_tool.chmod(0o755)
            env = os.environ.copy()
            env.update({
                "HOME": str(t),
                "PATH": str(bin_dir) + os.pathsep + env["PATH"],
                "HLS_PART": "xck26-sfvc784-2LV-c",
            })
            for kernel in CONFIGS:
                with self.subTest(kernel=kernel):
                    run = subprocess.run(
                        ["bash", str(runner), "--" + kernel, "--csim"],
                        cwd=str(t), env=env,
                        text=True, capture_output=True, check=False
                    )
                    self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
                    self.assertIn("STUB_ONLY PASS", run.stdout)
                    self.assertIn("M05 " + kernel + " csim exit code: 0", run.stdout)
            outputs = list((t / "Thesis_Evidence").glob("neuromorphic_v1_m05_*"))
            self.assertEqual(len(outputs), len(CONFIGS))
            for folder in outputs:
                self.assertEqual((folder / "result.txt").read_text().strip(),
                                 "exit_status=0")
                self.assertTrue((folder / "source_sha256.txt").is_file())
                self.assertTrue((folder / "effective_config_sha256.txt").is_file())
                self.assertTrue((folder / "hls_effective_config.cfg").is_file())
                self.assertIn("STUB_ONLY PASS",
                              (folder / "01_csim.log").read_text())
                self.assertTrue((folder / "log_sha256.txt").is_file())


if __name__ == "__main__":
    unittest.main()
