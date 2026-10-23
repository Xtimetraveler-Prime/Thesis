# P07-B.4f — Real ELF+Map Accepted; Low-DDR Boot Ownership and Read-Only Pilot Prerequisite

**State on 2026-10-21:** user successfully completed the first **genuine** Vitis 2025.2 standalone Cortex-A53 probe link with **real GNU linker map** and reran exact SHA256 on both. Accepted as a **real-toolchain build and offline ELF/section-layout checkpoint**, **NOT approved to download/launch on KV260**. Branch `agent/v3-p07-b-scaled-physical-inference`; PR #49 stays DRAFT and UNMERGED. Accepted Track A/B, original P03/P05 and B2 official MNIST TEST remain untouched/sealed.

### User real-build evidence (not present in GitHub repository)

- Build: `/home/dna/p07_b4c_real_linkmap_20261021T181921Z`.
- Genuine ELF: `vitis_workspace/p07_b4c_readonly_probe.elf`, 311 KiB, SHA256 **`ba96b4c6afac4dd4d7ceb63f417664da8fda1f482757a0b2b6ce80a8faecf86a`**.
- Genuine GNU linker map: `vitis_workspace/p07_b4c_readonly_probe.map`, 143 KiB, SHA256 **`a7b0ac270c92631d1f1a3a39a7af549523770cde031a998935b6bc000fdd7b02`**.
- User-reported `elf_admission.json`: AArch64; identity retained; all seven read-only P03/B4b symbols; full static P03 `hw` BSS; 19 allocated sections; `.heap [0x1EA40,0x20A40)`, `.stack [0x20A40,0x23A40)`, both inside PT_LOAD, P02 64MiB `[0x40000000,0x44000000)` untouched. `inference_authorized=false`, `DDR_exclusivity_verified=false`, `BSP_physical_address_owner_verified=false`, `MMU_cache_attributes_verified=false`, `KV260_live_shell_verified=false`.
- Earlier real `readelf -W -h/-l` of this same B4c application showed ELF entry `0x0`, a PT_LOAD at physical `[0x0,0x23a40)`. **The updated ELF bytes were NOT supplied**, so B4f must reread the actual later candidate directly on the user PC rather than blindly assume address invariance.
- Previously accepted routed FPD128 XSA `.../vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports/p03_2_ps_mmio.xsa`, SHA256 `52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f`.
- Routed `p03_2_ps_mmio.bit` observed SHA256 `beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4`, still **OBSERVED**, not independently established against a prior physical accepted bitstream receipt.

### Why the low DDR boot owner is the next blocker

The Zynq UltraScale+ MPSoC **APU low DDR begins at 0x00000000** (UG1085 system map). Its on-chip memory is separately mapped at **0xFFFC0000–0xFFFFFFFF**. The current default Xilinx standalone linker script uses `psu_ddr_0_MEM_0` starting at address 0 and the boot entry at `_vector_table`. A board running FSBL → TF-A → U-Boot/Linux may have code, tables or other owners in low DDR. **A valid ELF LOAD at address zero and an offline P02 DDR overlap check are NOT sufficient for a safe XSDB `dow` or boot.** A matching physical PL bitstream, Linux stopped/reboot plan, A53 execution ownership, PS DDR low 1MiB ownership, device MMU/cache attributes and trusted start/entry must be separately verified.

Sources: AMD UG1085 Chapter 10 System Address Map; AMD UG1137 Boot Flow; generated `lscript.ld` and real A53 ELF section/LOAD evidence from user. A low DDR risk flag is **not an assertion that a memory region above 1MiB is automatically free**.

### Implemented B.4f offline verifier

`scripts/p07_b4f_physical_launch_safety.py` (does **NOT** invoke XSDB, JTAG, Vitis, Vivado or the KV260) demands four explicit 64-digit SHA256s for the actual accepted XSA, observed BIT, actual genuine A53 ELF and genuine map. Reuses **unmodified B.4d** source XSA/BIT/LTX/FPD128 route hash gate, plus **B.4c actual `readelf` and `nm`** AArch64 ELF symbol/BSS/LOAD/map and embedded .heap/.stack section gate. Independently parses real ELF entry and PT_LOAD, verifies entry lies in a LOAD and that no LOAD overlaps frozen P02 64MiB. Reports whether a LOAD overlaps the conservative low-DDR first 1MiB and whether it starts exactly at 0. Outputs **`board_ELF_download_authorized=false` and `physical_inference_authorized=false` ALWAYS**. `--bit-provenance observed` must be used until matching prior independent BIT acceptance is located. The tool can save an optional JSON file **outside the repository only**.

