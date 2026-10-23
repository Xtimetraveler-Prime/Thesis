# P07-B.4 — Real A53 Probe Attempt 1: Vitis ELF linked, missing GNU map (2026-10-21)

**State:** real Vitis firmware **COMPILED and LINKED**, but prior build admission failed because Vitis did not emit a `.map`. **Not accepted as a read-only board-executable yet.** This is user-terminal evidence, not CI evidence or a repository copy of the ELF. User requested continued development; the next step is a **fresh isolated ELF/map rebuild**, not loading the board. Draft PR #49 remains unmerged. Track A/B frozen artifacts, original P03/P05 code and B2 official MNIST TEST remain untouched/sealed.

## User-terminal evidence from first real toolchain attempt

- Original accepted FPD128 XSA SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`, at `vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports/p03_2_ps_mmio.xsa`.
- Associated routed bitstream observed SHA256 `beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4`, **not independently promoted to an accepted fingerprint** by the hash observation alone.
- Vitis 2025.2, A53 cross-GCC at `/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-gcc`.
- First candidate: `/home/dna/p07_b4c_real_a53_20261021T175953Z/vitis_workspace/p07_b4c_readonly_probe.elf`, user reports `311K` on disk. The actual ELF bytes/sha were not uploaded and are not available here.
- Real `readelf -W -h/-l`: AArch64, little-endian ELF64 EXEC, **entry 0x00000000**; one `LOAD` at physical `[0x00000000,0x00023A40)`, filesz `0x00E054`, memsz `0x023A40`, permissions `RWE`, alignment `0x10000`. This is **outside** the reserved `[0x40000000,0x44000000)` P02 DDR area and P03 MMIO but low-memory and startup vector safety still require operator review before XSDB launch. Do **not** infer that entry point 0 is physically safe to boot in any board state.
- Exact original P03 adapter and B4b functions present in `nm -S`: `main` `0x2c48`, `p03_hw_identify`, `p03_hw_init`, `p03_hw_quiescent`, `p03_hw_xilinx_io`, `p07_b4b_probe`, `p07_b4b_xilinx_read_phys`, static `hw` BSS `0xE0B8`, `0x106D8` bytes (67,288).
- Actual `readelf -W -S`: `.bss [0xE080,0x1EA40)`; `.heap [0x1EA40,0x20A40)` (8,192 bytes); `.stack [0x20A40,0x23A40)` (12,288 bytes). These three ALLOC/NOBITS sections are **inside the single ELF LOAD** and disjoint from each other. The original generic B3c owner gate assumed separately allocated stack/heap, hence could not validate this legitimate embedded layout without a dedicated B4c/A53 section check.
- Vitis real log reports `Platform Build Finished successfully`, all five approved C objects built, `[7/7] Linking C executable p07_b4c_readonly_probe.elf`, and `Build Finished successfully`. Original B4c Python then emitted `RuntimeError: expected one generated linker .map ... []`; `find ... -name '*.map'` returned none, only generated `src/lscript.ld`. **The missing real link map was the sole reported postbuild blocker**, not C compilation.

## Implemented corrections (additive P07 branch only)

1. `software/p07/build_p07_b4c.py` now calls the **documented Vitis Unified Python API** `app.set_app_config(key='USER_LINK_OTHER_FLAGS', values=['-Wl,-Map=<workspace>/p07_b4c_readonly_probe.map'])` **before the actual application link**. This is implemented in the isolated new application only, preserving accepted P03/P05 code and original XSA. Map must physically exist and contain original GNU linker provenance `Linker script and memory map`, plus text/BSS/main before returning success. **Neither a fabricated map nor a post-hoc readelf/nm table is accepted.** See AMD UG1400 (2025.2) linker settings / `UserConfig.cmake`, UG1702 `set_app_config`, and Xilinx embeddedsw `USER_LINK_OTHER_FLAGS`.
2. `scripts/p07_b4b_elf_probe_admission.py` introduces an actual `readelf -W -S` allocated-section path: `*.heap` and `*.stack` MUST match the declared physical ranges, reside **within** ELF LOAD, avoid overlap with each other and every other allocated non-stack section, and exclude frozen P02 DDR and P03 MMIO. The original B3c external-buffer nonalias guard is **unchanged** for independently allocated DMA buffers. Synthetic legacy B4b tests retain their explicit declaration-only mode.
3. `scripts/p07_b4c_verify_elf.py` now **always requires actual ELF sections** and can derive `--stack auto --heap auto` from the true `.stack/.heap` ALLOC sections. This eliminates operator guesses. The resulting JSON still says `inference_authorized=false`, `board_probe_executed=false`, and `BSP_physical_address_owner_verified=false`; ELF layout alone does **not** authorize boot or DDR ownership.
4. `scripts/build_p07_b4c.sh` automatically validates the genuinely linked ELF/map, using actual ELF-derived stack/heap if none have been independently specified. It prints `P07_B4C_A53_READONLY_ELF_SECTION_LAYOUT_PASS=1` and `P07_B4C_PHYSICAL_STACK_HEAP_OWNERSHIP=PENDING` only on actual verifier success.
5. `tests/test_p07_b4c_build_admission.py`, `tests/test_p07_b4b_elf_probe_admission.py`, and B4c workflow: mock Vitis demands correct linker-flag API and ordering, rejects absent or non-GNU map, uses real-shaped embedded stack/heap fixtures, checks altered .heap/.stack/.bss/LOAD section boundaries and cannot return physical authorization. **Host synthetic fixture tests are not real Vitis acceptance.**

## User VS Code terminal — native first, then real fresh Vitis rebuild

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
  tests/test_p07_b4c_build_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py
```

