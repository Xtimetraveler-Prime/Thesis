# M08.4 — first source-only host-page/compute-port RTL conformance (not neural hardware)

**Status:** Actual first-party Icarus/vvp PASS in GitHub Actions on commit `146371b5...` (M08 source workflow [44843119050](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44843119050)); full M08 regression **515 tests PASS**, including the new integrated RTL simulation. **No Vivado 2025.2 project has been built for this new page-bank wrapper; no K26 board programming, physical DDR, new RAM readback or neural compute is claimed.**

**Purpose:** Instead of creating yet another nominal “D3.D.3A/B/C/D” milestone, place real memory ownership work inside consolidated **M08.4**, a single acceptance gate requiring a physical, compute-bearing signed16 paged neural system. The current deliverable is a first **synthesizable AXI-Lite + 256B host page + compute-port** integration validated on a real simulator. It is **supporting source evidence**, not M08.4 physical acceptance.

## Retained original first-party hardware components

- `rtl/m08/m08_host_staged_page_bank.sv` — unchanged real clocked one-slot 64×32 bank, per-byte host fill/readback coverage, host/compute mutex, dirty full-read coverage before save, invalid-request poison. Previously source tested.
- `rtl/m08/m08_axil_page_control.sv` — unchanged 32-bit AXI4-Lite control adapter, independent AW/W, B/R backpressure, 256B page register window 0x100–0x1FC and logical-ID/BEGIN/COMMIT/DISPATCH/SAVE commands. No AXI master or DDR.
- `rtl/m08/m08_ps_page_safe_shell.v` — existing PS-only compute-disabled module reference remains **unchanged** (ENABLE_COMPUTE=0). It is NOT the new connected datapath.

## New first-party real RTL

- `rtl/m08/m08_page_compute_probe.v` — clocked bounded 63 consecutive 32-bit page reads; computes XOR of words 0–62; writes result to **word 63**; asserts compute DONE only after acknowledged write, not before; sticky 16-cycle stalled compute-ack fault until reset. It is a **memory-ownership probe**, NOT a spiking neuron or HLS core.
- `rtl/m08/m08_page_compute_probe_shell.v` — new Verilog-2001 Vivado module-reference-style top, correctly maps **all 19 AXI4-Lite pins** and drives the compute port in the existing page adapter with `ENABLE_COMPUTE=1`. Exposes one AXI-Lite slave, no DDR/DMA master. Initial Icarus uncovered an omitted WVALID/WREADY port connection; corrected and statically regressed. It has **not** gone through genuine Vivado BD validation, route, DRC or bitgen.
- `rtl/m08/tb_m08_page_compute_probe_shell.sv`, `tests/test_m08_page_compute_probe_shell.py` — real Icarus integration of two different logical contexts, 64-word load, host full readback, computation-lease exclusion, 63 reads / one write, dirty save, page replacement and negative wrong logical ID, premature SAVE and withheld compute ACK → sticky fault. Seven unique PASS markers are mandatory; real compile/runtime errors fail the test.
- `scripts/m08_m06_parameter_pages.py` — **source-only** direct original 630-word M06/M02/M03 independent reference. Defines a *compute-input-only* signed16 ABI matching this small bank:
  - words **0–59** = 15 neurons × signed16 initial voltage, bias, threshold and reset (32-bit sign-extended);
  - words **60–62** = M6PG marker `0x4D365047`, selected *logical page ID*, and 15/15/2 valid neurons;
  - word **63** = initially 0, afterward the XOR probe output.
  - original **32 neurons across 3 distinct logical pages** (0: neurons 0–14; 1: 15–29; 2: 30–31), with only **one 256B resident physical RTL bank**. The host overwrites that bank after full observed readback and save.
  - **No expected neural voltage or spike trace is embedded as compute input**. No M06 external current or synaptic state in this pilot ABI yet, so this pilot CANNOT execute original M06 neural dynamics.
- `rtl/m08/tb_m08_m06_parameter_pages.sv`, `tests/test_m08_m06_parameter_pages.py` — Python derives three distinct 64-word hex images directly from unchanged M02/M03-backed M06 oracle, then **real Icarus** replays all three through AXI load/readback/dispatch and the RTL compute probe, checking exact page data, results and full dirty save. Tests reject wrong IDs, modified signed configs, output prepopulation, wrong image size, wrong metadata and altered expected probe checksum.

## Actual CI results and scope

Dedicated M08 source workflow [44843119050](https://github.com/Xtimetraveler-Prime/Thesis/actions/runs/44843119050) finished **success**; log includes `test_real_iverilog_three_page_m06_host_compute_ownership ... ok`, `test_integrated_256byte_host_compute_backpressure_and_faults ... ok`, `Ran 515 tests ... OK`. Also earlier eight 4KiB model-only original M06 page tests and independent M02/M03 and M07 regressions remain in the suite. **These are genuine simulator handshakes (not mocked board status)** but they do not establish timing closure, actual PL state capacity or physical neural computation.

## Next concrete M08.4 engineering target — keep this ONE gate

Adapt the existing accepted M32Q signed16 LIF recurrent engine **to a real compute-facing paged-state ABI**, not to the 4KiB reference fixture that contains expected traces. Page logical neuron state and signed32 input/recurrent currents, preserve exact 3/4 truncate-to-zero decay and 5 positive-delay synapses, and issue actual physical host-staged transfers where N>K. Real Icarus must compare all **128 voltages, 128 spike decisions, 128 delivered recurrent currents** (plus 128 fabric current input values) against original independent M02/M03 oracle *after page eviction and reload*; host must observe and save all altered state before replacing a page. This becomes a **new genuine K26 Vivado 2025.2 candidate** with original source hash, exact new DRC pin/route/timing report review and fresh bit SHA. **No programming** of the KV260 until owner-local exact native gate, cooling/UART/exclusive JTAG/recovery and explicit bounded one-shot authorization. The previously accepted physical M32Q image must never be rerun or changed.

Do NOT promote this checksum probe to its own new milestone or use its PASS as proof of neural page virtualization, DMA/DDR, asynchronous processing, full M05/M06 HLS, numerical physical 512 parity or speedup. These remain requirements of the consolidated [M08 execution plan](M08_REMAINING_PHYSICAL_EXECUTION_PLAN_2026_11_20.md).

## Owner VS Code verification — no physical hardware

```bash
cd ~/Git/Thesis
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-d3d3a-page-ownership
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
python3 -m unittest discover -s tests -p 'test_m08_m06_parameter_pages.py' -v
python3 -m unittest discover -s tests -p 'test_m08_page_compute_probe_shell.py' -v
python3 -m unittest discover -s tests -p 'test_m08_d3d3a_page_stage.py' -v
python3 scripts/m08_m06_parameter_pages.py --source-only
python3 scripts/m08_d3d3a_page_stage.py --source-only
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
```

**No owner evidence directory changes, no JTAG/Vivado board operations, no guessed PS addresses, no physical DDR writes.**
