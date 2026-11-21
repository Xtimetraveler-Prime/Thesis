# M08.5 — source-only trusted CSR ABI v1 and independent drain requirement (2026-11-20)

**State:** PC/source design and negative tests only. M08.4 original physical result stays ACCEPTED/CLOSED and immutable. M08.5 is ACTIVE on draft PR #95. This file does NOT attest a Linux kernel driver, actual PS AXI-Lite MMIO, PS HP0 memory, physical AXI drain, firmware ownership, measured throughput, Vivado route, or permission to touch the KV260. The existing seven-page signed16 recurrent engine and independent M02/M03 numerical oracle are unchanged.

## Read-only source/boot audit — what is actually known

| Boundary | Existing first-party source evidence | What remains missing |
| --- | --- | --- |
| PL AXI4 data master → PS HP0 | Loihi v3 `create_p02_ddr_impl_project.tcl` connects P02 AXI128 burst adapter → SmartConnect → PS `S_AXI_HP0_FPD`; `PSU__SAXIGP2__DATA_WIDTH=128`. Prior **different** v3 debug-stop hardware experiment accessed physical DDR. | **M08.5 has no such connected master**, new K26 XSA/route, live Linux ownership, IOMMU/bus translation, boot XMPU proof or independent drain. |
| PS HPM0 → PL control | Loihi v3 `create_p03_mmio_impl_project.tcl` handles 128-bit PS HPM0 → 32-bit control conversion; earlier boot mismatch produced a real failure. | M08.5 has **no** AXI-Lite slave, conversion, platform driver, protected register decode, verified AFI/firmware width, or attached interrupt. |
| Original accepted M08.4 | `scripts/m08_paged_m06_lif_build.tcl` disables `PSU__USE__M_AXI_GP0/1/2` and uses **JTAG AXI/BRAM**, one resident 256B bank. | This is NOT an HP0/DDR source or authenticated Linux MMIO route. Do not modify accepted bitstream/evidence. |
| M08.3 boot/Linux inventory | `scripts/m08_3_dma_readonly.py`, `M08_3_DMA_READINESS_RUNBOOK.md`, `M08_D3B_BOOT_PLATFORM_EVIDENCE_MATRIX_2026_11_12.md` provide bounded **read-only** inventory and explicit UNKNOWN/blocked records. | No source-only inspection establishes applied DTB, bound device, DMA mask, `dma_addr_t`, `dma-ranges`, IOMMU, kernel-validated buffer lifetime, booted AFI or true isolate/drain acknowledgment. |

**Decision:** actual PS/PL memory ownership and all physical DDR cells remain **UNKNOWN/BLOCKED**. Do not infer available DDR from synthetically asserted `*_verified` pins, a DMA heap, static v3 addresses, source connection strings, or prior hardware receipts.

## Candidate control path and register ABI

The new first-party `rtl/m08/m08_m085_trusted_control_abi.v` is a **32-bit CSR command decoder and sequencer**, not an AXI4-Lite slave. A future independently version-checked protected AXI-Lite bridge must verify booted PS HPM0 width, route/reset, actual privileged driver binding, access separation, write ordering and timeout/error behavior before presenting one atomic command beat here. The caller must NEVER directly expose these registers to userspace UIO, allow arbitrary user-provided addresses or interpret a CSR magic value as driver authentication.

**ABI identification:** `CAP_MAGIC=0x4D303835` (ASCII M085), `ABI_VERSION=0x00010000` (major 1, minor 0). All addresses below are **byte offsets in a future control register aperture**; they are not absolute MMIO addresses. They do not define a live PS address.

| Byte offset | Access | Semantics |
| --- | --- | --- |
| `0x00` | RO | `CAP_MAGIC`. Validate before any command. |
| `0x04` | RO | `ABI_VERSION`. Reject incompatible major/minor at driver probe. |
| `0x08` | RO | Local state/status: phase, stop, granted, sealed, sticky fault. NOT a hardware drain receipt. |
| `0x0C` | RO | Requested drain and **externally supplied** ack / transport-idle / bank-clean observations. |
| `0x10` | RW once before grant | `DMA_BASE_LO[31:0]`, from bound driver's **device** `dma_addr_t` only. |
| `0x14` | RW once before grant | `DMA_BASE_HI[63:32]`. |
| `0x18` | RW once before grant | `ALLOCATION_BYTES` supplied by same bound driver; requires at least 1,792. |
| `0x1C` | RW once before grant | Nonzero `GENERATION`, fresh per lifetime, not an identity secret. |
| `0x20` | WO | `1=GRANT` after all four fields and idle/drain-ack; `2=STOP_AND_DRAIN` once active. |

