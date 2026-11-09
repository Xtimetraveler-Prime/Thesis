# M05.12d.2c — Original Vivado 57-key PS property inventory and independent-sort audit incident

**Status:** real Vivado Tcl catalog discovery PASS, *overall* D2c FAIL (`exit_status=1`); Python independent report audit failed due to a code bug. This first run is **NOT accepted**, preserves original evidence. **Date:** 2026-11-08 18:51–18:52 local / 2026-11-09 01:51–01:52 UTC.

**Original operator evidence:** `~/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_20261109T015151Z_BNn7SH` on checkout `b2ad947c952b515acec3c061df2e04d6ddc3aba8`. `result.txt` reads `exit_status=1`. Genuine `02_vivado.log` shows the exact Tcl PASS `PASS: M05.12d.2c offline K26 PS property names and values discovered (NO WRITE/PRESET/DDR)`; the produced original 57-property `01_ps_properties.txt` is complete with 14 `TARGET|...|1`. The subsequent `03_independent_audit.log` shows `ERROR: M05.12d.2c PS property catalog audit: property records not sorted as the original Tcl contract`. Original source hashes and failures must remain immutable.

## Root cause and minimal fix

- Actual Vivado Tcl source `scripts/m05_12d2c_ps_properties.tcl` calls **`lsort [list_property $ps]`** (case-sensitive byte/code-point order). In that order uppercase `T` sorts before underscore, so `PSU__USE__STM` comes **before** `PSU__USE__S_AXI_ACE`.
- The independent Python auditor `scripts/m05_12d2c_ps_properties_audit.py` mistakenly checked **`sorted(values, key=str.lower)`** (case-insensitive). Lowercasing moves `S_AXI` before `STM`. The original report is correct according to Tcl; the Python auditor's order rule was wrong.
- **Fix the checker, not the evidence or IP:** change the order requirement to `list(values) == sorted(values)`, aligning with Tcl's case-sensitive sort; retain rejection of duplicates, missing targets, wrong part/IP/scope/source mode, unexpected config keys, malformed/noncanonical base64, truncated file and incorrect count.
- Add native regression `test_owner_d2c_ascii_sort_regression_stm_precedes_s_axi` using genuine observed **key names and default values** for `STM`, `S_AXI_ACE`, `S_AXI_ACP`, `S_AXI_GP0`, `M_AXI_GP2`, and clock enable/frequency. It admits correct case-sensitive order, *rejects deliberately swapped ordering*, and asserts both the Tcl producer and the Python checker use matching case-sensitive sorts.
- **No modifications** to original PS `zynq_ultra_ps_e` IP configuration, DMA IPs, original HLS signed32 engine, RTL shell, memory/clock interface wiring or original owner evidence. No PS/DDR/board access.

## Observed *default* PS IP values (actual Vivado readback, NOT connected hardware)

Original exact candidate keys all present (14/14). At default unconfigured PS IP:

| Verified catalog property | Actual value |
| --- | --- |
| `PSU__USE__M_AXI_GP0`, `PSU__USE__M_AXI_GP1` | `0`, `0` |
| `PSU__USE__M_AXI_GP2` | `1` |
| `PSU__USE__S_AXI_GP0` through `GP6` | all `0` |
| `PSU__USE__IRQ0` | `0` |
| `PSU__USE__FABRIC__RST` | `1` |
| `PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ` | `100` (requested default, not measured) |
| `PSU__FPGA_PL0_ENABLE` | `1` |
| `PSU__MAXIGP0__DATA_WIDTH`, `MAXIGP1`, `MAXIGP2` | 128, 128, 32 |
| `PSU__SAXIGP0..6__DATA_WIDTH` | 128 each |
| `PSU__CRL_APB__PL0_REF_CTRL__ACT_FREQMHZ` | 96.968727 (reported actual IP clock value, not verified routed output) |

Do **NOT** infer a physical K26 PS/DDR boot/preset, actual clock net, coherent access, or enabled HP/HPC ports from these unconfigured IP settings. The D2a default-pin inventory remains accepted separately.

## Fresh operator verification (no board, Vivado 2025.2)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m05-sparse-onchip
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m05_12d2c*.py' -v
python3 -m unittest discover -s tests -p 'test_m05*.py' -q

# Optional read-only diagnosis of the ORIGINAL FAILED report, never change it:
export OLD_D2C="$HOME/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_20261109T015151Z_BNn7SH"
python3 scripts/m05_12d2c_ps_properties_audit.py --report "$OLD_D2C/01_ps_properties.txt"

# Real acceptance still requires a NEW genuine original run:
bash -n scripts/run_m05_12d2c_ps_properties.sh
bash scripts/run_m05_12d2c_ps_properties.sh
export PS_PROPERTIES="$(ls -dt "$HOME"/Thesis_Evidence/neuromorphic_v1_m05_12d2c_ps_properties_* | head -n 1)"
cat "$PS_PROPERTIES/result.txt"
cat "$PS_PROPERTIES/commit.txt"
cat "$PS_PROPERTIES/01_ps_properties.txt" 2>/dev/null || true
tail -n 160 "$PS_PROPERTIES/02_vivado.log"
cat "$PS_PROPERTIES/03_independent_audit.log" 2>/dev/null || true
cat "$PS_PROPERTIES/source_sha256.txt"
```

**Acceptance remains gated:** new `exit_status=0`, genuine original Vivado Tcl PASS, independently printed D2c catalog PASS, original 57-key/14-target report consistent with source hashes. Never rewrite failed original `result.txt`. If further issues show up, diagnose first genuine error, do not weaken acceptance.

M05 remains OPEN; draft PR #79 remains UNMERGED. If accepted, proceed with **D2d** safe offline explicit K26 PS FPD master/HP memory-interface enablement/clock readback using actual already-discovered `CONFIG.PSU__USE__` keys; complete PS/PL BD + DDR + bitstream later under separate approvals.
