# P07-B — NEXT CHAT HANDOFF SEED, 2026-10-21 (SUCCESSOR TO OCTOBER 19 SEED)

> **Instructions for a new ChatGPT instance:** Read and follow this document first. It supersedes the STARTUP/BRANCH instructions in `docs/P07_B_NEXT_CHAT_HANDOFF_SEED.md`, which is a historical P06-B2→P07-B starting snapshot that incorrectly says to start P07-B from `main`. **P07-B is already in active development on a draft, unmerged feature branch.** Preserve this seed, milestone history, all source/evidence boundaries and the exact user's preferred local command workflow. First task in new chat: **solve the current KV260 FPD/LPD 64-bit boot-state discrepancy safely; do not jump to more B.4 synthetic gates or A53 physical download.**

**Snapshot 2026-10-21 after user's P08 historical-width log results.** Repository: `Xtimetraveler-Prime/Thesis`, main source `Loihi_Digital_Twin/v3`, active branch **`agent/v3-p07-b-scaled-physical-inference`**, draft [PR #49](https://github.com/Xtimetraveler-Prime/Thesis/pull/49), **UNMERGED**. New chat must `git fetch`, inspect the live branch head, and retain this feature branch; **do not switch to `main` to begin a new P07-B implementation branch**, do not merge without user approval. Older original Track A/P03/P05, P06-B1/B2 and their source/artifact identities are frozen. Machine-side FPGA tools and actual KV260 connected to **the user's PC**, not accessible to GitHub CI or this assistant.

## 1. Immediate reality — current blocker is BOOT/PS state, not compiler/model

**The user has genuinely compiled the P07-B.4c standalone read-only Cortex-A53 executable with Vitis 2025.2 and a linker-generated GNU .map.** User-reported hashes of the actual local files agreed with the ELF-admission JSON, confirming source functions, allocated .bss/.heap/.stack sections and no PT_LOAD collision with P02 reserved DDR. B.4f artifact/read-only launch-risk gate user verified. **No P07-B read-only A53 ELF has been downloaded or run on the KV260.** Its original ELF has entry `0x0` with a physical PT_LOAD near `[0x0,0x23a40)`: low DDR may belong to the bootloader/Linux. Offline load-segment correctness **does not establish an exclusively safe A53 boot address, Linux ownership, MMU or cache coherency**.

B.4g's **first physical**, operator-approved XSDB read-only shell observation connected to the PSU and found:
```text
P07_B4G_FPD_RAW=0x00002560           # @ 0xFD615000, bits [9:8] = 1 => 64 bit
Memory read error at 0xA4000000. AP transaction timeout
P07_B4G_READONLY_PS_PL_SNAPSHOT_FAIL=1
```
It did **not** verify the P03 shell, and the accepted P03 bitstream had **NOT** been programmed in this new boot before that MMIO attempt. The absent PL slave could cause the timeout, but FPD64→accepted Vivado FPD128 width mismatch is separately proven. Do not attribute AP timeout to width mismatch alone.

**Corrected B.4g** `vivado/p07_b4g_readonly_shell.tcl` first reads FPD width and now **fails before any PL MMIO access** when 64-bit, preventing repeat timeout in that case. Optional `vivado/p07_b4g_ps_width_only.tcl` has been physically exercised, successfully reading only PSU-side SLCR registers. It reported:
```text
P07_B4G_PS_ONLY_TARGET=PSU
P07_B4G_PS_ONLY_FPD_HPM0_RAW=0x00002560
P07_B4G_PS_ONLY_FPD_HPM0_WIDTH_BITS=64
P07_B4G_PS_ONLY_LPD_HPM0_RAW=0x00000512
P07_B4G_PS_ONLY_LPD_HPM0_WIDTH_BITS=64
P07_B4G_PS_ONLY_TWO_PS_REGISTERS_READ=1
P07_B4G_PS_ONLY_DONE_NO_PL_READ=1
P07_B4G_A53_ELF_DOWNLOAD_AUTHORIZED=0
P07_B4G_PHYSICAL_INFERENCE_AUTHORIZED=0
```
On October 21, user measured identical FPD64/LPD64 **before and after successful** `sudo xmutil unloadapp` on KV260 Linux: `remove from slot 0 returns: 0 (Ok)`. Thus unloading accelerators **does not restore PS width**. User explicitly reports the historical Track A board prep as **reboot → Linux login → `sudo xmutil unloadapp`**, same procedure now.

