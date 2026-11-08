# M04 — Native PC verification runbook (no board, no synthesis)

**Status:** M04.1–M04.3 audit/host candidate previously user-native verified; **M04.5 requirements and nine new host checks added**. Parent M04 was subsequently authorized for source/host closure and merge by the user. This runbook is for re-verification at the new commit. No JTAG, PL programming, A53 halt, DDR writes, Vitis HLS or Vivado are required. Run these commands in your Ubuntu VS Code terminal, using `~/Git/Thesis` as in prior milestones. Do **not** change or run historical v3 physical scripts.

## 1. Checkout exact M04 branch and inspect sources

```bash
cd ~/Git/Thesis
git status --short
# STOP if existing uncommitted work would be affected; preserve it.
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m04-hls-audit || \
  git switch --track origin/agent/neuromorphic-accelerator-v1-m04-hls-audit
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m04-hls-audit
git status --short
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 --version
g++ --version
```

Read [M04_HLS_ENGINE_AUDIT.md](M04_HLS_ENGINE_AUDIT.md), [M04_5_ENGINE_REQUIREMENTS_AND_M05_HANDOFF.md](M04_5_ENGINE_REQUIREMENTS_AND_M05_HANDOFF.md), [M04_TESTS_EXPLAINED.md](M04_TESTS_EXPLAINED.md) and [M02 numerical contract](M02_PROVISIONAL_LIF_CONTRACT.md). To avoid an inadvertent merge, **do not switch to main and merge this branch** until you approve it. The code under `Loihi_Digital_Twin/v3/` has not been modified.

## 2. Run host candidate and all accepted regressions

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m04*.py' -v
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
```

The updated M04 suite contains **22 unittest methods** (13 original, **9 M04.5**) and 16 seeded network subcases inside the old suite; prior suites contain **28+21+20** methods, for **91 named methods total**. An installed `g++` or `c++` is required; the test compiles from the checked-out **actual branch source**, with `-Wall -Wextra -Werror -pedantic`. A failure to compile is a failure, **not** a skip. A test method may contain multiple assertions/subcases. Independent user PC PASS is separate from GitHub Actions PASS.

## 3. Original immutable external evidence for your session

Run *once* per new timestamp. The new directory creation fails rather than reusing old evidence. Source files and raw test outputs remain in `~/Git/Thesis` and `$HOME/Thesis_Evidence`, respectively; no board is used.

```bash
set -euo pipefail
set -C
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
mkdir -p "$HOME/Thesis_Evidence"
export M04_UTC="$(date -u +%Y%m%dT%H%M%SZ)"
export M04_EVIDENCE="$HOME/Thesis_Evidence/neuromorphic_accel_v1_m04_host_$M04_UTC"
mkdir "$M04_EVIDENCE"  # Fails if it already exists; never delete originals.
git rev-parse HEAD > "$M04_EVIDENCE/source_head.txt"
python3 --version > "$M04_EVIDENCE/python_version.txt" 2>&1
g++ --version > "$M04_EVIDENCE/gpp_version.txt" 2>&1
sha256sum hls/m04_lif_eval/m04_eval.hpp \
  hls/m04_lif_eval/m04_eval.cpp \
  hls/m04_lif_eval/m04_host_cli.cpp \
  tests/test_m04_eval.py \
  tests/test_m04_handoff.py \
  src/neuromorphic_accelerator_v1/m04_profile.py \
  docs/M04_5_ENGINE_REQUIREMENTS_AND_M05_HANDOFF.md \
  src/neuromorphic_accelerator_v1/m02_dense_reference.py \
  src/neuromorphic_accelerator_v1/m02_event_reference.py \
  docs/M04_HLS_ENGINE_AUDIT.md \
  > "$M04_EVIDENCE/source_sha256.txt"
python3 -m unittest discover -s tests -p 'test_m04*.py' -v \
  2>&1 | tee "$M04_EVIDENCE/m04_host_tests_original.log"
python3 -m unittest discover -s tests -p 'test_m03*.py' -q \
  2>&1 | tee "$M04_EVIDENCE/m03_regression_original.log"
python3 -m unittest discover -s tests -p 'test_m02*.py' -q \
  2>&1 | tee "$M04_EVIDENCE/m02_regression_original.log"
python3 -m unittest discover -s tests -p 'test_m01*.py' -q \
  2>&1 | tee "$M04_EVIDENCE/m01_regression_original.log"
sha256sum "$M04_EVIDENCE/"*.log "$M04_EVIDENCE/source_sha256.txt" \
  "$M04_EVIDENCE/source_head.txt" > "$M04_EVIDENCE/evidence_sha256.txt"
cat "$M04_EVIDENCE/source_head.txt"
cat "$M04_EVIDENCE/evidence_sha256.txt"
git status --short
```

The user should report the M04 test summary and any failures, commit SHA and original evidence hashes. If a step fails, keep the failed evidence directory untouched and perform a *new* run with a fresh timestamp rather than overwriting data. `set -C` prevents accidental shell redirection overwrites; `tee` is used only within a newly created directory.

## 4. Scope and next approval gate

Review [M04 test-by-test explanation](M04_TESTS_EXPLAINED.md). A passing native suite proves the bounded stateless **host C++ arithmetic** agrees with M02 revision 1 over the tested inputs. It does not prove unbounded Python integer domain, C++->RTL synthesis, fixed initiation interval, streaming FIFO/AXI traffic, CPU/FPGA timing, DDR locality, memory capacity or hardware neural correctness.

**Optional M04.4:** genuine Vitis HLS synthesis can be proposed as a separate *PC-only* offline experiment only after the top-level interface/config are specified and the tool is confirmed present. The historical v3 `run_synth_cosim.sh` cleans output and is **not** to be run here. Never program or reset KV260 without new explicit authorization.

**Merge gate:** Keep M04 draft PR unmerged until independent native verification, review of the bounded-domain limitations and **explicit approval to merge**.


## M04.5 handoff-specific consistency check (PC ONLY)

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m04_handoff.py' -v
python3 -m unittest discover -s tests -p 'test_m04*.py' -v
git rev-parse HEAD
git status --short
```

Expected: **9 new M04.5 methods** and **22 total M04 methods**, plus **28/21/20** unchanged accepted M03/M02/M01 methods from the main command block. All are Python/C++ **PC-only**. No `vitis-run`, `vivado`, JTAG, ELF, PS DDR, bitstream or physical action. The first profile is a **known-input replay screen**: do NOT infer a real hardware 4096-event FIFO, HLS resources or guaranteed 100 MHz clock. If `g++` is missing the original 13 M04 tests fail setup rather than falsely skipping.

**Never close/merge M04** simply because these checks pass. Preserve logs in a new exclusive-create external evidence folder. If repeating the immutable-evidence recipe, use a newly minted `M04_EVIDENCE` directory, and include all M04.5 source/test/doc hashes in `source_sha256.txt`.
