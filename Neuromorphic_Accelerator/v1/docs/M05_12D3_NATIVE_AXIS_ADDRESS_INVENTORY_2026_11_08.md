# 2026-11-09 UTC — SAME M05.12d.3: genuine native-AXIS and six-bank Vivado inventory ACCEPTED; next explicit address map + full BD validation (OFFLINE owner trial)

**Milestone management:** Continue the existing **single M05.12d.3**, no new M05.x or D3.x milestone. Continue PR #79 DRAFT/UNMERGED. No physical FPGA, Linux /dev/mem, DDR ownership, JTAG, device programming, bitstream or performance/timing proof.

## Newly ACCEPTED original owner evidence

Owner provided `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_20261109T043302Z_KCWN0u`, checkout `d25d35c1a9b3a68b0970ddf5035ea20bfaa8d1d2`, **`result.txt exit_status=0`**, genuine original 2025.2 Vivado HLS preflight PASS, actual FOUR inferred native AXI4-Stream interface nets with all 24 original 128/192-bit TDATA/TVALID/TREADY pin widths/directions; original four DMA-facing 256-bit AXIS, seven PS control links to six distinct slaves, five DMA/PS memory links, 16 clocks and eight correct resets. No old BD 41-1306 scalar-interface override warnings reappeared. Genuine independent graph audit PASS.

**Crucial new six address-segment evidence:** real owner read-only Vivado report, independently audited PASS, lists exactly `/dma_neurons/S_AXI_LITE/Reg`, `/dma_synapses/S_AXI_LITE/Reg`, `/dma_external/S_AXI_LITE/Reg`, `/dma_trace/S_AXI_LITE/Reg`, `/shell/s_axi/reg0`, `/hls/s_axi_control/reg0`, and real PS control master space `/ps/Data`. Its address status remained `NOT_RUN` — these were real discovered **unassigned** slave segment objects, NOT decoded PS address ranges. All previous evidence retained, including earlier failed owner trials and the now-accepted original signed32 Vitis HLS contract `neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na`.

## Single next development increment: six real explicitly mapped AXI4-Lite apertures, and true Vivado validation attempt

Only the NEW **separate** candidate `scripts/m05_12d3_address_validate_candidate.tcl` and `scripts/run_m05_12d3_address_validate_candidate.sh` perform these steps. The already-PASS native grouped AXIS Tcl/runner, original signed32 C++/generated RTL and original owner evidence are unchanged.

The owner must explicitly supply an OFFLINE-ONLY six-line plan, e.g. repository-tracked `scripts/m05_12d3_control_apertures_candidate.txt`, NOT an OS MMIO entitlement:

| Slave | Explicit proposed PS base | Size | Actual authentic slave segment |
| --- | --- | --- | --- |
| DMA neurons MM2S | 0xA0000000 | 64KiB | `/dma_neurons/S_AXI_LITE/Reg` |
| DMA synapses MM2S | 0xA0010000 | 64KiB | `/dma_synapses/S_AXI_LITE/Reg` |
| DMA external MM2S | 0xA0020000 | 64KiB | `/dma_external/S_AXI_LITE/Reg` |
| DMA trace S2MM | 0xA0030000 | 64KiB | `/dma_trace/S_AXI_LITE/Reg` |
| M05 session shell | 0xA0040000 | 64KiB | `/shell/s_axi/reg0` |
| Original Vitis neural HLS | 0xA0050000 | 64KiB | `/hls/s_axi_control/reg0` |

This range selection is **an explicit offline candidate based on AMD UG835 examples**, NOT a claim that 0xA0000000 is an OS-permitted reservation on the real K26. Any future Linux/device-driver physical allocation requires owner hardware-side memory/resource proof separately. The `src/neuromorphic_accelerator_v1/m05_12d2_control_map.py` remains a pure proposed-plan validator and does not silently assign any address; new `m05_12d3_address_validate_audit.py` imports its immutable aperture constraints, checks six original HLS Vitis-register offsets including 0x40, and rejects zero, overlap, unexpected bank, misaligned/power-of-two/range failures before Vivado.

