# M06 — acceptance review (2026-11-10)

**Decision: COMPLETE under the user-authorized, OFFLINE, bounded simulation-backed residency scope.**
This review supersedes older G3.3/G4 in-progress runbooks and status notes.
M06 remains the original milestone; no new subdivisions. PR #80 was merged into main after all six final branch CI workflows passed.
GitHub merge commit: 9542789cdbe61449a84828a6340ed1f90237e825. No M07 changes are included.

**Final repository state:** PR #80 MERGED into main on 2026-11-10.
Merge commit 9542789cdbe61449a84828a6340ed1f90237e825;
accepted source HEAD e569a40d48dce5d805109cc1b955cd27ac420be3.
No original owner ZIP was modified or rerun after merge.

## Accepted contract — what M06 does and does NOT demonstrate

An original Vitis-generated, paged HLS neural engine and real AMD
SmartConnect/AXI width-converter simulation RTL operate against an
independently controlled 64 KiB simulated canonical image. A bounded
resident working set models DDR-style backing, cache evictions and
writeback/fill ordering, exact M02 numerical behavior and M03 traffic
semantics. A separate synthesizable-candidate epoch supervisor and a
bounded output trace/metrics quarantine reject poisoned runs and release
only clean completed results. This closes an OFFLINE/FPGA-TARGETED
virtual-residency prototype, **NOT PHYSICAL PS DDR**.

Previously accepted G1, G2, G3.2 and G3.3 remain immutable and in scope.
The definitive original G3.3 run checked 32 neurons x4 ticks, one-slot
eviction, high canonical addresses and genuine B-before-AR ordering,
with independently checked six-field trace and final state parity.

## Five independently accepted original-owner Vivado PASS ZIPs

| Gate | Original owner ZIP | SHA256 | Owner test commit | XSim finish |
| --- | --- | --- | --- | --- |
| G3.3 independent M02/M03 neural parity | M06_G3_3_M02_M03_PARITY_HLS_AMD_REVIEW_20261110T165556Z.zip | c3c9c6c1b21989b11f2d632b306981b10261aa1c6aedd8e54f7cd1c88ed4eb6c | bd52a31cbf6ef10a6a02749e772172b81527c54a | 496930 ns |
| G4 original memory write-B SLVERR quarantine | M06_G4_FIRST_B_SLVERR_HLS_AMD_REVIEW_20261110T171436Z.zip | 11c2960d6a130e530ccfde345c42828e42626936e523a77f7b35bacffc87eaca | e3a690f6b92dd1ae878a4e327abf158a45586a56 | 3900 ns |
| G4 original memory read-R SLVERR quarantine | M06_G4_FIRST_R_SLVERR_HLS_AMD_REVIEW_20261110T174333Z.zip | 55039df7443c0c0d6aba73d88d9eb80461a403684a46cf31ff0e736225a22d70 | bd19be6ee24a8d6add1e3a07f890304493e7b5dd | 7990 ns |
| G4 withheld memory write B, watchdog poison and zero publication | M06_G4_STALLED_B_HLS_AMD_REVIEW_20261110T181903Z.zip | 263d0735a8319d92e79758299cbbaf01943052840faf2e35842ace94260d27b8 | 2997547d54df140c83181618c98c1bcb26745936 | 11400 ns |
| G4 injected first R fault, explicit 64KiB discard/restore and clean verified postcommit replay | M06_G4_DISCARD_RESTORE_HLS_AMD_REVIEW_20261110T182012Z.zip | fa981f6dc18e750b863a81ffec1db8a0359b85f80fb7b178d197f1128dfa78af | 2997547d54df140c83181618c98c1bcb26745936 | 51970 ns |

For each genuine owner ZIP: result.txt exit_status=0; original Vivado
2025.2 xvhdl, xvlog, xelab and xsim returned zero, exact mode PASS
marker once and $finish with exit0. All local source SHA manifests match
their own before/after files (G3.3 14, first B 16, later G4 19).
Across ALL FIVE archives the original 40 generated Vitis HLS RTL,
14 HLS .dat init files and 67 AMD simulation RTL SHA rows are
BYTE-FOR-BYTE IDENTICAL, each with before==after. Both original
AMD DWC .xci SHA checks show OK in every run. The hashed generated
testbench source in each ZIP was checked against the manifest.
Original xvlog had no warnings. Each xelab retained the same four
previously known environmental/optional-port warnings
(LIBRARY_PATH, mb_reset, 2x aclk2x), not silently waived.
No original vendor HLS/AMD models or .xci were modified.