**After those native checks pass**, rebuild a new read-only A53 candidate with **the previously accepted FPD128 XSA** and the already user-discovered Vitis/A53 tools. Do **not** reuse/modify `/home/dna/p07_b4c_real_a53_20261021T175953Z`.

```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4C_XSA="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports/p03_2_ps_mmio.xsa"
export P07_B4C_XSA_SHA256="52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f"
export P07_B4C_ROUTE_METRICS="$(dirname "$P07_B4C_XSA")/p03_2_post_route_metrics.txt"
export P07_B4C_BUILD_DIR="$HOME/p07_b4c_real_linkmap_$(date -u +%Y%m%dT%H%M%SZ)"
unset P07_B4C_STACK P07_B4C_HEAP
bash scripts/build_p07_b4c.sh
```

Expected **only if verified by real linker**:

```text
P07_B4C_ELF_CREATED_NOT_BOARD_RUN=1
P07_B4C_A53_ELF_BUILT=1
P07_B4C_A53_READONLY_ELF_SECTION_LAYOUT_PASS=1
P07_B4C_PHYSICAL_STACK_HEAP_OWNERSHIP=PENDING
P07_B4C_KV260_BOARD_STATUS=NOT_RUN
P07_B4C_INFERENCE_AUTHORIZED=0
```

Save these generated files if present: `$P07_B4C_BUILD_DIR/vitis_build.log`, `$P07_B4C_BUILD_DIR/elf_admission.json`, `$P07_B4C_BUILD_DIR/artifact_sha256.txt`, the original `$P07_B4C_BUILD_DIR/vitis_workspace/p07_b4c_readonly_probe.elf`, and the genuine `p07_b4c_readonly_probe.map`. On failure send the last 100 lines of `vitis_build.log` and the application `Linker Flags:` segment, plus the exact `ls` status of the map file.

**Hard stop before physical KV260:** ELF layout pass still does not establish physical low-memory safety, PS/Linux owner, successful live FPD128/P03 shell probe, matching live bitstream SHA, 27-core context initialization, full physical image reset, independent PL source-neuron provenance or trained 26-tick oracle parity. B2 official MNIST TEST SEALED. PR #49 DRAFT/UNMERGED.
