# M06 — verification-only handoff: G3.3 active HLS/AMD AXI-Lite gate
**2026-11-10 | Read this first in the new chat. This is a verification handoff, NOT permission to implement or merge.**

## 1. Where the previous chat actually stopped

Repository \`Xtimetraveler-Prime/Thesis\`, project \`Neuromorphic_Accelerator/v1\`, branch \`agent/neuromorphic-accelerator-v1-m06-ddr-residency\`, PR **#80** draft/open/**unmerged**.

The last conversational message cited **parser-fix commit \`f7f23b521b5a21bf191ac972a5cce5430f7490cc\`**. A live branch comparison on 2026-11-10 found the branch had advanced **two more commits** to **\`13cacff14d59c2e73b8fafa76c6f06d57672becc\`**, with additional changes **only** in \`scripts/m06_g3_3_hls_control_map.py\` (support for actual Vitis \`ADDR_BITS=7\` metadata in grouped localparams and rejection of duplicate \`ADDR_BITS\`). ALL SIX M01–M06 GitHub Actions were **success** at that tested code commit. This handoff document creates a **later documentation-only HEAD**; check the branch's live HEAD/PR and CI rather than assuming the code SHA is the final branch SHA.

**No newer owner genuine ACTIVE XSim evidence was found or provided in this conversation.** Do not claim G3.3 active was verified by the source-only CI.

Project state at takeover:

| Gate | Accepted scope |
| --- | --- |
| G1 | Genuine corrected Vitis 2025.2 paged-HLS C/RTL cosimulation **PASS**, tested 4 transactions; original HLS files remain SHA-authenticated. |
| G2 | Genuine original AMD D3 SmartConnect A–E offline XSim **PASS**. |
| G3.2 | Genuine **dual 32→256-bit AMD Data Width Converters + ORIGINAL SmartConnect + simulated shared 64KiB canonical memory** BFM XSim **PASS**. Does not prove HLS neural parity. |
| G3.3 idle | Genuine 2025.2 XSim with the **40 actual generated-HLS Verilog files**, both genuine AMD DWCs, original SmartConnect, 64→32 address guards, and shared scratch **PASS for reset/idle only**. Does not prove active operation; earlier idle simulation had missing \`.dat\` warnings, for which a new source-authenticated staging step was developed. |
| **G3.3 active** | **UNVERIFIED:** new \`--mode invalid_geometry\` testbench and parser corrections committed/source-tested, but **no owner rerun** after parser fix. |
| G4 / M06 | **OPEN:** no full independent M02/M03 neuron trace/state and fault/eviction acceptance, no M06 merge. |

M06 architecture: 4096 canonical neurons ×16 bytes = **64KiB** external-state image, 8×256-byte on-chip cache, at most 1024 active neurons/64 ticks, Loihi-inspired digital twin, target \`xck26-sfvc784-2LV-c\`. The original HLS two memory ports have 32-bit data/64-bit address; AMD DWC SI is 32-bit data/32-bit address; original SmartConnect S00 read/S03 write are 256-bit data with 32-bit address. The candidate 64→32 guards and sideband adapters are part of the actual idle build. No physical DDR/JTAG/FPGA claims.

## 2. Exact historical failure and why this run matters

Prior user owner ZIP: \`M06_G3_3_ACTIVE_HLS_AMD_REVIEW_20261110T070129Z.zip\`; original owner folder:

\`~/Thesis_Evidence/m06_g3_3_actual_hls_invalid_geometry_xsim_lz3nplre\`

Historical owner run \`exit_status=1\`, **BEFORE HDL compilation or XSim**, at:

\`\`\`
03_control_map.log rc 2
M06_G3_3_HLS_CONTROL_MAP_REJECTED:
cannot parse generated HLS control-register address constants
\`\`\`

Prior owner data: original 40 HLS RTL hashes, 14 original \`.dat\` init files and staged hashes, 67 AMD vendor RTL hashes, 11 local source hashes unchanged; original two AMD converter XCI checks PASS. Genuine HLS \`.dat\` staging passed. Neither active HLS controller nor the neural engine was exercised by that attempt.

Parser \`scripts/m06_g3_3_hls_control_map.py\` now reads exact **SHA-attested** original \`m06_paged_rolling_replay_control_s_axi.v\` (does not guess offsets), accepts separate and grouped \`localparam\`/parameter \`ADDR_*\` literals, handles Vitis \`ADDR_BITS=7\`, rejects duplicate width metadata, invalid/missing/ambiguous/misaligned/unsupported addresses. Native tests cover the grouped-map path and dynamic \`AP_RETURN\` address.

**NEXT VERIFICATION ONLY:** Run ONE new genuine Vivado 2025.2 \`--mode invalid_geometry\` owner test, with \`ap_start\` / \`ap_done\` and expected error-status return for deliberately invalid neuron geometry. Expected exact XSim success marker:

\`\`\`
M06_G3_3_ACTUAL_HLS_ORIGINAL_AMD_AXILITE_BAD_GEOMETRY_XSIM_PASS
\`\`\`

A genuine PASS additionally needs \`result.txt=exit_status=0\`, original/staged HLS init SHA matches, all original HLS/vendor/local and XCI hashes intact, no unresolved \`.dat\` init warnings, no false \`FAIL\`/fatal marker. **This is an active-control negative-shape smoke, NOT neural inference, canonical memory transaction parity, or G4 success.** If any stage fails, preserve its FIRST evidence directory and ZIP it; do not rerun, suppress checks, change originals or continue development before reviewing the evidence.

## 3. New-chat workflow — strictly verification only, then wait

New instance's FIRST ACTIONS:
1. Read this doc, \`docs/M06_G3_3_ACTUAL_HLS_AMD_IDLE_OWNER_GATE_2026_11_10.md\`, and current \`roadmap.md\` top G3.3 status. Read \`scripts/m06_g3_3_hls_control_map.py\`, \`scripts/run_m06_g3_3_actual_hls_idle_xsim.py\`, and two test files \`tests/test_m06_g3_3_hls_control_map.py\`, \`tests/test_m06_g3_3_active_axilite_tb.py\`. Confirm PR #80 and current branch HEAD and six CI workflows.
2. Do **NOT** change implementation, create a branch, rerun accepted G1/G2/G3.2/idle, regenerate AMD IP, start positive neural workload, merge, or advance G4. This chat is ONLY to establish the next owner verification step, then receive and interpret one ZIP.
3. Give the owner the EXACT commands and ZIP packager below. Mention that the prior chat's \`f7f23b5...\` is stale: the actual tested parser code commit is \`13cacff...\`, plus this document-only commit. The user should \`git pull\` the latest branch and confirm \`git rev-parse HEAD\` against the current PR HEAD. Do not require checkout of the stale \`f7f23b5...\` commit.
4. After the owner uploads the new ZIP: inspect \`result.txt\`, actual first failing log or true XSim PASS, \`03_real_hls_axilite_control_map.json\`, source/data/AMD hashes, and \`08_operator_invocation_console.log\`. Summarize true gate outcome and **only then** resume G3.3/G4 development if supported by evidence and user's instruction. If failure, fix the *first genuine error* rather than guessing.
5. For all future vendor runs, preserve timestamped untouched \`~/Thesis_Evidence/\` directories. Always include exact git commands, exact local file paths, exact acceptance marker and a **one-ZIP packaging command accepting PASS or FAIL**. Never request proprietary AMD .xci/HDL unless justified. No JTAG, board programming, physical DDR, PS/Linux halt, bitstream, M07 or PR merge without fresh explicit approval.

## 4. Copy-paste local verification command — NO NEW DEVELOPMENT

\`\`\`bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g3_3_hls_control_map.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_3_active_axilite_tb.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
\`\`\`

The targeted parser suite had 6 methods and active AXI-Lite test suite 4 at the last source-tested code. If the Icarus compile-only test skips, install Icarus and rerun; never interpret fake vendor stubs as functional XSim.

\`\`\`bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
xvlog -version

export HLS="$HOME/Thesis_Evidence/m06_paged_rolling_hls_cosim_20261110T022111Z_iMNors"
export D3="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d3_ip_output_20261109T073025Z_y05CSJ"
export PORTS="$HOME/Thesis_Evidence/m06_vendor_xsim_port_contract_20261109T181345Z_f4X4Of"
export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
export INV="$HOME/Thesis_Evidence/m06_g3_3_hls_source_inventory_20261110T061525Z_qbrHKZ"

# Existing original owner evidence must be present. No recreation requested.
for dir in "$HLS" "$D3" "$PORTS" "$DW" "$EX" "$INV"; do
    test -d "$dir" || { echo "MISSING ORIGINAL OWNER EVIDENCE: $dir"; exit 2; }
done
for dir in "$HLS" "$EX" "$INV"; do
    test "$(cat "$dir/result.txt")" = "exit_status=0" || {
        echo "PRIOR OWNER EVIDENCE NOT ACCEPTED: $dir"; exit 2;
    }
done

export INVOCATION_LOG="$HOME/Thesis_Evidence/m06_g3_3_active_corrected_invocation_$(date -u +%Y%m%dT%H%M%SZ).log"
export BEFORE_FILE="$(mktemp)"
find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
    -name 'm06_g3_3_actual_hls_invalid_geometry_xsim_*' | sort > "$BEFORE_FILE"

set -o pipefail
if python3 scripts/run_m06_g3_3_actual_hls_idle_xsim.py \
    --mode invalid_geometry \
    --hls-cosim "$HLS" \
    --original-d3 "$D3" \
    --original-report "$PORTS/02_original_mem_sc_ports.txt" \
    --original-headers "$PORTS/08_mem_sc_wrapper_headers_nonansi_fixed.json" \
    --original-dwc "$DW" \
    --amd-export "$EX" \
    --accepted-inventory "$INV" 2>&1 | tee "$INVOCATION_LOG"
then
    echo "G3.3 ACTIVE CONTROL VERIFICATION COMMAND SUCCEEDED"
else
    echo "G3.3 ACTIVE CONTROL FAILED; preserve first evidence, do not rerun unchanged"
fi

export LINK="$(comm -13 "$BEFORE_FILE" \
    <(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d \
        -name 'm06_g3_3_actual_hls_invalid_geometry_xsim_*' | sort) \
    | tail -n 1)"
echo "NEW EVIDENCE DIRECTORY: \${LINK:-NOT_CREATED}"
if test -n "$LINK" && test -d "$LINK"; then
    cat "$LINK/result.txt" "$LINK/commit.txt"
    test ! -f "$LINK/03_control_map.log" || cat "$LINK/03_control_map.log"
    test ! -f "$LINK/07_xsim.log" || tail -n 80 "$LINK/07_xsim.log"
    test ! -f "$LINK/owner_error.txt" || cat "$LINK/owner_error.txt"
fi
\`\`\`

If \`LINK\` is empty, the invocation log still exists and MUST be packaged. DO NOT point the user to an older successful or failed \`LINK\`.

## 5. EXACT FILES to submit — package ONE ZIP on PASS or FAIL

Location of all per-run files: \`$LINK\` = \`/home/dna/Thesis_Evidence/m06_g3_3_actual_hls_invalid_geometry_xsim_<new_unique_suffix>/\`.

The per-run file allowlist is:
- Result/provenance: \`result.txt\`, \`commit.txt\`, \`worktree_status.txt\`, \`owner_error.txt\`, \`00_accepted_hls_interface_inventory.json\`.
- Original DWC/AMD plan: \`01_reaudit_dwc_owner.log\`, \`01_reaudit_dwc_sim_sources.json\`, \`01_reaudit_dwc_sim_paths.txt\`, \`02_vendor_plan.log\`, \`02_original_sc_compile_plan.json\`, \`03_merge_plan.log\`, \`03_connected_vendor_compile_plan.json\`.
- Genuine init/control/TB: \`03_hls_original_dat_stage.log\`, \`03_hls_original_dat_manifest.json\`, \`03_control_map.log\`, \`03_real_hls_axilite_control_map.json\`, \`03_generation.log\`, \`03_active_control_generation.log\`, \`tb_m06_g3_3_actual_hls_original_amd_idle.sv\`, \`tb_m06_g3_3_actual_hls_original_amd_active.sv\`, \`generated_hls_link_tb_sha256.txt\`.
- Real Vivado stages: \`04_xvhdl.log\`, \`05_xvlog.log\`, \`06_xelab.log\`, \`07_xsim.log\`.
- Source integrity: \`source_before_sha256.txt\`, \`source_after_sha256.txt\`, \`hls_sources_before_sha256.txt\`, \`hls_sources_after_sha256.txt\`, \`hls_dat_sources_before_sha256.txt\`, \`hls_dat_sources_after_sha256.txt\`, \`vendor_sha_before.txt\`, \`vendor_sha_after.txt\`, \`original_xci_after_sha_check.txt\`.
- Compiled source path lists/identity: \`verilog_sources.txt\`, \`vhdl_sources.txt\`, \`hls_sources.txt\`, \`include_dirs.txt\`, \`original_hls_folder.txt\`, \`original_d3_folder.txt\`, \`original_dwc_folder.txt\`, \`original_dwc_compile_order_folder.txt\`, \`original_g3_3_inventory_folder.txt\`, \`original_g3_2_zip_path.txt\`.
- Add owner console \`08_operator_invocation_console.log\` and \`operator_evidence_path.txt\` from the environment. Do not include proprietary vendor HLS RTL/source or .xci.

Copy/paste AFTER previous command (same VS Code terminal/environment):

\`\`\`bash
export ZIP="$HOME/Thesis_Evidence/M06_G3_3_ACTIVE_HLS_AMD_CORRECTED_REVIEW_$(date -u +%Y%m%dT%H%M%SZ).zip"

python3 - <<'PY'
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import os

folder_text = os.environ.get("LINK", "")
folder = Path(folder_text) if folder_text else None
output = Path(os.environ["ZIP"])
names = [
    "result.txt", "commit.txt", "worktree_status.txt", "owner_error.txt",
    "00_accepted_hls_interface_inventory.json",
    "01_reaudit_dwc_owner.log", "01_reaudit_dwc_sim_sources.json",
    "01_reaudit_dwc_sim_paths.txt",
    "02_vendor_plan.log", "02_original_sc_compile_plan.json",
    "03_merge_plan.log", "03_connected_vendor_compile_plan.json",
    "03_hls_original_dat_stage.log", "03_hls_original_dat_manifest.json",
    "03_control_map.log", "03_real_hls_axilite_control_map.json",
    "03_generation.log", "03_active_control_generation.log",
    "04_xvhdl.log", "05_xvlog.log", "06_xelab.log", "07_xsim.log",
    "tb_m06_g3_3_actual_hls_original_amd_idle.sv",
    "tb_m06_g3_3_actual_hls_original_amd_active.sv",
    "generated_hls_link_tb_sha256.txt",
    "source_before_sha256.txt", "source_after_sha256.txt",
    "hls_sources_before_sha256.txt", "hls_sources_after_sha256.txt",
    "hls_dat_sources_before_sha256.txt", "hls_dat_sources_after_sha256.txt",
    "vendor_sha_before.txt", "vendor_sha_after.txt",
    "original_xci_after_sha_check.txt",
    "verilog_sources.txt", "vhdl_sources.txt", "hls_sources.txt",
    "include_dirs.txt", "original_hls_folder.txt", "original_d3_folder.txt",
    "original_dwc_folder.txt", "original_dwc_compile_order_folder.txt",
    "original_g3_3_inventory_folder.txt", "original_g3_2_zip_path.txt",
]

with ZipFile(output, "w", ZIP_DEFLATED) as archive:
    if folder is not None and folder.is_dir():
        for name in names:
            source = folder / name
            if source.is_file():
                archive.write(source, arcname=name)
                print("ADDED:", name)
            else:
                print("NOT GENERATED:", name)
    else:
        print("No new evidence directory was created.")
    invocation = os.environ.get("INVOCATION_LOG", "")
    if invocation and Path(invocation).is_file():
        archive.write(invocation, arcname="08_operator_invocation_console.log")
    archive.writestr("operator_evidence_path.txt", (folder_text or "NOT_CREATED") + "\n")

print("UPLOAD EXACTLY THIS ZIP:", output)
print("SIZE:", output.stat().st_size, "bytes")
PY
sha256sum "$ZIP"
\`\`\`

**Next instance: after giving the user these commands, STOP and await the ZIP.** No speculative implementation changes before that evidence is reviewed. When the user returns the ZIP, identify the first actual error, compare every available source-identity manifest, and continue G3.3/G4 development only as justified. M06 stays OPEN, PR #80 draft/unmerged, physical board and M07 forbidden.

## 6. Where to read more *later*, not as a prerequisite for this verification

- \`docs/M06_G3_3_ACTUAL_HLS_AMD_IDLE_OWNER_GATE_2026_11_10.md\` — detailed preceding genuine idle pass and active original runner.
- \`docs/M06_NEXT_CHAT_HANDOFF_2026_11_09.md\` — history, evidence, scientific/physical scope.
- \`roadmap.md\` — accumulated M01–M06 milestone record.
- \`docs/M06_TESTS_EXPLAINED.md\` — native/real-vendor test boundaries.

These larger docs remain intact. This document exists deliberately to prevent a new chat from spending its first turn doing unnecessary development or repeating old owner simulations.
