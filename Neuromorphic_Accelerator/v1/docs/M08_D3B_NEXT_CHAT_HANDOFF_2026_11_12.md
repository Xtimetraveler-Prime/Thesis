# M08 D3.2B — next-chat development handoff and gated implementation roadmap
**Research project:** `Xtimetraveler-Prime/Thesis` → `Neuromorphic_Accelerator/v1`  
**Updated:** 2026-11-12, after owner's successful D3.2A PC validation  
**Authority:** this document is the **current forward-looking M08 D3.2B handoff**. Earlier `M08_NEXT_CHAT_HANDOFF_2026_11_11.md` preserves incident history; do not mistake its older D2/D3 STOP notes for a prohibition on *offline source development*. All hardware STOP conditions remain in force.  
**Status:** D3.1 *native BD validated*; D3.2A *offline policy + liveness simulation owner-verified*; **D3.2B PS/firmware/AXI integration design OPEN**; no protected HPM0 implementation, new bitstream, firmware, DTBO, or board authorization.

## 0. START HERE: preserve exact repository / PR stack

At time of handoff documentation, current GitHub branch was `agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design`, with pre-handoff HEAD `f78eb24ab1ee83813ac2e969d65baf9578cf9de3`. **This handoff is being committed onto that branch; resolve its final HEAD using `git rev-parse HEAD`, never hard-code the pre-handoff SHA as the final one.**

| PR | Head → target | Current state | Purpose |
| --- | --- | --- | --- |
| #83 | `agent/neuromorphic-accelerator-v1-m08-kv260-bringup` → `main` | DRAFT, unmerged | Original failed-image incident, D0–D2 forensics and quarantine |
| #84 | `agent/neuromorphic-accelerator-v1-m08-d3-failsafe-candidate` → #83 head | DRAFT, unmerged | D3.1 independent fan-first/no-HPM passive native BD |
| #85 | `agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design` → #84 head | DRAFT, unmerged | D3.2A architecture manifest, independent liveness diagnostic, PC evidence gates |

**First action for next chat:** inspect actual GitHub head, these documents, and draft PR stack; **create a new branch from the latest D3.2A handoff commit** such as `agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit` for D3.2B.1, or an equally distinct name. Do NOT work on `main`, automatically merge #83/#84/#85, force-push or modify the original accepted artifacts. If user asks to work further after verified tests, continue the new branch in ordered subgates and provide exact local commands after every change.

## 1. Latest OWNER-PC verification — what it proves, exactly

Owner ran `python3 scripts/m08_d3b_protected_axi_evidence_gate.py --owner-d3a-run "$RUN"` against **original** D3.1 Vivado PC evidence folder:

`$HOME/Thesis_Evidence/M08/m08_d3a_PASSIVE_NATIVE_PC_jA5mtaMf`

Its JSON returned:
- `D3A_original_native.status = D3A_NATIVE_OWNER_FILES_SHA256_AND_SEMANTICS_ACCEPTED`;
- `D3A_original_native.native_vivado_bd_reported_validated = true`;
- `D3A_original_native.original_legacy_xlslice_deprecation_notice = true`;
- `D3A_original_native.source_or_native_physical_atb4_proof = false`;
- owner receipt SHA256 `955677040227dd5eaef81e49421b6b4c56f2436ca829036d3836d217371043a1`;
- D3.2 manifest SHA256 as returned by owner script: `0bcd98e00c5f5aab64075d08fc97b71b0d4e05c032a1cfa563cd877873384824`;
- `status = D3B_CONTRACT_CREATED_PROTECTED_AXI_HARDWARE_BLOCKED`;
- `Linux_boot_clock_afi_config_proven=false`, `aib13_quiescence_or_no_outstanding_proven=false`, `atb4_enabled_or_safe_runtime_proven=false`, `hardware_mmio_authorized=false`, `ps_hpm0_protected_image_created=false`, `original_m08_image_quarantined=true`.

Original owner D3.1 text SHA256s **previously independently verified against the uploaded originals**, and now again reported by local gate:

| File relative to D3.1 run | SHA256 |
| --- | --- |
| `01_native_vivado.log` | `5debf086f5ead1acbea506570440a2a21d71eff9b53f0394ab9d2a5dc04b46c4` |
| `output/10_d3a_passive_bd_readback.txt` | `c0a4443fcf42ae9c95f8b8eb970511f7e07630722620cd83e115bb20fb9b9c76` |
| `output/11_d3a_passive_bd_export.tcl` | `a2a1f94d5fcf93ca87e2dea54d00227f4ec62bfa9ef947d456dd190af8525b19` |
| `output/12_d3a_fan_a12.xdc` | `7b5f25d14ed1b45ba4c858277d661ba61c0490957370c195218b65de30d899ff` |

