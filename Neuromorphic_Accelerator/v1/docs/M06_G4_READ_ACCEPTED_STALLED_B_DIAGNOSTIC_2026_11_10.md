# M06 existing G4: genuine R SLVERR accepted; old stalled B XSim first timeout

Status 2026-11-10: G4 OPEN, M06 OPEN, PR #80 DRAFT UNMERGED.
No new sub-milestone, board/FPGA, physical DDR, automatic rollback or M07.

## ACCEPTED genuine Vivado read fault

M06_G4_FIRST_R_SLVERR_HLS_AMD_REVIEW_20261110T174333Z.zip
SHA256 55039df7443c0c0d6aba73d88d9eb80461a403684a46cf31ff0e736225a22d70
Tested git commit bd19be6ee24a8d6add1e3a07f890304493e7b5dd.
Original owner folder:
~/Thesis_Evidence/m06_g3_3_actual_hls_g4_first_r_slverr_xsim_z64a3c3t

Original genuine Vivado 2025.2 xvhdl/xvlog/xelab/xsim rc0;
owner result exit_status=0, XSim at 7990ns:
M06_G4_ACTUAL_HLS_AMD_FIRST_R_SLVERR_QUARANTINE_XSIM_PASS
ORIGINAL_AMD_R_TO_HLS_GUARD_POISON NO_COMMIT NO_ROLLBACK_NO_DDR_NO_BOARD.

Real scratch R SLVERR returned through genuine original AMD interconnect
to genuine original HLS AXI read port; local read guard and independent G4
supervisor poison, no commit and no public trace. Identical before/after
source SHA: 19 local, 40 original Vitis HLS, 14 HLS dat, 67 original
AMD. Both original AMD DWC XCI checks OK. Four previously recognized
environment/optional-port xelab warnings recorded. No xVlog warnings.
ACCEPT only within connected simulation-only 64KiB scope.
Do not rerun this accepted read fault unchanged.

## First stalled-B owner experiment preserved as FAILED

M06_G4_STALLED_B_HLS_AMD_REVIEW_20261110T174933Z.zip
SHA256 5c3c40cbab666b939bc444f9f62ca915ee2ba00a3e726ef70986e32a81ac188f
Tested original git commit bd19be6ee24a8d6add1e3a07f890304493e7b5dd.
Original owner:
~/Thesis_Evidence/m06_g3_3_actual_hls_g4_stalled_b_xsim_g9g1gxou

Original Vivado compilation/elaboration each rc0, original/local
source integrity and both XCI checks match, but owner exit_status=1
because 07_xsim.log exceeded runner 300 seconds. Log reached run -all
but has NO simulated timestamp, no HDL PASS, no finish/fatal and no
information to determine if simulation time advanced slowly or stalled.
DO NOT accept this test or claim confirmed hardware fault.

The OLD test waited up to 10,000 supervisor cycles, then could poll
up to 4,000 windows of 20 cycles each, and had a 20ms simulated
global watchdog. No diagnostic progress printed. The revised
testbench keeps actual original HLS/AMD unchanged, and adds:
- smaller deliberately simulated-only 1,024-cycle watchdog;
- only 80 windows of 20 cycles, 30us simulated global watchdog;
- owner host xsim timeout 90s rather than 300s;
- progress at every 256 simulated cycles including $time, pending
  memory B, HLS B and supervisor poison;
- explicit reports of actual RAM-side AW and pending B;
- no PASS if poison preceded the watchdog, if a memory B was not
  actually pending, if an HLS-side B handshake occurred, or if
  the synthesizable trace+metrics quarantine released output.

The 1,024-cycle test threshold is not measured physical DDR timing.
Even this shorter case MAY fail; preserve the very first NEW result.
Its progress messages will pinpoint the unresolved behavior.

## New owner verification is ONLY the changed stalled B then recovery

The old general owner instructions for G4 first R are historical and
must not be rerun. Use the current branch, source tests, original
Vivado evidence paths, and existing provenance checks from:
docs/M06_G4_REMAINING_CONNECTED_OWNER_GATES_2026_11_10.md

Source regressions:
~~~bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_fault_matrix_tb.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g4_owner_zip_audit.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g4_output_quarantine.py' -v
python3 -m unittest discover -s tests -p 'test_m06_g4_actual_hls_recovery_tb.py' -v
python3 -m unittest discover -s tests -p 'test_m06*.py' -v
python3 scripts/m06_g4_owner_zip_audit.py \
  --mode g4_first_r_slverr \
  --zip "$HOME/Thesis_Evidence/M06_G4_FIRST_R_SLVERR_HLS_AMD_REVIEW_20261110T174333Z.zip"
~~~

Acceptance auditor MUST reject old first failed stalled-B archive.
First run original vendor source environment with existing instructions,
then replace original three-mode loop with only these two modes:

    g4_stalled_b g4_discard_restore

Run them sequentially. Stop on the FIRST new failure, preserve its ZIP
and do not run recovery if stalled B failed. If both PASS, upload both
new ZIPs with prefixes:
M06_G4_STALLED_B_HLS_AMD_REVIEW_
M06_G4_DISCARD_RESTORE_HLS_AMD_REVIEW_

Every original owner mode uses same strict separate artifact folder,
invocation console log, before/after hashes and original dual AMD XCI.
G4/M06 closure depends on auditing these new original Vivado results,
not host-only CI. No automatic PS DDR rollback, FPGA or physical proof.
