# P06-B1.2 — Deterministic synapse-aware destination partitioner

**Status:** source + synthetic tests COMMITTED as a host-only **native acceptance candidate**; no native PASS/physical KV260 result claimed here.  
**Base:** post-P08-A `main` `40b3d7c7092ea674e7d1d21647de2cd30e6b93b3`.  
**Branch:** `agent/v3-p06-b1-scalable-packing`, draft PR #46, **unmerged**.  
**Previous subgate:** User reported that **B1.1 passed** before authorizing B1.2; this is a user-attested result, not a fabricated GitHub CI run.

## Scope and immutable reference

B1.2 is an opt-in algorithm in
`src/loihi_twin_v2/p06_b12_partition.py`, which accepts exactly the
existing `NetworkSpec` and emits a `CompiledDeployment` with an explicit
**different** `compiler_version` (`p06-b1.2-destination-synapse-fit-v1`).
The accepted original P06-A `compile_network`, P03 exporter, P02 DDR serializer,
P05 resident contexts, P06 integer recurrence/input encoder, P07 accuracy and
P08-A physical results remain **untouched**.

The B1.1 `audit_compiled_candidate` is a required post-construction gate,
so every B1.2 output is packed with the accepted genuine P03 exporter and
each logical core obtains its full 524,288-byte initial P02 DDR record,
per-core P03/DDR SHA256, bank accounting and exact capacity checks. This is
a **source-derived initial memory image**, **not** a claim of a working scaled
bare-metal streaming firmware or live physical KV260 deployment.

## Algorithm and explicit non-claims

1. Validate source `NetworkSpec` (preserving its uniqueness, target and
   zero-delay restrictions); sort non-readout populations alphabetically,
   and place the named readout population **last** and separately.
2. For each destination neuron in ascending original neuron-index order,
   tentatively add it to the current logical destination core; derive
   actual input-source groups from `InputProjectionSpec` and
   `ProjectionSpec`, retaining their independent `("input"/"neuron",
   population, source_index)` keys.
3. Recompute **exact** offset-normalized source-to-compartment synapse
   patterns under the accepted P06 representation. Reuse a stored template
   only when the full ordered (relative target offset, signed weight)
   pattern is identical. Recalculate stored entries, template headers,
   destination axon bindings, and the project-defined logical 128 KiB
   cost, **not** just connection count or compartment count.
4. If a tentative neuron breaks any compartment, axon, stored synapse
   word/byte or conservative incoming event-bank limit, start a new
   logical core and retry. If even one neuron cannot fit an empty core,
   fail closed with `MappingError.code="b12_unplaceable_neuron"`. If
   logical IDs would exceed the admitted budget, fail with
   `b12_core_count`. **No edge or neuron is silently omitted.**
5. After all destinations are placed, assign deterministic axon IDs,
   synapse-template IDs, placements and ingress routes; build all
   source-to-destination output routes. Enforce per-core outgoing
   route/packet fanout `<=4096` (or a stricter explicit policy).
   Oversubscribed source routing fails with `b12_outgoing_route_capacity`
   instead of silently spilling the packet bank.
6. Encode actual `LogicalCoreConfig` objects and validate the original
   physical P03/P02/P08 boundary using B1.1's `audit_compiled_candidate`.
   Reject out-of-range signed24 weights, unrepresentable configuration
   and bank overflows without changing accepted arithmetic.
7. Produce a **distinctly versioned** B1.2 manifest and complete
   `B12Result.to_json` serialization. `B12Result.from_json`
   verifies outer SHA, reloads the original deployment schema through its
   validated `Deployment` reader, repacks all cores and requires
   the whole regenerated manifest to match. We deliberately do not lie
   to `CompiledDeployment.from_json` by impersonating P06-A's
   `p06-deterministic-first-fit-v1` compiler version.

This is a **deterministic greedy algorithm**, not a claim of globally
minimum core count or general backtracking search. Source route capacity
is checked at final placement; if it fails, the mapper **rejects** the
mapping rather than pretending it can automatically repair an arbitrary
fanout topology. Per-tick conservative capacity sums all potentially
simultaneous external and neural events on each destination core and all
outgoing static routes on each source core. No scheduling-dependent buffer
recovery is claimed.

**B1.2 accepted image bounds:** up to 126 logical IDs 0–125 in this
conservative P05-compatible planning profile, each 512 KiB backing image,
3 physical resident slots and 1 HLS engine, with independent core limits
1,024 compartments, 4,096 input axons, 32,768 stored synapse words,
131,072 project-accounted synapse bytes, 4,096 routes,
4,096 CURRENT events and 4,096 packets/core/tick. The P05 diagnostic
ABI **still supports only one valid external axon per core** and cannot
be used for this scaled model without the separately designed B1.3
multi-core input/packet streaming ABI.

## Synthetic tests and independent evidence