The new Tcl reuses **the entire original verified HLS/PS/PL graph topology**, authentic HLS Verilog from the accepted original source contract, 12 native stream handshakes through four real AXI interfaces, the six control endpoints, 16 clock and 8 reset pins, and the true PS reset inverter. It preserves the original graph report `02_native_axis_graph.txt` and read-only six-object inventory `05_read_only_address_inventory.txt` for their preexisting independent auditor. **Only after** that, for each of six true Vivado slave segments the Tcl calls `assign_bd_address` with the *explicit* input file's offset/range and *specific* PS master space `/ps/Data` — without `-force`, guessing, or automatically assigning other addresses. It checks the actual returned mapped master segment against a fresh `get_bd_addr_segs -of_objects` slave→master readback and reverse master→slave reference, checks unique PS `/ps/Data/...` name, and reads back actual Vivado `OFFSET` and `RANGE` properties, refusing any mismatch. Actual evidence goes into `06_real_ps_control_address_readback.txt` and is checked independently against the original plan; no fake mapping passes.

Finally, it calls the *actual* `validate_bd_design -force` and records one exact result in `07_full_bd_validation.txt`. **Full validation may genuinely fail** (e.g., unassigned separate DMA memory-master/PS DDR-related segments, clock/protocol propagation, or missing width adapter). If it does, owner trial overall **EXIT1**, with previous six successful mapping records and graph audit still available. This is NOT an address assignment bug unless those records themselves fail; never mark full BD accepted on a partial mapping PASS. Even a full BD validation PASS is NOT yet generated SmartConnect 256→128 width-adapter output product proof, bitstream proof, DDR buffers or physical timing.

Fresh runner writes `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_addr_validate_<UTC>_XXXXXX` with source hashes, commit/worktree status, explicit plan path, original HLS contract identity, plan-only admission, original HLS preflight, real Vivado transcript, original 4/7/5/4-net readback, old read-only six address-segment inventory, newly assigned exact PS mappings, exact validation outcome, original graph audit and independent address audit. All previously accepted evidence remains untouched.

**Authoritative tool references:** AMD Vivado 2025.2 UG835 `assign_bd_address` takes `-target_address_space`, `-offset`, `-range`, and specific slave segment objects; `validate_bd_design -force` runs full design validation (not just `-steps addressing`). `get_bd_addr_segs` maps slave↔master references and UG912 defines `OFFSET`/`RANGE` on returned master segments. Source links: https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/assign_bd_address and https://docs.amd.com/r/en-US/Vivado-Design-Suite-Tcl-Command-Reference-Guide-UG835/validate_bd_design and https://docs.amd.com/r/en-US/ug912-vivado-properties/BD_ADDR_SEG

## Owner VS Code terminal verification commands

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
bash -n scripts/run_m05_12d3_address_validate_candidate.sh

# Previously accepted original HLS source contract (DO NOT rerun it)
export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
export CTRL_PLAN="$PWD/scripts/m05_12d3_control_apertures_candidate.txt"
cat "$AUTH_HLS/result.txt"

# Safe, host-only plan admission, no Vivado/physical hardware
python3 scripts/m05_12d3_address_validate_audit.py --plan "$CTRL_PLAN" --plan-only

# Must source REAL Vivado 2025.2 (actual settings64.sh path) in this terminal
vivado -version
# Offline real Vivado explicit six-bank mapping + full validation EXPERIMENT:
bash scripts/run_m05_12d3_address_validate_candidate.sh "$AUTH_HLS" "$CTRL_PLAN"