All writes require a **single aligned full 32-bit strobe `0xF`** from an independently trusted producer while external platform/route verifiers are continuously valid. Partial writes, writes to RO/unknown offsets, malformed commands, mutation of a frozen descriptor, write-on-closed state, a forged producer bit or trust loss are terminal sticky errors. In this **test-only** implementation the `csr_trusted`, `driver_bound_verified`, `control_route_verified` and `interconnect_drain_ack` bits come from an Icarus testbench; they are **not authenticators**. A *real* AXI-Lite adapter would need WSTRB/address/AW/W/B arbitration, independent timeout/replay rejection, PS write barrier and readback; those are NOT implemented here.

The decoder instantiates the **existing** `m08_m085_kernel_dma_lease_fence.v`; it does not replace the seven-slot arithmetic, 65-bit allocation bounds, nonzero generation or original bank/AXI/neural design. A valid grant admits only the fence's frozen `[dma_base,dma_base+1792)` window. No user-chosen DDR transfer address is part of the ABI. The decoder provides `admit_work`/source-only `stop_new_requests` pins; **the new CSR decoder is not yet wired into the existing recurrent neural candidate or a protected physical PS control plane.** Existing source candidate/testbench behavior is unchanged.

### Drain/release state and proof obligation

1. Grant after exactly four complete descriptor writes, with bound-owner and control-route signals valid, source transport/bank idle, and independent *currently safe* bus indication. The source fence latches the record and admits work.
2. `STOP_AND_DRAIN` immediately makes `admit_work=0` and `stop_new_requests=1` combinationally on the command cycle. No new page or neural dispatch may be launched. Existing in-flight AXI transactions may still require completion/reset.
3. Assert `drain_request`. **Reject a stale/high `interconnect_drain_ack` from before STOP**: require it to be observed LOW after the request, and only later observed HIGH from the external drain controller. At the release edge also require `transport_idle` and `bank_clean_idle`. A bounded timeout quarantines the lease and **does not license freeing memory**.
4. Pulse release into the original DMA fence only after the fresh two-phase ack and clean-idle interlocks. Verify its SEALED state. Regrant is forbidden without separate reviewed full reset/recovery; a source reset itself is **not** bus drainage.
5. On any partial AXI write, lost B/R response, control loss, poison or drain-timeout, the kernel owner must **retain/quarantine** the allocation until independent bus isolation/reset and no-late-response proof. Merely setting busy=0, poison=1, or resetting fabric is insufficient to call `dma_free_coherent`.

**Important design limitation:** a malicious/faulty external source can still assert a false low→high drain ACK, or a fake "driver verified" bit. The RTL intentionally cannot prove the PS interconnect is empty or that MMIO is kernel-exclusive. A later hardware candidate must implement and independently validate the physical drain monitor/reset ownership and protected PS HPM0 adapter before this ABI can drive the existing M08.5 neural candidate. Do not treat the positive Icarus test as genuine drain attestation.

## Directed genuine source RTL verification

`rtl/m08/tb_m08_m085_trusted_control_abi.sv` instantiates the RTL decoder **and the unchanged real lease fence**, without any neural numerical changes or mock replacements. `tests/test_m08_m085_trusted_control_abi.py` compiles using genuine Icarus (`iverilog -g2012` + `vvp`), runs one positive CAP/version/four-field grant/fresh drain/one-way seal and **19 separately executed negative cases**: forged command, partial strobe, write to read-only, incomplete descriptor, zero generation, misaligned base, unbound producer, in-session owner/control withdrawal, regrant, mutation, dirty bank, stale preexisting ACK, busy transport, postrelease regrant, wrong command, mid-drain mutation, same-cycle untrusted STOP, and undersized allocation.

These tests do NOT exercise a physically connected AXI-Lite transaction, Linux security, IOMMU, new Vivado synthesis or physical PS/PL bus drain. All accepted M08.4 owner receipts, original signed16 oracle, 24 neural dispatches and six-cell comparison rules remain unchanged.

### Owner PC / VS Code verification (no board, no Vivado)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/neuromorphic-accelerator-v1-m08-matched-experiments
git pull --ff-only origin agent/neuromorphic-accelerator-v1-m08-matched-experiments
git rev-parse HEAD
cd Neuromorphic_Accelerator/v1
export PYTHONDONTWRITEBYTECODE=1
command -v iverilog && command -v vvp
python3 -m compileall -q src scripts tests
python3 -m unittest discover -s tests -p 'test_m08_m085_trusted_control_abi.py' -v
python3 -m unittest discover -s tests -p 'test_m08_m085_kernel_dma_lease.py' -v
python3 -m unittest discover -s tests -p 'test_m08*.py' -v
python3 -m unittest discover -s tests -v
```

For the **future** owner-approved read-only KV260 inventory, use the already-documented `docs/M08_3_DMA_READINESS_RUNBOOK.md` rather than executing any OS/driver/DDR writes here. A separate hardware release requires exact XSA/DT/bit/firmware evidence, routed resources/DRC/timing, real driver identity and buffer ownership, full physical outstanding drain, rollback/thermal/JTAG preflight and explicit session authorization.
