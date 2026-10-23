# P07-B.4m — complete physical inference development

**Status:** B4m.1 implemented in portable C11 / synthetic original-P03
native harness; real trained FPGA inference NOT yet attempted or accepted.
**Branch:** `agent/v3-p07-b-scaled-physical-inference`; draft PR #49 stays
unmerged. Frozen original B2.4, accepted P03 BIT/XSA, B4l ELF, and all
real B4l acceptance evidence remain immutable. Official MNIST TEST SEALED.

## Accepted entry boundary

P07-B.4l's original, separately accepted KV260 experiment successfully
programmed the original P03 shell, physically staged/read back 27 frozen
512KiB contexts and genuine 16KiB registered-axon descriptor, and
ran **27 actual P03 dispatches / 27 page-ins / 24 dirty page-outs**.
Its first B3 barrier intentionally remained **PENDING** and its
256-byte independently decoded mailbox reported **zero captured P03
packet words**, no external ingress, no NEXT commits, no barrier
acknowledgments, and no trained 26-tick parity.

## B4m.1 — physical packet-to-NEXT-to-global barrier coordinator

**Implemented**:
- `software/p07/include/p07_b4m_epoch_bridge.h`
- `software/p07/p07_b4m_epoch_bridge.c`
- `tests/native/p07_b4m_epoch_bridge_harness.c`
- `tests/test_p07_b4m_epoch_bridge.py`
- Expanded `.github/workflows/p07_b4i_native.yml` to run new native tests.

The reusable C11 function `p07_b4m_commit_pending_barrier` is called
only with an already pending and fully completed original B3c2
27-source P03 epoch. It accepts the actual source-indexed packet
buffers captured by original B3c2, separately supplied canonical
source-spike evidence and immutable B1.2 route binding, creates
the original independently verified P06B13R1 wire using B3c1/B2b,
prepares and commits physical NEXT writes using original B3c3,
and **only after successful completed writes and quiescence** calls
original B3c2/B3a barrier ACK. On any rejection or partial physical
failure it poisons the scheduler/pager, never returning a positive
barrier receipt. The user-facing return receipt distinguishes
captured packet count, originating spike count, inserted NEXT
records and newly acknowledged barrier.

**Native positive test** invokes the *actual original* P03 adapter,
B3a, B3c1, B3c2, B3c3 sources with its existing fake MMIO and fake
physical DDR callbacks: complete 26×27=702 dispatches and 26 real
software barrier commits under both ascending and alternating
paging orders, followed by the three final dirty slot flushes.
Tests additionally fail closed when the provenance approval is
missing, an independently supplied spike is missing, the observed
barrier is modified, or physical packet insertion faults.
**These are not physical KV260 measurements and not frozen-trained
neuron numerical parity.** All simulated packet/trace evidence
is synthetic and deliberately labeled.

## Critical remaining physical bridge gates

1. **Original frozen B2.4 route/ingress deployment admission:** build and
   pin actual B2.4 route bindings, genuine canonical B1.3 external
   current input frame(s), SHA/checksum, coherent DDR addresses,
   no collision with original B4l descriptor/model/mailbox or
   expanded low-DDR ELF. Check original `P07_B2_MAX_ROUTE_BINDINGS`
   (8192) against the *actual distinct emitted route* count rather
   than equating it with 21,384 registered input-axon entries.
2. **Independent emitting-neuron PL source evidence:** implement an actual
   P03 physical source-state/spike readback and source provenance
   verifier. The new `source_evidence_verified` argument is a caller
   obligation, **not** a proof of any PL observation; no physical
   firmware caller may set it to 1 without separate verification.
   Do not reconstruct source spikes from decoded packet words.
3. **CURRENT ingress physically committed:** connect original B4a
   external+NEXT preflight and physical debug/DDR commit before
   dispatch; verify all per-core current-bank counts and no
   stale cross-image bank data.
4. **26-tick A53 firmware and bounded physical runner:** apply B4m.1
   bridge with strict source proof and admitted real inputs.
   Pin new genuine Vitis ELF/map, distinguish its low-DDR ownership,
   route/packet buffers and I/O caches, preserve original B4l ELF.
   Require new physical approvals/evidence path, PS128, shell,
   staged/readback frozen data and fail-closed independent receipt.
5. **TRAIN-derived reference parity:** predeclared three frozen B2.3
   TRAIN validation frame witnesses (no TEST); require true all-26-tick
   neuron state, spike packet, NEXT bank and final readout/prediction
   parity including cold start and final writeback. Then proceed to
   P07-B.5 reproducible validation corpus and B.6 closeout.

**No KV260 execution authorized by this B4m.1 change.**
No A53 ELF has been rebuilt. Do not run the previously accepted
B4l `--mode execute` pipeline expecting it to produce full inference:
the original physical firmware is intentionally first-epoch only.
