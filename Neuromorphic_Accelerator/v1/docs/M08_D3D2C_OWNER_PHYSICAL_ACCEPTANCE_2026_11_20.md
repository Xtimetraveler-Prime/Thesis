# M08 D3.D.2C — Owner-original 32-neuron recurrent M06 physical acceptance

**Evidence date:** 2026-11-20. **Scope:** first original KV260 JTAG-only 32-neuron×4-logical-tick test. **Status:** **PHYSICALLY ACCEPTED (bounded M06 neural parity)**, on the strength of owner-provided terminal readback and independently executing read-only auditor. The assistant cannot inspect the owner's local files directly.

## Original, immutable evidence

| Item | Original value |
| --- | --- |
| Original accepted Vivado native directory | `~/Thesis_Evidence/M08/m08_d3d2c_m06_MN2pwduB` |
| Original first physical directory | `~/Thesis_Evidence/M08/m08_d3d2c_m06_HW_BsHcfs4j` |
| Accepted owner original bitstream | `bitstream_candidate/m08_d3d2c_m06_lif_jtag_UNRELEASED.bit` (native folder) |
| Bitstream SHA256 | `244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932` |
| Bitstream size | 7,797,842 bytes |
| Tool version | Vivado 2025.2 |
| Original routed timing | WNS **+2.675 ns**, TNS **0**, WHS **+0.010 ns**, THS **0** |
| Original DRC | 7 exact owner-reviewed vendor XSDB/JTAG advisories, not a generic waiver; detailed scope in D3.D.2C plan |
| Physical JTAG target | `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA` |
| Device | `xck26_0` |
| AXI debug master | `hw_axi_1` |
| Test | Original M06 G3.3: 32 signed16 neurons, 4 logical ticks, 5 recurrent signed positive-delay edges, 17 external events |
| External event delivery | **HOST-COALESCED** to 32×4 per-neuron/tick signed32 current registers |
| Hardware synapse routing | Recurrent current contributions calculated in FPGA using previously committed spike history, **not** host-computed recurrent traces |
| Physical comparison | **128/128 voltage values**, **128/128 spike decisions**, **128/128 recurrent delivered-current values**, all parity-accepted |
| Owner independently executed audit | `M08_D3D2C_PHYSICAL_M06_32X4_REAL_RECURRENT_M02_PARITY_ACCEPTED` |
| Physical SHA ledger | **6/6 `OK`**: executed Tcl, original JTAG log, Vivado journal, exit record, independent M06 golden, complete 32-neuron parity readback |

### What the owner actually supplied

The owner copied output of `(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)`: all six members returned `OK`. The owner copied the entire physical `80_m06_32x4_hw_parity.txt` receipt containing eight metadata lines and **32 distinct neuron rows** from `neuron=0` through `neuron=31`, each with four 32-bit hex voltage words, a four-bit spike mask and four 32-bit hex delivered recurrent-current words. That receipt records `target=localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, `device=xck26_0`, `debug_axi=hw_axi_1`, the accepted image SHA, `external_events_coalesced_on_host=YES`, and `physical_ddr_m06_hls_verified=NO`.

The owner then ran `python3 scripts/m08_d3d2c_m06_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"`; its reported status is `M08_D3D2C_PHYSICAL_M06_32X4_REAL_RECURRENT_M02_PARITY_ACCEPTED` and its independent counters are **128 voltages, 128 spike decisions and 128 recurrent currents** with `physical_neurons=32`, `four_ticks=true`, `recurrent_edges=5` and `host_coalesced_external_events=17`. The auditor verifies original native acceptance, six immutable physical receipt hashes, exact executed Tcl, one program marker, JTAG identity, original independent M02 dense/event + M03 sparse oracle and all 32 readback rows before returning this status. This is genuine owner-supplied physical evidence, not synthetic test output.

**Evidence precision:** the owner did not paste a separate terminal `M08_D3D2C_PHYSICAL_RUN_EXIT` line or the full UART log. The independently accepted six-file ledger includes a saved `03_exit.txt`, and the successful auditor checks `vivado_physical_exit=0` plus expected programming, BRAM, engine identity and parity markers in the original JTAG log. Do not invent additional UART, thermal, power, performance or bandwidth measurements.

## Scope and limitations

**This closes D3.D.2C hardware recurrent parity, not all of M08.** The four logical ticks run on the 32-neuron 100 MHz routed PL design. The long recurrent computation is pipelined over **five active synapses + five pipeline stages = ten fabric clocks/neuron/tick**, but no independent physical wall-time/energy or sustained throughput is measured here. The test does not demonstrate direct FPGA ingestion/coalescing of the 17 distinct external events, the original M05 event stream, M06 HLS FPGA integration, M06 simulated canonical 64KiB paging on real DDR, physically sparse execution (all 32 neuron states update), Linux-managed PS→PL MMIO, DDR DMA, clock independence from PS, or an asynchronous physical circuit. The seven accepted Vivado warnings remain documented and limited to this original reviewed bitstream.

**No repeated physical programming is necessary.** Preserve `MN2pwduB`, `HW_BsHcfs4j` and earlier failed original `m08_d3d2c_m06_RIezhupj` unchanged. Never rewrite their ledgers, Tcl sources or bitstreams.

## Next experiment: D3.D.2D external-event ingestion on fabric

The scientifically useful immediate next step is to remove the **host-coalescing** limitation while holding fixed 32 neurons, 4 logical ticks, five signed delayed recurrent synapses and the original 17 individual external M06 events. Create a **distinct** `M32E` v5 input-event ABI, perform sequential signed current accumulation inside FPGA registers, and compare to the same independent M02/M03 384-value trace, with event-register readback and negative cases. The host should send raw `(neuron,tick,signed_current)` records **without aggregating them**. This remains a JTAG control-plane ingress test, not asynchronous event streaming, DMA, M05 HLS or DDR. Use a fresh branch, RTL testbench, M06 event-vector generator, source-only gates, new isolated Vivado candidate, new source/image-specific DRC/timing review and a **separately** authorized one-shot physical test. Do not reuse D3.D.2C native/physical approvals for a new RTL/bitstream.

## Owner read-only replication

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2c_m06_MN2pwduB"
HW="$HOME/Thesis_Evidence/M08/m08_d3d2c_m06_HW_BsHcfs4j"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3d2c_m06_native_review.py --run-dir "$RUN"
python3 scripts/m08_d3d2c_m06_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```

All commands above are read-only. The independently audited physical PASS remains specific to **this** original image and experiment.