# A unique output folder is created even when REAL BD validation fails.
export ADDR_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_addr_validate_* | head -n 1)"
echo "New owner address/BD trial: $ADDR_D3"
cat "$ADDR_D3/result.txt"
cat "$ADDR_D3/commit.txt"
cat "$ADDR_D3/working_tree_status.txt"
cat "$ADDR_D3/00_offline_plan_admission.log" 2>/dev/null || true
cat "$ADDR_D3/01_hls_preflight.log" 2>/dev/null || true
cat "$ADDR_D3/02_native_axis_graph.txt" 2>/dev/null || true
cat "$ADDR_D3/05_read_only_address_inventory.txt" 2>/dev/null || true
cat "$ADDR_D3/06_real_ps_control_address_readback.txt" 2>/dev/null || true
cat "$ADDR_D3/07_full_bd_validation.txt" 2>/dev/null || true
cat "$ADDR_D3/04_independent_original_graph_audit.log" 2>/dev/null || true
cat "$ADDR_D3/08_independent_address_validation_audit.log" 2>/dev/null || true
tail -n 200 "$ADDR_D3/03_vivado.log" 2>/dev/null || true
cat "$ADDR_D3/source_sha256.txt"
```

If result is EXIT1 from a real Vivado command, **keep evidence intact**; original Vivado log and both independent audits will identify whether the failure was map assignment/readback or whole-BD validation. No fabricated successful acceptance. This is one ongoing M05.12d.3 effort; no separate milestone names created.

---

> **2026-11-09 UTC — ORIGINAL OWNER native grouped-AXIS Vivado graph successfully ran; combined result EXIT1 only because read-only address inventory used empty `PATH` property (CORRECTED in source):** Owner fresh `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_20261109T042636Z_NzIAw5` at `0d271faba545c8ede78a7da9936bc16b2c2df3c7` recorded original preflight PASS, actual **four native inferred grouped AXI4-Stream interface LINKs**, 24 original underlying pin width/direction readbacks, seven PS-control + five DMA-memory + four 256-bit DMA AXIS links, 16 clock/8 reset endpoints, real `PASS: M05.12d.3 genuine HLS grouped native AXIS connected`. No new `BD 41-1306` since the shell no longer connects individual AXIS signal pins. But **`result.txt exit_status=1`** because the separate address-inventory/independent audit produced `SLAVE|dma_neurons|dma_neurons/S_AXI_LITE|` and equivalents **for all six**, even though `get_bd_addr_segs -of_objects` found six Vivado segment objects; `get_property PATH $segment` returned the empty string. The PS master space reported correctly `/ps/Data`. Existing independent audit correctly rejected the empty names. AMD UG835 `get_bd_addr_segs` documents returning segment objects (which render canonical `/cell/interface/Reg` names in Tcl). **New source fix:** record the actual returned `segment` object directly as its canonical Tcl name (after checking real cell namespace), *not* the missing `PATH` property; require full original AXI interface ownership in the independent auditor, reject empty/foreign names. Two new host tests reproduce the six blank owner records, show they fail, and verify synthetic correctly scoped object names without claiming PS assignment. Original EXIT1 and all previously accepted proof folders untouched. **A fresh run of the SAME owner command below is mandatory** to prove a full result exit0, six actual segment paths, real audit PASS. No new PS address, BD validation, converter, PS/DDR, or physical board claim.

# M05.12d.3 — Native AXI4-Stream Interface Normalization + Six-Bank Address Inventory

**Status:** source-developed new first offline native-AXIS rewire candidate; genuine **owner Vivado 2025.2 rerun required**. Draft PR #79 stays open/unmerged. No physical FPGA, DDR, Linux PS MMIO, JTAG, bitstream, board power or netlist timing permitted.

## Accepted original-owner evidence (do not rerun/mutate)

- Source contract: `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na`, at commit `f5c305ccb676d30fe8d43fbe09f30b57a4c3eca6`, `result.txt exit_status=0`; exact real Vitis HLS 2025.2 `m05_rolling_replay` ports, 26 Verilog siblings, original generated driver AXI4-Lite map, frozen signed32 CPP SHA256 `24c4de87b5557cd536b33fe518595d56133e2ac737786bdf0d6fdbc53a687073`.
- Original connected partial PS/PL graph (no HLS): `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_connected_20261109T032316Z_WQjAyg`, genuine owner full partial audit PASS, original 15 interface nets.
- **NEW owner accepted REAL HLS module attachment:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_hls_connected_20261109T040940Z_h2Ni5q` at source `e82fd1e9bf364581fc184ca7b523b748d97d73ce`, **`result.txt exit_status=0`**, fresh source preflight, real Vivado six-bank PS graph PASS and independent auditor PASS: 4×256-bit DMA/shell interfaces, 7 PS control interface links (including new sixth HLS AXI4-Lite), 5 DMA/PS memory links, 12 exact original native HLS scalar pair nets (128/192-bit data with individual valid/ready), 16 common clocks, 8 reset consumers, one genuine PS reset inversion chain. The reported PS HP0 is 128-bit while DMA memory AXI-MM is 256-bit. **Real neural attachment is therefore ACCEPTED as a scalar-connected graph only**, not BD validation, address assignment, width converter or DDR.
- The original Vivado transcript of that successful scalar graph has **24 real `WARNING: [BD 41-1306]` warnings** (two endpoints × 12 pair nets). Vivado recognized its grouping as `shell/hls_neuron`, `hls/neurons`, `shell/hls_synapse`, `hls/synapses`, `shell/hls_external`, `hls/external_events`, `hls/trace`, `shell/hls_trace`. Each per-pin `connect_bd_net` overrode the inferred AXI4-Stream interface grouping; AMD UG994 states individually connected pins are removed from the encompassing interface connection and may not be reconstructed on `write_bd_tcl`. **This warning is not a data/RTL error and does not negate owner scalar connectivity PASS; it does need correction before grouping-level BD validation**. Source: [AMD UG994 Connecting Interface Signals](https://docs.amd.com/r/2020.2-English/ug994-vivado-ip-subsystems/Connecting-Interface-Signals).

## New separate warning-free native-AXIS implementation

The new `scripts/m05_12d3_native_axis_candidate.tcl` is a **new source-only candidate**, not a mutation of the accepted Tcl, report, signed32 CPP or 26 generated Verilog siblings. It loads every authentic HLS file only after the existing strict SHA256 source/RTL/register preflight. It reuses the owner-accepted PS/PL topology, real six-bank SmartConnect and genuine 1-bit reset inverter (no guessing of read-only `C_EXT_RESET_HIGH=1`).

For each of the 12 existing neural signal connections, it verifies the **24 original** generated+shell endpoint pin direction and 128/192-bit data widths by real Vivado pin readback, but does **not** call `connect_bd_net` on any of those pins. Instead it requires and connects **four authentic inferred native AXI4-Stream interface pairs**, checking MASTER/SLAVE modes, unique interface nets, and exactly two interface endpoints:

| Original shell HLS native interface | Genuine Vitis HLS interface | Payload |
|---|---|---|
| `shell/hls_neuron` (MASTER) | `hls/neurons` (SLAVE) | 128-bit |
| `shell/hls_synapse` (MASTER) | `hls/synapses` (SLAVE) | 192-bit |
| `shell/hls_external` (MASTER) | `hls/external_events` (SLAVE) | 128-bit |
| `hls/trace` (MASTER) | `shell/hls_trace` (SLAVE) | 192-bit |

Native AXIS streams have TDATA/TVALID/TREADY, no invented TKEEP/TLAST. Four original 256-bit DMA-facing AXIS interfaces remain unchanged; HLS does not inherit DMA padding. The new graph auditor requires exact 4 native interface net pairs, all 24 original signal declaration contracts, 4 DMA shell stream nets, 7 control interfaces, 5 memory links, 16 clock and 8 reset consumers, original PS width 128, original D3 polarity and two distinct inversion nets. It refuses truncated/duplicated/wrong/aliased nets and claims of unassigned addresses or nonexistent width adapters.

The new runner **fails if Vivado emits a `WARNING: [BD 41-1306]`** again. It produces a unique `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_<UTC>_XXXXXX` evidence directory, recording result, source commit, repo status, source SHA256, old HLS contract path, preflight PASS, actual Vivado transcript, actual new group-level graph, and independent audit. The original scalar-evidence directory is untouched.

### NEW: read-only Vivado six-bank address inventory

The candidate also reports **actual address-segment objects** exposed by Vivado for each of `dma_neurons/S_AXI_LITE`, `dma_synapses/S_AXI_LITE`, `dma_external/S_AXI_LITE`, `dma_trace/S_AXI_LITE`, `shell/s_axi`, `hls/s_axi_control` and PS control master `ps/M_AXI_HPM0_FPD`. See `05_read_only_address_inventory.txt`. This is **discovery, not address assignment**. If a Verilog Module Reference lacks an address segment, it records `NO_BD_SEGMENT_YET` and no fictitious segment, base or decoder is introduced. The independent audit validates six identities and the PS master inventory, but the number of discovered address segments is only a diagnostic.

Crucial potential finding: Vivado may infer an AXI4-Lite native HLS *interface* without registering its expected IP-XACT *memory-map segment*. If so, a real vendor-generated HLS component packaging step (reusing the exact original Vitis RTL/driver and hash manifest, not fabricating a memory map) might be required before the sixth bank can be address-decoded. No claim is made until original owner Vivado observation.

**Still OPEN:** explicit nonoverlapping *actual* PS AXI4-Lite address segments for six real control banks, HLS native offsets relative to genuine physical base, clock FREQ_HZ propagation, `validate_bd_design`, generated SmartConnect 256-bit DMA to 128-bit PS-HP0 converter, generated IP simulation/output products, reproducible PS/DDR ownership and full system runtime. No physical FPGA operations.

## Operator VS Code verification (new original evidence)

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

# Source Vivado 2025.2 in current terminal first, if necessary.
vivado -version
export AUTH_HLS="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T035628Z_pPZ6na"
cat "$AUTH_HLS/result.txt"
bash -n scripts/run_m05_12d3_native_axis_candidate.sh

# Only NEW native grouped AXIS graph + discovery, never board/JTAG/DDR.
bash scripts/run_m05_12d3_native_axis_candidate.sh "$AUTH_HLS"

export NEXT_D3="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_native_axis_* | head -n 1)"
echo "$NEXT_D3"
cat "$NEXT_D3/result.txt"
cat "$NEXT_D3/commit.txt"
cat "$NEXT_D3/working_tree_status.txt"
cat "$NEXT_D3/01_hls_preflight.log" 2>/dev/null || true
cat "$NEXT_D3/02_native_axis_graph.txt" 2>/dev/null || true
cat "$NEXT_D3/05_read_only_address_inventory.txt" 2>/dev/null || true
cat "$NEXT_D3/04_independent_audit.log" 2>/dev/null || true
tail -n 240 "$NEXT_D3/03_vivado.log" 2>/dev/null || true
cat "$NEXT_D3/source_sha256.txt"
```

Owner exit0 PLUS genuine unmodified Vivado grouped interface nets PLUS independent auditor PASS PLUS **no BD 41-1306** warnings would constitute this **new native interface cleanup gate**. Otherwise preserve fresh EXIT1 output and diagnose from actual Vivado log; never reinterpret old scalar PASS as new grouped PASS.

## Tests and CI meaning

`tests/test_m05_12d3_native_axis_candidate.py` contains ten additional host **synthetic-only** tests: strict expected grouped axes+six controls+D3 clocks, missing/duplicate/wrong native endpoints, corruption of all scalar data widths and directions, reused DMA/native AXIS net, missing real HLS control/reset/clock, six-bank inventory with a missing segment reported faithfully, rejection of fabricated address assignments, no `connect_bd_net` of native individual signals, BD41-1306 runner guard and no hardware operations, accepted source immutability, and read-only CLI audit failure path. **Tests cannot certify new original grouped Vivado graph.** Run result is needed. Original HLS and old real HLS scalar proofs remain accepted independently.

