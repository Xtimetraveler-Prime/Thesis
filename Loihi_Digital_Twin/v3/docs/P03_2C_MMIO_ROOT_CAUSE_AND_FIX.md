# P03.2c engineering case study — KV260 AXI MMIO failure, root cause, and verified read-path fix

**Date:** 2026-10-11  
**Hardware:** AMD/Xilinx Kria KV260 / K26 (Zynq UltraScale+ MPSoC)  
**Toolchain:** Vivado / Vitis 2025.2  
**Branch:** `agent/v3-p03-autonomous-runtime` (not merged to `main`)  
**Status:** **Full Cortex-A53 read-only MMIO gate physically PASSED** on the boot-matched 128-bit FPD/SmartConnect/32-bit AXI-Lite candidate. **P03.2c full page/resident/dispatch acceptance remains OPEN** until the separate write/command smoke gate completes.

> Read this as a verified read-path root-cause record, not as a claim that
> the autonomous PS runtime or the complete P03 milestone has passed.

## 1. Executive finding

The original custom P03.2 controller was mapped at `0xA4000000` behind
`M_AXI_HPM0_FPD`. Vivado's block design configured the *PL-facing interface*
for **32-bit AXI** and placed a dedicated AXI4-to-AXI4-Lite Protocol Converter
before a **32-bit register slave**. However, the KV260 was initialized by its
existing boot firmware *before* the FPGA PL bitstream was programmed over
JTAG. This boot firmware left the *physical PS HPM0 master width selector*
at **128 bits**, not 32.

A 32-bit peripheral read of offset `+0x000` returned the expected ID.
Reads at offsets `+0x004`, `+0x008` and `+0x018` consistently appeared
as zeros to both XSDB and a standalone Cortex-A53 application—even though
the FPGA's AXI ILAs saw the **correct addresses, successful handshakes and
the correct data** for all four A53-originated transactions.

The measured mismatch was:

```text
Booted FPD_SLCR.afi_fs @ 0xFD615000 = 0x00000A00
  dw_ss0_sel[9:8] = 2 -> PS M_AXI_HPM0_FPD = 128 bits

Booted LPD_SLCR.afi_fs @ 0xFF419000 = 0x00000200
  dw_ss2_sel[9:8] = 2 -> PS M_AXI_HPM0_LPD = 128 bits

Original routed Vivado control interface = 32-bit AXI
Original custom AXI4-Lite register slave = 32-bit AXI-Lite
```

**Corrective design (physically verified for MMIO reads):** retain the
existing FPD master and `0xA4000000` ABI, configure the *Vivado PS-facing
HPM0 interface* for **128-bit AXI4** (matching the live PS configuration),
and insert **SmartConnect 1x1** to perform 128-bit AXI4 to 32-bit AXI4-Lite
width and protocol conversion. The custom register RTL is unchanged.

```text
                    Processing System (PS)
                 M_AXI_HPM0_FPD — 128-bit AXI4
                               |
                               v
              p03_hpm0_width_smartconnect_0
            (128-bit AXI4 -> 32-bit AXI4-Lite)
                               |
                               v
                    p03_ps_control_regs
           (32-bit AXI4-Lite, 0xA4000000 + offset)
                               |
                               v
          Page / debug resident memory / dispatch

Separate inherited bulk path:
    P02 DDR page walker -> 128-bit AXI adapter -> HP0 -> PS DDR
    [UNCHANGED]
```

Independent physical execution of the **read-only A53 diagnostic** on this
candidate reported:

```text
P03_2C_A53_MAGIC=0x50335244
P03_2C_A53_RESULT=0x600D600D
P03_2C_A53_COMPLETE=0xC0DEF00D
PASS: Cortex-A53 MMIO 0xA4000000 returned 0x4C543302, expected 0x4C543302
PASS: Cortex-A53 MMIO 0xA4000004 returned 0x00010000, expected 0x00010000
PASS: Cortex-A53 MMIO 0xA4000008 returned 0x0001031F, expected 0x0001031F
PASS: Cortex-A53 MMIO 0xA4000018 returned 0xD1A60018, expected 0xD1A60018
PASS: P03.2c read-only Cortex-A53 MMIO diagnostic
```

This before/after intervention, paired with a physically measured width
mismatch and otherwise unchanged decoder/ABI, establishes **strong causal
evidence** that the PS/PL width mismatch caused the offset-only read
failures. We did not separately probe the internal PS data-lane mux after
the bus boundary; the precise PS microarchitectural mechanism remains an
inference.

## 2. Project requirements and what must not change

