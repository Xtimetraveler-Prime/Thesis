# AUTHORITATIVE NEXT-CHAT HANDOFF — Neuromorphic Accelerator v1 / M06 DDR-backed residency

**Updated 2026-11-09 17:48 America/Denver; documentation-only continuation from M06 branch source HEAD `1e1a76aecdc3f270345ce83bcd4d12f38be5b69d`.** GitHub repository `Xtimetraveler-Prime/Thesis`, current active development branch `agent/neuromorphic-accelerator-v1-m06-ddr-residency`; PR [#80](https://github.com/Xtimetraveler-Prime/Thesis/pull/80) remains **OPEN/DRAFT/UNMERGED**, M06 **OPEN**. The exact new handoff-document commit will advance the HEAD (docs only); the canonical `git rev-parse HEAD` after pull is authoritative. Do not confuse **code/evidence origin** with the newer handoff commit.

## 1. Major milestone transition — do NOT resume M05.12d.4

- PR [#79](https://github.com/Xtimetraveler-Prime/Thesis/pull/79) was **owner-authorized and MERGED 2026-11-09 16:36:23 UTC** as `main` merge `b908fd94d2ab817c2f118573b8fd374476707bf6`. The acceptance decision is `docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md`, scoped to **on-chip bounded signed32 event-driven neural engine with genuine Vitis HLS synthesis/C-RTL cosim, standalone shell XSim, and independent M02 numerical comparison**. This is **not** hardware deployment or PS Linux/DDR correctness. Old D3 warning inventory, real PS HP0 memory ownership, full memory-path correctness were properly **deferred to M06** rather than blocking M05.
- Keep original M05 generated HLS RTL/source, M02 oracle and original owner evidence immutable. Do not work in now-merged M05 branch or amend/erase its accepted trials. M06 is the current unfinished milestone.

## 2. Current M06 verified work and exact evidence boundary

**Actual original vendor 2025.2 memory SmartConnect XSim:** The accepted A/B archive `m06_vendor_xsim_ACCEPTED_20261109.tar.gz`, original SHA256 `f6f842c3d17b552d5604a5552c292d72a9b889518e8b69f42f10db581644d2ff`, contains genuine original Vivado simulator Stage A 256b upstream↔128b downstream byte/WSTRB/read/write test PASS (4 writes / 14 reads) and Stage B one-slot 256B dirty eviction, reload and poison PASS, with original IP SHA before==after. See `docs/M06_M05_NATIVE_AND_VENDOR_STAGE_CD_INTEGRATION_2026_11_09.md`.

**Owner new genuine vendor XSim C/D:** Original owner folder `~/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261109T225500Z_Q55EJq`. Owner supplied `result.txt: exit_status=0` and genuine XSim 2025.2 logs `09_neural_paged_xsim.log`, `11_lru8_xsim.log`. Stage C = 32 neurons × 4 ticks, **128** M02-scored signed16 RTL updates, **8 spikes, 10 page fills, 8 dirty writebacks, fault quarantine** through original AMD SmartConnect. Stage D = **8-slot × 256B = 2048B** RTL LRU, **19 fills / 11 evictions / 2 dirty writebacks**, fault quarantine through original AMD IP. **Boundaries:** C's driving currents are reference-precomputed and it does NOT instantiate original M05 generated HLS; D tests real RTL page control but not the M05 engine or real DDR. The owner-supplied subset did **not** include original C/D `commit.txt` and before/after SHA manifest readback; obtain a local `cmp` before claiming full run-wide source attestation.

**Current autonomous paged M05-derived HLS candidate:** `hls/m06_paged_rolling/m06_paged_rolling.cpp` / `m06_paged_rolling_replay` is a NEW synthesis-targeted top (original accepted M05 code unchanged), with the signed wheel/synapses/events and exact M04 LIF step, but voltage state entirely through **8×256B canonical 16B-neuron page slots**. Session admission remains max **1024 active neurons, 4096 synapses, 4096 arrivals/tick, 64 ticks, recurrent delay ≤8**. `canonical_first_neuron` supports aligned tiles in a **4096-neuron / 64KiB canonical address region**; the 4096th neuron is *addressable*, not 4096 simultaneously active neurons. HLS has **two separate AXI masters**, read-only `canonical_read_words` → original SmartConnect S00 READ_ONLY, write-only `canonical_write_words` → S03 WRITE_ONLY. Actual HLS AXI data width, generated port names, synthesis resources, coherency/order and physical SmartConnect binding **NOT VERIFIED**. `tests/test_m06_paged_rolling_hls.py` native g++ verifies full six-field trace vs untouched M05 rolling and independent M02/M03, signed extremes, 64-tick recurrence, 1 vs 8 slots, upper canonical tiles and last-byte bounds; the native/host Vitis CSim-style bench does not count as genuine Vitis.

**Stage E, NOT EXECUTED in owner Vivado yet:** Existing `scripts/run_m06_original_mem_sc_vendor_xsim.sh` adds genuine vendor-original scratch-64KiB address probe of highest legitimate **page 255** (byte offset 65535 / neuron 4095), actual dirty writeback/reload and illegal page 256 quarantine without an AXI access. Its real required markers are `M06_ORIGINAL_VENDOR_4096_RANGE_PASS` and `M06_ORIGINAL_VENDOR_4096_OUT_OF_RANGE_QUARANTINE_PASS` in `13_4096_xsim.log`. The runner replays previously accepted A–D in a **new** evidence directory; synthetic CI compiles E with a FAKE, unexecuted vendor stub. **Do not mark E passed until owner real XSim log+exit0.**

**Current verified source CI:** six M01–M06 no-board workflows **all green at code commit `1e1a76aecdc3f270345ce83bcd4d12f38be5b69d`**; M06 host tests **158/158 PASS**, M05 430 discovered with one optional pre-Icarus skip, standalone RTL/Icarus CI checks PASS. This is separate from original vendor 2025.2 simulator evidence. The new handoff doc commit is documentation-only and must receive fresh CI verification.

## 3. EXACT NEXT USER COMMANDS — send FIRST to owner in the new chat

**Phase A — pull current M06 / local source verification and inspect existing successful C/D without retesting them.** Do not claim command outputs before owner runs. The following are safe, no programming / real DDR:

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
git status --short
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
bash -n scripts/run_m06_paged_rolling_hls.sh
bash -n scripts/run_m06_original_mem_sc_vendor_xsim.sh

# Already-successful original C/D, READ ONLY. Do not overwrite/rerun.
export CD="$HOME/Thesis_Evidence/m06_original_vendor_mem_sc_xsim_20261109T225500Z_Q55EJq"
cat "$CD/result.txt" "$CD/commit.txt"
cmp "$CD/sha_before.txt" "$CD/sha_after.txt"
grep -E 'M06_ORIGINAL_VENDOR_NEURAL_PAGED_|M06_ORIGINAL_VENDOR_LRU8_'   "$CD/09_neural_paged_xsim.log" "$CD/11_lru8_xsim.log"
```

**Phase B — FIRST NEW owner gate: genuine Vitis 2025.2 CSim+C synthesis of NEW paged engine.** The effective settings path has historically been `$HOME/Vivado/2025.2/Vitis/settings64.sh`. Stop on the first real error, keep `~/Thesis_Evidence` original folder. Run `--synth` once (it automatically runs real CSim first). Do NOT attempt `--cosim` until synth successfully completes and the generated-header audit is understood.

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source "$HOME/Vivado/2025.2/Vitis/settings64.sh"
vitis-run --version
bash scripts/run_m06_paged_rolling_hls.sh --synth
echo "M06 paged Vitis synth trial exit: $?"

export HLS="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d   -name 'm06_paged_rolling_hls_synth_*' | sort | tail -n 1)"
echo "Evidence: $HLS"
cat "$HLS/result.txt" "$HLS/commit.txt" "$HLS/report_paths.txt" 2>/dev/null || true
cmp "$HLS/source_before_sha256.txt" "$HLS/source_after_sha256.txt" 2>/dev/null || true
tail -n 70 "$HLS/01_csim.log" 2>/dev/null || true
tail -n 95 "$HLS/02_csynth.log" 2>/dev/null || true

# ONLY after result.txt is exit_status=0 and a true csynth report exists:
python3 scripts/m06_paged_hls_port_audit.py   --hls-evidence "$HLS"   --output "$HOME/Thesis_Evidence/m06_paged_hls_ports_$(date -u +%Y%m%dT%H%M%SZ)_$$.json"
```

**Owner should return:** real `result.txt`, `commit.txt`, `01_csim.log` (or relevant failing lines), `02_csynth.log`, `report_paths.txt`, actual `*_csynth.rpt` if present, port-audit JSON/result, source SHA compare and first failure. If Vitis fails or exits nonzero, the *new chat must debug first actual failure* and produce a source/testing fix + CI; do not automatically ask owner to rerun or call genuine RTL generated. The existing `scripts/m06_paged_hls_port_audit.py` expects a genuine source-synthesized top with two separate read/write m_axi groups; actual names/data widths are a measurement, not an assumption.

**Phase C — INDEPENDENT SECOND owner gate: original AMD SmartConnect Stage E**. It need not wait for HLS if separately useful, but best to assess Phase B first to avoid burning repeat simulator cycles. It runs **A–E in a NEW unique evidence folder**, no board/real DDR:

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
vivado -version
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
cat "$D3/result.txt"
bash scripts/run_m06_original_mem_sc_vendor_xsim.sh   "$D3" "$PORTS/02_original_mem_sc_ports.txt"   "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json"
echo "M06 original vendor A-E XSim exit: $?"

export E="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d   -name 'm06_original_vendor_mem_sc_xsim_*' | sort | tail -n 1)"
echo "Evidence: $E"
cat "$E/result.txt" "$E/commit.txt" 2>/dev/null || true
cmp "$E/sha_before.txt" "$E/sha_after.txt" 2>/dev/null || true
grep -E 'M06_ORIGINAL_VENDOR_4096_|M06_VENDOR_4096_FAIL|ERROR:|FATAL'   "$E/12_4096_xelab.log" "$E/13_4096_xsim.log" 2>/dev/null | tail -n 80 || true
tail -n 65 "$E/13_4096_xsim.log" 2>/dev/null || true
```

**Owner should return:** fresh `result.txt`, `commit.txt`, SHA before/after comparison, `13_4096_xsim.log`, `12_4096_xelab.log` on fail, and earliest error in `03_xvlog.log` if E was not reached. Preserve all older original AMD evidence untouched. Do not fabricate Stage E, generated memory width adaptation or DDR proof.

## 4. After owner gates: next coding and M06 acceptance plan

1. If real Vitis synth succeeds, inspect actual **CSim**, **csynth resource/latency**, **two independent memory read/write M_AXI port roles**, generated Verilog widths/AXI-Lite and stream interfaces, and HLS BRAM/state inference. Correct only true errors; if accepted, request **real `--cosim`** using the same new runner in a separate immutable folder, with independent neural M02 trace replay. New HLS cannot be bound by guessing widths.
2. Once Stage E proves legal high-page and out-of-range quarantine, explicitly address **remaining integration**: connect real generated `m06_paged_rolling_replay` to original AMD `mem_sc` READ_ONLY S00 / WRITE_ONLY S03, keep read/write coherency ordering and transaction completion, verify 256-bit input vs actual HLS M_AXI width with appropriate explicit conversion, and reverify complete canonical image with original real IP and paged neural outputs. Build a new strictly offline Vivado project if justified; include independent source/BD/RTL SHA and negative cases. Never patch original generated vendor sources or M05 RTL.
3. M06 acceptance: bounded physically representable state slots vs logical state, page identity/timestamp/dirty eviction/restoration/fault poison, M02 exact numerical traces with forced capacity pressure, strict DMA/AXI boundary checks, and original vendor IP functional evidence. Distinguish **offline simulated scratch** from actual PS DDR Linux allocator/ownership and real board hardware. Full physical deployment and measurements belong later stages, require explicit separate authorization. No M07 work and **no merge PR #80** until owner acceptance.
4. The existing C/D owner file subset did not include source `commit.txt` and `sha_before/after` attestation. The local read-only `cmp` in Phase A resolves that gap **if operator supplies actual outputs**; don't silently infer them from the supplied two logs.

## 5. Preservation, engineering workflow and safety — MANDATORY

- Work **only on the current active M06 branch** `agent/neuromorphic-accelerator-v1-m06-ddr-residency`, draft PR #80 (not old merged M05 branch); commit independently testable increments. Preserve M05 acceptance at original scope; don't backport D4 tasks into M05.
- Preserve all original genuine owner **pass and failed** `~/Thesis_Evidence/` artifacts and signed32 generated HLS/Vivado original products. The agent can inspect GitHub source/CI but cannot execute owner-installed Vivado/Vitis 2025.2 or see external immutable `~/Thesis_Evidence/` unless user supplies logs/files. Read-only evidence attestation first; never overwrite vendor IP or mutate `source_before_sha256` manifests, never conflate source, synthetic fixtures, Icarus RTL, true vendor XSim, genuine Vitis HLS and physical hardware.
- For **each** source increment: implement source + focused independent POSITIVE and NEGATIVE cases, preserve immutable original test fixtures, update `docs/M06_CLOSEOUT_HLS_AXI_OWNER_GATES_2026_11_09.md`, `docs/M06_NEXT_CHAT_HANDOFF_2026_11_09.md`, `docs/M05_TESTS_EXPLAINED.md` (if shared) and a stage-specific tests explanation/runbook plus `roadmap.md`. Run local `python3 -m compileall -q src scripts tests`, `python3 -m unittest discover -s tests -p 'test_m06*.py' -v`, M05 and M01–M04 regression tests, RTL/Icarus, available HLS-native benches, and verify all **SIX** M01–M06 GitHub Actions workflows at each updated HEAD. Provide exact local Ubuntu/VS Code pull/test/repro commands to owner **after every source change**. Keep existing source SHA and generated-output SHA. Do not claim user-local tests without actual logs.
- Before any **new** owner 2025.2 runner, require a NEW unique evidence folder and documented result.txt, commit.txt, source-hash/manifest, raw tool stderr/stdout, strict independent audit, and first-error diagnostics. Never force a tool PASS based on printed Tcl echo/synthetic signs. On genuine failure, analyze **first actual error**, fix source/regressions, run CI, then provide fresh runner commands. No repeated owner-run requests before reading existing original results.
- **Hard safety boundary:** absolutely NO programming/JTAG/XSDB, halting ARM/A53, reflashing, destructive PS/Linux DDR, MMIO, bitstream for deployment, board boot, or physical measurement. Physical actions require separate explicit operator permission, safe buffer ownership/isolation and fresh provenance plus prescribed power-cycle/JTAG recovery checks. Never repurpose historical v3 JTAG scripts or overwrite any archived original signed32 HLS RTL. No merge / M07 advance without user authorization.
- Numeric and research integrity: M02 dense/event is the independent neural truth; M03 PC-only traffic analytics are not FPGA bytes; all real HLS timing estimates are NOT full PS/PL routed results. Model event-order, zero/cancel events, saturation, recurrent delay, sticky failure/timeout and transaction quiescence honestly. Disclose bounds (1024 active/session vs 4096 canonical capacity). Credit YANA/SENECA/HiAER when applicable, avoid proprietary IP source sharing without need.

## 6. Context references

`docs/M05_ACCEPTANCE_REVIEW_2026_11_09.md` (actual M05 acceptance); `docs/M06_CLOSEOUT_HLS_AXI_OWNER_GATES_2026_11_09.md` (older gate design), `docs/M06_M05_NATIVE_AND_VENDOR_STAGE_CD_INTEGRATION_2026_11_09.md` (accepted original A/B and C/D detail), `scripts/run_m06_paged_rolling_hls.sh`, `scripts/m06_paged_hls_port_audit.py`, `scripts/run_m06_original_mem_sc_vendor_xsim.sh`, `scripts/m06_vendor_evidence_attest.py`, `docs/M06_SOURCE_INTEGRATION_2026_11_09.md` (first M06 models), `docs/M05_PC_ONLY_VERIFICATION.md`, `roadmap.md`.

**New chat first action:** read THIS file and current branch/source/scripts, confirm git + PR and CI HEAD, then present **Phase A+B user-local commands** promptly. If previous owner results not supplied, do not claim new tool runs; wait for original logs. After the Vitis gate, diagnose/continue as far as possible in the current conversation, then handle Stage E and the true binding gate, documenting exact acceptance and keeping M06 open until owner approval.
