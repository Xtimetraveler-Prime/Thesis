# M05.12d.3 — Real signed32 HLS + already verified PS/PL graph: FIRST OFFLINE ATTACHMENT CANDIDATE

**2026-11-08 local / 2026-11-09 UTC** · same ONE **M05.12d.3** · **draft PR #79 open/unmerged** · offline, source-authenticated generated neural RTL only · no board, JTAG, A53 boot, physical PS/DDR, bitstream, or performance claim.

## Accepted gates and exact new source identity

- **Previously accepted genuine offline partial PS/PL graph:** owner `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_20261109T032316Z_WQjAyg`, original checkout `8385daf1973b94945f9266b8090a52fe83507684`, exit0 Vivado Tcl PASS and independent audit PASS. This proved 15 separate physical Vivado BD interface-net objects: four 256-bit DMA↔shell AXIS, six PS control links for five independent AXI4-Lite banks, five DMA-memory→PS HP0 links; 15 common PL clock participants and seven reset consumers with one genuine 1-bit NOT inverter. It did **not** attach HLS, allocate addresses, validate BD, generate a width adapter or use board/DDR. **Do not rerun this old accepted gate to claim new progress.**
- **New genuine owner authenticated signed32 RTL evidence:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na`, checkout `f5c305ccb676d30fe8d43fbe09f30b57a4c3eca6`, original `result.txt exit_status=0`, `PASS: M05.12d.3 ORIGINAL generated signed32 HLS RTL port/regmap/source attestation`. This binds the real original M05.11c XSim artifact and Vitis 2025.2 RTL `m05_rolling_replay` to source `hls/m05_rolling/m05_rolling.cpp` SHA256 `24c4de87b5557cd536b33fe518595d56133e2ac737786bdf0d6fdbc53a687073`. All 26 generated `.v` siblings and their hashes, all 32 top-level ports, native stream widths/roles, real 7-bit AXI-Lite address bus and genuine generated native register map were accepted. **The original owner working-tree status included preexisting untracked Vivado and Loihi evidence; no original tracked neural/BD file changed.** Preserve this folder, the older failed HLS contract folder and all older D3 evidence untouched.

Actual HLS native register offsets **inside** its yet-unassigned PS control bank are AP_CTRL 0x00, AP_RETURN 0x10, NEURON_COUNT 0x18, SYNAPSE_COUNT 0x20, EXTERNAL_COUNT 0x28, TICKS 0x30, DECAY_NUM 0x38, DECAY_DEN 0x40. These are not PS physical base addresses or Linux device MMIO permission.

## This new first authentic integration increment

The new **separate** `scripts/m05_12d3_hls_connected_candidate.tcl` is a controlled copy of the previously accepted D3 PS/PL IP Integrator topology, preserving the previously verified original Tcl, runner, independent auditor and all original evidence. **It is not yet an accepted native Vivado run.**

1. Original signed32 **real Vitis-generated** `m05_rolling_replay.v` plus every generated sibling is read from the original Vitis `work/hls/syn/verilog` path, exactly as resolved by the accepted HLS evidence. No mock IP, reconstructed/retimed kernel, fake `ap_return` or rewritten original HLS module is involved. New `scripts/m05_12d3_hls_connected_preflight.py` independently recomputes the entire accepted attestation including all actual RTL SHA256 values, original implementation/driver-map, correct source hash and exact full report, before calling Vivado.
2. Vivado source-management remains `All`; the original `m05_12d_axis_shell_ref` is reused **unchanged**. An actual `m05_rolling_replay` RTL Module Reference `hls` is added to the candidate graph. Original genuine `ctrl_sc` is extended from **1:5** to **1:6**, preserving M00..M04 recipient identities (four DMA AXI4-Lite registers + original M05 session-control shell). The sixth M05 `ctrl_sc/M05_AXI` is connected **only** if genuine Vivado Module Reference infers an actual `hls/s_axi_control` SLAVE interface. Missing or wrong ROLE is a fail-closed first error, never a reason to substitute fake RTL.
3. Exactly **12 independently read-back native signal pair nets** join the original shell's four 128/192-bit native TDATA/TVALID/TREADY handshakes with authentic HLS `neurons`, `synapses`, `external_events`, `trace` generated pins. The actual `DIR` output→input roles, 128/192 TDATA widths (Vivado `LEFT/RIGHT` pins), unique net membership and exactly two endpoints per scalar net are checked. **No TLAST/TKEEP or 256-bit padding is introduced into native HLS.** The original 4×256-bit DMA/shell AXIS links remain the same endpoint identities.
4. Add `hls/ap_clk` to the preexisting proven single PS-derived PL clock net (now expected 16 clock pins) and `hls/ap_rst_n` to the proven peripheral reset net (now eight reset consumers). The original read-only `proc_sys_reset CONFIG.C_EXT_RESET_HIGH=1` and genuine one-bit reset inverter are unchanged, including two distinct actual PS-reset inversion nets.
5. Strict independent new `scripts/m05_12d3_hls_connected_candidate_audit.py` requires all **16** PS/control/stream/memory interface links (4 existing DMA-shell streams +7 control with sixth HLS +5 DMA-memory), **12 native scalar pair links**, 16 common clocks, eight resets, every previous reset-polarity readback, four DMA role/config rows, PS width128, and explicit negative status for addresses, generated converter and full BD validation. Bad/missing/duplicate/mislabeled links, reused nets, malformed data widths, missing HLS control or prematurely claimed BD/DDR evidence are rejected.
6. `scripts/run_m05_12d3_hls_connected_candidate.sh` requires real locally sourced Vivado **2025.2** and one argument: **the accepted genuine HLS contract evidence directory**. It creates a unique new `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_hls_connected_<UTC>_XXXXXX`, preserves `result.txt` even on failure and saves Git commit/working-tree status, SHA256 of all relevant source, original contract reference, full HLS preflight, real Vivado transcript, actual graph report and independent audit. It does not overwrite or mutate any previous original evidence.

**Current source/host CI status:** at original source implementation commit `da6da432d7b6d0514356656507e894d9fdbd8996`, all five no-board workflows PASS including M05 native suite with **330 named methods** (329 initially pass, one optional Icarus absence skip then mandatory installed-Icarus HLS shell module tests PASS). Ten new **synthetic host-only** `test_m05_12d3_hls_connected_candidate.py` methods cover graph shape, original retained link constraints, corrupted native data/handshake directions, omitted HLS sixth control bank, stale/aliased reset/clock nets, false completion claims, failed provenance inputs and runner no-hardware discipline. This is NOT genuine attached HLS Vivado acceptance, Vivado generated memory-width conversion or address-map validity.

## NEW independent owner-side offline Vivado check — exact VS Code terminal commands

**Safe:** Vivado 2025.2 must be sourced into terminal first (using your actual installed `settings64.sh` path). The command does NOT connect to a board, launch Hardware Manager, run JTAG, program a PL device, or read/write DDR.

```bash
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