P03 moves algorithmic control from the development PC into the
Cortex-A53/PS. The PS should issue MMIO page-in/page-out, inspect resident
bank state, dispatch the Loihi core, and eventually own scheduling, routing,
and the global timestep barrier. The physical PL includes one HLS
execution engine, three resident-context slots, and an inherited 128-bit
HP0 DDR paging path.

The existing P03.2a register contract includes:

| Relative offset | Name / diagnostic | Value used in physical probe |
|---|---|---|
| `+0x000` | `ID` | `0x4C543302` |
| `+0x004` | `VERSION` | `0x00010000` |
| `+0x008` | `CAPABILITIES` | `0x0001031F` |
| `+0x018` | Temporary otherwise-unmapped signature | `0xD1A60018` |

The `+0x018` signature was temporary diagnostic instrumentation: it
encodes the requested offset, making it especially useful for confirming
that an unusual address actually reached the custom decoder. It must not
be confused with the production architectural register ABI.

Constraints preserved by the fix:

1. The canonical MMIO base stays `0xA4000000` (`M_AXI_HPM0_FPD`).
2. The slave register map stays **32-bit AXI4-Lite**.
3. Existing page, resident-memory and dispatch command semantics remain.
4. The 128-bit HP0-to-DDR bulk paging path remains independent and unchanged.
5. The v2 architectural acceptance record and existing P03.2a/b artifacts
   remain frozen, with a distinct new build of the corrected candidate.
6. Static PS configuration registers are **not patched after Linux boot**.

## 3. Initial physical symptom

Early physical XSDB reads gave:

```text
0xA4000000 -> 0x4C543302  (correct)
0xA4000004 -> 0x00000000  (incorrect)
0xA4000008 -> 0x00000000  (incorrect)
0xA4000018 -> 0x00000000  (incorrect)
```

The fact that ID was correct argued that the full 4 KiB register window
was **at least partially accessible**, but did not establish how bytes at
different offsets were transported. RTL simulation passed. Blindly
rewriting the slave decoder would have risked obscuring the true problem.

A separate practical symptom was that PuTTY/Linux often stopped accepting
commands after JTAG-related programming/debug steps. The project's
subsequent standalone A53 and DDR mailbox testing deliberately avoided
depending on a responsive serial/Linux console. **The PuTTY freeze was not
independently diagnosed and must not be attributed to the width mismatch.**

## 4. Diagnostic sequence and falsified hypotheses

### 4.1. Replace speculative changes with two AXI analyzers

The routed diagnostic FPGA contains:

- **Upstream System ILA:** PS HPM0 -> protocol/width-conversion boundary,
  observing AXI AR/R address, width, handshake, response and data.
- **Downstream native ILA:** passive mirror of the custom AXI4-Lite
  slave's ARVALID, ARADDR, ARREADY, RVALID, RREADY, RDATA and RRESP.

The original attempt to attach a System ILA as if it were an ordinary
third AXI endpoint failed BD validation; the corrected approach monitors
the existing functional net passively, using the native 7-probe ILA to
observe the AXI-Lite slave.

The first successful dual-ILA run was XSDB-initiated. At the VERSION
address `0xA4000004`, both analyzers observed a completed read returning
`0x00010000`. XSDB still printed zero. This **falsified** the claim that
the custom decoder could not handle nonzero offsets. It did *not* yet prove
the CPU sees the correct result, because XSDB accesses were not the same
as A53-originated accesses.

### 4.2. Execute a standalone A53 diagnostic independent of PuTTY

The project added `software/p03/p03_2c_readonly.c`, built for the candidate
fixed XSA by Vitis. XSDB loads/runs that ELF on Cortex-A53 #0. The program
performs four `Xil_In32` MMIO reads, writes their raw values into a
**64-byte DDR mailbox at `0x43FF0000`**, flushes the mailbox, then
marks completion. The host reads the mailbox via the PS debug DDR path.

The initial FPD 32-bit hardware **completed** the ELF (valid mailbox magic
and completion) but reported ID correct and the other three values zero.
Therefore the issue was **not confined to XSDB's physical MMIO read
procedure**.

### 4.3. Try LPD master: same failure

An isolated LPD experiment moved the control aperture to
`M_AXI_HPM0_LPD` at `0x80000000`, retaining the **32-bit PL-facing
interface**. The routed bitstream programmed and the independent A53
read-only mailbox completed, but yielded the identical symptom:

```text
0x80000000 -> 0x4C543302
0x80000004 -> 0x00000000
0x80000008 -> 0x00000000
0x80000018 -> 0x00000000
```

