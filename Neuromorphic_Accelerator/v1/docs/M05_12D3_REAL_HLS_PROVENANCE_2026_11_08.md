> **OWNER ORIGINAL POST-STAGE FAILURE / SOURCE FIX — 2026-11-09 UTC:** The user's first genuine read-only HLS provenance runner produced immutable `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_20261109T034756Z_QuSV1u`, **`result.txt exit_status=1`**, error `generated HLS port s_axi_control_AWADDR: got None, expected ('input', 7)`. Actual original generated Vitis HLS v2025.2 non-ANSI Verilog has `input [C_S_AXI_CONTROL_ADDR_WIDTH - 1:0] s_axi_control_AWADDR;`, with `C_S_AXI_CONTROL_ADDR_WIDTH=7`, 32-bit data, `C_S_AXI_CONTROL_WSTRB_WIDTH=(32/8)`. This is a **defect in the source-only attestation parser's narrow numeric-regex assumption**, not evidence of a defect in signed32 generated RTL. Fixed restricted integer-parameter evaluation using Python AST (no dynamic eval), preserved exact original source/RTL/BD/evidence, added native positive fixture from owner-observed declaration syntax and corruption tests. **Do not rerun older accepted PS/PL partial verification** and **do not overwrite** the failed attestation directory. After pulling latest commit, rerun this SAME read-only runner in its own new unique evidence directory and inspect the original `result.txt`, `01_original_hls_contract.txt`, and `02_attestation.log`. CI synthetic PASS is not original-owner Vitis attestation PASS. If another generated-RTL mismatch emerges, preserve it and inspect the true vendor source before editing. No FPGA access, sixth bank or BD validation yet.

# M05.12d.3 — Original signed32 HLS artifact attestation before PS/PL neural attachment

**2026-11-08 local / 2026-11-09 UTC** · **Same M05.12d.3 milestone** · **PR #79 remains DRAFT/UNMERGED**. No physical board operation is authorized. The previously **accepted** owner D3 partial connected graph (checkout `8385daf1973b94945f9266b8090a52fe83507684`) is **not rerun** by this gate.

## Why this new source/evidence gate exists

The accepted Vivado 2025.2 D3 report established 15 genuine PS/PL/DMA/shell interface nets, 15 PL clock pin participants, seven generated reset consumers, genuine 1-bit PS-reset inversion, and PS 128-bit interface properties. The accepted report explicitly did **NOT** attach real HLS or assign AXI addresses or validate the full BD or prove generated 256→128 conversion. Those remain one open D3 milestone.

**Original real neural RTL lives outside Git.** The user-owned accepted M05.11c XSim evidence is:

`~/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy`

Its original `source_impl_evidence.txt` points to the already accepted Vitis `neuromorphic_v1_m05_rolling_impl_*` directory. **Never guess, recreate or replace that referenced implementation.** The generated `work/hls/syn/verilog/m05_rolling_replay.v` and sibling RTL must remain unchanged.

## New independent read-only host-side gate

- `scripts/m05_12d3_real_hls_contract.py` validates M05.11c `exit_status=0` **and** the retained independent raw 256-bit replay PASS marker; follows its one absolute `source_impl_evidence.txt` path; checks referenced original Vitis `exit_status=0`, `top.txt=m05_rolling_replay`, `part.txt=xck26-sfvc784-2LV-c`.
- Checks that the **current, original signed32** `hls/m05_rolling/m05_rolling.cpp` SHA256 equals **both** the frozen Vitis `source_sha256.txt` and the passed M05.11c `source_sha256.txt` recorded values. No HLS source edit or re-synthesis.
- Parses the **actual tool-generated top-level Verilog declarations**, requiring the exact ports exercised by accepted M05.11c XSim: `ap_clk/ap_rst_n`, `interrupt`, native `neurons` 128-bit sink, `synapses` 192-bit sink, `external_events` 128-bit sink, `trace` 192-bit source, each with real `TDATA/TVALID/TREADY` directions. The generated native streams **must not gain synthetic TLAST/TKEEP/TSTRB**. The four 256-bit DMA-facing AXIS signals and their TLAST/TKEEP remain in the existing shell, not the native neural kernel.
- Requires native HLS `s_axi_control` to have the exact **7-bit AWADDR/ARADDR, 32-bit WDATA/RDATA, four WSTRB and all handshake/response signals** observed in prior M05.11c XSim. The HLS `AP_CTRL`, six arguments and `AP_RETURN` offsets are parsed from the **original generated driver or RTL** by `scripts/m05_axis_regmap.py`. All eight offsets must agree with the actual `m05_rolling_replay_control_s_axi.v`; never assign guessed offsets or conflate them with the separate M05 shell registers.
- Rejects missing generated sibling RTL, differences from the M05.11c `generated_rtl_files.txt` original compiled-path list, or missing/conflicting original Vitis generated RAM `.dat` init assets. Records SHA256 of **each current generated sibling** for the next stage.
- `scripts/run_m05_12d3_real_hls_contract.sh` runs this check in a fresh uniquely named `~/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_<UTC>_XXXXXX` directory. It saves `result.txt`, `commit.txt`, `working_tree_status.txt`, `source_xsim_evidence.txt`, `source_sha256.txt`, `01_original_hls_contract.txt` and `02_attestation.log`. The trap preserves a failed run with original exit status. No output overwrites original Vitis, accepted XSim or accepted PS/PL D3 evidence.

