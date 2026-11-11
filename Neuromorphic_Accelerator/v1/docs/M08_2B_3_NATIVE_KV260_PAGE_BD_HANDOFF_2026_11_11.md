# M08.2b.3 — genuine native KV260 PS→two-slave safe-page Vivado BD

**Engineering status November 11, 2026:** New first-party *source* candidate, exclusive native-Vivado runner, independent original-evidence auditor and targeted negative tests implemented. **The owner has performed one original native Vivado run; it FAILED at the unsupported .sv module-reference top before BD validation. A fresh post-fix run is required.** The original owner-accepted M08.2a identity-only native offline BD remains accepted, but it does **not** prove these new connections. The owner independently confirmed the previous M08.2b.2 AXI-Lite adapter's Icarus simulation and regressions PASS; M08.2b.2 is accepted in **source scope only**.

## First original native Vivado attempt: module-reference top-file type rejection

**Original owner attempt 1 (2026-11-11 10:10 local; preserved unchanged):**
`/home/dna/Thesis_Evidence/M08/m08_2b_3_page_bd_20261111T171034Z_8UoMK5`, `result.txt=exit_status=1`. The owner provided the original terminal's extracted `01_vivado_page_bd.log` lines: actual installed KV260 board part `xilinx.com:kv260_som:part0:1.4`, applied PS preset, PS PL0 `99999001` Hz, deviation `999` Hz, and `WARNING: [IP_Flow 19-11770] Clock interface 'aclk' has no FREQ_HZ parameter.` The **first fatal** was:
```text
ERROR: [filemgmt 56-195] Reference 'm08_ps_page_safe_shell' contains top file '.../m08_ps_page_safe_shell.sv' of type SystemVerilog. This type is not allowed as the top file in the reference.
ERROR: [BD 41-1690] Unable to resolve module-source based on inputs: m08_ps_page_safe_shell
ERROR: [Common 17-39] 'create_bd_cell' failed due to earlier errors.
```
The owner also checked all **seven source SHA rows** against the checkout and all passed. Thus the run advanced through **accepted PS preset/clock boundary** but did **not** add the page cell or run `validate_bd_design -force`. No address map/export/independent-audit completion, routed bitstream or board transaction is established. AMD Vivado UG994 expressly limits IP Integrator **module-reference top-level definitions** to Verilog or VHDL (SystemVerilog source files can still be present as underlying children); see AMD `UG994 — Limitations of the Module Reference Feature`.

**Narrow source correction, preserving the accepted memory protocol:** change the **outermost** `m08_ps_page_safe_shell` definition from `.sv` to strict Verilog-2001 `.v` with the same 21 Vivado AXI/clock/reset annotations and the same `ENABLE_COMPUTE=0` tie-off. Retain the child `m08_axil_page_control.sv` and `m08_host_staged_page_bank.sv` unchanged; do not convert their state arithmetic or alter AXI transactions. Remove the former `.sv` top to avoid a duplicate module name. Update the new Tcl four-source list, both runner SHA manifests, the auditor's exact source manifest/report path, the safe-shell testbench's source list and the operator commands. A regression now demands `.v` as the module-reference top and explicitly rejects the rejected `.sv` file.

**Verification gate:** source tests and CI at the new SHA must run first, followed by **one fresh** native Vivado run in a **new exclusive directory**. This is a strongly evidence-supported correction to the specific vendor fatal, **not yet a proven actual Vivado BD pass**. Any subsequent error must be evaluated from its own new original log; preserve this first original failed folder exactly.

## Purpose, design and inheritance

The accepted sixth/seventh M08.2a Vivado 2025.2 runs established real K26 part `xck26-sfvc784-2LV-c`, SOM board part `xilinx.com:kv260_som:part0:1.4`, **PS board preset applied before explicit clock/master overrides**, PL0 clock actual **99,999,001 Hz** from requested 100 MHz, and PS `M_AXI_HPM0_FPD`→SmartConnect→read-only `identity/S_AXI` with correct common reset/clock and a 4 KiB PS register region. Prior failure history is retained; do not reproduce legacy clock or unused-LPD mistakes. [Historical acceptance](M08_2_IDENTITY_BD_SCOPED_ACCEPTANCE_2026_11_11.md).

The new source candidate intentionally keeps the accepted identity peripheral **and** introduces a **new, independent** PS-controlled signed16 staging peripheral behind one **two-output AMD SmartConnect**:

~~~text
                   K26 PS FPD HPM0 master, nominal 100 MHz
                              |
                   AMD SmartConnect (1 SI, 2 MI)
                     /                     \
      M00_AXI -> identity/S_AXI    M01_AXI -> page/S_AXI
                32-bit read-only         32-bit control and 256B state page
                 4 KiB region                 4 KiB region
                     \                     /
                COMMON: PS pl_clk0, proc_sys_reset
~~~

**All actual physical offsets are assigned and read back by genuine Vivado, not chosen from user space.** The new Tcl requires exactly **two distinct, nonoverlapping, 4 KiB, 4 KiB-aligned** PS-visible address segments; the previous identity `0xA0000000` from the accepted, *different* BD is a precedent, **not** a guaranteed mapping in this new design. Even if Vivado assigns that value, it does **not** authorize Linux `/dev/mem` or a physical DMA buffer.

### Safe compute boundary

The accepted M08.2b.2 `m08_axil_page_control.sv` exposes an external compute port for *later* M06 signed16 integration. A PS-only design with this port tied idle but with DISPATCH enabled would enter `RUNNING` indefinitely. Therefore the new `m08_ps_page_safe_shell.v` wraps the adapter with **`ENABLE_COMPUTE=0`** and ties compute request/write/done/fault inputs to 0; the adapter must return **SLVERR** on command `DISPATCH (4)` without entering `RUNNING`. The original adapter default `ENABLE_COMPUTE=1` remains available for its prior *standalone testbench* and future genuine compute integration. No unused compute input is exposed/floating in this BD. This is not an actual neural kernel or hardware inference test.

### Exact source components

| Artifact | Function |
| --- | --- |
| `rtl/m08/m08_axil_readonly_identity.v` | Previously vendor-proven first-party read-only identity, preserved in BD |
| `rtl/m08/m08_host_staged_page_bank.sv` | 256-byte M06 signed16 state-page owner/arbitration |
| `rtl/m08/m08_axil_page_control.sv` | New 32-bit PS AXI4-Lite slave, existing source-level bus acceptance |
| `rtl/m08/m08_ps_page_safe_shell.v` | Exposes one S_AXI/clock/reset interface; compute explicitly disabled at elaboration |
| `scripts/m08_page_ps_bd_candidate.tcl` | Genuine Vivado 2025.2 board preset, FPD HPM0-only IP, two SmartConnect MIs, clock/reset, two address segments and validated Tcl export |
| `scripts/run_m08_page_bd.sh` | Exclusive immutable owner-original evidence directory, native Vivado batch and source SHA before/after |
| `scripts/m08_page_bd_audit.py` | Independently re-hashes current sources, verifies the native vendor result/log and distinct PS apertures and output export, rejects false physical claims |
| `rtl/m08/tb_m08_ps_page_safe_shell.sv`, `tests/test_m08_page_ps_bd_candidate.py` | Safe-shell Icarus, Tcl grammar, project-before-catalog mock, source structure, independent synthetic-auditor negative tests. **Synthetic is not original Vivado proof.** |

### Phase A — source verification on the development PC (no Vivado execution)

From `~/Git/Thesis/Neuromorphic_Accelerator/v1` after pulling the exact source branch:

~~~bash
python3 -m compileall -q src scripts tests
bash -n scripts/run_m08_page_bd.sh
python3 -m unittest discover -s tests -p 'test_m08_page_ps_bd_candidate.py' -v
python3 -m unittest discover -s tests -p 'test_m08_axil_page_control.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -p 'test_m07*.py' -v
python3 -m unittest discover -s tests -v

# Independent clocked SAFE-SHELL test (requires actual installed Icarus)
TMP="$(mktemp -d)"
iverilog -g2012 -s tb_m08_ps_page_safe_shell -o "$TMP/m08_safe_page.vvp" \
    rtl/m08/m08_host_staged_page_bank.sv \
    rtl/m08/m08_axil_page_control.sv \
    rtl/m08/m08_ps_page_safe_shell.v \
    rtl/m08/tb_m08_ps_page_safe_shell.sv
vvp "$TMP/m08_safe_page.vvp"
~~~

Expected actual new safe-shell Icarus markers:
- `M08_SAFE_SHELL_AXIL_FULL_PAGE_READBACK_PASS`
- `M08_SAFE_SHELL_DISPATCH_DISABLED_NOT_STUCK_BUSY_PASS`
- `M08_SAFE_SHELL_SOURCE_ONLY_NO_K26_NO_BITSTREAM_NO_DDR_PASS`

