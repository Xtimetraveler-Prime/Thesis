# P07-B.4c — Reproducible Vitis A53 Read-Only Probe ELF Candidate

**Status:** B.4c isolated build recipe and fail-closed native build contract implemented; **actual Vitis A53 ELF NOT YET BUILT** and user-local B.4c native PASS **PENDING**. B.4b host-native PASS was attested by the user, recorded in `docs/P07_B4B_USER_ACCEPTANCE_LEDGER.json`. PR #49 stays **draft and unmerged**. Frozen Track A/B, accepted original P03/P05 source, trained B2.4 inputs, and sealed B2 official MNIST TEST remain untouched.

## Milestone scope and what it does NOT prove

B.4c connects the B.4b read-only shell-admission source to the accepted *existing P05 and P07-A Vitis Python embedded-app APIs* (Vitis 2025.2, `vitis -s` with `vitis.create_client`, new standalone `psu_cortexa53_0` platform, `no_boot_bsp=True`, source-free `empty_application`). It is intentionally NOT the autonomous 27-core inference ELF. Its purpose is to produce, pin, audit and ultimately **separately** read-only-boot a standalone A53 probe.

**New files:**

- `software/p07/p07_b4c_readonly_board.c`: unique retained compiled identity `P07_B4C_A53_READONLY_FPD128_SHELL_PROBE_V1`, the original P03 `p03_hw_xilinx_io` transport, original adapter init and B.4b FPD128/shell/idle **read-only** gate; UART PASS/FAIL then A53 WFE. No context initialization, actual DDR scans, MMIO writes, paging, HLS dispatch, packet routing, protected mailbox, inferred source trace or classifier.
- `software/p07/build_p07_b4c.py`: isolated new Vitis platform `p07_b4c_readonly_platform`, standalone domain `standalone_psu_cortexa53_0`, app `p07_b4c_readonly_probe`. Imports **exactly five C files** (B4c main + B4b admission/Xilinx reader + original P03 adapter and original Xilinx bridge) and nine transitive headers. It refuses missing, extra and symlinked staged sources; imported app C/header manifest must match exactly. Retains a unique candidate ELF and a **real** generated .map; missing/multiple maps fail closed. It refuses overwriting a prior Vitis workspace. The build is not invoked on GitHub or by pytest.
- `scripts/build_p07_b4c.sh`: isolated native-user Vitis launcher. Requires an **independently accepted** XSA SHA256, accepted P03 FPD128 routed metrics (128-bit PS HPM0, SmartConnect width/protocol, 32-bit AXI-Lite endpoint, FPD master, base `0xA4000000`), an absolute fresh build directory **outside the entire Thesis repository**, and installed Vitis/A53 toolchain. Copies only approved additive sources into the new staging area. Refuses to overwrite an existing path or accept a wrong SHA/route. Captures actual Vitis build log, candidate ELF, map and three artifact hashes. Does **not** run XSDB, program PL, load firmware to board or read frozen B2 data. If actual stack/heap extents are not yet known, the script labels the output `ELF_ADMISSION=PENDING_ACTUAL_STACK_HEAP` instead of fabricating a pass.
- `scripts/p07_b4c_verify_elf.py`: requires actual ELF64 magic and unique retained B4c identity, ELF and matching linker map files. Uses **the supplied cross A53** `aarch64-none-elf-readelf -W -h/-l` and `aarch64-none-elf-nm -S --defined-only`, then reuses the accepted B4b AArch64/little-endian EXEC, immutable P03 adapter >=65KiB BSS, no-overlap original P02 64MiB and P03 MMIO, all required read-only code symbols, stack/heap and linker-map checker. Outputs SHA256 of ELF and map but **never** authorizes inference, even on a valid ELF. Its stack/heap extents are external declarations and must still be reconciled manually against *actual* BSP/linker records; an ELF parser cannot prove the boot image's DDR/PS ownership.
- `tests/test_p07_b4c_build_admission.py`, `.github/workflows/p07_b4c_native.yml`: mock Vitis API verifies platform/domain/template name, exact source list, map and ELF output, refusal of reused workspace, extra/missing sources and linkers, synthetic fake ELF header/symbol/map reject cases, wrong XSA digest before invoking Vitis, shell syntax check, and unique board-app source contract. **Mocked Vitis/ELF data never count as a real Vitis build or physical run.**

