from pathlib import Path

path = Path("MILESTONES.md")
text = path.read_text(encoding="utf-8")

old_evidence = "**Repository evidence:** `main` through M11.5.5"
new_evidence = "**Repository evidence:** `main` through M11.5.5; branch `agent/m11-6-bitstream-hardware-smoke` for M11.6"
if old_evidence not in text:
    raise SystemExit("M11 repository-evidence pattern not found")
text = text.replace(old_evidence, new_evidence, 1)

start = text.index("### M11.6 — Generate first integrated bitstream and perform hardware smoke checks")
end = text.index("\n---\n\n## M12 — Validate FPGA against Python golden model", start)
replacement = """### M11.6 — Generate first integrated bitstream and perform hardware smoke checks

**Status:** In progress  
**Started:** 2026-08-25  
**Repository evidence:** branch `agent/m11-6-bitstream-hardware-smoke`

### Goal

Produce the first routed, timing-clean, loadable FPGA image containing the complete M11 core and prove through JTAG/VIO that its control and debug boundaries operate on the physical K26.

### Implementation approach

- Keep the complete M11.5 computational RTL and packaged `neuron_step_v1` HLS IP unchanged.
- Use the Zynq UltraScale+ PS `pl_clk0` and `pl_resetn0` so the first hardware shell does not require carrier-card PL pin assignments.
- Add a VIO-over-JTAG command/status boundary rather than introducing a new software/AXI host protocol during bring-up.
- Reuse the Python-golden M11.5.4 four-tick recurrent chain as an autonomous on-FPGA smoke workload.
- Have the on-FPGA sequencer preload packed M08 weight/config/route memories, issue architectural reset, execute four ticks, and compare committed state, spikes, recurrent counts/bank selection, and recurrent event data against the generated expectations.
- Generate a `.bit`, `.ltx`, routed `.dcp`, and `.xsa` from a source-controlled Vivado 2025.2 flow.
- Accept the bitstream only if routed setup and routed hold slack are both nonnegative, implementation DRC has no errors, and every tracked K26 resource class remains within capacity.
- Program and start the physical design from a batch Hardware-Manager Tcl flow using VIO `OUTPUT_VALUE`, `commit_hw_vio`, and `refresh_hw_vio`.

### Active closure gates

- [x] Define carrier-independent PS-clock + VIO physical shell.
- [x] Add autonomous packed-M08 + real-HLS + recurrent smoke sequencer.
- [x] Add source-controlled implementation/bitstream/reporting flow.
- [x] Add source-controlled VIO programming/smoke flow.
- [x] Add focused M11.6 source-regression guards.
- [ ] Independently run focused M11.6 and complete Python regressions.
- [ ] Run Vivado synthesis, placement, routing, DRC, and bitstream generation.
- [ ] Confirm nonnegative routed WNS and WHS.
- [ ] Confirm final implemented resource-capacity marker.
- [ ] Confirm `.bit`, `.ltx`, routed `.dcp`, and `.xsa` artifacts.
- [ ] Program the physical K26 through JTAG.
- [ ] Confirm VIO control/readback and autonomous four-tick `smoke_pass=1`.
- [ ] Record final hardware evidence and mark M11.6 and M11 complete.

### Detailed design record

See `Neuromorphic Digital Twin/docs/M11_6_BITSTREAM_HARDWARE_SMOKE.md` for the physical shell, smoke sequence, failure codes, routed implementation gate, programming flow, and M12 handoff.
"""
text = text[:start] + replacement + text[end:]
path.write_text(text, encoding="utf-8")
