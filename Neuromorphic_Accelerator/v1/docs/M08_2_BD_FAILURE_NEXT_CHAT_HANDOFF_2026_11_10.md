# AUTHORITATIVE NEXT-CHAT HANDOFF — M08.2 original Vivado failure preserved; diagnostic addendum

> **Diagnostic addendum (2026-11-10 America/Denver, after owner upload).** The historical handoff below accurately records the state **before** the original log was available; its instructions to diagnose before changing source have now been fulfilled. The uploaded `01_vivado_identity_bd.log` shows genuine Vivado 2025.2 ending with `ERROR: [Common 17-53] User Exception: No open project` when first executing `get_ipdefs -all -quiet $vlnv` *before* `create_project`. `result.txt` says `exit_status=1` and the original four source SHA-256 hashes are identical in `source_sha256_before.txt`/`source_sha256_after.txt`. The narrow correction on this same M08 branch creates/verifies the K26 project before the exact same five-IP availability check. Added `test_ip_catalog_query_occurs_only_after_open_project` recreates that boundary with Tcl mocks; **this does not validate real IP Integrator**. After all eight updated same-SHA Actions pass, require **one separate new local Vivado** run in a newly auto-created evidence directory, with original failures retained. PR #83 remains draft/unmerged. No bitstream, physical FPGA, DDR or neural inference result is claimed.


**Date:** 2026-11-10 America/Denver (owner terminal evidence folder UTC 2026-11-11 05:56:14).  
**Scope:** M08.2 **diagnose and repair the first genuine Vivado 2025.2 PS→PL AXI4-Lite read-only identity BD trial**.  
**This is a handoff and diagnostic plan, NOT evidence of a repaired design, physical programming, a new successful vendor run, or authorization to advance the rest of M08 automatically.**

## 1. Current repo, branch and acceptance boundaries

