# M08.5 — accelerator-specific 256B AXI/64-word neuron-bank integration

**Status:** first-party RTL source + genuine Icarus/AXI BFM, **NOT** physical DDR, NOT a routed Vivado image, NOT matched-performance acceptance. One continuing development increment inside existing **M08.5**, same stacked DRAFT PR #95. User has independently passed prior M08.5 Icarus/PCI-only checks. Accepted M08.4 original physical evidence, bitstream and RTL unchanged.

## Why this bridge exists

The original M08.4 on-K26 result had six 256-byte signed16 neural context pages but a single resident bank; the host/JTAG loaded each page, read it back before computation, and read back dirty updates before the host claimed a save. The M08.5 AXI128 master already performs a full 16×128-bit AXI4 read/write on a **simulated** page. That 2048-bit snapshot port alone did **not** constitute a verified load into the actual 64×32-bit neural bank, nor a verified save of its dirty state.

The new **rtl/m08/m08_m085_axi_bank_bridge.v** composes these *exact existing* components without changing their original code:

- First-party **m08_host_staged_page_bank.sv**: one real 256B bank, EMPTY/LOADING/READY/RUNNING/DIRTY/FAILED semantics; per-byte initialized coverage, all-64-word load readback coverage, dirty-readback coverage, compute-vs-host exclusions.
- First-party **m08_m085_ddr_page_admission.v**, **m08_m085_axi128_page_engine.v** and **m08_m085_axi128_page_candidate.v**: 256B exact address/size/page/tick/owner checks and one 16-beat, 128-bit AXI4 burst master, actual B/R response fencing and timeout quarantine. Default address window is **[0,0)**. No v3 0x40000000 range.
- New explicit bridge FSM drives the actual host words of the unchanged bank. It exposes original bank's external dispatch/compute signals as a *separate optional logic port* for tests; it is **not yet wired to the physically accepted m08_paged_m06_lif_engine or the AXI-Lite control wrapper**.

## Safety sequence

**LOAD from abstract backing:** only when compute is idle, ownership lease input asserted, and no dirty page may be discarded. The bridge requires **one contiguous six-slot (6 × 256B) owner-assigned backing allocation**, with DDR address equal to `WINDOW_BEGIN + logical_page*256`, base aligned and window at least 1,536 bytes; this prevents a legal logical page from overwriting the wrong DDR slot. The parameters remain empty by default, and the owner signal is not a kernel authentication mechanism. Execute a full AXI4 256B READ into a distinct snapshot. Validate signed16 header: word60=0x4D364E46 (M6NF), word61=logical page in 0..5, word62=6 neurons (page5=2), word63=tick 0..3. Only then call the bank's host_begin, write all 64 words with full WSTRB, read each of those 64 words from the actual bank, independently compare against the captured AXI data, and assert host_commit with host_readback_verified only after the full comparison. Require bank READY/valid/full 256B and correct logical ID. A malformed DDR header **never** becomes dispatchable.