**If Icarus is not installed or the test skips, source-level safe-shell verification is NOT accepted.** Any unexpected real compiler/runtime failure blocks Phase B; preserve its exact output and fix the first root cause. Source grammar and mocked IP calls are not vendor validation.

### Phase B — ONE fresh original native *offline* Vivado K26 run (owner development PC)

**Run only after Phase A source validation and same-HEAD GitHub M01–M08 CI evidence are established or a clearly documented CI network-only blocker is independently replaced with matching local tests.** This uses no physical KV260, JTAG, bitstream, hw_server, PS DDR or driver; it only generates and validates a native offline block design in an exclusive source-hash-pinned evidence directory.

~~~bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
source /home/dna/Vivado/2025.2/Vivado/settings64.sh
vivado -version
mkdir -p "$HOME/Thesis_Evidence/M08"

CONSOLE="$(mktemp "$HOME/Thesis_Evidence/M08/m08_2b_3_page_console_XXXXXXXX.log")"
set +e
bash scripts/run_m08_page_bd.sh 2>&1 | tee "$CONSOLE"
RUN_EXIT=${PIPESTATUS[0]}
set -e
echo "M08_2B_3_EXIT=$RUN_EXIT"

D="$(sed -n 's/^M08_PAGE_BD_EVIDENCE_DIR=//p' "$CONSOLE" | tail -n 1)"
echo "M08_2B_3_EVIDENCE_DIR=$D"
test -n "$D" && test -d "$D" || { echo "Missing original evidence folder"; exit 2; }
ls -lah "$D"
cat "$D/result.txt"
cmp "$D/source_sha256_before.txt" "$D/source_sha256_after.txt"
sha256sum -c "$D/source_sha256_after.txt"
grep -nE 'M08_|ERROR:|CRITICAL WARNING:|WARNING:' "$D/01_vivado_page_bd.log" || true

if [[ "$RUN_EXIT" == 0 ]]; then
    cat "$D/02_vivado_page_bd_readback.txt"
    python3 -m json.tool "$D/04_m08_page_independent_audit.json"
    sha256sum -c "$D/05_evidence_sha256.txt"
else
    echo "M08_2B_3_NATIVE_VENDOR_FAILED — preserve all original evidence"
fi
~~~

Original runner emits `M08_PAGE_BD_EVIDENCE_DIR=<unique path>` before Vivado executes. It writes:
- `result.txt` with exact actual native batch exit status;
- `01_vivado_page_bd.log` *original vendor output*;
- `02_vivado_page_bd_readback.txt` exact native PS clock, both PS slave interfaces and **distinct assigned** aperture offsets/ranges, plus explicit negative physical claims;
- `03_page_bd_export.tcl` original `write_bd_tcl`;
- `source_sha256_before.txt` and `source_sha256_after.txt` (all 7 source+script paths separately recomputed);
- `04_m08_page_independent_audit.json` plus `05_evidence_sha256.txt` **only after a successful vendor command and auditor**.

**Do not delete, modify, move, merge or rerun into any historical M08.2a or M08.2b.3 evidence folder.** On a failed attempt, review the **first original native ERROR/CRITICAL WARNING** and keep its full directory unchanged. A fresh follow-up run gets its own exclusive directory and source SHA.

### Owner handoff/acceptance

Share the new original `result.txt`, `01` Vivado log, `02` report, `03` exported BD, `source_sha256_before/after`, `04` audit, `05` SHA receipt (when generated), the complete console marker and exact `git rev-parse HEAD`. Source-only tests cannot replace these original files.

Accept **M08.2b.3 as OFFLINE NATIVE TWO-SLAVE BD VALIDATION** only after native `validate_bd_design -force` passed with no errors/critical warnings, board preset/actual PS and page+identity AXI clock propagation verified, exactly two non-overlapping 4KiB owner-Vivado-assigned PS addresses, no floating compute port, a credible export, unchanged original source hashes and independent receipt status `ORIGINAL_OWNER_KV260_PS_TO_SAFE_PAGE_BD_EVIDENCE_CONSISTENT`. Even acceptance at that stage is **not** route/timing closure, a new bitstream, Linux MMIO, DDR, physical memory ownership or real signed16 inference. **M08.2b.4** full routed implementation + original bitstream and **M08.4** safe owner physical proof remain separate gates.
