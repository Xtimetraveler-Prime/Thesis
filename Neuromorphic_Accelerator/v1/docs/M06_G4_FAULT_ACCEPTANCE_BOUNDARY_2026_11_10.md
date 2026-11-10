> **FINAL AUTHORITATIVE M06 STATUS 2026-11-10: COMPLETE under user-authorized OFFLINE ORIGINAL HLS+AMD 64KiB simulation-scratch scope, PR #80 eligible for merge after CI.** All original G3.3 parity and four G4 connected owner modes now possess distinct immutable genuine Vivado 2025.2 XSim PASS ZIPs. Corrected stalled-B genuine PASS ZIP M06_G4_STALLED_B_HLS_AMD_REVIEW_20261110T181903Z.zip SHA256 263d0735a8319d92e79758299cbbaf01943052840faf2e35842ace94260d27b8, finished at 11400 ns with actual pending B, zero HLS B, 1024-cycle watchdog poison and no public trace. Original recovery PASS ZIP M06_G4_DISCARD_RESTORE_HLS_AMD_REVIEW_20261110T182012Z.zip SHA256 fa981f6dc18e750b863a81ffec1db8a0359b85f80fb7b178d197f1128dfa78af, 51970ns verified full simulated owner reset/image rewrite and clean postcommit output. Source/AMD/HLS SHA inventories match across all five accepted ZIPs. **Formal current acceptance, physical nonclaims and local verification:** [docs/M06_ACCEPTANCE_REVIEW_2026_11_10.md](M06_ACCEPTANCE_REVIEW_2026_11_10.md). The rest of THIS file contains historical troubleshooting/runbook claims that G4 is open, tests are pending, or PR must remain draft; those claims are RETIRED, not current instructions. Do NOT rerun already accepted Vivado owner gates. No physical DDR, FPGA, JTAG, measured physical timing or automatic rollback is implied.

> **STATUS UPDATE 2026-11-10:** Independent original-HLS/AMD G3.3 M02/M03 neural/state parity is now genuinely accepted (first owner ZIP SHA256 c3c9c6c1b21989b11f2d632b306981b10261aa1c6aedd8e54f7cd1c88ed4eb6c). G4 remains OPEN. Beyond standalone source tests, first genuine original-HLS/AMD B-SLVERR quarantine trial is source-ready but UNVERIFIED; current owner runbook docs/M06_G4_REAL_HLS_AMD_FIRST_B_SLVERR_OWNER_GATE_2026_11_10.md. Prior statements that G3.3 parity was pending below are historical, not the current state. No physical DDR/board or atomic rollback claim.

# M06 — existing G4 fault/quarantine acceptance boundary (2026-11-10)

This is work WITHIN G4, not a new submilestone. PR #80 stays draft/unmerged.

## Source-only candidate, NOT owner genuine AMD fault proof

New bounded synthesizable candidate:
rtl/m06/m06_g4_epoch_commit_gate.sv
and independent RTL testbench:
rtl/m06/tb_m06_g4_epoch_commit_gate.sv

The gate combines observed original-HLS ap_start/ap_done/return-status,
read/write 64→32 guard sticky fault signals, write AW/B handshakes and read AR.
It permits an advisory epoch-commit token only if: HLS ap_done occurred;
ap_return is 0; both guards report no error; every observed write AW has an
acknowledged B; and the read path never began while accepted writes remained
unacknowledged. A nonzero HLS status, premature done, orphan B, overlapping
read, write-response fault or illegal re-start quarantines that simulated
canonical epoch. A configurable MAX_EPOCH_CYCLES watchdog additionally
poisons a lost-acknowledgment/no-ap_done epoch without assuming HLS returns.
This bound is a source-only safety parameter, NOT a physical performance figure.
A registered post-ap_done settling cycle prevents a same-clock original
AXI guard fault latch from transiently publishing a commit token. A sticky poison blocks re-use until explicit reset and
external image discard/restore. No raw AMD RTL or original HLS is modified.

The source-only test checks clean completion and nine negative/guard cases,
using genuine standalone RTL in Icarus, not fake functional vendor models.
Source-only CI does NOT prove actual original AMD fault propagation.

## HARD G4 gaps and scope boundary

The accepted generated M06 HLS top uses ordinary Vitis m_axi pointers for
canonical state. Its C++ return status does not explicitly capture AXI BRESP,
RRESP or a physical DDR hardware error. Guard fault_seen is independent from
the HLS return path. A supervisor can therefore BLOCK EXTERNAL ACCEPTANCE,
but cannot automatically make the already issued memory writes transactional
or roll them back.

The trace stream is also delivered incrementally. No consumer may publish
its trace merely because valid/ready transferred a row: consumers must buffer
all provisional rows until the gated successful end-of-epoch token. A failure
invalidates ALL rows and the externally visible canonical state; hardware
atomic rollback has NOT been demonstrated. The gate has no output storage,
and is not yet wired into original HLS/AMD XSim.

A true original-Vivado G4 acceptance needs a new FIRST owner simulated
fault experiment in the connected system, with properly timed AMD RAM
injected read/write error, actual HLS-generated interface, measured guard
fault, verified gated poison/reuse denial, and no false positive neural
commit after failed AXI. It must preserve the original first-run evidence.
Longer-term recovery requires external canonical-image ownership/restore.
The existing host M06 ShadowEpoch / BlockCache models do not prove that
PS DDR, Linux memory, or AMD fabric implements physical rollback.

## Acceptance prior to any M06 merge

- Keep accepted G1, G2, G3.2, G3.3-idle, AXI-Lite-negative and positive16
  immutable. Do not rerun unchanged already accepted owner tests.
- G3.3 full independently checked original-HLS M02/M03 parity and memory
  complete before claiming end-to-end neural correctness.
- G4 original AMD fault injection, late B/write quarantine, read failure,
  no stale cache reuse and clean discard/restore protocol genuinely proven
  by reproducible first owner evidence. The standalone gate is insufficient.
- M06 pass must remain scoped to original Vivado 2025.2 hardware-model
  experiments and software source-only results. Do not claim physical FPGA
  execution, PS DDR ownership, routed timing, performance, power or full
  crash-atomic commit without later new owner authorization and evidence.
- No M07 or PR #80 merge until the user explicitly reviews and approves
  M06 acceptance.

No changes to original signed32 HLS, genuine generated M06 paged HLS,
original SmartConnect, original AMD width converters or accepted evidence.