## Native gate and its true evidence

Native GitHub Actions runs host-C11 source **syntax only** with deliberately fake Xilinx headers, `bash -n`, Python syntax, and a pytest suite using a **mock Vitis API**. A successful run does **not** mean an actual Xilinx platform or A53 program ELF was generated. Other independent gates B.3c2/3, B.4a and B.4b should remain green.

The real build may be attempted only on the user's installed Vitis 2025.2 host, after identifying the existing accepted P03.2c 128-bit routed XSA and its actual SHA256 from prior verified evidence. There is no new bitstream, boot image or firmware launch in this milestone.

## VS Code native test commands — user approval gate

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
  tests/test_p07_b4c_build_admission.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4b_board_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py \
  tests/test_p07_b4a_current_ingress.py \
  tests/test_p07_b3c23_hw_integration.py \
  tests/test_p07_b3c3_elf_admission.py \
  tests/test_p07_b3c_packet_bridge.py
```

**Stop after user-native B.4c PASS** before advancing to the actual Xilinx build or board operation, unless the user explicitly asks for that additional gate.

## Future Vitis build and memory-map admission (NO EXECUTION AUTHORIZED BY NATIVE PASS)

The following commands are a recipe, not a result. Resolve paths using your actual accepted P03 physical XSA SHA and routed-metrics evidence. Do not invent checksums, manually reconstruct signed model records or use official TEST.

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
# Source your installed Vitis 2025.2 settings64.sh first if necessary.
export P07_B4C_XSA="/ABSOLUTE/path/to/accepted/p03_2_ps_mmio.xsa"
export P07_B4C_XSA_SHA256="<64 lowercase hex chars from accepted P03 XSA evidence>"
export P07_B4C_ROUTE_METRICS="/ABSOLUTE/path/to/accepted/p03_2_post_route_metrics.txt"
export P07_B4C_BUILD_DIR="$HOME/p07_b4c_probe_build_01"  # MUST NOT EXIST
bash scripts/build_p07_b4c.sh
```

A real Vitis build requires Vitis 2025.2 embedded Python APIs, bundled A53 compiler and an actual generated linker map. If Vitis produces no map, configure the real app linker command to emit `-Wl,-Map=...` and perform a new isolated rebuild in a different fresh directory; **do not make up a .map file**.

After locating genuine map/BSP stack and heap physical extents, execute the admission checker on the actual ELF and map (the build script may be run with `P07_B4C_STACK` and `P07_B4C_HEAP` only if those addresses were already established from BSP/linker documentation):

```bash
python scripts/p07_b4c_verify_elf.py \
  --elf "$P07_B4C_BUILD_DIR/vitis_workspace/p07_b4c_readonly_probe.elf" \
  --linker-map "$P07_B4C_BUILD_DIR/vitis_workspace/p07_b4c_readonly_probe.map" \
  --stack "0xACTUAL_STACK_START:0xACTUAL_STACK_END" \
  --heap "0xACTUAL_HEAP_START:0xACTUAL_HEAP_END" \
  --readelf "$(command -v aarch64-none-elf-readelf)" \
  --nm "$(command -v aarch64-none-elf-nm)"
```

Even a genuine A53 ELF admission is only **candidate read-only probe evidence**. Before allowing an operator-run XSDB probe or any full 27-core inference, separately establish accepted bitstream/live shell identity, exclusive Linux-free `[0x40000000,0x44000000)`, correct BSP MMU cache attributes, safe reset, separately verified B2 trained 27-core P02 records/trusted mutable CRCs, independent PL emitted-neuron evidence, the original full 794,000 signed edges, and all 26-tick oracle parity. The B.4c probe intentionally DOES NOT contain those operations.

**Milestone boundary:** host-native B.4c PASS pending. No merge, no real ELF claim, no board operation, no sealed official MNIST TEST unseal.