The final corrected stalled-B run recorded first original memory AW
at 2795ns and genuine pending withheld B at 2865ns; HLS B handshake
count stayed 0, independent G4 supervisor reached the directed
1024-cycle watchdog and poisoned, output remained blocked.
The fault controller finished at 11300ns while the neuron source
remained correctly backpressured (sourceFinished=0); genuine XSim
reported a single STALLED_B_WATCHDOG_QUARANTINE_XSIM_PASS and finished
11400ns. This is a finite simulation watchdog parameter, NOT
measured physical DDR timing.

The final 51970ns recovery run injected original AMD/HLS R SLVERR,
quarantined that epoch, externally reset the original engine/guards
and explicitly rewrote all 65536 bytes of pristine simulated image.
The clean original HLS run returned genuine AXI-Lite AP_DONE and
AP_RETURN=0. Synthesizable candidate quarantine RTL attached to the
original HLS streams released exactly 16 verified six-field trace
records and 1 metrics beat only AFTER supervisor commit.
No failed-run provisional output became visible.

The two historical failed stalled-B owner runs (first 300s XSim host
timeout, then original negative testbench fork/join blocked at 30us)
remain preserved. A corrected named fork/join_any testbench gate,
tested in the genuine owner run above, eliminated that testbench
completion bug. No accepted earlier run was silently rewritten.

## Independent acceptance tooling and CI

scripts/m06_g4_owner_zip_audit.py checks per-mode genuine owner source
integrity, status, warning and PASS indicators. The stronger
scripts/m06_g4_complete_evidence_gate.py requires the fixed SHA
of G3.3 and four DISTINCT passing original G4 owner ZIPs,
cross-checking the original generated Vitis HLS / .dat and AMD
source manifests. It rejects missing, failed, duplicated, mutated or
SHA-inconsistent evidence. Its synthetic regression tests are a
software policy check, NOT a replacement for original vendor XSim.
The actual five owner archives were also independently checked for
full source/manifest identity, testbench SHA, original XCI and PASS.

Six independent no-board GitHub Actions M01–M06 workflow gates must
be green at final closeout. M06 source CI runs broad host regression,
strict generated-HLS+AMD declaration-only Icarus syntax checks,
real standalone local RTL Icarus/vvp functional tests for fail-closed
quarantine and handshakes, plus the evidence auditor. Declaration
stubs are NEVER used as fake vendor functional simulations.

## Limitations that carry forward

This does NOT prove physical KV260/K26 fabric inference, Linux/PS DDR
memory ownership, a real DDR DMA page-transfer path, DDR performance
or measured DDR service latency, whole-system synthesis, on-board
timing/resource/energy measurements, JTAG programming, crash-atomic
persistent rollback, production-wired reset/recovery arbitration,
or physical scalability. The simulated memory is a scratch model,
NOT allocated physical PS DDR. The pristine image was restored
EXPLICITLY by a simulated external owner, not by hardware rollback.
The large output quarantine FIFO is a synthesizable candidate but
is NOT accepted as placed/routed or measured on K26 hardware.

Although the original roadmap calls M06 a DDR state backing engine,
this user-authorized closure is carefully limited to its honest
OFFLINE model/connected HLS+AMD RTL simulation contract. A future
real PS DDR demonstration belongs to separately scoped physical
integration/evaluation, not an implied consequence of this approval.
M07 and M08 retain their own acceptance gates. The no-board physical
safety workflow and independently authorized board preflight apply
before any real DDR writes.

## Post-merge local verification (NO rerun of accepted original owner gates)

    cd ~/Git/Thesis
    git fetch origin
    git switch main
    git pull --ff-only origin main
    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06_g4_complete_evidence_gate.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g4_owner_zip_audit.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g4_output_quarantine.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_fault_matrix_tb.py' -v
    python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_recovery_tb.py' -v
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v

Accepted original owner archives remain immutable in
~/Thesis_Evidence and are not checked into Git.
