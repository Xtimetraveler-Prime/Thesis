# AUTHORITATIVE NEXT-CHAT HANDOFF — Accelerator v1 M05.12d.3: six-bank PS address readback retry

**Updated 2026-11-08 22:32 America/Denver / 2026-11-09 UTC.** This replaces outdated M05.12d.3 *project context and next-task status* in the previously issued handoff. The established development/explanation workflow in §7 below is **copied verbatim**, except the final immediate-task statement. The original safety and scientific-integrity statements in §6 are **unchanged**. Existing historic reports in linked dated engineering documents and immutable owner evidence directories are not modified.

## 1. Repository, authoritative branch, toolchain, milestone and PR status

- **Repository:** `Xtimetraveler-Prime/Thesis`, accelerator directory `Neuromorphic_Accelerator/v1/`. **This is NOT the Loihi digital twin project.**
- **Active exact branch:** `agent/neuromorphic-accelerator-v1-m05-sparse-onchip`; PR **#79 OPEN/DRAFT/UNMERGED**. M01–M04 accepted, **M05 OPEN**. Keep work inside **one M05.12d.3**; the user has explicitly requested no proliferation of new D3 micro-milestones.
- **Latest verified engineering/source commit:** `82cda21caf7ac6c49cf8f17ca39c7aa2d1ff80a6` (updated six-bank address-space membership check, negative test and diagnostics). Any handoff-only commit later changes branch HEAD without changing those validated source files. Check Git HEAD and worktree at each new stage.
- **Operator environment:** Ubuntu VS Code clone `~/Git/Thesis`, local Vivado/Vitis **2025.2**, K26 target `xck26-sfvc784-2LV-c`; all original real Vivado/Vitis/HLS/XSim evidence under `~/Thesis_Evidence/`, *outside Git*. Agent has GitHub source/CI tools but **not** owner's actual Vivado process, local generated HLS artifact bytes unless owner supplies evidence, or connected hardware.
- **Safety boundary:** only native/host tests, original static reports and **offline, in-memory** Vivado permitted under the existing workflow. **No PS Linux /dev/mem, physical DDR transfers, device boot, programming, JTAG/XSDB, bitstream, physical runtime or PR merge without explicit owner authorization.** Retain pristine original generated signed32 HLS RTL and `hls/m05_rolling/m05_rolling.cpp`; do not rewrite accepted tests or weaken independent auditors to force a pass.

## 2. Genuinely accepted work since the previous handoff (and exact original owner evidence)

The previous handoff stopped after the **partial PS/PL graph PASS**. Since then genuine original operator Vivado 2025.2 gates reached:

1. **Original partial D3 PS/DMA/shell graph ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_20261109T032316Z_WQjAyg`, source `8385daf1973b94945f9266b8090a52fe83507684`, exit0, 15 real interface links (4 DMA AXIS, 6 PS control for 5 existing slaves, 5 DMA AXI-MM), 15 clock pins, 7 reset consumers and proven one-bit reset inversion; both previous failed original attempts remain immutable. **No HLS yet in this first partial graph.**
2. **Original signed32 Vitis-generated HLS artifact contract ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na`, checkout `f5c305ccb676d30fe8d43fbe09f30b57a4c3eca6`, exit0, source reattestation, hashes for **26 actual generated Verilog files**, original `m05_rolling_replay` **32 authentic top pins**, native **128-bit neuron/external, 192-bit synapse/trace** buses and actual generated AXI4-Lite HLS register offsets (including `DECAY_DEN_DATA=0x40`). This is genuine RTL provenance, not a physical processor.
3. **Original genuine HLS↔shell scalar-connected PS/PL graph ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_hls_connected_20261109T040940Z_h2Ni5q`, source `e82fd1e9bf364581fc184ca7b523b748d97d73ce`, exit0, actual HLS added as sixth AXI4-Lite slave and native stream signals physically net-connected in *offline Vivado*. Evidence exposed **24 BD 41-1306 warnings** from individually connected native AXIS scalar pins, potentially breaking inferred bus interface reconstruction; the newer grouped-AXIS path below supersedes this wiring method.
4. **Preferred original 2025.2 grouped AXIS + real six-segment inventory ACCEPTED:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_20261109T043302Z_KCWN0u`, source `d25d35c1a9b3a68b0970ddf5035ea20bfaa8d1d2`, exit0, real **four native inferred HLS↔shell grouped AXI4-Stream interfaces**, verified 24 native signal widths/directions, existing four 256-bit DMA AXIS, **seven PS control links** reaching all six independent real slaves (4 DMA + shell + authentic HLS AXI4-Lite), **five memory AXI-MM links**, **16 same-domain clock pins**, **8 reset consumers**, no BD41-1306 warnings. Original Vivado returned **six real unassigned slave address-segment objects** and genuine master address-space **`/ps/Data`**, independent graph+segment-inventory audit PASS. Actual slave segments:
   - `/dma_neurons/S_AXI_LITE/Reg`, `/dma_synapses/S_AXI_LITE/Reg`, `/dma_external/S_AXI_LITE/Reg`, `/dma_trace/S_AXI_LITE/Reg`;
   - `/shell/s_axi/reg0`, `/hls/s_axi_control/reg0`.
   **Important:** these are *present, unassigned segment identities*, not six mapped PS addresses. Preserve this result rather than re-running it to claim more progress.