`tests/test_p07_b4f_physical_launch_safety.py` and `.github/workflows/p07_b4f_native.yml` test only synthetic archive/ELF evidence, deliberate wrong ELF/map SHA, unsafe entry/LOAD, frozen P02 intersection, unverified section ownership and `NO-GO` status. A synthetic CI PASS does not mean the actual operator file is accessible in CI or that the board was probed.

### Host-native VS Code gate

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
  tests/test_p07_b4f_physical_launch_safety.py

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4d_readonly_evidence.py \
  tests/test_p07_b4c_build_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py
```

### Real user-owned **offline** audit (NO board connection)

```bash
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
export P07_B4C_BUILD_DIR="/home/dna/p07_b4c_real_linkmap_20261021T181921Z"
export P07_B4F_REPORTS="$PWD/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports"
python scripts/p07_b4f_physical_launch_safety.py \
  --build-dir "$P07_B4C_BUILD_DIR" \
  --xsa "$P07_B4F_REPORTS/p03_2_ps_mmio.xsa" \
  --bit "$P07_B4F_REPORTS/p03_2_ps_mmio.bit" \
  --ltx "$P07_B4F_REPORTS/p03_2_ps_mmio.ltx" \
  --route-metrics "$P07_B4F_REPORTS/p03_2_post_route_metrics.txt" \
  --xsa-sha256 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f \
  --bit-sha256 beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4 \
  --elf-sha256 ba96b4c6afac4dd4d7ceb63f417664da8fda1f482757a0b2b6ce80a8faecf86a \
  --map-sha256 a7b0ac270c92631d1f1a3a39a7af549523770cde031a998935b6bc000fdd7b02 \
  --bit-provenance observed
```

Expected only on a genuine user-local file identity, source and ELF/map successful audit:
`P07_B4F_OFFLINE_LAUNCH_SAFETY_AUDIT_PASS_NO_BOARD_GO=1`. Expected current `low_DDR_first_1MiB_overlap=true` and `low_DDR_start_zero=true` **if the second ELF retains the previously reported default entry/LOAD**. Even with that marker, **DO NOT run `dow`, reset, halt A53/Linux, load bitstream or dispatch**.

### Separate physical *read-only shell* pilot gate — not run or approved by the offline audit

The existing `vivado/p07_b4d_readonly_shell.tcl` is a **nonhalting, register READ only** XSDB snapshot of six PS/PL registers, physically scoped to the accepted FPD128/P03 shell. It is distinct from an ELF download and does **not** validate the actual ELF's execution. It may be considered only after operator confirms:

1. Current KV260 Linux/A53 state and JTAG access ownership (even reading APUs during Linux operation must be coordinated).
2. The PL is already correctly configured and observed against the exact accepted bitstream/identity; no implicit reprogramming just to make the read pass.
3. A fallback/reboot recovery procedure and physical access permissions, and whether any other process is using the PS/PL registers.
4. The operator explicitly chooses to run the nonhalting static XSDB capture while leaving `p07_b4c_readonly_probe.elf` **not downloaded**. Raw output and separate provenance must be retained; the B.4d log parser will not authenticate pasted text.

**Physical A53 ELF ramp:** remains NO-GO until an independently established safe low-DDR window (or a fresh ELF relinked into a verified exclusively owned window), PS boot owner/no-concurrent-Linux policy, runtime cache/MMU map and console/CPU launch contract, with explicit separate acceptance. The already user-accepted P03.2c full smoke is precedent for controlled processor halts and DDR writes but is a **different disruptive physical test**; do not reuse those scripts as if they were nonintrusive.

No Track A/B edits, no unseal of official B2 MNIST TEST, and no PR merge.
