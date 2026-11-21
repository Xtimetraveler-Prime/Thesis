# M08 D3.D.2E — FIRST independently accepted M32Q 32-neuron queued-event physical evidence

**Date:** Friday, 2026-11-20. **Acceptance:** **D3.D.2E PHYSICAL ACCEPTED** for the specifically bounded synchronous 32-neuron×4-tick M06 workload and the on-fabric FIFO/tick-service contract. This document supersedes the older provisional audit-pending text in the chronological notes. **M08 remains OPEN, M09 remains PLANNED, PR #93 draft and unmerged.**

## Original evidence provenance, never modify

| Evidence | First original owner path / immutable identity |
| --- | --- |
| Vivado native first owner offline | `~/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC` |
| Accepted original bit | `bitstream_candidate/m08_d3d2e_queue_lif_jtag_UNRELEASED.bit`, **7,797,844 bytes**, SHA256 `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc` |
| First physical owner JTAG run | `~/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN` |
| Original native ledger | **12/12 first original SHA entries** independently accepted by exact-native source/DRC/route/image gate before programming |
| Original hardware ledger | `99_evidence_sha256.txt` with **6/6** SHA rows `OK` on owner local re-audit; all original bytes unchanged |
| Full original routed DRC | SHA `3c4c1d8bd304dc71eb4f21bddee7a9c35cbf2053857a805c097bc2e96f0157c6`; seven image-specific vendor debug/JTAG advisories individually reviewed |
| Original routed timing | SHA `cdeaf520fbbb944de4148cecca290651125c3009a2375966ee2b5d17f584c59f`, **WNS +1.844 ns, WHS +0.010 ns**, 0 failing setup/hold, nominal PL0 100 MHz |
| Original clock report | SHA `836479b2faf87c71df2f50b9b19128d4b6ba7e9ac6dd72a41a6f42383ae43820` |

The user personally ran the first actual Vivado 2025.2 physical shell on 2026-11-20 **16:54:56–16:55:20 America/Denver**, using exactly one JTAG `program_hw_devices`. The live device was `xck26_0`, JTAG target `localhost:3121/xilinx_tcf/Xilinx/XFL1RK5M5ILQA`, debug AXI `hw_axi_1`, BRAM write/read `55AA22DD`, M32Q identity `4D333251`, version `00060000`. The first physical shell itself ended with an independent-auditor false negative, which **was not a hardware error**.

## Original first hardware functional results

The original hardware JTAG Tcl checked **17 separate signed32 raw external events**, each atomically PUSHed into a bounded **32-entry FIFO** with 64 accepted-event lifetime cap. It observed **17 accepted and 0 serviced** before any SERVICE, and verified all **128 live FPGA input-current buckets remained ZERO** before explicit SERVICE; FIFO high-watermark **17**.

Four **ordered, explicit** tick SERVICE barriers transferred **5, 5, 4, 3** original events for ticks 0, 1, 2, 3, with final count **17 serviced**, FIFO **depth 0**, high watermark **17**, tick completion mask **0xF**, four per-tick counters passing. These are synchronous PL0-clocked service boundaries, **not asynchronous independent event processing**.

The original M02 dense/event and M03 sparse-matched M06 32-neuron×4-tick/five-positive-delay-edge reference produced **512 exact hardware comparisons**: **128/128 external fabric-summed current buckets**, **128/128 neuron membrane voltages**, **128/128 neuron/tick spike decisions**, **128/128 delivered recurrent signed currents**. Original hardware log printed all per-neuron markers and final `M08_D3D2E_PHYSICAL_M06_128_EVENT_128_VOLTAGE_128_SPIKE_128_SYN_CURRENT_PASS`. The first original physical `99_evidence_sha256.txt` showed six files verified.

## Root cause of initial standalone Python audit failure — repaired WITHOUT replaying hardware

The first independent receipt auditor returned `M08_D3D2E_PHYSICAL_RECEIPT_REJECTED: missing/duplicated physical per-tick SERVICE receipt` because its string contained a **literal backslash-n** rather than the actual newline in the Vivado log. This was a code-level parsing bug. No hardware mismatch was observed and **no new bitstream or JTAG programming** was permitted to fix the auditor.

Source-only fix in `scripts/m08_d3d2e_queue_physical_audit.py` compares exactly four **ordered whole log lines** from `splitlines()`; negative tests reject duplicated, missing, reordered and altered tick markers. Independent synthetic six-file receipt tests also reject changed SHA, missing native acceptance and altered neural traces. Source-only GitHub CI passed on both push and PR for the changed code (runs `44840475601` and `44840480839`), and the owner subsequently ran the updated software **read-only** on the exact first-original physical directory.

## Final FIRST ORIGINAL independent owner physical acceptance (new user results)

Owner supplied the following *completed* read-only audit output, with no second physical run:

- `Ran 6 tests in 0.063s — OK` (new adversarial read-only auditor tests);
- **6/6 physical SHA evidence entries `OK`**, exactly `00_executed_source.tcl`, `01_jtag_m06.log`, `02_jtag_m06.jou`, `03_exit.txt`, `10_m06_tickqueue_golden.hex`, and `80_m06_tickqueue_hw_parity.txt`;
- Full exact-original image SHA `2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc`;
- Auditor JSON `external_event_ingestion_in_fabric=true`, `fifo_live_buckets_zero_before_service=128`, `physical_events_accepted=17`, `physical_events_serviced=17`, `fifo_high_watermark=17`, `four_service_tick_barriers=true`, `hardware_input_buckets_verified=128`, `hardware_voltages_verified=128`, `hardware_spike_decisions_verified=128`, `hardware_recurrent_currents_verified=128`, `physical_neurons=32`, `logical_ticks=4`, `recurrent_synapses=5`, `external_raw_events=17`;
- **Exact independent terminal status**:

```text
"status": "M08_D3D2E_PHYSICAL_M06_17_QUEUED_EVENT_128_BUCKET_384_NEURAL_ACCEPTED"
```

**Acceptance decision: PASS, D3.D.2E PHYSICAL COMPLETE** in this precise JTAG-FPGA FIFO/clocked-service 32×4/17-event/five-edge scope. This is a user-supplied independent original audit result; the repository cannot directly inspect the owner's off-repo physical evidence bytes. Do **not** reprogram this original image or rehash/rewrite either original evidence directory; preserve all previously accepted D3.D.2A–D owners' immutable records.

## Explicit nonclaims and handoff

This PASS does **not** demonstrate independently asynchronous clock domains, AXI streaming event ingress, DMA/DDR-backed neural state, pageable signed16 physical state ownership, original M05 HLS or original M06 HLS hardware, matched four-way physical comparisons, Loihi silicon operation, throughput/latency measurements, energy or power. The PS-supplied PL0 clock remains an architectural dependency.

**Next scoped M08 stage: D3.D.3 — safe host-paged state-memory integration**, beginning with source-only state-page ownership protocol and read-only kernel/PS memory authorization review; no DDR addressing/writes or new hardware release until separately accepted. M09 quantitative interaction study follows **completed and accepted M08 measurement**. New work requires a **separate new stacked branch** from this approved source head; PR #93 stays **draft/unmerged** until owner authorizes release.

## Local read-only re-verification (never run the physical shell again)

```bash
cd ~/Git/Thesis/Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
RUN="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_GFz0SbiC"
HW="$HOME/Thesis_Evidence/M08/m08_d3d2e_queue_HW_4HQkm7rN"
(cd "$HW" && sha256sum -c 99_evidence_sha256.txt)
python3 scripts/m08_d3d2e_queue_physical_audit.py --run-dir "$RUN" --hw-dir "$HW"
```