5. **Explicit candidate six-bank plan passes HOST admission only:** `scripts/m05_12d3_control_apertures_candidate.txt` proposes respectively `0xA0000000`, `0xA0010000`, `0xA0020000`, `0xA0030000`, `0xA0040000`, `0xA0050000`, each **64KiB**, against exact native HLS register schema. **This does not confer Linux MMIO address-space ownership, board access or real decode.**

**Latest native CI:** At source commit `82cda21caf7ac6c49cf8f17ca39c7aa2d1ff80a6`, **all five no-board GitHub Actions workflows passed**. M05 discovered **359** methods (358 initial pass +1 optional pre-Icarus skip, subsequently covered by mandatory installed-Icarus RTL verification), M01–M04 **91** methods (22+28+21+20), **450 distinct named methods** passing at least once. A focused D3 test suite discovers **60** host-only/synthetic methods, including latest regression `test_owner_second_failure_requires_real_ps_master_space_not_filtered_addressed`. These do **NOT** constitute genuine Vivado six-bank address or full BD validation.

## 3. The two latest REAL owner address trials, exact failures and current code fix

Both original owner attempts are genuine **`result.txt exit_status=1`** and immutable. No fresh PASS for six actual mapped control banks was provided to this instance.

**Attempt #1 (failed early Tcl return-value assumption):** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_addr_validate_20261109T044947Z_Hh85ty`, source `21be4e1396d1438df49fc98a484e37d32696babf`, exit1. Actual owner offline plan admission, signed32 HLS authentication and original 4-grouped-native-AXIS + six genuine unassigned-slave independent audit passed. Vivado printed *an intended* `assign_bd_address` for `/dma_neurons/S_AXI_LITE/Reg` under `/ps/Data` at 0xA0000000 [64K], but the Tcl mistakenly demanded a nonempty return object and aborted. An assignment message alone is not verified mapping; no six readbacks and no `validate_bd_design -force`.

**Attempt #2 (wrong PS master-space membership query):** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_addr_validate_20261109T051640Z_WDPHFb`, source `495aed38390369da8b0ffb51abd7a4a6d7b1dd80`, exit1. Original preflight and independent native-AXIS/six-unassigned-slave inventory again PASS. After the first `assign_bd_address` attempt, `get_bd_addr_segs -addressing -quiet -of_objects $slave` **returned one actual master segment** (script got past the empty-mapping check), but custom Tcl's next filtered `get_bd_addr_segs -addressed -of_objects $control_space` failed to find the master: `slave dma_neurons is not actually addressed in the required PS /ps/Data space`. This establishes an **incorrect/unsupported verification query** as a plausible root cause, not accepted map success. The original `06_real_ps_control_address_readback.txt` contains only a header/PS space; `07_full_bd_validation.txt` and independent `08` complete mapping audit were not produced.

**Latest fix is committed but NOT YET OWNER-VIVADO VERIFIED:** `82cda21caf7ac6c49cf8f17ca39c7aa2d1ff80a6` updates only the NEW address-validation candidate (not previously accepted graph or HLS RTL) to use documented **unfiltered** `set ps_mappings [get_bd_addr_segs -quiet -of_objects $control_space]` for master-space membership. Keeps the real one-to-one `-addressing` slave→master query and `/ps/Data/*` namespace requirement, checks unfiltered master-space list membership, reverse master→original authentic slave segment, actual `OFFSET` and `RANGE` readbacks matching each proposed plan, all six unique mappings and *then* real `validate_bd_design -force`. New diagnostic output is emitted as `ADDR_D3_SPACE_QUERY`, `ADDR_D3_REVERSE_QUERY`, `ADDR_D3_PROP_QUERY` in `03_vivado.log`. CI regression prevents reverting to `-addressed` for this check. Host CI passed but **no subsequent owner Vivado transcript** is available here.