Merely changing PS master region or physical base **did not fix** the
problem. This was an important negative control.

### 4.4. Capture the actual A53-originated reads on LPD

The next step captured the very same A53 execution from both ILAs and
from the DDR mailbox. It ruled out mismatched transactions:

| CPU address | Upstream AR / R sample | Slave AR / R sample | AXI4-Lite RDATA | PS-facing AXI4 RDATA | A53 mailbox |
|---|---:|---:|---|---|---|
| `0x80000000` | 0 / 5 | 0 / 1 | `4C543302` | `4C543302` | `4C543302` |
| `0x80000004` | 37 / 42 | 37 / 38 | `00010000` | `00010000` | `00000000` |
| `0x80000008` | 63 / 68 | 63 / 64 | `0001031F` | `0001031F` | `00000000` |
| `0x80000018` | 90 / 95 | 90 / 91 | `D1A60018` | `D1A60018` | `00000000` |

All observed upstream requests had `ARSIZE=4 bytes`,
`RVALID && RREADY`, `RLAST=1` and `RRESP=OKAY`.
The downstream slave also completed each read. The ILAs had independent
sample windows; do not infer inter-ILA latency by subtracting their
sample numbers.

This established a **PS-side return-path mismatch**, not a bad address,
bad register value, AXI4-Lite decoder bug, or conversion-layer drop.

Relevant raw diagnostic artifacts uploaded for this phase:
`p03_2c_hpm0_capture.csv`, `p03_2c_mmio_slave_capture.csv`,
`p03_2c_a53_readonly_mailbox.bin`, `vivado_ila_capture.log`.
The successful correction's read-only console log was provided later
as text; that log does not retroactively change the earlier raw traces.

### 4.5. Read the *live* PS width selectors

AMD UG1087 describes two static PS registers controlling the master
interface width (details in vendor citations below):

| Hardware selector | Absolute address | Bits | Encoding |
|---|---|---|---|
| FPD_SLCR.afi_fs / dw_ss0_sel | `0xFD615000` | `[9:8]` | 0=32, 1=64, 2=128 |
| LPD_SLCR.afi_fs / dw_ss2_sel | `0xFF419000` | `[9:8]` | 0=32, 1=64, 2=128 |

The project introduced a *read-only* XSDB script
`vivado/p03_2c_xsdb_ps_axi_width_diag.tcl`, which halted A53s and read
these actual PS registers through the PSU debug target.

The user's physical result:

```text
P03_2C_PS_FPD_AXIFS_RAW=0x00000A00
P03_2C_PS_FPD_HPM0_WIDTH_BITS=128
P03_2C_PS_LPD_AXIFS_RAW=0x00000200
P03_2C_PS_LPD_HPM0_WIDTH_BITS=128
P03_2C_PL_EXPECTED_HPM0_WIDTH_BITS=32
P03_2C_PS_WIDTH_MISMATCH_FPD=1
P03_2C_PS_WIDTH_MISMATCH_LPD=1
```

**The mismatch was a measurement of the live KV260, not speculation based
on a reset-value datasheet.** Both original FPD and failed LPD PL
interfaces expected 32 bits; both physical PS interfaces had been
initialized for 128 bits.

### 4.6. Correct the interface, then test the A53 again

A separate candidate used
`P03_PS_MMIO_MASTER=FPD` and `P03_PS_HPM0_DATA_WIDTH=128`.

- Vivado was instructed to instantiate the PS HPM0 master as 128-bit.
- A 1-SI/1-MI SmartConnect was placed before the 32-bit AXI-Lite slave.
- SmartConnect performed **both** width downsizing and AXI4/AXI4-Lite
  protocol conversion.
- The original MMIO register RTL, addresses, PS boot image, and inherited
  DDR HP0 path were not changed.

The user independently built, routed, programmed, built a corresponding
A53 read-only ELF and ran the physical diagnostic. All four values matched
and the mailbox reported `RESULT=0x600D600D` and
`COMPLETE=0xC0DEF00D`.

**No post-fix ILA trace was provided or needed to establish the four A53
read results.** The fix is physically validated for those reads only;
the test did not send command writes or perform page/dispatch operations.

## 5. Why the fix works

The Zynq UltraScale+ PS-to-PL interface width has two distinct sources
of configuration:

1. **PS hardware state established at boot** by firmware/initialization.
2. **PL hardware interface generated by Vivado** and supplied later by a
   JTAG-loaded bitstream.