D3.1 original native Vivado 2025.2 BD: K26/SOM board part `xilinx.com:kv260_som:part0:1.4`, actual reported PL0 `99,999,001 Hz`, PS HPM0 FPD/HPM1 FPD/HPM0 LPD **disabled**, no SmartConnect, identity/page or UIO, PS TTC0 EMIO channel-2 fan route A12. Original `xlslice` raises a **nonfatal** Vivado `BD 5-1043` advisory favoring `xilinx.com:inline_hdl:ilslice:1.0`; any future migration must be a separately validated *new source*, not an edit to original evidence. D3.1 BD acceptance is **not** a routed/temperature/actual-clock/PS timeout guarantee.

Owner also compiled and ran Icarus **TWICE**, both times obtaining all expected markers and `$finish` without fatal:
- `tb_m08_d3b_ps_linux_release_policy`: `M08_D3B_EACH_MISSING_PREREQUISITE_BLOCKS_ACCESS_PASS`; `M08_D3B_FIRST_TIMEOUT_STICKY_QUARANTINE_NO_RETRY_PASS`; `M08_D3B_ONE_SUCCESSFUL_PROBE_PER_FULL_RESTART_PASS`; `M08_D3B_READINESS_LOSS_LOCKS_UNTIL_RESTART_PASS`; `M08_D3B_STOPPED_PS_CLOCK_IS_UNPROTECTED_NEGATIVE_PASS`; final `M08_D3B_OFFLINE_PS_LINUX_POLICY_ALL_PASS_NOT_HARDWARE_ATB_OR_MMIO_PROOF`.
- `tb_m08_d3b_clock_liveness_probe` using real `m08_d3b_clock_liveness_probe.v`: `M08_D3B_LIVENESS_RUNNING_PL_EDGES_OBSERVED_PASS`; `M08_D3B_LIVENESS_PL0_STOPS_INDEPENDENT_MONITOR_DETECTS_PASS`; `M08_D3B_LIVENESS_RESUME_DOES_NOT_CLEAR_STICKY_POISON_PASS`; `M08_D3B_LIVENESS_STOPPED_MONITOR_CLOCK_IS_UNPROTECTED_NEGATIVE_PASS`; final `M08_D3B_LIVENESS_GENUINE_RTL_ALL_PASS_NOT_PS_ATB_OR_PHYSICAL_CLOCK_PROOF`.
- The second run repeated the same five + six markers, providing reproducibility, **not independent PS clock/ATB evidence**.

Last known CI status before handoff: **all M01–M08 GitHub Actions PASS** on pre-handoff D3.2A HEAD `f78eb24ab1ee83813ac2e969d65baf9578cf9de3`; M08 **239 targeted tests**, full discovery **1,125**. GitHub CI uses real Icarus but **does not run the owner's genuine Vivado IP / hardware**. Future edits must rerun jobs and report exact final HEAD.

## 2. Immutable incident / safety constraints (NONNEGOTIABLE)

Original failed dual-UIO M08 `.bit.bin` SHA256 **`a8ed0e4d461029522750afa7afd9318e956e0874d1b6e5f7f4e6607562c9f45b`** resulted in Linux RCU/timer CPU stall symptoms and SSH loss around the first identity access attempt; root cause is **NOT PROVEN**. Board was restored via hard power cycle to stock. The **original M08 bitstream remains QUARANTINED**, regardless of nominal routed timing, offline HDL model passes or original device-tree review.

Original deployed dual-UIO overlay `m08-v1-fan-page-uio-review.dtbo` SHA256 `2b7798053d10415ef528d4abbbdcb5251cd0dee4845c3288de2a3ef7bd2e75ed` decoded with *no explicit* PL0 clock/assigned-clock, AFI or UIO clock consumer; two independent `&amba` UIO windows `0xA0000000` (identity) / `0xA0001000` (page). This **does not prove** PL0 was stopped, width wrong or ATB4 missing: actual old failed boot configuration and original stock DTBO SHA `1e998ffd5d33a05da3746df3603e65603e1628006bc878209a836cc9bd3c4ae1` remain unavailable on PC. Stop repeating already exhausted stock DTBO PC searches; record UNKNOWN.

