# P08-B4.6.3 — rebuilt A2.1 all-1024 **REAL KV260 PHYSICAL ACCEPTANCE** (operator-attested)

**Acceptance: YES, for one distinct reconstructed Track A2.1 physical validation session.**  
**Study status: B4.6 six-session Track A vs B_AUTH_ONCE repeated trial NOT RUN.**

- Operator ran on KV260, local November 5, 2026 / UTC November 6.
- Recorded immutable run directory (PC):
  \`/home/dna/Thesis_Evidence/p08_b46_A21_rebuilt_real1024_20261106T033101Z/\`
- Physical capture’s independent report:
  \`p08_b46_rebuilt_A21_1024_independent.json\`
  SHA-256 \`b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6\`.
- Independently re-executed **PC-only** verifier (same original captured files):
  \`/home/dna/Thesis_Evidence/p08_b46_rebuilt_A21_rereview_20261106T034152Z.json\`
  SHA-256 **identical**
  \`b57f20beb80943fb8d6b526a2e119cd12b17641db6fa7e55dbab8ca9f2f148a6\`.
  Equality indicates deterministic output for the same evidence and verifier;
  it is **not an independent second boot/physical run**.
- Physical capture manifest \`physical_output_sha256.txt\`:
  SHA-256 \`7978b82ade256fc9e419510036131115e93a18b6b80e55048e3132904d223a7e\`.
- \`attempt_exit_status.txt\`: \`script_exit_status=0\`.
- Physical terminal status:
  \`P08_A2_1_TIMING_STATUS=0x600D600D\`,
  \`P08_A2_1_KV260_STATUS=TERMINAL_BOTH_SUCCESS_UNVERIFIED_NUMERICS\`.
- Crucially, this was **followed by** separate physical-readback independent
  \`P08_A3_2_INDEPENDENT_ORACLE_PASS_FOR=.../p07_a4_journal_1m.bin\` and
  \`P08_B46_REBUILT_A21_INDEPENDENT_ORIGINAL_ALL1024_PACKED_NEURAL_AND_TIMING_PASS=1\`,
  and the physical script printed
  \`P08_B46_NEW_REBUILT_A21_ORIGINAL_1024_PHYSICAL_AND_INDEPENDENT_PASS=1\`.
- A53 \`CNTFRQ_EL0\`: **99,999,001 Hz**, measured from this run, not
  an assumed 100 MHz or PL clock.
- Median A53 ordinary per-image service **35.696886611897256 ms**
  over the **1,023 ordinary frames**; the selected trace at ordinal
  **1023** remains independently validated but excluded from this
  ordinary latency summary.

## Physical behavior actually proven

1. Source-gated **new rebuilt** A2.1 A53 ELF
   SHA-256 \`fa926823c291b70267c099db00c5052e62405444db58863436c1b2f950a58793\`
   (42 neurons, 26 PL dispatches/image); accepted original P03.2c
   hardware XSA SHA
   \`52aea12bd0169584a84e383982304ac1b78ccfe8eb8b035970fa29373492af6f\`.
2. Original P07 independent software packed oracle accepted all 1024
   frozen original TRAIN-derived inputs, their output/spikes and
   selected 26×42 trace, without executing the sealed official MNIST TEST.
3. Full A53 timing journal and checked per-image records; 1023
   non-trace observations summarized. Original source report SHA
   \`ec853c596a9dcfefee57d4da727a31dc55e3852407c589869c7b8838fb0ccd56\`
   independently matches 1024 raw-image TRAIN indices/pixel SHA
   between Track A and chosen B_AUTH_ONCE architecture.
4. Original physical output hashes and runtime status captured in one
   persisted **non-/tmp** evidence directory, with identical independent
   rereview SHA.

## What this acceptance deliberately does NOT prove

- The **historical original** A2.1 ELF
  \`fc44b5d9d7f3f481e1da2101fea0010661c24b2491005f013e9e66893af138f0\`
  was **not** reproduced after the PC's previous \`/tmp\` build
  disappeared. The rebuilt ELF is a **distinct** physical acceptance;
  old historical A3.2 results belong to the old SHA.
- The source-admission gate earlier reported
  \`P08_B46_TRACK_A_REBUILT_CANDIDATE_PHYSICAL_REACCEPTED=0\`
  because it was created **before** the new physical experiment;
  retain the original source report unmodified.
  This NEW document and new genuine physical report supersede that
  historical pending flag for **one new A2.1 standalone run only**.
- **A versus B_AUTH_ONCE full-service timer boundary equivalence**
  has not been signed off. Track A times from immediately before
  \`load_image_record\` through journal commit; selected trace flushing
  can be in its measured interval. Track B_AUTH_ONCE begins before
  reset and ends at journal-commit timestamp, with distinct scheduler,
  paging, routing, 702 dispatches and evidence sidecars. The final
  trace image is excluded from ordinary distributions.
  Next task is explicit source and sidecar timing-contract audit.
- No new B4.6 six independent boot sessions exist yet. Neither
  this standalone A session nor the earlier B4.5 once run counts
  towards pre-registered three independent A/B pairs.
  Terminal messages explicitly printed:
  \`P08_B46_NEW_A_B_SIX_REPEATED_PHYSICAL_SESSIONS_ACCEPTED=0\`,
  \`P08_B46_SIX_REPEATED_A_B_SESSION_BENCHMARK_ACCEPTED=0\`,
  \`P08_B46_6_SESSION_TRACK_A_VS_B_AUTH_ONCE_STUDY=NOT_RUN\`,
  and \`P08_B46_A_B_TIMER_BOUNDARY_EQUIVALENCE_PROVEN=0\`.
- No verified exclusive ownership of boot/DMA DDR, no XMPU/immutable
  B_AUTH_ONCE backup write protection, no exclusion of transient
  DDR corruption; these are deliberately reduced-integrity
  experiments with explicit operator risks.
- No matched network size or pure PL computation speedup.
  A=42 neurons/26 dispatches vs
  B_AUTH_ONCE=1010 neurons/702 dispatches,
  with 27 virtualized cores in three PL slots.
  Comparing A's ~35.7 ms with old B4.5 single-session
  ~7225 ms **is not** a paired session-level hardware
  speedup/significance result. Do not infer energy efficiency.
- The tool prints \`REBOOT KV260; NEVER RESUME HALTED LINUX.\`
  Operator supplied the instruction printout, **not a separate
  board power-cycle confirmation**. The next operator session
  must confirm a fresh power cycle before ANY other JTAG action.

## Evidence quality and workflow boundary

The user copied the actual stdout and both SHA-256 digests into
the conversation. The GitHub connector **does not mount or rehash**
the PC's private \`~/Thesis_Evidence\` binary files; therefore label
these as **operator-attested** rather than claiming raw physical
data was independently downloaded into this Git branch.
The actual independent local verification script, frozen source
code and test fixtures are checked into Git; original physical
capture remains external and unmodified.

Source branch:
\`agent/v3-p08-b46-a21-candidate-physical-validation\`,
draft PR #69, stacked on unmerged #68, #67, #66, #65.
Do not merge any branch unless the operator explicitly requests it.

Related critical paths:
- Source-only next-chat handoff:
  \`docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md\`
- Original candidate physical runbook:
  \`docs/P08_B46_REBUILT_A21_FIRST_1024_PHYSICAL_RUNBOOK.md\`
- Source/ELF candidate admission:
  \`docs/P08_B46_REBUILT_A21_DISTINCT_ELF_PC_ADMISSION_2026_11_05.md\`
- B4.6 selected B_AUTH_ONCE source gate:
  \`docs/P08_B46_SELECTED_AUTH_ONCE_PC_SOURCE_GATE_RUNBOOK.md\`
- Original B4.5.5 optimized-phase closeout:
  \`docs/P08_B45_5_FINAL_REAL_PHYSICAL_QUANTITATIVE_ACCEPTANCE_2026_11_05.md\`

## B4.6 closeout remaining — sequence (no automatic JTAG)

1. **B4.6.4a (NEXT PC-ONLY):** audit and explicitly freeze common
   A53 per-image service timing boundaries/trace exclusions across
   both C implementations, exact independent oracle, signed input
   identities, real per-session counter and timing sidecar formats.
   Verify no double-count of PS+PL; both are system/workload timers.
   Verify existing A/B physical runner safety differences and DDR
   occupancy/owner risks. Add negative native tests and a new
   source-gated **PC-only** six-session protocol/manifest.
2. **B4.6.4b:** independent operator decision/approval per fresh
   disposable KV260 session, with exact hardware/ELF/oracle pins,
   independently reviewed A-run and B_AUTH_ONCE run scripts,
   no-overwrite evidence, matching timing bounds, source staging and
   full neural trace validation, DDR/PS128 and reboot requirements.
   Pre-register sequence **A B / B A / A B** (three matched
   temporal pairs, three truly independent booted sessions per arm).
   Do **not** count historic B4.5 once or this A revalidation.
   Do not run unapproved JTAG or restore halted Linux.
3. **B4.6.4c:** once six new sessions independently pass, analyze
   each session’s 1023 ordinary-image median and P95, actual CNTFRQ,
   three B/A median ratios + differences, their descriptive geometric
   mean and order effects. **N=3 independent pairs, not 1023
   independent board trials**. Avoid unjustified formal significance,
   matched-complexity, protected memory, PL-only or energy claims.
   Preserve exact receipts/raw sidecars and six-reboot evidence.
4. **Beyond B4.6:** original v3 roadmap goals include real PS/PL
   latency/throughput/power/energy characterization, improving the
   27-core virtualized paging/dispatch path (B4.5.5 identified
   mixed 26-tick phase as 96.11% of total service tick sum),
   more extensive hardware regression, and deferred multi-engine
   PL memory/port arbitration work. Do not assume a named B4.7
   has been approved: review roadmap and plan a separate milestone
   before code/hardware changes. Official MNIST TEST remains sealed.

**No new B4.6 six-session hardware authorization follows from this
document or from successful single-run numerical acceptance.**
