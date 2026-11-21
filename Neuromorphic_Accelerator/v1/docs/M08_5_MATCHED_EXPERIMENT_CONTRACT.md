# M08.5 — matched execution/memory experiment contract (SOURCE ONLY)

**Status:** First coherent source increment within the ONE M08.5 gate; not a new subdivision or hardware acceptance. M08.4 is PHYSICALLY ACCEPTED/CLOSED. All first-owner evidence under ~/Thesis_Evidence/M08 is immutable, and draft PRs #93/#94 remain unmerged.

## Six-cell scientific design

Use the independently checked original M06 G3.3/M02 dense+queued/M03 sparse reference: signed16 LIF, 3/4 truncate-toward-zero leak, saturation/threshold/reset, 32 neurons, 4 ticks, 5 signed positive-delay recurrent connections, 17 external events. Preserve exact event order, neural roles, and intended workload across controls. The source-only CLI hashes all six 256-byte ORIGINAL input pages (6+6+6+6+6+2 neurons), separate five-edge configuration page, ordered 17 events, independent 512-word golden and six source-reference files. It verifies no expected voltage/spike/recurrent outputs were prefilled into input pages.

The previously accepted M07 four-way PC research was a MEMORY/SERVICE MODEL, not physical DDR or comparable FPGA hardware; its timestep DDR-style stream was M02-oracle-guided state movement, its event DDR-style path M06 Python paging, and synapse transfers were analytically estimated. M08.5 explicitly splits JTAG-host staging from real PS/PL DDR:

| Control cell | Actual accepted foundation | Current experimental classification |
| --- | --- | --- |
| timestep/onchip | D3.D.2C: host-coalesced 17-event input; 384 FPGA computed neural values | Historical physical; NOT MATCHED |
| event/onchip | D3.D.2E: 17 raw FIFO events, clocked tick-service barriers; 128 FPGA current +384 neural checks. **All neurons still advance; physically sparse skipping is not demonstrated.** | Historical physical; NOT MATCHED |
| timestep/jtag_host_paged | M08.4: host-coalesced inputs; six logical 256B pages, one actual 256B bank, 24 full compute/dirty-save page dispatches; 128 HOST current +384 FPGA neural checks | Historical physical, **M08.4 ACCEPTED**; NOT MATCHED |
| event/jtag_host_paged | No source-identical sparse paged RTL/physical point | UNAVAILABLE — not built |
| timestep/ps_pl_ddr | No independently verified kernel-owned memory and connected route | BLOCKED — DDR OWNERSHIP |
| event/ps_pl_ddr | No independently verified kernel-owned memory and connected route | BLOCKED — DDR OWNERSHIP |

The original 512 comparisons of M08.4 do not mean 512 PL-computed neural values. No previous original yields a measured, identical-clock, equal-on-chip-resource performance pair. Historical checks are recorded faithfully, but matched host wall-time, PL cycles, JTAG transferred bytes, DDR physical transactions, service stalls, clock MHz per measurement window, or power remain NULL (NOT MEASURED).

## Provenance and fail-closed rules

1. Keep independent original neural evidence, exact source/file digests, signed16 arithmetic and recurrence, input event order and a six-page witness. Numerical parity alone is NOT a speedup.
2. Compare only one experimental axis at a time. Execution pairs require fixed placement; placement pairs require fixed execution. Require identical ingress interface, event order, neural work, precision, timing start/end semantics, and a documented matched physical resource envelope. If N>K cannot fit an on-chip control under the declared resource budget, mark UNAVAILABLE instead of extrapolating.
3. For future physical points require fresh original source/bit SHA, genuine routed Vivado 2025.2 device/clock/resource/DRC evidence, independent original raw receipts, complete correctness, measured on-fabric activity and skipped-neuron counts, counted page transfers, real stall counters, and explicitly labeled PS/JTAG versus PL timing boundaries. Previous bitstream route performance is NOT inherited by a new design.
4. For real PS/PL DDR require the routed master/alternative safe PS page service, kernel-bound owner, device DMA mask/IOMMU map, kernel-managed buffer lifetime, cache-coherency or sync protocol, outstanding-request drainage, fault quarantine, reset/recovery and independently audited original driver/bit/receipts. A DMA heap, DT name, candidate /dev/mem address or JTAG scratch BRAM does NOT prove ownership. Existing read-only M08.3 observations stay UNKNOWN unless owner proves a path ABSENT; an AVAILABLE_VERIFIED grant requires a NEW dedicated authenticated checker, not a source-side boolean.

The source validator compare_structure is explicitly an intermediate METADATA check: even its synthetic positive test returns STRUCTURALLY_MATCHED_ONLY_NO_LATENCY_CLAIM, speedup=null. A real independently verified measurement receipt/auditor is still needed to release any performance comparison. Present historical rows do not satisfy this gate.

## New source tests and owner VS Code commands

New files:
- src/neuromorphic_accelerator_v1/m08_matched_experiments.py — six-cell report; original 384/512/512 check accounting; source digest/geometry assertions; safe DDR inventory statuses and pair metadata gate.
- scripts/m08_matched_contract.py — imports unchanged M02/M03/M06 fixture and creates deterministic JSON to stdout or an exclusive fresh output file; never accesses owner evidence/board.
- tests/test_m08_matched_experiments.py — positive exact-original data, synthetic future metadata match, negative tampered neural/work/ingress/order/resource/timing/domain, false DDR readiness, fake physical quantities, stale-page record and output overwrite.
- This document is the M08.5 test explanation and comparison runbook; no new milestone number.

Copy/paste on Linux in VS Code; NONE of these operations program/operate the board or rewrite original hardware evidence:

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git log -1 --format='%h %s'
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m compileall -q src scripts tests
python3 scripts/m08_matched_contract.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_matched_experiments.py' -v
python3 -m unittest discover -s tests -p 'test_m07_matched_controls.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
~~~

The broad M08 suite uses genuine Icarus for RTL checks (requires iverilog and vvp on owner PC). CI also runs M08/M07/full suite source/RTL, not physical Vivado or KV260.

## Next engineering work (still M08.5)

Use the existing strictly read-only M08.3 DMA inventory and owner-reviewed Linux/DT driver binding to assess real PS↔PL memory ownership; then implement source-identical on-chip/host-paged timestep/event controls with real RTL and negative service/lease/page corruption tests, before new offline native image and separate per-session board authorization. If DDR remains UNKNOWN/NOT_AVAILABLE, preserve it as BLOCKED and report only safely supported comparisons. Repeated physical timing/resource/variation studies remain the combined M08.6–M08.7 gate.