`tests/test_p06_b12_partition.py` intentionally does **not** load
a model checkpoint, MNIST train/validation images, or sealed TEST data.

- Two independently ordered but semantically identical signed-weight
  networks must create identical placement/image SHA manifests.
- A manually worked 2-timestep LIF example and the original accepted
  compiler's same-placement `LogicalChip` execution must agree on
  emitted spikes, signed inputs, NEXT-epoch delivery, and states under
  both valid core-service orders.
- An independent edge-reconstructor follows **actual per-core axon
  bindings/templates and route tables** back to every distinct
  (source kind, original source, original destination) integer weight;
  its result must equal the direct original source-network edge ledger.
- A repeated template pattern must occupy one stored template but
  retain separate input axon IDs.
- A smaller-than-physical policy forces a **3+3 hidden / 1 readout**
  split solely because of synapse pressure. Impossible single-neuron,
  insufficient core-ID budget, output route-fanout and ingress/event
  bounds must reject explicitly. Exact P03/DDR export is mandatory.
- A normal native structural test synthesizes a distinct-weight dense
  **784→40→10** graph, for which **39+1 hidden / 10 readout** is the
  expected resource-constrained partition.
- A separate **26-tick all-255 synthetic fanout** numerical regression
  drives all 784 input channels for exactly 25 ticks, then a drain tick,
  through both hidden partitions. Its independent expected spike counts,
  NEXT arrival epoch and state traces must match under normal and reverse
  legal service/packet ordering. This validates Python architecture
  behavior, **not** physical scaled ingress firmware.
- An **opt-in RAM/CPU-intensive** full synthetic **784→1000→10**
  test checks the 794,000-entry network's *structural* core partition,
  occupancy, route/event budget, full initial 512 KiB per-core records
  and exact source-preserving counts. Its expected `26 hidden + 1
  readout = 27 cores` is a **test hypothesis until native execution
  verifies it**. These integer weights are **synthetic**, not a trained
  checkpoint, and NO accuracy or physical scheduling result is implied.

## Native B1.2 verification (PC / VS Code Linux; no board)

```bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch agent/v3-p06-b1-scalable-packing
git pull --ff-only origin agent/v3-p06-b1-scalable-packing

source ~/Git/Thesis/.venv-p08/bin/activate
cd ~/Git/Thesis/Loihi_Digital_Twin/v3
set -o pipefail

PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_b12_partition.py tests/test_p06_b1_contract.py
PYTHONPATH="$PWD/src" python -m pytest -q -rs \
  tests/test_p06_lif_compiler_probe.py tests/test_p06_lif_input_probe.py
PYTHONPATH="$PWD/src" python -m compileall -q \
  src/loihi_twin_v2/p06_b12_partition.py \
  tests/test_p06_b12_partition.py
PYTHONPATH="$PWD/src" python scripts/p06_b12_synthetic_probe.py --hidden 40

# Separate optional high-memory/high-CPU 794,000-edge source/image probe:
PYTHONPATH="$PWD/src" python scripts/p06_b12_synthetic_probe.py --hidden 1000
# Separate optional high-memory/high-CPU full 794,000-edge structural test:
P06_B12_FULL_SYNTHETIC=1 PYTHONPATH="$PWD/src" \
  python -m pytest -q -rs tests/test_p06_b12_partition.py \
  -k full_784_1000_10_synthetic_structural_feasibility_only
```

The standard commands run the B1.2/B1.1 regressions, Track A structural
regressions, syntax checks and the smaller structural probe. The opt-in full
network probe/test is **also a B1.2 target acceptance gate**, but may be long
and memory-intensive and must be reported separately; it is safe to run
off-board because it uses **synthetic integer weights only**. Avoid running
multiple copies concurrently on a low-memory host.

**Not performed:** JTAG, bare-metal reboots, destructive DDR captures,
new Vitis firmware, Loihi measurements, official MNIST TEST evaluation,
scaled physical acceptance or Track A retraining. No new board run should
be attempted in B1.2.

## Next acceptance gates

- **B1.3:** a new explicitly versioned multi-logical-core ingress
  streaming ABI, mapping 784 external input indices to replicated
  destination core/axon events, NEXT timing, packet and bank pressure,
  backpressure/rejection policy and physical firmware compatibility.
- **B1.4:** **independent full-length monolithic integer LIF oracle**
  and separate partitioned 26-tick multi-core reference with exact
  first-divergence tests. B1.2's tiny manual two-tick oracle and
  independent edge-decoder are not substitutes.
- **B1.5:** service-order/paging invariance plus separately estimated
  full-page-in and mutable-page-out bytes, distinguished from the
  accepted P05 *measured* physical page sizes and from actual elapsed
  latency.
- **B1.6:** complete accepted SHA/occupancy/source ledger, B1
  feasibility and B2 training entry recommendation.

Do not merge draft PR #46 until explicit user permission for that PR.
