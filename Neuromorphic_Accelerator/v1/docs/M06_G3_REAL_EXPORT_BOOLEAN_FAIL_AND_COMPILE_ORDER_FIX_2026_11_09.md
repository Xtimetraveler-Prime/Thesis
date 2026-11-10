# M06 G3 — Genuine Vivado read-only simulation export failure and bounded compile-order correction

Date: 2026-11-09 20:51 America/Denver. **M06 OPEN; PR #80 draft/unmerged.** No board, physical PS DDR, JTAG, bitstream, or mutation of original D3/owner IP evidence.

## User-provided first failure — independently inspected the original ZIP

Owner uploaded **M06_G3_EXPORT_ERROR_REVIEW.zip** after running `bash scripts/run_m06_g3_amd_xsim_export.sh` at Git commit `cbff062322fd0bbbac76219e31faef586f04f0f2`.

Owner immutable failure folder:
`/home/dna/Thesis_Evidence/m06_g3_amd_sim_export_20261110T035128Z_faM8Yr`, `result.txt=exit_status=1`.

Actual owner ZIP contains `01_vivado_export.log` (22,583 bytes), **`02_genuine_dwc_sim_compile_order.tsv` (2,692 bytes)**, `03_result.txt`, `04_vivado.jou`, `05_vivado.log`. The original evidence is complete; DO NOT ask owner for more files and DO NOT rerun it.

The genuine Vivado 2025.2 log shows:
- Accepted original owner dual AMD `axi_dwidth_converter` project opened `-read_only` as requested, and IP objects were reported as locked due to that read-only project.
- Actual `get_files -compile_order sources -used_in simulation -of_objects $ip` **SUCCEEDED FOR THE READ IP** and wrote `ip_sim_file_count\t13`. Authentic source list includes Verilog, one VHDL, one **Verilog Header** `axi_infrastructure_v1_1_0.vh`, and the actual generated vendor sim wrapper `sim/m06_g3_read_dwc.v` inside the original owner scratch project.
- The **subsequent, unnecessary** `export_simulation -simulator xsim -of_objects $ip ... -force` invoked Vivado's simulation exporter, which reported an internal Tcl `expected boolean value but got ""` and failed before it could query the write IP. Root internal cause is NOT known from logs; read-only locking is a plausible trigger, not proven.
- Board catalog warnings and locked project IP messages are background; no evidence of malicious IP mutation, AXI arithmetic error or connected HLS error. The journal confirms the exact Tcl script invocation and saved original paths. This is an **export-tool compatibility failure**, not an AMD converter generation failure.

## Scoped correction, new source code — NOT YET OWNER VIVADO VERIFIED

Rather than reopen the original project write-enabled or guess undocumented `export_simulation` flags, preserve `open_project -read_only` and **remove only the failing standalone export operation**. Both IPs are probed with the EXACT genuine `get_files -compile_order sources -used_in simulation -of_objects $ip` operation which has been observed successful already for the read IP.

Changed:
- `scripts/m06_g3_export_real_dwc_xsim.tcl`: outputs `02_genuine_dwc_sim_compile_order.tsv` with complete ordered real sources for READ and WRITE, exact named `sim/<name>.v` wrapper, nonempty genuine Verilog Header, source file existence/size, canonical project-root constraint, role/readback and zero false connected/XSIM claims. **Never calls `export_simulation`.** The script filename is historical; it does NOT produce an official generated `*.sh` compile script.
- `scripts/run_m06_g3_amd_xsim_export.sh`: preserves new unique evidence dir, genuine Vivado version, full original .XCI pre/post hashes and own four source SHA scripts; requires new marker and independent validation. New `03_real_amd_sim_source_paths.txt` contains the literal original vendor source paths as returned by the audited compile order, NOT fictitious standalone XSim scripts. New `06_amd_sim_compile_order_audit.json` records actual source-order and SHA; existing `04_real_amd_dwc_port_headers.json` captures only actual simulated wrapper port names/widths, not vendor source.
- New `scripts/m06_g3_real_amd_compile_order_audit.py` strict independent read-only source-order parser, required two-role original AMD file list, exact source paths inside original successful scratch project, role, type, suffix, nonempty and no extra/false result, one genuine header + exact generated IP wrapper per role, SHA per source. Reports `REAL_AMD_XSIM_SOURCES_RECORDED_NOT_EXPORTED_NOT_COMPILED`; never G3 PASS. No proprietary source bytes copied.
- New `tests/test_m06_g3_real_amd_compile_order_audit.py`: **seven synthetic positive/negative unit methods**, fixtures structurally matching the observed genuine 13-source read list, reject missing source/headers, duplicate/foreign paths, wrong roles/counts, false connected status, CLI overwrite and tampering. The original exporter test `tests/test_m06_g3_amd_xsim_export.py` no longer falsely requires `export_simulation`; now explicitly refuses it and asserts the actual vendor query.

