# P07-B.4e — Genuine Routed XSA/BIT Inputs and Real Vitis Build Readiness

**Development state:** new offline-input checks and user-invoked real-toolchain launcher implemented; **USER-NATIVE PASS PENDING**. The user independently accepted P07-B.4d's native regression suite on 2026-10-21 (recorded in `docs/P07_B4D_USER_ACCEPTANCE_LEDGER.json`). The accepted P03/P05 code, Track A/B frozen artifacts, and B2 official MNIST TEST remain unchanged; PR #49 stays draft, unmerged.

## Goal and boundary

This is the **last pre-build software gate before a user-owned real Vitis 2025.2 A53 read-only ELF attempt**. B.4c was a mocked Vitis API/source check and B.4d was an offline artifact/log adjudicator. Neither builds a real standalone program in CI. B.4e instead validates the actual already-accepted **Vivado XSA ZIP archive** and matching separately SHA-pinned **.bit**, **.ltx**, and **post-route metrics**, plus the exact B.4c read-only source allowlist and whether the genuine embedded toolchain executables are on the workstation PATH.

Nothing in B.4e reads the actual sealed B2 official MNIST TEST or writes P02 records. The new code does not run XSDB, connect to JTAG, program PL, halt Linux, read PS device registers or authorize inference. The optional launch script invokes **Vitis only after the operator explicitly runs it** and after the gate passes. CI does not invoke Vitis or produce a real A53 executable.

## Added paths

- `scripts/p07_b4e_vitis_inputs.py`: *read-only* deterministic preflight for the existing `P03_DIAG_REPORTS` directory (exact names `p03_2_ps_mmio.xsa`, `p03_2_ps_mmio.bit`, `p03_2_ps_mmio.ltx`, `p03_2_post_route_metrics.txt`). Requires separately pinned accepted XSA/BIT SHA256, exact accepted 128-bit FPD routed metrics and valid ZIP/HWH XSA with all archive-member CRCs intact. Verifies there are exactly **5 C sources and 9 headers** needed for the read-only candidate, records each SHA256, checks new canonical build path is outside *entire* Thesis repository, and optionally requires visible genuine `vitis`, `aarch64-none-elf-gcc`, `aarch64-none-elf-readelf`, `aarch64-none-elf-nm` executable paths. It does **not** validate actual toolchain version (operator must inspect Vitis 2025.2), independently link the bitstream to XSA internals, or authenticate a prior physical acceptance without external pins.
- `scripts/run_p07_b4e_real_vitis_build.sh`: **manual, not used in CI**. Fail-closed before any filesystem mutation if the above admission rejects. Writes a fresh private offline manifest **outside repository**, exports matching B.4c environment variables, invokes the already existing `scripts/build_p07_b4c.sh` and retains logs. The B.4c builder is still responsible for creating one *new* Vitis 2025.2 standalone A53 project in a separate fresh out-of-repo build folder. It creates a candidate ELF only when **real** Vitis executes successfully, and must refuse missing actual `.map` rather than forging map evidence. B.4e shell does not accept a user's declared stack/heap range as automatically verified. B.4c real ELF admission is still required.
- `tests/test_p07_b4e_vitis_inputs.py` + `.github/workflows/p07_b4e_native.yml`: synthetically generated XSA ZIP/HWH fixture, pinned fake bitstream/route file and negative cases for wrong XSA/BIT pins, non-ZIP or no-HWH XSA, ZIP path traversal, missing/empty LTX/BIT, 64-bit wrong route, source-list drift, missing tools, existing/relative/in-repo build folder, and launcher failure **before creating any build output**. No physical artifact is accepted by these simulated fixtures.

### Physical evidence policy and hard NO-GOs

A **pre-build gate PASS** proves only the submitted file set has the expected structure and the two user-supplied SHAs match. It does not prove the XSA and bitstream belong together unless the accepted operator evidence independently ties them to the same routed run; nor does it prove a live programmed PL image. After the first real Vitis build the user must still run `scripts/p07_b4c_verify_elf.py` on actual AArch64 ELF and real linker map, using **actual** independently reconciled physical BSP stack/heap extents. B.4d then binds the XSA/BIT/ELF/map/source to an offline evidence bundle before a separate read-only board experiment may be considered.

Full physical inference is still **NO-GO** pending Linux-free 64MiB P02 DDR ownership, MMU/cache proof, complete 27-core B2 trained P02 records, full per-image pristine reset/restore, independent PL emitting-neuron source list, 794k-edge signed neuronal parity, 26-tick numerical first-divergence comparison, and explicit board-operation approval.

## VS Code native verification commands — run now

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
  tests/test_p07_b4e_vitis_inputs.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4d_readonly_evidence.py \
  tests/test_p07_b4c_build_admission.py \
  tests/test_p07_b4b_board_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py \
  tests/test_p07_b4a_current_ingress.py \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py
```

**Native checkpoint:** stop after these tests for independent user results. Do not claim that fake archive fixtures equal a real XSA.

## Separate user-owned first REAL Vitis build — not performed in this work

When the user is ready to attempt the actual A53 read-only probe build, start with their **accepted P03.2c FPD128 report folder** on the workstation. Import accepted fingerprints from previously independently verified hardware evidence; do **not** substitute randomly generated SHA strings. In particular, verify the BIT fingerprint has independent provenance, not merely a hash copied from an arbitrary file that happens to exist.

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
# First source the Vitis 2025.2 settings64.sh using the actual installation.
# Ensure vitis, aarch64-none-elf-gcc/readelf/nm are on PATH.
export P07_B4E_ACCEPTED_REPORTS="/ABSOLUTE/accepted/P03.2c/report_directory"
export P07_B4E_ACCEPTED_XSA_SHA256="<ACCEPTED_64_HEX_XSA_FINGERPRINT>"
export P07_B4E_ACCEPTED_BIT_SHA256="<ACCEPTED_64_HEX_BIT_FINGERPRINT>"
export P07_B4C_BUILD_DIR="$HOME/p07_b4c_real_a53_candidate_01"     # MUST NOT EXIST
export P07_B4E_PREFLIGHT_DIR="$HOME/p07_b4e_real_preflight_01"      # MUST NOT EXIST

# This first command is OFFLINE and read-only, with zero board/Vitis calls.
python scripts/p07_b4e_vitis_inputs.py \
  --reports "$P07_B4E_ACCEPTED_REPORTS" \
  --xsa-sha256 "$P07_B4E_ACCEPTED_XSA_SHA256" \
  --bit-sha256 "$P07_B4E_ACCEPTED_BIT_SHA256" \
  --build-dir "$P07_B4C_BUILD_DIR" --require-tools

# Separately authorized real standalone ELF *build only*.
# This runs Vitis on PC; it does NOT call xsdb, program FPGA or boot A53.
bash scripts/run_p07_b4e_real_vitis_build.sh
```

At that point the user may share the resulting `P07_B4E_PREFLIGHT_DIR/preflight.log`, `P07_B4E_PREFLIGHT_DIR/real_vitis_build.log`, the created ELF/linker map paths and Vitis platform errors (if any). **Do not run board commands automatically.**

The next physical gate, once a **real** candidate ELF is independently audited and the user separately approves it, is read-only KV260 PS/PL shell evidence collection per B.4d (without DDR writes or algorithmic dispatch). B.4e itself does not authorize that operation.