### Definitive recent historical-width reconciliation

On October 17, user independently read **19** preserved Track A P07-A2/A3/A4 `/tmp/v3_p07_*/ps_width.log` logs; **ALL 19** FPD=128, LPD=128. Three confirmed accepted XSA/BIT/LTX hashes and successful P03 bitstream programming/PL reset release. On Oct 18–19, user read **7** original P08-A latency physical `ps_width.log` files under `/home/dna/Thesis_Evidence` (one A3.1 pilot and six A3.2 A2.1/A2.2 paired sessions): **ALL SEVEN** reported
```text
P03_2C_PS_FPD_AXIFS_RAW=0x00000A00
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_AXIFS_RAW=0x00000200
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
```
Latest original archived one: `/home/dna/Thesis_Evidence/p08_a3_2_pair3_A2_2_20261019T013054Z/ps_width.log`. The other six file paths and user-provenance limits are in `docs/P07_B4G_P08_7_RUN_WIDTH_RECONCILIATION_LEDGER.json` and `docs/P07_B4G_P08_SEVEN_RUN_WIDTH_ROOT_CAUSE_UPDATE.md`. **Therefore FPD/LPD128 was still definitely present in P08's last preserved physical run, and 64 was first observed October 21. EXACT TRANSITION TIME/CAUSE UNKNOWN.** Do not claim P08 caused a permanent change, or that P08 positively rules out every indirect boot/recovery effect.

Original P08-A3.1 and A3.2 physical runners **refused to proceed unless FPD128**, then staged DDR, programmed same accepted P03 BIT, and launched standalone A53. Review `scripts/run_p08_a3_1_pilot.sh`, `scripts/run_p08_a3_2_1024.sh`, `vivado/p08_a2_xsdb_run.tcl`, `vivado/p08_a2_2_xsdb_run.tcl` and `docs/P07_B4G_P08_A_PERSISTENT_WIDTH_CAUSE_AUDIT.md`. **No direct static FPD/LPD SLCR width `mwr`, boot-firmware flash/update or `psu_init`** in inspected P08 runners. They did stop/reset A53 and overwrite dedicated reserved DDR, requiring a proper reboot, but that does not prove a persistent change to PS width.

Current KV260 PuTTY screenshot: Ubuntu **24.04.2 LTS**, `xmutil bootfw_status` showed requested and last boot **Image A**, both A/B `K26-BootFW-01.02-06140626` and bootable. **NO October 17–19 saved boot image/FSBL hash** was provided for comparison. Before the verified unload, screenshot of `/sys/kernel/config/device-tree/overlays/` showed `k26-starter-kits_image_1`; current post-unload overlay status is **not yet checked**, and attempted multiline FPGA-manager command had a Bash syntax error (not device failure). No reason to suppose a specific firmware update occurred without evidence.

**Prior accepted physical design:** `FPD M_AXI_HPM0_FPD 128-bit AXI4 → SmartConnect 128→32 conversion → P03 32-bit AXI-Lite at 0xA4000000`. Earlier P03 root cause `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`: previous boot already FPD128, original Vivado port was 32; fix was to change **Vivado interface to match existing booted 128**, not runtime write PS widths. **Track A/P08 scripts checked FPD128 BEFORE PL programming**. Do **NOT** run those old destructive runners under Linux, load FPD128 PL on current PS64 expecting repair, or re-read the PL MMIO address without verified PL state.

## 2. Current priorities for first next-chat interaction (do not invent other tasks)

**A. Investigate actual PS boot initialization and Kria FPGA-manager state.** Ask user to run simplest *board-side one-line read-only commands* via PuTTY, which has inconvenient copy/paste, or SSH from VS Code PC if `hostname -I` gives accessible IP:
```bash
# RUN ON KV260 LINUX/PuTTY; one line each:
cat /sys/class/fpga_manager/*/state
cat /sys/kernel/config/device-tree/overlays/*/status
sudo xmutil listapps
hostname -I
```
If no such file is present, record exact error. Keep previously reported `sudo xmutil bootfw_status`; repeat only if new reason. If user can SSH `ssh ubuntu@<IP>` from PC, future commands can be pasted, but don't assume networking or expose the IP. Verify post-unload default starter-kit overlay status and whether the P03 PL slave is absent. Avoid changing overlays or re-running `xmutil unloadapp` blindly.