**Important separation:** If new owner Vivado records all six genuine `READBACK` rows yet `07_full_bd_validation.txt` reports `VALIDATION|FAIL|FULL_BD_VALIDATE_FORCE`, then **address mapping may be accepted independently if the strict mapping audit confirms it**, while **full BD is still FAILED/INCOMPLETE**. Do not claim the entire runner PASS or D3 closure. Investigate the first real BD validation error, preserving its evidence. If mapping itself fails, inspect the *first* new `ADDR_D3_*` diagnostic and source path semantics—never change validators merely to accept a requested base instead of actual Vivado readback.

## 4. Authoritative source files and exact next engineering direction

**Inspect these current files first:**
- `docs/M05_12D3_NATIVE_AXIS_ADDRESS_INVENTORY_2026_11_08.md` — CURRENT exact candidate explanation, owner commands and failure history. `docs/M05_12D3_REAL_HLS_PROVENANCE_2026_11_08.md`, `docs/M05_12D3_REAL_HLS_CONNECTED_CANDIDATE_2026_11_08.md` — accepted HLS origin and earlier native-connection history.
- `scripts/m05_12d3_address_validate_candidate.tcl` — only script now attempting actual six PS AXI4-Lite address assignments plus `validate_bd_design -force`. `scripts/run_m05_12d3_address_validate_candidate.sh` — provenance-aware **new unique owner evidence** and independent audits.
- `scripts/m05_12d3_address_validate_audit.py` — explicit plan-only admission, actual six mapped PS slave/master/offset/range audit, genuine HLS register map check, and separate full-BD PASS/FAIL handling; `scripts/m05_12d3_control_apertures_candidate.txt` — six *proposed* offline ranges.
- `tests/test_m05_12d3_address_validate_candidate.py` and other `test_m05_12d3*.py` — actual current 60 synthetic host test methods, including two original-owner-error regressions.
- `scripts/m05_12d3_native_axis_candidate.tcl` + independent auditor + accepted original owner evidence above: last TRUE six-unassigned-slave and HLS grouped-AXIS topology. `scripts/m05_12d3_hls_connected_preflight.py` and original `scripts/m05_12d3_real_hls_contract.py` re-authenticate unmodified generated Verilog without inventing an HLS IP. `hls/m05_rolling/m05_rolling.cpp`, original generated Vitis RTL and all accepted HLS+shell net results must remain immutable.

**Immediate next step:** **A fresh owner offline Vivado 2025.2 retry** of the current patched six-address candidate on a clean checkout. In the *new chat*, ask whether there is NEW owner output beyond `82cda21...`; if none, present the exact following copy-paste commands, not a claim of success. Do not call user output absent because of a malformed `-addressed` query a Vivado design failure until the new canonical query has been tested.

**After owner evidence:** inspect `result.txt` + genuine `03_vivado.log` first, then current `06` mapping readbacks and `07` actual validation state, and `08` independent address audit if created. If real six assigned rows PASS but validation FAIL, diagnose the first genuine `validate_bd_design` error while retaining good mapping evidence. If both PASS, proceed within SAME D3 to demonstrate actual generated SmartConnect **256→128-bit** width adaptation and review AXI-MM PS memory segment mapping; shell clock `FREQ_HZ` and associated bus metadata; Vivado 2025.2 inline HDL replacements for deprecated constant/vector-logic IP; exact PS/PL reset and HLS AXI-Lite control semantics; full offline simulation of success/error/timeout and DMA quiescence before any physical board request. No DDR/FPGA/PS Linux/performance claims until separately authorized and proven.

## 5. Safe Ubuntu/VS Code operator commands for the pending original retry

**Owner has sourced Vivado 2025.2 in the terminal; use only an OFFLINE in-memory experiment. The accepted original generated HLS contract must already exist and PASS.**

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
git status --short
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m05_12d3*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q
python3 -m unittest discover -s tests -p 'test_m04*.py' -q
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
bash -n scripts/run_m05_12d3_address_validate_candidate.sh

# Reuse the original previously ACCEPTED signed32 HLS provenance artifact.
export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
export CTRL_PLAN="$PWD/scripts/m05_12d3_control_apertures_candidate.txt"
cat "$AUTH_HLS/result.txt"
python3 scripts/m05_12d3_address_validate_audit.py --plan "$CTRL_PLAN" --plan-only
vivado -version

# OFFLINE, in-memory Vivado PS/PL only; fresh immutable evidence folder.
bash scripts/run_m05_12d3_address_validate_candidate.sh "$AUTH_HLS" "$CTRL_PLAN"

