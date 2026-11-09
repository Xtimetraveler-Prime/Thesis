# M05 first real Vitis HLS C simulation — failure analysis and source-path repair

**Operator observation:** 2026-11-08 local; checkout `6f5ca78a15b2a895cf8dcdc09f29bf57b7879142`, Vitis HLS **v2025.2 build 6295257**, K26 part **`xck26-sfvc784-2LV-c`**, 10 ns clock with 12% uncertainty. All three original **genuine Vitis C simulations FAILED**, and their original evidence must be preserved unchanged. **This is not a numeric/RTL result** because no project source/testbench was found or compiled.

## Observed logs and exact root cause

Original operator stdout and evidence paths, each on the original source commit:

| Top | Original external evidence directory | Diagnostic |
| --- | --- | --- |
| `m05_stream_eval` | `~/Thesis_Evidence/neuromorphic_v1_m05_stream_csim_20261108T071012Z_63215` | `HLS 200-2001` cannot find source and testbench; `HLS 200-627` cannot find C testbench; exit 1. |
| `m05_stateful_service` | `~/Thesis_Evidence/neuromorphic_v1_m05_stateful_csim_20261108T071032Z_63752` | Same: source/testbench not located; exit 1. |
| `m05_event_accumulator` | `~/Thesis_Evidence/neuromorphic_v1_m05_accumulator_csim_20261108T071048Z_64272` | Same: source/testbench not located; exit 1. |

Vitis HLS printed `Changing directory to /home/dna/Thesis_Evidence/<run>` before resolving paths like `syn.file=hls/m04_lif_eval/m04_eval.cpp`, `tb.file=hls/..._csim_tb.cpp` and `-Ihls/...`. Our old templates had `relative_roots=cwd` which pointed at the *changed HLS working location*, not the original `Neuromorphic_Accelerator/v1` checkout. That caused the missing-testbench failure before neural arithmetic was reached. The source tree remained valid; **our runner/configuration was wrong**, not the operator's installation.

Also: the **actual Vitis v2025.2 logs** explicitly warn `syn.output.format` is **deprecated** and suggest **`package.output.format`**. The prior M05 code incorrectly used the former and a setup test enforced the wrong key. All three templates and setup tests have now been corrected.

## Remediation on the SAME M05 draft branch

1. Config templates now set `package.output.format=rtl` and `relative_roots=file/../..`. The relative-root prefix is intended for the checked-in template, but the unattended runner **does not rely on it**.
2. New [`prepare_hls_config.py`](../hls/m05_stream_eval/prepare_hls_config.py) reads each versioned template; validates K26 part, top, RTL output, clock, every design/testbench file and every `-I` directory; generates a **NEW** `hls_effective_config.cfg` inside that run's exclusive external evidence directory with **absolute paths** for sources and includes. It will refuse missing files or overwriting an existing generated config. This works independently of Vitis changing directories.
3. The [no-board runner](../hls/m05_stream_eval/run_m05_offline_hls.sh) passes the **same generated absolute-path effective config** to `vitis-run --csim`, `v++ -c --mode hls`, `vitis-run --cosim` and optional `vitis-run --impl`; records the config and its SHA-256 in evidence. Original failed folders are **never** modified, reused or removed.
4. New [`test_m05_hls_path_regression.py`](../tests/test_m05_hls_path_regression.py) has three **PC-only** methods: all three generated configs resolved from an unrelated directory; missing input/overwrite negative checks; and an explicit **FAKE Vitis executable** that changes directories and checks resolution for all three kernels. These tests **cannot be reported as genuine Vitis HLS C simulation**.
5. Existing [`test_m05_hls_setup.py`](../tests/test_m05_hls_setup.py) now checks the *correct* 2025.2 package key, file-root setting, generated effective config and runner use. Five baseline setup methods remain, with three additional path-regression methods.

**Evidence boundary:** Before this failure, **45** M05 host methods and **91** older methods passed. After new regression addition, expected **48 M05 + 91 M01–M04 = 139** named PC unittest methods, **NOT** 139 Vitis/RTL tests. Original three HLS Csim runs still have `FAILED` status. No genuine successful HLS Csim, synthesis, co-sim, BRAM inference, II, timing or board result may be claimed until new original Vitis logs are supplied and reviewed.

## Operator next action

On the existing M05 development branch, `git fetch` / `git pull --ff-only`, verify the new HEAD, then run:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05_hls*.py' -v
export HLS_PART=xck26-sfvc784-2LV-c
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stream --csim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --stateful --csim
bash hls/m05_stream_eval/run_m05_offline_hls.sh --accumulator --csim
```

**Stop and provide the full original `01_csim.log` and `result.txt` from the first failing top** before attempting the next. If all three are genuinely `PASS`, proceed only then to HLS synthesis/co-sim under [the main M05 HLS runbook](M05_HLS_OPERATOR_RUNBOOK.md). The operator's environment was shown to launch Vitis 2025.2; no need to reinstall the tools for this specific cause.

**No merge and no FPGA/JTAG operations.** M05 remains OPEN on draft PR #79.