**B. Investigate why FPD/LPD PS registers changed to 64 since the historical Oct 19 snapshot.** Compare boot image A/B, FSBL/psu-init method, possibly reset type (full power cycle vs processor-only warm restart), any firmware/update evidence *on user PC* vs frozen Track A/P08 logs. BootFW slot version on Oct 21 is not proof of a changed firmware. There may be a boot-time PS initialization difference; this hypothesis is not yet proven. If a clean, controlled cold boot is proposed, obtain user's board-state/recovery agreement and avoid automatic JTAG writes. Read AMD UG1087 `afi_fs` register semantics and current Kria dfx-manager `xmutil` docs before proposing specific boot changes; use web for current official documentation if needed.

**C. Only after finding/recovering known FPD128 and PL image provenance** plan a *separately approved* read-only shell pilot; physical A53 ELF download remains blocked by **independent low DDR/Linux/MMU/cache/owner gate** even if PS width fixed. Do not substitute new FPD64 hardware design before checking if old acceptance setup can be recovered.

**Immediate output expected from new assistant:** short causal interpretation of existing 26 historical PS-width logs; precise next safe, noninvasive commands; no speculative programming/unverified resets/ELF launch.

## 3. Current P07-B implementation status — DO NOT RESTART milestones

P06-B1/P06-B2 accepted host-source freezes are already **merged into `main`** as PRs #46/#47. P07-B active development branch **`agent/v3-p07-b-scaled-physical-inference`**, **draft/unmerged PR #49**, follows additive-only tracked changes relative to main; original accepted P03/P05/Track A/B sources/artifacts untouched.