export ADDR_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_addr_validate_* | head -n 1)"
echo "$ADDR_D3"
cat "$ADDR_D3/result.txt"
cat "$ADDR_D3/commit.txt"
cat "$ADDR_D3/working_tree_status.txt"
cat "$ADDR_D3/00_offline_plan_admission.log" 2>/dev/null || true
cat "$ADDR_D3/01_hls_preflight.log" 2>/dev/null || true
cat "$ADDR_D3/04_independent_original_graph_audit.log" 2>/dev/null || true
cat "$ADDR_D3/06_real_ps_control_address_readback.txt" 2>/dev/null || true
cat "$ADDR_D3/07_full_bd_validation.txt" 2>/dev/null || true
cat "$ADDR_D3/08_independent_address_validation_audit.log" 2>/dev/null || true
grep -E 'ADDR_D3_|ERROR:|WARNING:|PASS:|M05_D3_' "$ADDR_D3/03_vivado.log" | tail -n 120 || true
tail -n 220 "$ADDR_D3/03_vivado.log"
cat "$ADDR_D3/source_sha256.txt"
~~~

**Do not accept six decoded controls / full BD merely from `assign_bd_address` messages or host CI.** Full runner acceptance requires fresh `result.txt exit_status=0`, authenticated source+old graph/inventory audit PASS, six real `READBACK` rows with original slave identifiers + correct real PS `/ps/Data/*` master identities and actual `OFFSET/RANGE`, strict address audit PASS, plus `VALIDATION|PASS|FULL_BD_VALIDATE_FORCE` and exact original Tcl PASS. The runner itself explicitly does **NOT** prove generated SmartConnect width-converter output products, actual PS DDR ownership, Linux MMIO mappings, board boot or neural inference.

## 6. Immutable safety/scientific integrity and unfinished D3 proof

**Safety:** Do not program FPGA, run JTAG/XSDB, halt A53, reflash a device or write PS/Linux-owned DDR based on this handoff. Any later physical tests require user authorization, memory ownership and provenance checks, fresh immutable evidence and power-cycle after JTAG attempts. Never import/execute old frozen v3 JTAG scripts.

**Scientific integrity:** M02 is the accepted numerical truth, M03 is only a PC-only analytical traffic comparator, and M05.11c is an offline real-generated-RTL transport gate. Credit YANA/SENECA/HiAER where architectural ideas overlap. Do not claim real hardware speedup, Loihi-equivalent silicon, power saving or guaranteed synthesizability of an entire system from isolated simulation.

**Additional already-established constraints (unchanged in meaning):** preserve all original passed and failed evidence folders and genuine HLS generated output bytes; no direct owner Vivado/board access from the assistant; no old v3 JTAG scripts; no PR merge without owner authorization; no changes to sealed MNIST TEST. Maintain distinction between synthetic native checks, original generated RTL simulation, offline Vivado IP/BD connectivity, full block-design validation, generated IP output proof, and physical hardware. Do not reset failed evidence or claim new Vivado acceptance without owner files.

## 7. Continuing engineering and explanation-doc workflow

For every independently testable new M05.x increment:
- write the design/evidence doc and update the dated engineering ledger;
- update docs/M05_TESTS_EXPLAINED.md with actual test names, vectors, expected pass/fail paths, native versus simulator versus physical result, correction history and negative cases;
- update docs/M05_PC_ONLY_VERIFICATION.md or a new stage-specific runbook for exact operator commands;
- run available native tests + all M01–M04 regressions, and verify five GitHub Actions workflows at current source HEAD;
- preserve source SHA and generated evidence SHA, do not silently overwrite original files or reset a failed-run gate;
- update roadmap with ONLY achieved results; leave PR #79 draft/unmerged until user verification and explicit authorization.

**Immediate task for the next instance (project-context replacement only):** The latest engineering commit `82cda21caf7ac6c49cf8f17ca39c7aa2d1ff80a6` corrected a false-negative PS master-space membership query; source/CI is PASS but genuine SIX-bank Vivado readback and `validate_bd_design -force` remain NOT OWNER-VERIFIED. First inspect whether the owner has run the fresh offline `run_m05_12d3_address_validate_candidate.sh` using the accepted `AUTH_HLS` evidence; if no fresh output exists, provide §5 commands. If real Vivado fails, preserve original evidence, diagnose first log error and add regression without loosening readbacks; if all six map PASS and full BD FAIL, isolate validation from mapping; after both PASS continue generated SmartConnect 256→128 converter and clock/PS-MM review within ONE D3 milestone. Keep existing workflow bullets above exactly unchanged.