Those are not automatically kept synchronized when a custom PL bitstream
is loaded on top of a separately booted KV260 Linux image. The 32-bit
Vivado drawing did **not** prove the physical PS side was 32-bit.

For an AXI master configured for 128 bits, a 32-bit register access
may target any one of four 32-bit byte lanes in a 16-byte data beat.
A correctly configured bridge must preserve the address/size semantics
and align the right word/lane on the wide PS bus. With incompatible
PS-versus-PL widths, the observed symptoms are consistent with return
data for nonzero offsets not being delivered into the word selected by
the processor, despite the narrow PL bus having supplied correct data.

**Caution:** The specific internal PS mux/data-lane failure has not been
probed directly. It is a technically grounded explanation for the
measurements, not a proven internal implementation trace.

AMD SmartConnect PG247 documents that when wide AXI4/AXI3 masters feed
32-bit AXI4-Lite slaves, it inserts lightweight protocol conversion and
data-width downsizing automatically. This is exactly the supported
boundary needed here. See:

- [AMD SmartConnect AXI4-Lite low-area mode (PG247)](https://docs.amd.com/r/en-US/pg247-smartconnect/AXI4-Lite-Low-Area-Mode)
- [AMD SmartConnect downsizing to AXI4-Lite slave (PG247)](https://docs.amd.com/r/en-US/pg247-smartconnect/Downsizing-to-an-AXI4-Lite-Slave)
- [AMD UG1087 FPD_SLCR afi_fs](https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/afi_fs-FPD_SLCR-Register)
- [AMD UG1087 LPD_SLCR afi_fs](https://docs.amd.com/r/en-US/ug1087-zynq-ultrascale-registers/afi_fs-LPD_SLCR-Register)

The original AXI Protocol Converter adapted **protocol** but did not
correct the **physical PS/PL width mismatch**. Switching to another PS
master retained the same mismatch and therefore failed. Matching the
physical master width and performing conversion explicitly succeeded.

## 6. Design choice versus alternative boot-time repair

There are two legitimate integration approaches:

| Option | Mechanism | Impact |
|---|---|---|
| **A. Boot-matched FPGA bridge (chosen now)** | Keep live PS HPM0 at 128; generate 128-bit Vivado master and SmartConnect 128->32 | Works with existing KV260 Linux/FSBL boot; existing 32-bit MMIO ABI unchanged |
| B. Boot-time PS init | Build/boot firmware from the *same* candidate XSA and select 32-bit PS HPM0 before accesses | Requires controlling early PS initialization/FSBL; more invasive to existing board boot environment |

Option A has now **passed the read-only physical gate** and is the most
practical path for this phase. It also avoids unsafe writes to width
selectors after the PS is running. AMD describes those SLCR selectors as
static; never change them ad hoc while Linux is active.

For later production boot integration, explicitly document whether the
boot image expects 128-bit PS HPM0 or whether an intentional PS init
change is being introduced. The runtime must not silently rely on an
unverified arbitrary system boot image.

## 7. Reproduce the proven read-only verification

The corrected candidate is opt-in, leaving the original default route
available for historical reproducibility:

```bash
cd ~/Git/Thesis
git switch agent/v3-p03-autonomous-runtime
git pull --ff-only origin agent/v3-p03-autonomous-runtime
source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3

export P03_PS_MMIO_MASTER=FPD
export P03_PS_HPM0_DATA_WIDTH=128
export P03_MMIO_STAGE=bd
export P03_MMIO_BUILD_DIR="$PWD/vivado/build/p03_2c_fpd128_bd_$(date -u +%Y%m%dT%H%M%SZ)"
bash vivado/run_p03_mmio_impl.sh

export P03_MMIO_STAGE=route
export P03_MMIO_BUILD_DIR="$PWD/vivado/build/p03_2c_fpd128_route_$(date -u +%Y%m%dT%H%M%SZ)"
bash vivado/run_p03_mmio_impl.sh

export P03_DIAG_REPORTS="$P03_MMIO_BUILD_DIR/reports"
export P03_XSA="$P03_DIAG_REPORTS/p03_2_ps_mmio.xsa"
export P03_2C_APP_NAME=p03_2c_readonly
export P03_2C_SOURCE_FILE=p03_2c_readonly.c
export P03_2C_READONLY_MMIO_BASE=0xA4000000
export P03_2C_EXPECTED_XSA_SHA="$(sha256sum "$P03_XSA" | awk '{print $1}')"
export P03_2C_BUILD_DIR="$PWD/vivado/build/p03_2c_readonly_fpd128_$(date -u +%Y%m%dT%H%M%SZ)"
bash scripts/build_p03_2c_smoke.sh

# Reboot KV260; let normal firmware initialize DDR; keep hw_server up.
bash scripts/run_p03_2c_readonly.sh
cat "$P03_2C_BUILD_DIR/read_only_physical_evidence/verify.log"
# Reboot KV260 again: A53 Linux execution context was replaced.
```

The build directory, XSA, bitstream, probes, ELF and run log must be kept
together for independent audit. The user's most recent passing console
log is recorded above; its **exact artifact SHA-256 fingerprints were not
provided in the conversation** and must not be invented.

## 8. Full P03.2c acceptance gate (next, not yet completed)

The successful read-only probe verifies ID/VERSION/CAPABILITIES and an
otherwise-unmapped signature. It does **not** prove AXI writes, paging,
debug/resident reads or HLS dispatch. These are required for P03.2c.

The repository already contains `software/p03/p03_2c_smoke.c` and a
deterministic fixture generator. A new candidate build switch and full
physical driver now support the corrected XSA **without overwriting
the previously frozen baseline build**.

Required full acceptance observations:

1. A53 MMIO ID `0x4C543302`, VERSION `0x00010000` and
   CAPABILITIES `0x0001031F`.
2. Page core0's DDR backing record from `0x40000000` into resident slot 0.
   Check completion with no errors, `438272` transferred bytes,
   `1712` read bursts and `0` write bursts (per generated fixture).
3. Read back the resident `config[0]` with the debug/resident-memory path,
   check done/rvalid/no error, and compare to the frozen fixture manifest.
4. Issue an HLS dispatch on context 0 with no current events; require
   completion, no packet/core errors, and one completed dispatch.
5. Verify global status is clean and result mailbox passes **all** verifier
   checks. Preserve bitstream/XSA/ELF/fixture hashes and physical logs.

The full test uses the existing `p03_2c_verify_mailbox.py` to verify
the completed 64-byte DDR mailbox against `fixture/manifest.json`.
It is intentionally **not** the autonomous five-over-three test.

**After independent full-smoke PASS:** update the P03.2c acceptance record,
agree on what diagnostic instrumentation should be retained/removed for a
final shell, route that final shell if necessary, and then close P03.2.
Do **not** merge until explicitly authorized.

## 9. Consequences for P03.3–P03.5 and later phases

- **P03.3:** Implement the PS-local scheduler/router/barrier runtime using
  the now-working `0xA4000000` MMIO transport and DDR-backed context
  management. The PC must not drive any algorithmic control after launch.
- **P03.4:** Run the frozen five-logical-core/three-resident-slot,
  seven-timestep/35-dispatch workload with a single PC start action.
- **P03.5:** Run 100 timesteps board-locally and compare normalized state,
  packet, and event outcomes to the frozen Python/v2 model.
- **P05:** Expand board-local regressions/observability after the runtime is
  functional; do not confuse the present read-only smoke with P05 coverage.
- **P06–P09:** Select/audit a reproducible benchmark, execute it on the
  board, characterize latency/power/energy, and write a source-backed
  comparison. These depend on the complete P03 runtime, not just MMIO.

The relevant engineering lesson is a general PS/PL integration principle:
**a Vivado BD interface width is not evidence that the already-booted PS
runtime configuration matches it**. Measure static PS selectors, inspect
both sides of the AXI handshake, and record the exact bitstream and boot
context before changing the custom slave RTL.

## 10. Evidence provenance and claims discipline

- **Independent user hardware results:** first failing XSDB MMIO values;
  failing FPD and LPD standalone A53 mailboxes; live FPD/LPD width
  registers; successful corrected FPD128 full *read-only* A53 mailbox.
- **Uploaded raw measurements from the earlier bad configuration:**
  `p03_2c_hpm0_capture.csv`, `p03_2c_mmio_slave_capture.csv`,
  `p03_2c_a53_readonly_mailbox.bin`, `vivado_ila_capture.log`.
- **Source/static gates:** RTL/Vivado scripts, Python/pytest tests,
  manifest-based verifiers and isolated candidate XSA identity checks.
  Static source checks are not substitutes for routed/physical tests.
- **Vendor sources:** AMD UG1087 register descriptions and PG247
  SmartConnect data-width/protocol conversion semantics.
- **Not yet proven:** full P03.2c command smoke; final non-diagnostic
  P03.2 shell; P03.3 autonomous scheduling/routing/barriers; P03.4/P03.5
  workload equivalence; explanation for PuTTY/Linux freeze.
