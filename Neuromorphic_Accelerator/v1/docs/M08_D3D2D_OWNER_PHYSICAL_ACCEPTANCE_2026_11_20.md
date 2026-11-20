# M08 D3.D.2D — owner-original KV260 raw-event ingestion physical acceptance

**Date:** Friday, 20 November 2026. **Authoritative state:** **D3.D.2D PHYSICALLY ACCEPTED** for the explicitly bounded 17-input-event/32-neuron×4-tick M06 workload. This record supersedes the *historical* "not yet programmed / gate still pending" sections of the earlier D3.D.2D design plan; those sections are left in repository history for traceability. **M08 remains OPEN; M09 remains PLANNED.**

## Real original owner evidence (DO NOT ALTER)

| Field | Observed/reported first-owner original |
| --- | --- |
| New design | M32E v5: 32 signed16 LIF neurons, four logical timesteps, five positive-delay signed16 recurrent edges, **17 individually transmitted signed32 external events** |
| Native directory | `/home/dna/Thesis_Evidence/M08/m08_d3d2d_event_DE6kQWvt` |
| Native original bitstream | `bitstream_candidate/m08_d3d2d_event_lif_jtag_UNRELEASED.bit` |
| Exact bitstream SHA256 | `f50a156342eaf1173a3869b5316e4edc1d59662d9f0d687bcec600f7b0efdeab` |
| Bitstream bytes | 7,797,844 |
| Native original SHA ledger | **12/12 OK**, reported in owner Vivado output and rechecked in owner DRC transcript |
| Original DRC full report SHA256 | `f1cc7a7b72b7eeee85828a6c5f7cb75d56894a55a2143cfe4e0f1f6c8098ebee` |
| Native DRC | Seven individually owner-reviewed **vendor XSDB/JTAG infrastructure warnings**, not a generic waiver; details in D3.D.2D plan and exact gate |
| Routed 100 MHz timing | WNS **+2.136 ns**, TNS 0, WHS **+0.010 ns**, THS 0, no failing setup/hold endpoints |
| Original physical folder | **`/home/dna/Thesis_Evidence/M08/m08_d3d2d_event_HW_h7RmZQui`** |
| Physical SHA ledger | **6/6 OK**: `00_executed_source.tcl`, `01_jtag_m06.log`, `02_jtag_m06.jou`, `03_exit.txt`, `10_m06_raw17_golden.hex`, `80_m06_raw17_hw_parity.txt` |
| Owner physical exit file | `vivado_physical_exit=0` |
| User-executed independent auditor | `scripts/m08_d3d2d_event_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"` |
| Independent auditor acceptance status | **`M08_D3D2D_PHYSICAL_M06_17_RAW_EVENT_128_BUCKET_384_NEURAL_ACCEPTED`** |
| Real hardware quantities checked | **128/128** fabric-accumulated external current buckets; **128/128** membrane voltages; **128/128** spike decisions; **128/128** FPGA-delivered recurrent synaptic current values; **512 numerical checks in total** |

**Evidence provenance and independence.** The owner supplied the terminal transcript showing six original SHA receipts each `OK`, `cat "$HW/03_exit.txt"` returning `vivado_physical_exit=0`, and the independent physical auditor JSON reporting `external_event_ingestion_in_fabric=true`, `external_raw_events=17`, `physical_neurons=32`, `logical_ticks=4`, `recurrent_synapses=5`, each of the four `hardware_*_verified` counters exactly **128**, and the acceptance marker above. The assistant did **not** directly open the user's original `/home/dna/Thesis_Evidence` hardware folder; independent checker behavior is documented in source and its mock/mutation tests, but the *genuine board observations* in this record are the user-provided outputs. The owner did not separately upload the full UART capture or standalone `80_m06_raw17_hw_parity.txt` here. Do **not** fabricate those or any energy, temperature, event-rate or latency figures.

The physical auditor requires the **exact original accepted M32E image**, original 12-file native/source/builder/DRC/timing provenance, original physical six-file SHA receipt, exact executed Tcl, one observed programming marker, unique K26 target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, device `xck26_0`, debug AXI `hw_axi_1`, BRAM `55AA22DD` echo, `M32E/0x00050000` identity, 17 real event PUSHes with per-event count, 128 on-FPGA input-current sums and all 32 complete voltage/mask/recurrent-current readback rows against the independently generated original M02 dense/event and M03 sparse golden. The auditor's acceptance means those checks passed; its **hardware evidence** must not be conflated with synthetic parser tests or a source-only CI pass.