**CI tests do not invoke Vivado**. An owner Vivado 2025.2 rerun is required to verify the corrected source collection for **BOTH** IPs and any vendor SIM wrapper quirks. Actual original AMD width converter XSim, original SmartConnect linked HLS IP and G4 trace/state/fault acceptance remain open.

## Exact owner local verification

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1

python3 -m compileall -q src scripts tests
bash -n scripts/run_m06_g3_amd_xsim_export.sh
python3 -m unittest discover -s tests -p 'test_m06_g3_real_amd_compile_order_audit.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g3_amd_xsim_export.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v

source "$HOME/Vivado/2025.2/Vivado/settings64.sh"
vivado -version
export DW="$HOME/Thesis_Evidence/m06_g3_real_amd_dwc_20261110T032341Z_YUDRD3"
bash scripts/run_m06_g3_amd_xsim_export.sh "$DW"
echo "M06 real AMD SIM compile-order capture exit: $?"

export EX="$(find "$HOME/Thesis_Evidence" -maxdepth 1 -type d -name 'm06_g3_amd_sim_export_*' | sort | tail -n 1)"
echo "$EX"
cat "$EX/result.txt" "$EX/commit.txt"
test -f "$EX/02_genuine_dwc_sim_compile_order.tsv" && grep -E '^ip_(name|mode|sim_file_count)' "$EX/02_genuine_dwc_sim_compile_order.tsv"
```

DO NOT rerun the earlier failed original evidence or recreate AMD XCI. On failure retain first new log; do not edit IP, and use the same ZIP packaging command.

## Exact next files; ONE ZIP, no ambiguity

The new owner runner writes unique `$EX=~/Thesis_Evidence/m06_g3_amd_sim_export_<timestamp>_<suffix>` folder. ZIP **`~/Thesis_Evidence/M06_G3_REAL_AMD_SIM_SOURCE_REVIEW.zip`** with precisely the following files that exist from **this new run**:

1. `result.txt` — `$EX/`
2. `commit.txt` — `$EX/`
3. `vivado_version.txt` — `$EX/`
4. `01_vivado_export.log` — `$EX/` (old stable file name; log now contains compile-order query only)
5. `02_genuine_dwc_sim_compile_order.tsv` — `$EX/`
6. **`03_real_amd_sim_source_paths.txt`** — `$EX/` (not old `03_official_amd_xsim_script_paths.txt`)
7. `04_real_amd_dwc_port_headers.json` — `$EX/`
8. `05_owner_xci_after_check.txt` — `$EX/`
9. `00_owner_xci_before_check.txt` — `$EX/`
10. `06_amd_sim_compile_order_audit.json` — `$EX/`
11. `source_before_sha256.txt` — `$EX/`
12. `source_after_sha256.txt` — `$EX/`
13. `original_width_ip_folder.txt` — `$EX/`

The same ZIP packer should record missing optional artifacts for a FAILED run. NO proprietary original AMD RTL or .XCI files need uploading.

## Hard gates still outstanding

G1 corrected HLS-generated RTL C/RTL cosim PASS; G2 original AMD SmartConnect A–E XSim PASS; G3 two genuine DWC XCI generated PASS. The new compile-order collection is **preparation** for real connected original SmartConnect plus generated HLS C/RTL XSim, NOT an adapter/XSim PASS. G4 independent M02/M03 full neural trace and 16-byte canonical memory with dirty eviction, fault containment and read-after-write B response ordering still pending. No board/JTAG/physical DDR, no PR merge/M07 without explicit owner approval.