**No** original M08 image reloading, PS↔PL MMIO (`/dev/uio*`, `/dev/mem`), JTAG, `xmutil`, FPGA manager firmware/overlay installation, SSH/physical board interrogation, changing clocks/resets/ATB/AIB live, fan control, stock boot/kernel mutation, board power cycles or hardware retry from this handoff. Do not relax `scripts/m08_kv260_physical_uio_operator.py` quarantine guards. **Only owner-PC/offline GitHub and self-contained Vivado validation on a new PC evidence directory** are permitted while hardware safety gates remain open. No future physical attempt without independent upstream timeout, isolation, outstanding-transaction recovery, cooling rollback and explicit owner approval. No HPM0-enabled loadable bitstream until those hardware protection proofs exist.

**Key constraint:** a PL-clocked watchdog, PL0-derived ILA, Python process timeout or simulated synthetic `SLVERR` is NOT a safety barrier against a stopped `pl_clk0`. The new dual-clock liveness RTL needs a **genuinely independent monitor clock**, whose board implementation and CDC have *not* been verified. The D3.2 policy testbench assumes seven upstream readiness signals; none is a hardware-qualified signal. ATB instance **4** is the candidate upstream PS FPD block for `M_AXI_HPM0_FPD`; AIB instance **13** is candidate PS isolation. Actual firmware configuration/clock domain, timeouts, error response type, isolation ACK, downstream late response and restart semantics are unknown. AMD's guidance emphasizes boot-time setup, finite timeout tracking and restart after first timeout.

## 3. Existing authoritative paths to read (in order)

1. `docs/M08_D3B_PROTECTED_AXI_DESIGN_AND_EVIDENCE_GATES_2026_11_12.md` — complete D3.2A design / owner native receipts / gate limitations.
2. `docs/M08_D3B_PROTECTED_AXI_ARCHITECTURE_CONTRACT.json` and `scripts/m08_d3b_protected_axi_evidence_gate.py` — BLOCKED contract, no hardware approval.
3. `rtl/m08/tb_m08_d3b_ps_linux_release_policy.sv`, `rtl/m08/m08_d3b_clock_liveness_probe.v`, `rtl/m08/tb_m08_d3b_clock_liveness_probe.sv`; `tests/test_m08_d3b_protected_axi_design.py`, `tests/test_m08_d3b_clock_liveness.py`.
4. `docs/M08_D2_PS_PL_FAILURE_CONTAINMENT_DESIGN_REVIEW_2026_11_12.md` and `docs/M08_D2_OWNER_ORIGINAL_M08_DECODED_OVERLAY_FINDINGS_2026_11_12.md` — original PS HPM0 / full AXI RCU fault investigation, original DTBO decoding.
5. `docs/M08_D3A_PASSIVE_FAN_ARCHITECTURE_AND_GATES_2026_11_12.md`; `scripts/m08_d3a_passive_fan_bd_candidate.tcl` — accepted fan baseline without any PS-to-PL AXI access.
6. `scripts/m08_page_ps_bd_candidate.tcl` + `scripts/m08_path_a_fan_bd_candidate.tcl`, `rtl/m08/m08_axil_readonly_identity.v`, `rtl/m08/m08_ps_page_safe_shell.v` — *original/quarantined* source for reference only. NEVER run original staging/programming.
7. `roadmap.md`, `docs/M08_TESTS_EXPLAINED.md`, `docs/M08_NEXT_CHAT_HANDOFF_2026_11_11.md` — project-wide milestones, test explanations, historical incident notes.

## 4. Ordered NEXT DEVELOPMENT — D3.2B subgates (develop only offline)

### D3.2B.1 — inventory owner-PC platform artifacts and model their provenance (FIRST)

**Goal:** identify actual boot/PS/FPD/clock/AFI owners before writing any configuration guesses. Work on a NEW D3.2B branch created from this updated handoff branch.

