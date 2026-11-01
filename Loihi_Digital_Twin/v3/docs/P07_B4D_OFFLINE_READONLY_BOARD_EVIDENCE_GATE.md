# P07-B.4d — Offline Pinned Hardware Evidence and Read-Only XSDB/UART Gate

**Status:** source and host-native regression committed; user-local PASS **PENDING**. B.4c mock Vitis build-contract native tests **user-accepted** and recorded in `docs/P07_B4C_USER_ACCEPTANCE_LEDGER.json`. B.4d does not itself build a real Xilinx ELF, connect to hardware, program PL, download A53 firmware, write PS DDR, stop Linux or execute any inference. Official B2 MNIST TEST remains SEALED; draft PR #49 is unmerged. All accepted Track A/B and original P03/P05 source files are untouched.

## Why this follows B.4c

B.4c delivered a Vitis 2025.2 **build path**, a distinct read-only A53 shell-probe source, and an actual ELF/map **verifier**. Mocked Vitis CI acceptance is **not** an actual executable. Before a legitimate live KV260 experiment, the user must first produce the real A53 ELF/map from an independently accepted routed FPD128 XSA, then pin the exact bitstream/build inputs and record *who* collected PS/PL observations. The original P03.2c read-only width diagnostic **stops Cortex-A53 processors** and cannot be casually called a nonintrusive probe. B.4d adds an independent **no-stop, read-only** Tcl observation candidate plus a non-executing evidence gate; even read-only XSDB requires operator control of the board.

### Added sources

1. **`scripts/p07_b4d_readonly_evidence.py`** — independent host-side `prepare` and `review-logs` commands. Never invokes `vitis`, `xsdb`, `vivado`, `ssh`, JTAG, or board actions. `prepare` requires real nonempty ordinary XSA, BIT, LTX, routed metric report, B.4c built ELF + linker map, generated platform XPFM and **identical imported versions of exactly five accepted C sources and nine headers**, with no source drift. Requires separately pinned 64-hex **XSA and BIT SHA256** values and exact accepted routed PS FPD128 metrics. Uses the unchanged B.4c real ELF auditor (AArch64, retained read-only identity, original P03 BSS, LOAD/memory nonoverlap) with **operator-supplied actual physical BSP stack/heap extents** and A53 cross-binutils. No fake ELF is accepted in a normal CLI run. Only on total success creates a fresh **out-of-repository** evidence folder containing `offline_preflight.json`, its checksum, and `README_NO_BOARD_RUN.txt`. The JSON explicitly reports `physical_acceptance=false` and `inference_authorized=false`.
2. **`vivado/p07_b4d_readonly_shell.tcl`** — operator-triggered XSDB **read-only register snapshot** of six static/status registers through the PSU/APU physical access target: `0xFD615000` PS FPD width, `0xA4000000` P03 ID, `0xA4000004` version, `0xA4000008` capabilities, `0xA400000C` global status and `0xA4000054` pending page bytes. Checks width selector [9:8]==2, ID `0x4C543302`, version `0x00010000`, capabilities `0x0001031F`, idle and zero pending. Prints the raw values, explicit PASS marker and `P07_B4D_INFERENCE_AUTHORIZED=0`. No `stop`, `rst`, `dow`, `mwr`, `con`, PL programming, DDR reads or writes. JTAG connection is **still** a physical user/operator operation and is NOT run by CI.
3. **`review-logs`** independently rehashes the offline manifest, its XSA/BIT/LTX/route XPFM/ELF/map artifacts and staged source files before parsing a separately captured A53 UART log and XSDB read-only log. Requires the exact B.4c executable identity **once**, a unique probe PASS and unique XSDB PASS, six correctly formatted register values, exact idle/capabilities and `INFERENCE_AUTHORIZED=0`. Rejects any failure marker, duplicate/missing/reordered or contradictory values, changed artifacts and log truncation. Its result reports `logs_authenticity=NOT_INDEPENDENTLY_ESTABLISHED` and `board_physical_acceptance=false` even when these text-format checks pass; **pasted logs alone cannot prove the physical instrument or full DDR ownership**.
4. **`tests/test_p07_b4d_readonly_evidence.py`** and `.github/workflows/p07_b4d_native.yml` — offline synthetic fixture and adversarial log tests, including source mutation *while preserving the correct retained identity*, exact XSA/bit SHA, routed metrics, missing ELF, 4 KiB fake shell mismatch, torn/malformed logs and changed evidence. All mocked Vitis and fake ELF fixtures are marked not hardware. **No hardware tools** are invoked by tests.