# Already accepted original signed32 attestation. DO NOT rerun it.
export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
cat "$AUTH_HLS/result.txt"
cat "$AUTH_HLS/commit.txt"
bash -n scripts/run_m05_12d3_hls_connected_candidate.sh

# Source Vivado 2025.2 in this terminal before the next command!
vivado -version
bash scripts/run_m05_12d3_hls_connected_candidate.sh "$AUTH_HLS"

# A new unique folder exists even on a failing new integration experiment:
export NEXT_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_hls_connected_* | head -n 1)"
echo "Original NEW D3 candidate: $NEXT_D3"
cat "$NEXT_D3/result.txt"
cat "$NEXT_D3/commit.txt"
cat "$NEXT_D3/working_tree_status.txt"
cat "$NEXT_D3/source_hls_contract_evidence.txt"
cat "$NEXT_D3/01_hls_preflight.log" 2>/dev/null || true
cat "$NEXT_D3/01_hls_preflight.txt" 2>/dev/null || true
cat "$NEXT_D3/02_hls_connected_graph.txt" 2>/dev/null || true
tail -n 240 "$NEXT_D3/03_vivado.log" 2>/dev/null || true
cat "$NEXT_D3/04_independent_audit.log" 2>/dev/null || true
cat "$NEXT_D3/source_sha256.txt"
```

**Expected new first-attachment acceptance (if genuine Vivado supports the direct module-reference interface inference):** fresh `result.txt exit_status=0`, genuine `PASS: M05.12d.3 offline REAL HLS + original four DMA PS/PL graph (CANDIDATE: NO ADDR/BD-VALIDATION/DDR)`, independent `PASS: M05.12d.3 independent real signed32 HLS PS/PL graph audit`, and full report with 4/7/5 point-to-point interface nets, 12 native nets, 16 clock pins, eight peripheral/interconnect reset pins, real HLS native control SLAVE role, unchanged PS 128-bit width. **Only a new original owner Vivado 2025.2 exit0+genuine report+independent PASS can close this first attached-graph gate.** If real Vivado does not infer HLS `s_axi_control`, generated module pins/metadata, or does not allow native scalar pin wiring, preserve that new failure as EXIT1; the next SAME-D3 corrective patch should be grounded in the actual Vivado error and possibly use an explicit metadata-only pass-through shell adapter **instantiating the same genuine HLS top**, not a mock.

## Still OPEN in SAME M05.12d.3 milestone — no inflated claims

The new Tcl explicitly marks `address_map=NOT_ASSIGNED`, `data_width_conversion=SMARTCONNECT_CANDIDATE_NOT_GENERATED`, `full_bd_validation=NOT_RUN`. These are intentional **limits**, not forgotten acceptance requirements.

- After actual owner HLS attachment verification, assign six truly disjoint 4KiB PS-visible AXI4-Lite apertures through `assign_bd_address` with actual segment readback and independent nonoverlap (the existing `m05_12d2_control_map.py` is a **proposal**, not physical/decoded PS proof). Native HLS offsets are relative to its own sixth physical base.
- Resolve clock `FREQ_HZ`, actual PS reported 96.968727MHz versus nominal 100MHz and associated interfaces; do not force guessed constants or alter reset polarity without real Vivado readbacks.
- Run genuine `validate_bd_design` and generated SmartConnect IP output-product checks or simulation proving 256-bit DMA AXI-MM → 128-bit PS HP0 width conversion. The accepted partial graph's interface width readback is **not** proof of generated adapter.
- Confirm PS address segments/DDR ownership, AXI protocols, output TLAST, error/session behavior and full offline XSim with actual memory/PS stimuli before calling D3 integrated.
- No physical K26 operations, no PS/Linux-controlled DDR buffer writes, no bitstream, energy, speedup or routed full-system timing claims. PR #79 remains draft and unmerged. Failure evidence remains original and immutable.