**DIRTY SAVE to abstract backing:** only for the current DIRTY logical page. Check its actual resident M6NF/page/count/**tick** header against the selected page and tick **before issuing any AXI write**. Read all 64 real bank words through the real host read protocol, stage them as a separate 2048-bit snapshot, issue one full 16-beat AXI write and wait for an OKAY B response. **Then issue an independent second full AXI read from the same address**. Byte-compare its full 2048 bits against the saved bank snapshot. Only then assert original bank's host_save_done, require return to clean READY, and acknowledge a saved page. Corrupt readback, lost R/B/timeout, revoked owner lease, concurrent request or compute fault must fail closed, without claiming an accepted save.

**Recovery:** a timed-out AXI burst can have issued partial real writes. A sticky source fault blocks new transactions and marks the resident bank poisoned; actual future recovery requires quiescing/resetting the *entire relevant AXI interconnect/PS path* and invalidating uncertain memory, not merely asserting resetn and reusing the address.

## Genuine simulation tests and what they do NOT prove

**rtl/m08/tb_m08_m085_axi_bank_bridge.sv** builds an independently clocked **six-page 256B software-in-Verilog AXI memory model** and drives the actual AXI4 AW/W/B and AR/R valid/ready handshakes. Its normal case:

1. Initializes source page with an *existing independent* M02/M03 signed16 M06 input page (64 32-bit words), 6 actual pages tested separately; **the 512 golden neural-output words are never loaded**.
2. Loads that page through all 16 AXI R beats, all 64 bank host writes and 64 bank host reads, then asserts READY and full 256-byte coverage.
3. Issues a legitimate bank dispatch and a **test-controlled synthetic compute write** to one bank word. **This is not real LIF inference**. Drives compute_done, checks DIRTY.
4. Reads all 64 dirty bank words, writes all 16 AXI W beats to simulated DDR, observes OKAY B, reads all 16 R beats back, compares 2048 bits, and checks bank READY / 768 cumulative **simulated AXI bytes** (256 load +256 save +256 verification).
5. Evicts to a different logical page and reloads the saved page through the same route. Reads the restored word via the bank's public compute port and checks the persisted test mutation (total five simulated page transfers, 1,280 synthetic AXI bytes).

The independent **tests/test_m08_m085_bank_axi_bridge.py** additionally runs 19 adversarial RTL cases: wrong M6NF header, ownership withdrawal, corrupt post-save DDR readback, absent B response, premature save while EMPTY/CLEAN, illegal eviction of a DIRTY page, second concurrent request, compute during loading, invalid logical page, early RLAST, BRESP error, RRESP error, missing final RLAST, stuck AWREADY, stale tick during DIRTY save, illegal logical-page to DDR-slot alias, wrong DDR neuron count, and stale DDR page tick. The bridge must enter sticky quarantine, suppress new AXI requests, and never emit a false page-save completion. Existing **25 lower-level AXI faults** and **18 page-admission faults** remain inherited.

All testbench DDR physical addresses are **artificial** (0x1000..0x15FF), backed by on-simulator registers. **No CPU, driver, IOMMU, PS DDR, Vivado route or physical board access exists in these simulations.** Counter labels are testbench-only; no measured physical DDR bytes/speedup or neuron-compute workload claim.

## Remaining M08.5 gates, in order

1. Review the bridge RTL and actual inferences/synthesis resource impact (two 2048-bit payload registers and original bank) offline; optimize buffering only if it preserves the original bank invariants. Connect the actual signed16 **m08_paged_m06_lif_engine** to the same bank with exact 32×4/five-edge/17-event oracle checks and reject readback/DDR faults in a full closed-loop test. Any new RTL must continue to leave accepted M08.4 image untouched.
2. Independently inspect a real PS boot/device tree/driver/DT overlay and XSA memory map **read-only**, selecting a Linux-owned bound DMA allocation with explicit IOMMU/cache/lifetime, **or** a separately operator-reviewed standalone/disposable reservation. The Digital Twin's old 64MiB region and its halted-PS debug workflow confer NO authorization. Verify PS HPM boot-time 128→32-bit control SmartConnect separately from the HP0 128-bit AXI master.
3. Only under separate operator authorization, prepare an independently assessed Vivado/K26 sourced/routed PS HP0 candidate with real resource/clock/timing/DRC/evidence; **no current M08.5 source pass authorizes new hardware contact**. The six-cell matched-experiment contract still marks physical DDR and event-sparse timing as unmeasured until an actual source-matched physical owner trial exists.

## Owner Linux VS Code test commands (PC ONLY)

Run from the existing checkout on the M08.5 branch; use the current exact HEAD (no new branch/merge).

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git log -1 --format='%h %s'
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v iverilog
command -v vvp

# New original signed16 six-page real bank+AXI conformance and 19 negative tests
python3 -m unittest discover -s tests -p 'test_m08_m085_bank_axi_bridge.py' -v

# Unchanged v3 lineage / standalone AXI+page guards
python3 scripts/m08_m085_twin_pspl_audit.py --source-only
python3 -m unittest discover -s tests -p 'test_m08_m085_pspl_reuse.py' -v
python3 -m unittest discover -s tests -p 'test_m08_matched_experiments.py' -v

# Full M08 + all v1 inherited tests
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
~~~

The accepted M08.4 physical evidence and original SHA, plus draft PRs #93/#94, remain untouched. M08.5 continues as **one** gate on PR #95; M08.6–7 remains future repeatable measurement.