### User VS Code workstation native gate (now)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4d_readonly_evidence.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4c_build_admission.py \
  tests/test_p07_b4b_board_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py \
  tests/test_p07_b4a_current_ingress.py \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py
```

### Separate, operator-approved *future* hardware readiness procedure (NOT EXECUTED)

**A. Build the actual Vitis probe ELF first** with the existing accepted B.4c build procedure in `docs/P07_B4C_A53_ELF_BUILD_NATIVE_GATE.md`. Resolve real accepted P03.2c 128-bit `p03_2_ps_mmio.xsa`, `p03_2_ps_mmio.bit`, `p03_2_ps_mmio.ltx`, `p03_2_post_route_metrics.txt` files and separately pinned XSA/BIT SHA256s. Do **not** invent stack/heap declarations—inspect the actual BSP linker map/symbols first. B.4c's lack of a genuine generated `.map` is a hard **NO-GO** until fixed by a fresh isolated build.

**B. Create the offline evidence bundle** after acquiring a **real ELF**, matching linker map, XPFM and verified BSP memory extents:

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

python scripts/p07_b4d_readonly_evidence.py prepare \
  --build-dir "$P07_B4C_BUILD_DIR" \
  --xsa "$P07_B4C_XSA" \
  --bit "/ACTUAL/accepted/p03_2_ps_mmio.bit" \
  --ltx "/ACTUAL/accepted/p03_2_ps_mmio.ltx" \
  --route-metrics "$P07_B4C_ROUTE_METRICS" \
  --xsa-sha256 "$P07_B4C_XSA_SHA256" \
  --bit-sha256 "$P07_B4D_BIT_SHA256" \
  --stack "0xACTUAL_STACK_START:0xACTUAL_STACK_END" \
  --heap "0xACTUAL_HEAP_START:0xACTUAL_HEAP_END" \
  --out "$HOME/p07_b4d_readonly_evidence_01"
```

This command **does not touch the KV260** and prints `P07_B4D_OFFLINE_PREFLIGHT_PASS_NO_BOARD_RUN=1` only when the verified artifact set is complete. A real standalone build is blocked by missing Vitis/toolchain and must take place on the operator's Xilinx-enabled workstation.

**C. Separate actual board operation, only after operator approves boot/CPU/DDR state.** Establish whether Linux is active and whether the accepted P03 bitstream is already loaded. Any download/reset/`dow` or FPGA programming is a **different, physically intrusive phase** and is **NOT** performed by `prepare`. It may change A53 memory and replace Linux even if the probe application itself only reads PS/PL registers. An operator may capture the standalone B.4c app's UART lines and, separately, invoke the new read-only XSDB Tcl command (after physical ownership is established) with e.g. `xsdb vivado/p07_b4d_readonly_shell.tcl tcp:127.0.0.1:3121` and separately retained raw stdout. Avoid using the older P03.2c width diagnostic in this stage because it stops cores. Neither this document nor code grants board execution permission.

**D. Inspect separately collected human-operated raw logs offline:**

```bash
python scripts/p07_b4d_readonly_evidence.py review-logs \
  --build-dir "$P07_B4C_BUILD_DIR" \
  --evidence-dir "$HOME/p07_b4d_readonly_evidence_01" \
  --uart "/ACTUAL/path/read_only_A53_uart.log" \
  --xsdb "/ACTUAL/path/read_only_PSU_XSDB.log"
```

A format PASS from this parser is **never sufficient evidence to accept the physical inference runtime**. The operator must preserve logs, ELF/map/build SHA, boot process notes and a description of how PS/PL ownership was established. Complete 27-core test readiness additionally requires authenticated frozen trained P02 contexts, **27-core pristine reset/restore**, correct noncoherent DDR cache ownership, independently observed emitting-neuron provenance (not reconstructed from packets), the 794,000 signed edges and 26-tick oracle comparison. Official B2 MNIST TEST stays **SEALED**, and PR #49 is not merged.

**Hard stop:** User-native B.4d PASS pending; no physical board probe/ELF/result has been produced by CI or this development turn.