**Provenance limitation:** the historical M05.11c manifest lists original compiled Verilog file paths but **did not historically record individual generated Verilog SHA256 values**. This new checker hashes current original generated files and binds their paths, original passed XSim pointer, frozen source digest, control map and RAM availability. It cannot retroactively prove a prior generated byte-for-byte hash that was never retained. Keep that distinction explicit.

## Local Ubuntu VS Code verification (no Vivado required for this check)

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

bash -n scripts/run_m05_12d3_real_hls_contract.sh
export M05_ACCEPTED_XSIM="$HOME/Thesis_Evidence/neuromorphic_v1_m05_11c_real_hls_20261109T000446Z_keEFQy"
test -f "$M05_ACCEPTED_XSIM/source_impl_evidence.txt"
cat "$M05_ACCEPTED_XSIM/source_impl_evidence.txt"
bash scripts/run_m05_12d3_real_hls_contract.sh "$M05_ACCEPTED_XSIM"

export HLS_CONTRACT="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d3_real_hls_contract_* | head -n 1)"
echo "$HLS_CONTRACT"
cat "$HLS_CONTRACT/result.txt"
cat "$HLS_CONTRACT/commit.txt"
cat "$HLS_CONTRACT/working_tree_status.txt"
cat "$HLS_CONTRACT/02_attestation.log"
cat "$HLS_CONTRACT/01_original_hls_contract.txt" 2>/dev/null || true
cat "$HLS_CONTRACT/source_sha256.txt"
```

**Acceptance for this FIRST source contract gate:** fresh original `result.txt exit_status=0`, original `01_original_hls_contract.txt` with all 32 verified native/top pins, eight genuine HLS control offsets and SHA manifests, and `02_attestation.log` exact PASS. A host CI synthetic test PASS is **not** proof that your external HLS files passed. If the owner's gate fails, preserve it and inspect exact real Verilog/driver discrepancies before changing wrapper/Tcl. Do not fake/stub the module or weaken original oracle traces.

## Next development in the SAME M05.12d.3 after accepted generated HLS contract

1. Add a **new** offline Vivado 2025.2 candidate consuming **that exact attested generated RTL** as a Module Reference/real HLS source, not a mock IP; retain the original passed partial D3 Tcl/audit and keep its original evidence immutable. Attach 128/192 native HLS streams to the existing shell without 256-bit native padding. Check directions, widths and actual Vivado net memberships and control interface role.
2. Expand `ctrl_sc` from five to **six independently connected slaves**, leaving original `M00..M04_AXI` linked to the exact existing four DMA controls and shell; connect `M05_AXI` to real HLS `s_axi_control`. Require actual sixth bank interface readbacks and native HLS regmap separately from 4KiB PS apertures.
3. Run genuinely assigned **six nonoverlapping 4KiB control address segments** through `assign_bd_address` + actual readbacks (proposal-only validator is `src/neuromorphic_accelerator_v1/m05_12d2_control_map.py`). No invented PS DDR physical map or claimed Linux ownership. Correct module clock `FREQ_HZ` and AXI bus clock/reset associations without changing passed polarity. Handle 2025.2 inline HDL advisories only when their actual net behavior is verified.
4. Run full offline `validate_bd_design`, original generated SmartConnect output-product checks proving 256-bit DMA AXI memory masters reach 128-bit PS HP0 with a real converter, and separate independent evidence audit and RTL replay. **Stop** on unresolved PS DDR/address/clock/IP constraints. Nothing here authorizes PS boot, DDR traffic, physical K26 JTAG/bitstream or a PR merge.

## Host-only test intent / failure coverage

`tests/test_m05_12d3_real_hls_contract.py` has **eight synthetic negative/contract methods**. It verifies the parsed port count/directions, native data widths, missing/duplicated/unterminated top rejection, forbidden native sidebands, basic ANSI/non-ANSI Verilog declaration forms, rejection of failed/missing original evidence, source/run safety markers and read-only behavior. It does **not** use or invent a successful generated HLS artifact. The only real positive source-contract acceptance is the separate owner-side original tool-artifact check above.

**Scientific/physical boundary:** M02 remains numerical oracle; original M05.11c is already accepted RTL-only XSim; no actual connected HLS PS/PL BD verification, FPGA run, physical timing, A53 DDR buffer, measured energy or speedup is claimed at this stage.