## What advanced physically over D3.D.2C

| Property | D3.D.2C (already physically accepted) | D3.D.2D (this accepted result) |
| --- | --- | --- |
| Original M06 neurons/ticks/recurrent edges | 32 / 4 / 5 | 32 / 4 / 5 |
| Original signed external events | 17 | 17 |
| External current summation | **PC host-coalesced** to signed32 per neuron/tick | **On FPGA**, 17 separate host-sent `(neuron,tick,signed_current)` AXI-Lite mailbox PUSHes |
| Recurrent synaptic routing | On FPGA | On FPGA |
| Independent hardware neural results | 128 voltage +128 spike +128 recurrent current | Same 384, all pass |
| Additional **hardware input** results | Not physically reconstructed from raw event pushes | **128** FPGA-generated input buckets, all pass |
| Scope of hardware conclusion | Bounded M06 recurrent parity | Bounded M06 recurrent parity **plus on-FPGA signed input event accumulation** |

The v5 peripheral can reject out-of-range neuron/tick, partial writes, overflow, >64 accepted PUSHes, and writes while BUSY in the actual Icarus AXI test; the original owner hardware run specifically exercised the 17-event normal workload and 512 positive numerical comparisons, **not** a comprehensive physical fault-injection or stress/throughput test. Event arrival still depends on **serialized synchronous JTAG AXI-Lite transactions**: fabric accumulation is real, but autonomous event scheduling and asynchronous transport are *not* thereby demonstrated.

## Scope limitations and ongoing research

**Proven (bounded):** one physical, timing-closed 100 MHz PL image accepting 17 signed raw external events over JTAG AXI-Lite; 128 independent signed input-current bucket sums and 384 independent neural outputs; M06 dense/event and M03 sparse reference agreement in simulation; full physical SHA receipt and read-only audit. Earlier successful D3.C→D3.D.2B and D3.D.2C physical stages remain separately documented.

**Not proven:** original M05 physical HLS event router; original M06 HLS paged memory or real DDR traffic; 64KiB paging in physical DDR; physically sparse neuron skipping (32 neurons are evaluated), autonomous tick/event queue, asynchronous hardware delivery, AXI-Stream/DMA, CPU/PL independent operation (PL clock remains requested from PS PL0), Linux management or PS-to-PL MMIO coexistence, sustained throughput, power/energy, thermal/cooling duration, or system-level equivalence to Loihi.

All prior D3.D.2C original artifacts `m08_d3d2c_m06_MN2pwduB`, `m08_d3d2c_m06_HW_BsHcfs4j` and earlier native timing-failure evidence `m08_d3d2c_m06_RIezhupj` are immutable as well. New D3.D.2D first original image and physical folder are now immutable. **Never reprogram this accepted image by default; preserve ledgers, journals, bitstreams and UART data exactly as created.**

## Owner reproduction of read-only acceptance (not a new physical attempt)

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2d_event_DE6kQWvt"
HW="$HOME/Thesis_Evidence/M08/m08_d3d2d_event_HW_h7RmZQui"
(cd "$RUN" && sha256sum -c 99_evidence_sha256.txt)
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
cat "$HW/03_exit.txt"
python3 scripts/m08_d3d2d_event_native_review.py --run-dir "$RUN"
python3 scripts/m08_d3d2d_event_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```

**Expected result:** original 12/12 and six/six ledgers `OK`, original `vivado_physical_exit=0`, native `M08_D3D2D_EXACT_OWNER_NATIVE_RAW17_IMAGE_ACCEPTED_NO_BOARD`, physical `M08_D3D2D_PHYSICAL_M06_17_RAW_EVENT_128_BUCKET_384_NEURAL_ACCEPTED`. These are read-only; **no physical rerun is required**.

## Next step

Continue in a **new branch and new chat**. Read the **new handoff** `docs/M08_D3D2D_TO_NEXT_PHYSICAL_HANDOFF_2026_11_20.md` and **repeatable implementation methodology** `docs/M08_KV260_SUCCESSFUL_BITSTREAM_METHODS_2026_11_20.md` first. Favor a small, distinct next on-FPGA event queue/tick-consumption experiment over simultaneously introducing DDR, Linux/PS MMIO, HLS and autonomous event execution. The proposed next phase is **D3.D.2E (plan/propose first)**, not claimed to be already physically implemented. Every new RTL, bitstream and DRC profile requires new tests, original owner-native review and separate, manually authorized one-shot hardware validation. M08 stays OPEN/M09 PLANNED; do not merge draft PRs without owner approval.