**Deliverables:**
- A bounded, strictly read-only, PC-only artifact-inventory/receipt script (default to known repo and `~/Thesis_Evidence/M08` with explicit owner-chosen narrow extra folders; exclude enormous caches and symlinks; file-count bounds; no board or downloaded proprietary firmware by guessing). Search names/extensions useful for **original** `.xsa`, `psu_init.c`, `psu_init.tcl`, original boot `BOOT.BIN` *metadata only*, FSBL/PMU, Linux/base `.dtb`/`.dts`, kernel/device-tree source, build manifests, firmware/dfx-manager manifests, native logs. Record path, SHA256, size, provenance and **UNKNOWN** for missing source; avoid blindly expanding or executing binary bundles.
- Evidence-class distinctions: XSA / generated PS init source ≠ runtime PS register state; stock `dtbo` ≠ base DTB ≠ **applied** tree; standalone Vivado PS preset ≠ boot-time FPD/clock owner.
- Tests: synthetic candidate files and false matches, hash mismatch, overbroad scan limit, path/symlink boundaries, missing originals and no board access. No `git add` of owner's private binary artifacts.
- A markdown matrix `docs/M08_D3B_BOOT_PLATFORM_EVIDENCE_MATRIX_2026_11_12.md` (new) with exact references, version/boot owner for ATB4/AIB13/PL0/HPM0/AFI/Linux + independent fan and **UNKNOWN/BLOCKED** if missing.
**Gate to B.2:** owner validates script output and any artifacts discovered. If originals unavailable, record it and continue only tool-independent simulation/research; DO NOT invent source to manufacture a pass.

### D3.2B.2 — PS boot integration and clock/isolation ownership review

**Goal:** design a **reviewable source-level** first-fault timeout/quiescence contract, not a live register program.

**Deliverables:**
- Vendor documentation AND pinned installed firmware/kernel evidence crosswalk for `ATB4` upstream of `M_AXI_HPM0_FPD`, `AIB13`, FPD/APB timeout timebase, `ATB_RESP_EN`, `ATB_RESP_TYPE`, prescaler/IRQ/reset defaults, transaction tracking limitations and **one-time fault→stop/restart**. Resolve conflicting vendor timing formulas by doc revision and clock data; NO guessed numeric programming sequence.
- Ownership table for FSBL/PMU/ATF/U-Boot/Linux/FPGA manager, `PL0_REF_CTRL`, `pl_resetn0`, HPM0 128-bit AFI setup, bridge isolation and stock rollback. Provide exact location/version/line evidence *if present*, otherwise state NOT PROVEN.
- Safe state-transition sequence (fail-closed): boot configure PS protection **before PL mapping**, no new PS transactions, quiesce and drain, isolate with actual ACK, clock/reset and region programming, release bridge only after independent readiness, expose driver for a **single** diagnostic, latch first error, stop and controlled recovery. Explicitly examine accepted AR with missing R, outstanding AW/W/B and responses after isolation.
- Read-only/offline source tests checking required dependencies and rejecting partial configurations or false owner approval.
**Gate:** if real ATB/AIB response and outstanding handling remain unverified, **cannot** mark protection PASS or produce a protected HPM0-enabled image.

### D3.2B.3 — complete AXI fault-containment validation (offline)

**Goal:** upgrade the D2 abstract *read-only* model to a bounded, protocol-aware offline verification plan. Distinguish a **real vendor PS model** from mock/testbench logic.

**Deliverables:** reusable BFM/scoreboard with read `AR/R`, write `AW/W/B`, reset, backpressure, missing `ARREADY`, accepted AR with no `RVALID`, accepted writes with missing B, stopped PL0 before/after handshake, late downstream completions, unresponsive SmartConnect, concurrent/outstanding traffic and overflow/first-fault cases. Assert stable `RVALID/RDATA/RRESP`, correct `BRESP`, no duplicate completion and no illegal retry; explicitly **FAIL** a mock that returns synthetic SLVERR while leaving downstream protocol state undrained. Prefer vendor AXI VIP / PS-ATB model if verifiably available; otherwise label the simulation **ABSTRACT, not proof of hardware isolation**. Require genuine Icarus/`vvp` when claiming model pass; skipped test is NOT pass. Preserve negative stopped-PS-clock and stopped-monitor-clock cases.
**Gate:** can finish *offline coverage* even when actual ATB4 semantics unknown; DO NOT equate a passing mock test with release.

### D3.2B.4 — Linux FPGA region, clock/reset, AFI & fan integration design (offline only)

**Goal:** produce new **review-only** integration contract, never installable on the board as-is. Use vendor generated overlays/XSA only if compatible with actual boot software.

