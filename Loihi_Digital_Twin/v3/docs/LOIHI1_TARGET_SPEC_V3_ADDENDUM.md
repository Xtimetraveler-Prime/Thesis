# Loihi-1 Target Specification — FPGA-v3 Board-Local Addendum

**Status:** P03.1 verification candidate  
**Date:** 2026-10-06

## 1. Scope

This addendum supplements `docs/LOIHI1_TARGET_SPEC.md` for FPGA-v3.

It does not replace or weaken the inherited logical architecture contract.

Its purpose is to keep three categories separate:

1. source-backed Loihi-1 behavior;
2. inherited project-level architectural choices;
3. FPGA-v3 board-local implementation choices.

## 2. Logical rules unchanged in v3

FPGA-v3 preserves these existing normative logical rules:

- logical core ID is architectural identity;
- resident context slot is not logical identity;
- physical engine ID is not logical identity;
- spike communication is packetized by logical destination;
- destination axon IDs expand to local synaptic effects;
- a spike generated while evaluating timestep `t` is delivered to the
  destination's subsequent architectural update;
- CURRENT and NEXT event traffic remain separated;
- global timestep advancement requires all required logical work and packet
  delivery to quiesce;
- service order and virtualization policy must not alter normalized results;
- algorithmic timestep is distinct from physical FPGA clock cycles.

No v3 PS/DDR choice changes these semantics.

## 3. FPGA-v3 implementation choices

The following are PROJECT CHOICES, not claims about Loihi-1 physical
microarchitecture:

- Cortex-A53 software owns scheduling, page replacement, cross-page routing,
  barrier control, and run control;
- K26 DDR stores non-resident logical-core context images;
- three full logical contexts are resident in K26 URAM;
- one physical HLS engine is the initial baseline;
- resident contexts are time-multiplexed through that engine;
- PL bulk paging uses a non-coherent PS DDR high-performance AXI path;
- the PS/PL control plane is memory-mapped;
- deterministic round-robin replacement is the initial page policy;
- board-local control is synchronous to PS/PL clocks rather than physically
  asynchronous;
- multi-engine execution is deferred pending measurement.

## 4. Board-local autonomy rule

For an accepted P03 run, after RUN/START is accepted:

- no external PC action may be required to select a logical core;
- no external PC action may be required to page a context;
- no external PC action may be required to route a packet;
- no external PC action may be required to decide a barrier;
- no external PC action may be required to advance a timestep.

The external PC may observe or retrieve results without affecting forward
progress.

This is a v3 project acceptance rule, not a Loihi hardware claim.

## 5. DDR backing is implementation storage

The fixed 512 KiB logical-core DDR record is an FPGA-v3 ABI.

It is **not** claimed to match native Loihi SRAM organization, packet encoding,
or proprietary NxSDK/NxTF binary layout.

Logical equivalence is evaluated at normalized state/spike/packet/barrier
boundaries.

## 6. Runtime metadata versus architectural state

PS runtime metadata such as:

- residency tables;
- dirty bits;
- event counts;
- victim cursor;
- page counters;
- timer counters;
- fault codes;

is FPGA-v3 control state.

It is not additional modeled Loihi neuron state.

Changes to that metadata are permitted as long as normalized logical behavior
is unchanged.

## 7. Timing interpretation

FPGA-v3 reports separately:

- algorithmic timestep;
- PL page cycles;
- PL dispatch cycles;
- PS control/routing/barrier timer ticks;
- complete board-local inference latency.

None of these quantities is claimed to equal Loihi's proprietary physical
router/core timing unless a separate source-backed comparison establishes
equivalent boundaries.

## 8. Error behavior

Fail-closed PS/runtime behavior is an FPGA-v3 verification feature.

Sticky software/hardware fault codes are not presented as native Loihi error
semantics.

## 9. Explicit non-claims retained

FPGA-v3 still does not claim:

- transistor-level Loihi equivalence;
- physically asynchronous-circuit equivalence;
- exact NoC timing;
- exact native packet bitfields;
- exact native synaptic SRAM packing;
- proprietary NxSDK/NxTF microcode or checkpoint equivalence;
- exact unpublished NxTF network/checkpoint identity;
- direct Loihi-vs-KV260 latency or energy equivalence from unlike measurement
  boundaries.

## 10. Revision rule

A board-local implementation optimization may change PS/PL/DDR partition details
only if:

- the inherited logical target specification remains satisfied;
- the P03 autonomous-runtime contract remains satisfied or is explicitly
  versioned;
- normalized regression results remain unchanged;
- any new claim is classified as source-backed fact, project reconstruction,
  project measurement, contextual comparison, or unsupported/non-comparable.