P07-B engineering moved through host and integration checks P07-B.1, B.2, B.3(a/b/c...), then **B.4a–B.4h** safety/build/evidence gates on the **same branch**. Many CI jobs passed and user independently verified earlier native submilestones, including B.4e and B.4f; B.4g/h fake XSDB + offline evidence native tests user reported passed. Specific important files:
- `scripts/build_p07_b4c.sh`, `software/p07/build_p07_b4c.py`, `software/p07/p07_b4c_readonly_board.c`: genuine Vitis standalone A53 read-only ELF build from accepted XSA, requires generated original GNU linker `.map`, retained code identity and required P03/B4b C sources; no inference dispatch and no board action.
- `scripts/p07_b4c_verify_elf.py` + `scripts/p07_b4b_elf_probe_admission.py`: actual AArch64 `readelf`/`nm`, linker and `.bss/.heap/.stack` section/checksum/LOAD tests, exclude protected P02 64MiB DDR and P03 MMIO; embedded heap/stack are **inside PT_LOAD** for actual Vitis ELF.
- `scripts/p07_b4d_readonly_evidence.py`, `scripts/p07_b4e_vitis_inputs.py`, `scripts/p07_b4f_physical_launch_safety.py`: offline source/artifact/config/ELF pins and explicit PS boot-risk NO-GO. Even all PASS **never authorizes physical A53 execution**.
- `vivado/p07_b4g_readonly_shell.tcl`: non-halting opt-in XSDB six static/idle reads with **FPD128 fail-fast before any P03 MMIO**; *original first physical* attempt FAILED at FPD64/AP timeout. `vivado/p07_b4g_ps_width_only.tcl`: optional non-halting PS-only 2 SLCR reads user has actually run. `scripts/p07_b4h_review_shell_capture.py`: host-only transcript receipt with no provenance authentication and no launch GO.
- `tests/test_p07_b4gh_readonly_pilot.py`, `tests/test_p07_b4g_width_timeout_regression.py`: **22 fake XSDB/Tcl and host-only tests CI PASS** [run #39656101558](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/39656101558); not a successful physical shell check. B.4f **11** synthetic native tests CI PASS [run #39652698874](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/39652698874). B.4c/B.4b real-layout corrected **23** native tests CI PASS [run #39650755489](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/39650755489).
- `docs/P07_B4C_REAL_A53_ATTEMPT2_ACCEPTANCE_LEDGER.json`, `docs/P07_B4F_USER_ACCEPTANCE_LEDGER.json`, `docs/P07_B4G_REAL_XSDB_FPD64_TIMEOUT_LEDGER.json`, `docs/P07_B4G_PS_ONLY_64BIT_RECHECK_LEDGER.json`, `docs/P07_B4G_P08_7_RUN_WIDTH_RECONCILIATION_LEDGER.json`: distinct chronological *user-reported* provenance. Do not rewrite old frozen evidence with new interpretations; append new files.

**Genuine local Vitis build** (user PC, 2026-10-21):
```text
/home/dna/p07_b4c_real_linkmap_20261021T181921Z/vitis_workspace/
    p07_b4c_readonly_probe.elf   SHA256 ba96b4c6afac4dd4d7ceb63f417664da8fda1f482757a0b2b6ce80a8faecf86a
    p07_b4c_readonly_probe.map   SHA256 a7b0ac270c92631d1f1a3a39a7af549523770cde031a998935b6bc000fdd7b02
```
Original candidate A53 ELF was ELF64 LE AArch64 EXEC, physical LOAD `[0x0,0x23a40)`, entry `0x0`, `.bss [0xe080,0x1ea40)`, `.heap [0x1ea40,0x20a40)`, `.stack [0x20a40,0x23a40)`. Real linker map correct, all 7 read-only symbols present, 19 allocated sections checked. Second ELF hashes user-reported and independently rehashed by user; actual bytes have NOT been uploaded to GitHub.

**Accepted P03.2c hardware artifacts on user PC:**
```text
~/Git/Thesis/Loihi_Digital_Twin/v3/vivado/build/p03_2c_fpd128_route_20261011T225538Z/reports/
p03_2_ps_mmio.xsa SHA256 52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f
p03_2_ps_mmio.bit SHA256 beb7324decacf1c39d1cda97b6f13f347ecb1901a9670e75479f27a669d988a4
p03_2_ps_mmio.ltx SHA256 31f5771432ffb8c72b35a55e1ef7e88e9d96d406fe8cb306733df474df360238
```
BIT/LTX hashes now **independently trace to 2026-10-17 Track A physical receipts**, not merely to current matching files; **not proof of current loaded bitstream**. If an old B.4f audit was run with `--bit-provenance observed`, leave its historical JSON intact rather than quietly changing it.

## 4. Architectural/scientific scope and invariants inherited from original seed

Develop a digital **Loihi-1-inspired event-driven, tick-synchronous** virtualized neuromorphic chip, **not** true asynchronous Loihi silicon, transistor/NoC/SRAM/power identity or analog dynamics. One physically resident HLS inference engine, **3 physical core slots**, and **27 logical P02 contexts** paged through DDR, originally accepted P03/P05 5-core/3-slot smaller physical workload.

P06-B2 independent trained dense **784→1000→10**, **794,000 signed synapses including zeros**. 26 hidden logical cores + 1 readout core = 27; 25 quota/phase17 external-input spike ticks + one empty drain tick = **26** ticks/image. Signed24 saturating LIF recurrence, strict `>` threshold, correct reset/refractory semantics; all inter-core hidden→readout spikes delivered **NEXT** tick with global barrier; ten readout counts/argmax lowest-index tie (all silent → class 0). Keep exact input encoder, source graph and source-preserving P03/P02 packing. **Cannot** simplify 784 inputs to P05 single diagnostic external axon or drop signed-zero synapses.

The frozen P06-B2 trained user-local `artifacts/p06_b24_frozen_1000/` has 27×512KiB initial P02 context binaries = 14,155,776 B, 33 SHA-indexed freeze files and validated host source/packet numerical oracles. Trained B2 10k **TRAIN-derived validation 97.08%**, not official TEST. B2 signed weights/encoder frozen; independent official B2 MNIST **TEST SEALED**. Original Track A 784→32→10 attained **94.56% physical official TEST**, distinct population/model from B2 validation; don't compare as if same held-out metric. P08-A original full A53 service median ~35.7 ms on 1023 ordinary validation frames; not PL-only latency/power/energy. P08-A physical experiments (Oct18–19) were original compact benchmark, NOT proof of trained B2 27-core physical execution.

Frozen physical addresses/contracts:
- P02 reserved DDR `[0x40000000,0x44000000)` = 64MiB; 27 initial 512KiB contexts `[0x40000000,0x40D80000)`, original P05 staging/descriptor/mailbox towards `0x43F00000` / `0x43FE0000` / `0x43FF0000`.
- P03 4KiB AXI-Lite `[0xA4000000,0xA4001000)`; expected ID `0x4C543302`, version `0x00010000`, caps `0x0001031F`. PS master FPD128, SmartConnect to 32-bit slave; P02 HP0 DDR access separate.
- Physical execution still lacks confirmed 27-core trained source-spike provenance from independent PL neurons, mutable DDR per-image reset/ownership/caching, full 26-tick board numerical trace parity, official B2 TEST gate and P08-B measured scaling.

Do not edit accepted original P03/P05/Track A or B2 frozen files. Gitignored actual MNIST TRAIN and model are only in user's v3 `data/mnist_raw` and `artifacts`; don't pretend GitHub contains them. B2 canonical unsigned frozen manifest SHA `d01ccd2d5a85b22f81580cd7800933642e19d1a43e8a2f38eac1f6c4d83cab90`; actual pretty-printed JSON file SHA `d71e2827a81ab1f00ef1e89446540ac04b7d7b34d89b30d46cd6e4ff013c7a63`. Preserve distinction and don't mutate accepted manifest.

## 5. Developer/GitHub workflow & local command preferences — preserve in every reply

**Workflow:** Work on **`agent/v3-p07-b-scaled-physical-inference`**, reviewable draft PR #49; incremental additive P07-B submilestones, one independently testable deliverable at a time unless user explicitly requests related grouped steps. Make real changes through GitHub connector (`functions.exec`, `tools.mcp__GitHub__fetch_file/create_file/update_file/fetch_commit_workflow_runs` etc.), check live branch head, CI and changed file scope. Do NOT claim to execute Vitis, Vivado, XSDB, hardware, or local data unless the user provided terminal output. No automatic merges; **wait for user test confirmation** before next step. Preserve accepted P03/P05 and Track A/B sources; create versioned P07 additions, separate evidence ledgers. Physical destructive actions (CPU halt/reset, DDR writes, FPGA programming, A53 download) require **separate explicit user authorization and verified Linux/DDR/PS ownership**, never in CI.

**After every code/doc development change, give exact VS Code terminal sync commands + applicable tests**, not just a PR link, and expected pass marker. User executes in VS Code Ubuntu/Linux shell on PC; PuTTY on KV260 has **poor copy/paste**, so only give short **single-line** board shell commands, never multiline loops for PuTTY. If `hostname -I` and network are available, use user-operated `ssh ubuntu@<KV260-IP>` from PC to paste/capture longer read-only diagnostics.

**Normal PC checkout sync (CURRENT branch, NOT main):**
```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p07-b-scaled-physical-inference
git pull --ff-only origin agent/v3-p07-b-scaled-physical-inference
git rev-parse HEAD
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
```
**Native fake-XSDB / post-timeout regression only (never actual board):**
```bash
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4g_width_timeout_regression.py \
  tests/test_p07_b4gh_readonly_pilot.py
# Expected: 22 passed
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p07_b4f_physical_launch_safety.py \
  tests/test_p07_b4d_readonly_evidence.py \
  tests/test_p07_b4c_build_admission.py \
  tests/test_p07_b4b_elf_probe_admission.py
```
No new code/tests were added for the seven P08 logs; newest commits are *documentation-only* and do not need a new native regression. If user asks a new implementation change, add independently verifiable native tests and CI before asking for user acceptance.

**Vitis/XSDB 2025.2 toolchain on actual PC:**
```text
Vitis settings: /home/dna/Vivado/2025.2/Vitis/settings64.sh
Vitis app:      /home/dna/Vivado/2025.2/Vitis/bin/vitis
Cross GCC:      /home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin/aarch64-none-elf-gcc
Cross nm/readelf in same GCC bin directory
XSDB:           /home/dna/Vivado/2025.2/Vivado/bin/xsdb
```
```bash
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
```
User wants all actual GitHub changes pushed and their verified commit SHAs stated. PR #49 remains **DRAFT/UNMERGED**.

## 6. Safety blockers, interpreted truthfully

- Live B.4g PS+PL shell admission **FAIL** (AP transaction timeout, FPD64; no P03 ID/version/caps).
- Corrected B.4g/h host native Tcl/pytest **PASS**, not physical P03 shell evidence.
- Genuine B.4c Vitis ELF+map **PASS offline**, not actual board run.
- B.4f user verified **offline launch safety audit**, which expressly says board ELF download/inference authorized **false**; no physical low-DDR owner proof.
- PS width FPD64/LPD64 persists after `xmutil unloadapp`, so repeat unloading is not a fix.
- Historical 19 Track A + 7 P08 both FPD128/LPD128 does **not** identify changed boot/FSBL/reset exact cause.
- **Do NOT** run old `scripts/run_p07_a2_physical.sh`, `scripts/run_p07_a4_physical.sh`, `scripts/run_p08_a3_1_pilot.sh`, `scripts/run_p08_a3_2_1024.sh` now. They deliberately overwrite 64MiB DDR, program PL and reset/halt A53.
- **Do NOT** `mwr` static FPD/LPD SLCR under Linux, retry `mrd 0xA4000000` before confirming programmed P03 PL, run `vivado/p03_2c_program_bitstream.tcl` while PS stays 64, `dow` unowned low-DDR A53 ELF, or open B2 official TEST.
- A fresh cold reboot, boot-image experiment, reprogramming or new 64-bit Vivado route is a distinct operator-approved hardware milestone with provenance, exact safety checks and recovery procedure—**not automatic**.

## 7. Must-read current repository files for new chat

Read in this order:
1. **This successor** `docs/P07_B_NEXT_CHAT_HANDOFF_SEED_2026_10_21.md`.
2. **New evidence/interpretation** `docs/P07_B4G_P08_SEVEN_RUN_WIDTH_ROOT_CAUSE_UPDATE.md` and `docs/P07_B4G_P08_7_RUN_WIDTH_RECONCILIATION_LEDGER.json`.
3. `docs/P07_B4G_P08_A_PERSISTENT_WIDTH_CAUSE_AUDIT.md`, `docs/P07_B4G_TRACK_A_19_RUN_WIDTHS_AND_OVERLAY_EVIDENCE.md`, `docs/P07_B4G_PS_ONLY_RECHECK_BOOT_INVENTORY.md`, `docs/P07_B4G_FPD64_AP_TIMEOUT_RECOVERY_GATE.md`.
4. `vivado/p07_b4g_readonly_shell.tcl`, `vivado/p07_b4g_ps_width_only.tcl`, `tests/test_p07_b4g_width_timeout_regression.py`; P03 acceptance `docs/P03_2C_MMIO_ROOT_CAUSE_AND_FIX.md`.
5. `scripts/run_p07_a2_physical.sh`, `scripts/run_p07_a4_physical.sh`, `scripts/run_p08_a3_1_pilot.sh`, `scripts/run_p08_a3_2_1024.sh` **read-only** for historical comparison.
6. `docs/P07_B4C_REAL_A53_ATTEMPT2_ACCEPTANCE_LEDGER.json`, `docs/P07_B4F_REAL_ELF_LOW_DDR_SAFETY_GATE.md`, `docs/P07_B4GH_READONLY_SHELL_PILOT_AND_EVIDENCE_NATIVE_GATE.md`.
7. `LOIHI_TWIN_ROADMAP.md`, `docs/P06_B2_5_HOST_SOFTWARE_EXIT_AND_P07B_HANDOFF.md`, original `docs/P07_B_NEXT_CHAT_HANDOFF_SEED.md` for **historical architectural details only**, not startup instructions.

## 8. What to tell the user / next checkpoint

Treat the seven P08 archived width logs as physical-history **PASS** (all 128), but the current live P03 shell as **NO-GO**. Prefer a minimal board-Linux read-only inventory and boot-provenance investigation, not further synthetic submilestones or speculative FPGA rebuild. If new user supplies current FPGA-manager/overlay state and network status, interpret carefully: `fpga_manager operating` is *not* proof of loaded P03 bitstream SHA. Ask only one necessary question at a time; do not re-ask what has already been answered. After source/test changes, provide both PC commands and a clear stop for independent user testing.

**End of handoff. New instance: continue on the existing P07-B draft branch at live latest HEAD; do not restart, merge, change frozen weights, access sealed official B2 TEST, or touch KV260 until preconditions are met.**