**Deliverables:** derive PS clock consumers/assigned clocks/AFI from correct platform source, inspect independent `&amba` vs FPGA-region child-device population, bridge ordering and driver security; choose a fail-closed access policy that does not expose raw arbitrary UIO before readiness, and design one 32-bit identity read with before/after breadcrumbs and no retries. Preserve exact PS TTC0 channel-2 EMIO → A12 fan route, audit `xlslice:1.0` warning / native `ilslice:1.0` migration in a **new** candidate. Document fan cooling while PL changes and stock recovery, not mere A12 connectivity. Only create non-deployable example DTS/JSON if values and binding compatible; label placeholders unbuildable where needed.
**Gate:** no user-side system changes, no `dtc`-generated DTBO for physical installation and no exposure of original UIO.

### D3.2B.5 — conditional new Vivado candidate OFFLINE, only after hard gates

If and ONLY if independent PS-side timeout/isolation/clock/AFI/driver ownership and quiescence are genuinely sourced and reviewed:
- Create unique versioned *new* D3.2 protected PS HPM0/identity + disabled page candidate (do not reuse old `m08-v1-fan-page-uio-review.bit.bin` or original loadable image); fan path unchanged. Review genuine Vivado 2025.2 PS board preset, precise propagated FREQ_HZ, GP0 128-bit, AIB/ATB firmware assumptions, clock/reset, DRC/reset RTSTAT-10, unconstrained paths, CDC, no unintended paths to DMA/DDR, native interface simulation.
- Owner runs **offline** native Vivado in a fresh `~/Thesis_Evidence/M08/m08_d3b_*_` directory and returns SHA-ledger/log/BD export/timing reports. NO `write_bitstream`, packaging/loading/DTBO installation yet; an ordinary BD validate cannot establish stopped-clock safety. Source/CI checks plus owner original native artifacts required.
- If hard gates are missing, **do not enable HPM0 even in a new deployment candidate**. Continue D3.2B.1–B.4 with honest blockers, instead of pushing a cosmetically 'fixed' bitstream. Separate physical D3.3/D4 authorization only with complete evidence and explicit owner agreement.

## 5. Workflow contract for NEXT CHAT — follow after EVERY development change

1. **Scope/branch:** read this file, roadmap and relevant full docs first. Check latest remote branch and PR states; create a **new feature branch** from current D3.2A docs branch, not from `main`, and avoid changes to original .bit.bin, DTBO, stock path or previous owner evidence. Use named submilestones `D3.2B.1`, `D3.2B.2`, etc. Do small reviewable commits. Prefer draft PR stacked on #85 rather than merging D3.2A with `main`.
2. **Development style:** implement real first-party code/docs/tests; fail closed on missing prerequisites and mismatched hashes; no mocks passed off as native vendor models; distinguish source simulation, real Icarus, actual owner Vivado, and physical proof. Every test should include negative/failure cases, explicitly check old quarantine guards remain active, prevent artifact replacement, pin metadata and source hashes.
3. **Automated verification:** run applicable Python unittest `test_m08*.py` and full `test_*.py` discovery, native Icarus when available, `python3 -m compileall -q src scripts tests`; for native tooling not accessible on GitHub runner, make a *read-only* owner-PC script and label native results **PENDING**. Check **all eight** GitHub Actions M01–M08 workflows for final HEAD and inspect logs, don't claim PASS merely from pushed commits. If CI fails, fix and rerun before handoff.
4. **Owner replication:** after EACH committed deliverable give exact, copy/paste Linux VS Code commands: `git status --short`, `git fetch origin`, `git switch <branch>`, `git pull --ff-only origin <branch>`, `git rev-parse HEAD`, `cd Neuromorphic_Accelerator/v1`, targeted unittest + full discovery and direct `iverilog`/`vvp` commands where relevant. Include expected marker, output file path and SHA ledger check if native evidence. **Let owner verify before next dependent hardware/native step.**
5. **Evidence files:** put generated owner-PC outputs only in a new exclusive sibling under `~/Thesis_Evidence/M08` (use `mktemp -d`, never overwrite original). Preserve raw logs, native version, first failure, XSA/source/DT receipts and `99_evidence_sha256.txt` relative hashes. If earlier conversation uploads are expired, rely on pinned docs & owner local originals; ask for reupload only for specific byte-level review needed.
6. **Documentation/PR:** update `roadmap.md`, `docs/M08_TESTS_EXPLAINED.md`, this latest handoff, source design docs and draft PR description after each accepted gate. Mark `COMPLETE` vs `PARTIAL` vs `BLOCKED` precisely, include current branch/commit/tests, and do not erase incident history.
7. **Hardware safety:** No board ssh, JTAG, `xmutil`, physical register reads/writes, manager action, fan override, firmware/DTBO/bitstream loading, power cycles or attempts to 'check if protection works' on real K26. Physical release is a **separate explicit authorization**, never inferred from user saying “continue development”.