- GitHub repository: `Xtimetraveler-Prime/Thesis`, subproject `Neuromorphic_Accelerator/v1`.
- Work on the **existing** branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`, draft PR **#83**. **Do not start a second branch, switch to main to develop, or merge PR #83**. Refresh and inspect the actual branch HEAD/CI in the new chat; the SHA of the *documentation-only* handoff commit may advance beyond the previously verified source HEAD.
- M01–M07 completed and merged to `main` at `c1223149d7884958984cdb77b37fc50201c3061f`. `main` must remain unchanged during M08 work. The accepted M05 signed32 and M06 signed16 HLS/vendor sources and all owner-original evidence must stay immutable.
- Before the owner's new failed vendor run, M08.1 and the standalone M08.2 identity hardware/test model had passed **all eight M01–M08 source-only GitHub workflows** at source commit `e71cdc954b1851e12fcc14b891a99d9c4466d738`. M08 workflow had **27 targeted tests**, independent Icarus identity RTL PASS, and full discovery **913 tests, 0 failures, 13 optional skips**. **These do not validate Vivado block design, a bitstream or hardware.**
- M08 standing owner authorization covers KV260 activity, but this immediate task is a **local Vivado BD-failure diagnostic**. Avoid JTAG, physical DDR, boot/flash changes and wider M08 work until this gate is correctly resolved and verified.
- The user explicitly requested in this handoff turn: **plan, documentation and roadmap updates only; no implementation changes yet**. The next chat may begin fixing the cause **after inspecting actual original evidence**. Use the existing development/testing/owner-evidence protocol; never guess the first vendor failure.

## 2. Exactly what the owner actually observed (unrepaired)

In the Linux VS Code terminal in `~/Git/Thesis/Neuromorphic_Accelerator/v1`:

~~~bash
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
source /home/dna/Vivado/2025.2/Vitis/settings64.sh
export PATH="/home/dna/Vivado/2025.2/gnu/aarch64/lin/aarch64-none/bin:$PATH"
vivado -version
vitis_hls -version
mkdir -p "$HOME/Thesis_Evidence/M08"
bash scripts/run_m08_identity_bd.sh
~~~

**Observed actual tool results:**

~~~text
vivado v2025.2 (64-bit)
Tool Version Limit: 2025.11
SW Build 6299465 on Fri Nov 14 12:34:56 MST 2025
IP Build 6300035 on Fri Nov 14 10:48:45 MST 2025
SharedData Build 6298862 on Thu Nov 13 04:50:51 MST 2025
vitis_hls: command not found
M08_IDENTITY_BD_EVIDENCE_DIR=/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ
M08_VIVADO_BD_ORIGINAL_FAILED exit_status=1 evidence=/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ
~~~

**Evidence classification:** genuine Vivado **process returned nonzero** during the wrapper's offline BD trial. It is **not** proof that the AXI-Lite RTL failed, that the PS or SmartConnect is unsupported, that the board booted incorrectly, or that physical DDR was accessed. The genuine original `01_vivado_identity_bd.log` was **not uploaded or inspected in this conversation**. Therefore the **first fatal Vivado ERROR, Tcl line, IP/property readback, BD validation stage, and root cause are all UNKNOWN**. Do not label it a confirmed Vivado/script bug until that log is examined. The wrapper's reported exit1 is **not** the independent auditor's failure: the runner exits early when Vivado returns nonzero, before generating an acceptance audit.

The `vitis_hls` missing command is a **separate environment observation**. `scripts/run_m08_identity_bd.sh` only invokes `vivado -version`, `vivado -mode batch`, `python3` and hashes; this isolated identity BD **does not invoke `vitis_hls` or use generated HLS RTL**. Do NOT require reinstallation of Vitis HLS or conflate missing `vitis_hls` with the demonstrated cause. Resolve Vitis HLS tool discovery later for the M08 neural path if needed.

**Preserve exactly:** `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ` (directory may include a partially generated Vivado `project/` and no `02_vivado_identity_bd_readback.txt`). No script retries, `rm -rf`, original log edits, directory reuse, or regenerating accepted owner M06/Loihi assets.

## 3. Architecture and why this trial is narrow

The new read-only `rtl/m08/m08_axil_readonly_identity.v` is an AXI4-Lite **slave** with fixed magic/version/build placeholders, *no AXI master, DMA or writable register*. Its standalone directed `tb_m08_axil_readonly_identity.sv` Icarus test covers independent AW/W, R/B backpressure, invalid addresses and reset; PASS does not imply the Vivado IP Integrator recognizes the module reference.

The original-source candidate `scripts/m08_identity_ps_bd_candidate.tcl` attempts, on part `xck26-sfvc784-2LV-c` and Vivado **2025.2**:

```
PS M_AXI_HPM0_FPD (genuine Zynq UltraScale+ PS)
     → AMD SmartConnect one-master/one-slave
     → first-party identity/S_AXI AXI4-Lite slave
