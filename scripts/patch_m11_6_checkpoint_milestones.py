from pathlib import Path

path = Path('MILESTONES.md')
text = path.read_text(encoding='utf-8')
old = '''### Active closure gates

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
'''
new = '''### Active closure gates

- [x] Define carrier-independent PS-clock + VIO physical shell.
- [x] Add autonomous packed-M08 + real-HLS + recurrent smoke sequencer.
- [x] Add source-controlled implementation/bitstream/reporting flow.
- [x] Add source-controlled VIO programming/smoke flow.
- [x] Add focused M11.6 source-regression guards.
- [x] Independently run the focused M11.6 source guard.
- [ ] Independently rerun the complete Python regression suite after the final M11.6 shell changes.
- [x] Run Vivado synthesis, placement, routing, DRC, and bitstream generation.
- [x] Confirm nonnegative routed WNS and WHS.
- [x] Confirm final implemented resource-capacity marker.
- [x] Confirm `.bit`, `.ltx`, routed `.dcp`, and `.xsa` artifacts.
- [ ] Program the physical K26 through JTAG.
- [ ] Confirm VIO control/readback and autonomous four-tick `smoke_pass=1`.
- [ ] Record final hardware evidence and mark M11.6 and M11 complete.

### Implementation and bitstream checkpoint — 2026-08-25

The source-controlled Vivado 2025.2 flow has now crossed the complete pre-board physical implementation boundary for `xck26-sfvc784-2LV-c`.

The K26 PS board preset and PL boundary validated successfully after correcting three integration assumptions discovered by real Vivado execution: ZynqMP/K26 dedicated DDR/MIO do not require PS7-style top-level `DDR`/`FIXED_IO` ports; the realizable PS `pl_clk0` frequency is propagated rather than forcing an exact `100000000`-Hz Module-Reference property; and `proc_sys_reset` now provides synchronized active-low smoke reset plus synchronized active-high HLS `ap_rst`.

Placement and routing completed successfully with zero final failed, unrouted, or partially routed nets. Vivado's router repaired the temporary intermediate hold violation and the explicit final routed timing gate passed:

```text
M11.6 routed timing check passed: WNS=1.202 ns, WHS=0.016 ns
```

The routed implementation DRC completed with zero errors and Vivado successfully generated the physical artifacts:

```text
neuromorphic_twin_m11_6.bit
neuromorphic_twin_m11_6.ltx
neuromorphic_twin_m11_6_routed.dcp
neuromorphic_twin_m11_6.xsa
```

The implementation resource checker was hardened after Vivado 2025.2 omitted a literal `Block RAM Tile` row from the implemented utilization table. The accepted split-report checker uses implementation utilization plus dedicated RAM utilization and passed with:

```text
M11.6 implementation resource check passed: CLB_LUT=2657/117120, CLB_REG=3095/234240, BRAM_TILE<=13/144 (RAMB36=9, RAMB18=7), DSP=2/1248, URAM=0/64
```

This is a checkpoint, not M11.6 completion. The remaining decisive evidence is physical K26 programming plus VIO/JTAG execution of the autonomous four-tick recurrent smoke workload with `smoke_pass=1`. M11.6 and M11 therefore remain **In progress**.

### Detailed design record
'''
if old not in text:
    raise SystemExit('M11.6 active closure-gate block not found')
path.write_text(text.replace(old, new, 1), encoding='utf-8')