### Owner-PC starting commands (for current D3.2A verification)

```bash
cd /home/dna/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3b-protected-axi-design
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 scripts/m08_d3b_protected_axi_evidence_gate.py
RUN="$HOME/Thesis_Evidence/M08/m08_d3a_PASSIVE_NATIVE_PC_jA5mtaMf"
python3 scripts/m08_d3b_protected_axi_evidence_gate.py --owner-d3a-run "$RUN"
python3 -m unittest discover -s tests -p 'test_m08_d3b_*.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_*.py' -v

command -v iverilog
command -v vvp
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_d3b_ps_linux_release_policy \
  -o "$TMP/policy.vvp" rtl/m08/tb_m08_d3b_ps_linux_release_policy.sv
vvp "$TMP/policy.vvp"
iverilog -g2012 -s tb_m08_d3b_clock_liveness_probe \
  -o "$TMP/liveness.vvp" \
  rtl/m08/m08_d3b_clock_liveness_probe.v \
  rtl/m08/tb_m08_d3b_clock_liveness_probe.sv
vvp "$TMP/liveness.vvp"
```

**Expected evidence gate:** `D3A_NATIVE_OWNER_FILES_SHA256_AND_SEMANTICS_ACCEPTED` and `D3B_CONTRACT_CREATED_PROTECTED_AXI_HARDWARE_BLOCKED`.  
**Expected Icarus final labels:** `M08_D3B_OFFLINE_PS_LINUX_POLICY_ALL_PASS_NOT_HARDWARE_ATB_OR_MMIO_PROOF` and `M08_D3B_LIVENESS_GENUINE_RTL_ALL_PASS_NOT_PS_ATB_OR_PHYSICAL_CLOCK_PROOF`.

### Safe first-step for the next instance

**Do D3.2B.1 first**: bounded offline inventory + evidence matrix + synthetic negative tests, in a fresh development branch. Check previously saved repo/file sources before asking user to search again. Provide local commands immediately after code/tests. If no original PS init/XSA/boot sources are on the PC, mark ATB4/AIB13/PL0/AFI UNKNOWN and move to genuinely independent D3.2B.3 offline simulation **without** creating or enabling a protected HPM0 image. 

## 6. Primary technical references (review version before relying on numeric values)

- AMD Zynq UltraScale+ TRM UG1085 ATB/AIB instances and programming, first-timeout restart: https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Instances and https://docs.amd.com/r/en-US/ug1085-zynq-ultrascale-trm/Programming
- AMD FPGA manager for ZynqMP clock/AFI DT overlays: https://xilinx-wiki.atlassian.net/wiki/spaces/A/pages/18841847
- Xilinx SDT generator versioned source: https://github.com/Xilinx/system-device-tree-xlnx/blob/xlnx_rel_v2025.2/device_tree/data/device_tree.tcl
- Linux FPGA-region sequencing: https://kernel.org/doc/html/next/driver-api/fpga/fpga-programming.html
- Project incident/master roadmap and native owner evidence are the **authoritative local context**; generic docs do not prove original board settings.

**FINAL GATE AT HANDOFF:** D3.1 genuine native PS/no-AXI BD + D3.2A owner simulation **PASS**. D3.2B protected PS boot/AXI/LINUX integration and corrected image **OPEN/BLOCKED**. Original bitstream and all physical operations still **STOP/QUARANTINED**.

## D3.2B.1 execution addendum — new development branch (2026-11-12)

Created `agent/neuromorphic-accelerator-v1-m08-d3b-boot-ownership-audit` from this handoff commit `1a1495fe624027482f003a2bde10fd777de0e690`. Implemented only the FIRST B.1 deliverables: bounded offline PC artifact inventory, synthetic negative tests and [boot evidence matrix](M08_D3B_BOOT_PLATFORM_EVIDENCE_MATRIX_2026_11_12.md). **Owner PC inventory not yet executed**, no authentic boot XSA/PS-init/base DTB/firmware source accepted, no PS ATB4/AIB13/PL0/AFI proof. Proceed to B.2 only after owner validates B.1 receipt; unrelated tool-independent simulation may advance, but cannot satisfy PS hardware protection. Do not modify this original D3.2A handoff or claimed owner-native evidence outside the new feature branch; all previous STOP conditions remain unchanged.