PS PL clock + reset polarity inverter + proc_sys_reset
Vivado-selected address segment → validate_bd_design → save/export BD
```

The invoked wrapper `scripts/run_m08_identity_bd.sh` creates the fresh evidence directory, takes four source SHA256s before and after, runs original Vivado batch, and returns **before** the independent `scripts/m08_identity_bd_audit.py` when Vivado exits nonzero. The report does **not** implement, place/route, generate bitstream, launch hw_server, run on board, access MMIO or DDR.

Earlier original M05.12d.3 Vivado proofs used the same PS/SmartConnect family and **explicit active-low PS reset inversion**, with real warnings about unsupported/read-only reset IP properties. Reuse those **specific original source/protocol lessons** but do not assume that the new M08 candidate passes every property check or will have the identical address mapping. The separate `Loihi_Digital_Twin/v2/docs/P08_4_ACCEPTANCE.md` and `P08_4_3B_ACCEPTANCE.md` document a previous real K26 routed/JTAG physical host-paged dispatch; this precedent is *not* M08 signed16 or real PS-DDR evidence.

The owner reports the KV260 Linux boots normally and normally runs `sudo xmutil unloadapp`. **Board boot is not the immediate blocker**. Earlier submitted host inventory receipt SHA `2c4276c13e3adb21721b8b49e027aa94cbe1e51cf592d402272684bc518606e0` and all **five accepted M06 original ZIP hashes** already matched; do not repeat those checks in response to this unrelated BD error.

## 4. FIRST action in next chat: inspect the original failure, not guess

**Read in this order:**

1. This handoff and current `Neuromorphic_Accelerator/v1/roadmap.md` §5. Current M08 test ledger `docs/M08_TESTS_EXPLAINED.md`, operator runbook `docs/M08_FIRST_PC_KV260_RUNBOOK.md`, and plan `docs/M08_PHASED_HARDWARE_PLAN.md`.
2. Original `scripts/run_m08_identity_bd.sh`, `scripts/m08_identity_ps_bd_candidate.tcl`, `scripts/m08_identity_bd_audit.py`, `rtl/m08/m08_axil_readonly_identity.v`, `tests/test_m08_identity_bd_candidate.py`. Distinguish **synthetic auditor fixtures** from the genuine vendor run.
3. Verify live PR #83 HEAD, draft/unmerged status, source SHA and same-SHA M01–M08 CI. The source HEAD that failed locally is **not independently provided** in the terminal output: verify from `source_sha256_before.txt` and `git rev-parse HEAD` rather than presuming.
4. **First inspect the actual owner original**
   `/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ/01_vivado_identity_bd.log`
   along with `result.txt`, `source_sha256_before.txt`, `source_sha256_after.txt`, and any `02_vivado_identity_bd_readback.txt` or generated BD files. The GitHub connection cannot read the owner's private PC evidence folder; the owner must paste/upload relevant originals or use a tool that genuinely has access.
5. Identify and report the **FIRST** original `ERROR`/`CRITICAL WARNING`/Tcl exception with its actual line and stage. Do not focus only on a later cascading error. Determine precisely whether failure is project/part/IP lookup, PS property readback, AXI interface inference, clock/reset pin, `assign_bd_address`, `validate_bd_design`, BD-export/report code, or an earlier unexpected environment issue. If output is absent, state it is unknown and request the **existing** log rather than running another trial.

**Minimal non-destructive owner-side commands to inspect the existing evidence (no rerun):**

~~~bash
D="/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ"
ls -lah "$D"
cat "$D/result.txt"
grep -nE 'ERROR:|CRITICAL WARNING:|invalid command|wrong # args|couldn.t read|couldn.t find|M08_' "$D/01_vivado_identity_bd.log" | head -80 || true
tail -n 140 "$D/01_vivado_identity_bd.log"
[ ! -f "$D/source_sha256_before.txt" ] || cat "$D/source_sha256_before.txt"
[ ! -f "$D/source_sha256_after.txt" ] || cat "$D/source_sha256_after.txt"
~~~

To transfer one immutable archive rather than screenshots, create a **new ZIP outside the failed folder** with the source hashes, original log and status. Include generated BD evidence if it exists, but do not overwrite the folder or run Vivado again. E.g.:

~~~bash
D="/home/dna/Thesis_Evidence/M08/m08_2_identity_bd_20261111T055614Z_B7OyfZ"
cd "$(dirname "$D")"
tar -czf "$HOME/Thesis_Evidence/M08/M08_2_IDENTITY_FIRST_FAILURE_20261111T055614Z_B7OyfZ.tar.gz" \
  "$(basename "$D")/result.txt" \
  "$(basename "$D")/01_vivado_identity_bd.log" \
  "$(basename "$D")/source_sha256_before.txt" \
  "$(basename "$D")/source_sha256_after.txt"
sha256sum "$HOME/Thesis_Evidence/M08/M08_2_IDENTITY_FIRST_FAILURE_20261111T055614Z_B7OyfZ.tar.gz"
~~~

If any file is missing, report that honestly and archive the existing files instead; do not manufacture missing evidence. The original log may contain host paths/device identifiers: redact secrets if posting text publicly while preserving **raw local evidence**.

## 5. Proposed fix-and-verify workflow AFTER original log inspection

**Do not perform this workflow during this plan-only handoff turn. The next chat may execute it after the actual failure is visible.**

1. **Triage environment and scope.** `vivado v2025.2` is confirmed. Missing `vitis_hls` is not a blocker for this Tcl. First distinguish first-party Tcl/HDL bug, incorrect vendor API call, genuine unavailable IP, incomplete local board/IP configuration, or a wrapper/auditor issue. If necessary create a separate **read-only Vivado diagnostic probe** under a new source commit *only after* the original error is known. Do not assume changes to module interface annotations fix a PS property error or vice versa.
2. **Smallest corrective change.** Modify **only** the affected M08 candidate, runner or auditor and directly relevant tests. Preserve fail-closed checks, correct PS reset polarity, original K26/Vivado part, AXI4-Lite protocol behavior, exact artifact provenance and warnings. Do NOT edit the accepted M05/M06 original HLS/goldens or Loihi v2 code. If the root cause is an incorrect query for the assigned memory segment, fix the query using actual Vivado object readbacks rather than hardcoding a PS MMIO base.
3. **Native source tests and CI.** Add a regression reproducing the exact observed failure boundary (fake Tcl objects can validate parsing/argument logic, but cannot stand in for real vendor IP). Run `python3 -m compileall -q src scripts tests`, M08 targeted, M07 regression and full `python3 -m unittest discover -s tests -v`. Run standalone mandatory Icarus identity tests; verify **all eight** GitHub no-board workflows succeed on the **same updated branch SHA**. Keep draft PR #83 unmerged.
4. **ONE NEW owner Vivado run** at precisely updated and source-hashed branch HEAD: owner sources their real Vivado 2025.2 `settings64.sh`, verifies `vivado -version`, runs `bash scripts/run_m08_identity_bd.sh`. The runner creates a **different timestamped folder**. Do not rerun or replace original `...B7OyfZ`. Preserve failure even if correction fails. Build still must end at local BD validation, not bitstream/physical programming.
5. **Acceptance only on real evidence:** require `result.txt=exit_status=0`, original genuine `02_vivado_identity_bd_readback.txt`, exported `03_identity_bd_export.tcl`, exact before/after source SHA, `04_m08_identity_independent_audit.json`, no unresolved `ERROR/CRITICAL WARNING`, and exact marker `M08_IDENTITY_BD_GENUINE_LOCAL_VIVADO_VALIDATED_NOT_A_BITSTREAM_OR_FPGA_TEST`. A syntax/unit-test PASS is **not** a vendor PASS. Fix an auditor that rejects genuinely valid Vivado output only after original object properties prove it is valid, not by weakening checks speculatively.
6. **Stop after verified M08.2 identity BD**, summarize what did and did not pass, give owner terminal commands, update M08 docs/roadmap and next gate. Only after a new explicit task to progress further should build a real bitstream, physical PL readback, signed16 HLS, kernel-owned DDR, or benchmarking.

**Possible failure sites (hypotheses, not diagnoses):** genuine 2025.2 PS/IP catalog or property names; X_INTERFACE_INFO module-reference AXI-Lite inference; 128-bit PS master-width assumption; proc_sys_reset/IP pin availability; address-space/segment discovery and object references; `assign_bd_address` command options; report/export behavior. These are tests to discriminate by *first log error*. DO NOT announce any of them as the actual bug absent the original log.

## 6. Reporting, branching and safety instructions for the next assistant

- Upfront development plan, then **perform** focused fixes with no unnecessary follow-up if original evidence is attached. No asynchronous promises or guessed success. Keep status updates during substantial tool work.
- New commits only to branch `agent/neuromorphic-accelerator-v1-m08-kv260-bringup`; no merge/rebase/squash without owner direction. Never `git clean`: operator has untracked Loihi-v2 physical artifacts and Vivado logs.
- Archive evidence under `~/Thesis_Evidence/M08` with new unique directory every run, exact SHA and raw failures. Do not copy accepted Loihi/M05/M06 genuine artifacts into Git, do not mutate original generated AMD RTL/HLS.
- Keep RTL and neural comparison honest: M05 is signed32, M06 is signed16; Loihi v2 is distinct signed24. Source-only M07 time/DDR does not measure FPGA performance. No physical results until independent owner-controlled board evidence.
- Maintain `docs/M08_TESTS_EXPLAINED.md`, the local operator runbook, the roadmap and PR #83 description; provide full local VS Code verification commands after any code change.
- Existing KV260 Linux boot + `sudo xmutil unloadapp` is owner-confirmed and not presently a fault; investigate the **Vivado offline trial**, not board recovery. M08 standing hardware authorization remains in force but provides no reason to touch live hardware for this first diagnostic.

**Success condition for handoff:** next chat begins by reading the preserved **first** failed Vivado log, fixes the actual first error, CI-verifies the narrow source correction, and then requests one **fresh** owner vendor verification with immutable original evidence. Until that happens **M08.2 Vivado BD validation is BLOCKED/NOT VERIFIED**, and PR #83 stays DRAFT.
