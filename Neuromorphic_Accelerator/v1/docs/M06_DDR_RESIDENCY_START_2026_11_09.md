> **NEWEST M06 STATE 2026-11-09:** Initial 15-test source-only whole-block cache model has been extended in the **same existing M06 development stream** to actually run M02-exact sparse recurrent neural workloads with paged neuron voltage and last-update ticks; a separate synthetic AXI4 256→128 byte/burst/stall/partial-write backend, safe copy-on-write shadow epoch with M02 full-trace + exact canonical validation, and a 12-case matched-neural-work locality source traffic study. Total **67 new M06 host tests**; no genuine vendor SmartConnect XSim or real DDR/FPGA. [Authoritative current consolidated implementation, exact source behavior, matched model-only output and local commands](M06_SOURCE_INTEGRATION_2026_11_09.md). The earlier 15-test-only narrative below is historical. PR #80 remains draft/unmerged, owner genuine PS/DDR safety separate.

# M06 start — canonical neuron state residency, software-only exactness baseline

**2026-11-09 UTC — M06 IN PROGRESS, NO PHYSICAL DDR OPERATIONS.** User accepted scoped M05 closure after the original on-chip neural prototype review and conditionally authorized merge and M06 start. M05 PR #79 **successfully merged** into main at merge commit b908fd94d2ab817c2f118573b8fd374476707bf6. NEW M06 branch agent/neuromorphic-accelerator-v1-m06-ddr-residency was created from that exact main commit (not from stale M05 head). [Accepted M05 scope](M05_ACCEPTANCE_REVIEW_2026_11_09.md).

## Why this starts M06 without another protocol-warning rabbit hole

The experiment now studies what happens when the accepted exact event-driven on-chip neural state engine gains a bounded working set with canonical neuron state in DDR. The [accepted M01 residency study](M01_ARCHITECTURE_OPTIONS.md) provisionally chose **option B: configurable whole-block cache**. Individual-neuron A and fixed-pinned-prefix hybrid C remain later controls. M01 explicitly did not measure real AXI transaction latency, physical memory coherence, page control area or synaptic storage.

The first M06 implementation is a **functional software memory model**, not a PS/DDR hardware implementation:

- src/neuromorphic_accelerator_v1/m06_block_residency.py: logical neuron count, fixed record bytes, page width/offset, 32-bit DMA logical-offset bound, configurable on-chip budget, LRU block tags, clean/dirty state, canonical-block version, byte-exact record reads/writes and explicit flush.
- CanonicalImage is an IN-MEMORY Python bytearray; its EMULATED owner lease does NOT grant physical Linux/FPGA DDR ownership. It stages complete block transfers in bounded chunks; a simulated mid-transfer read/write failure fails closed without silently committing partial canonical bytes; a dirty write/eviction requires matching canonical generation or fails rather than overwrite stale state. A poisoned cache cannot continue without explicit separate recovery work. Diagnostic APIs retain dirty/uncommitted state locations after failure. No actual DMA, MMIO, JTAG, DDR allocation, Vivado/XSim vendor runtime or software deployment occurs.
- Original M01 default geometry retained as initial *example* (4096 logical neurons, 16 bytes per neuron, 16 neurons per block = 256-byte blocks, 2048-byte modeled cache budget = 8 resident blocks, maximum 256-byte modeled transfer). These are future experiment knobs, **NOT measured AXI capability** and NOT proof that 4096 neurons have executed on a real FPGA. Source rejects invalid widths/IDs/negative/boolean values, fractional blocks, cache under-capacity and source address-window overflow.
- Tests/test_m06_block_residency.py has **15 SYNTHETIC/host-only positive and negative methods**: M01 B geometry, invalid config/owner/32bit overflow, dirty eviction/hit/miss counts, true 2-slot LRU, idempotent flush/version, wrong page/record, injected mid-read fault, mid-write fault (canonical bytes unchanged), dirty-eviction interruption, competing canonical version/stale dirty flush, stale cache hit, revoke owner with uncommitted dirty state, overlapping transfer rejection, modeled chunk/byte counters and 12-tick M02 dense reference voltage-state preservation through repeated block churn. The last test replays an INDEPENDENT M02 neural trace through storage; it is NOT M06 computing LIF or a functional neuromorphic accelerator over DDR.
- New .github/workflows/neuromorphic_accelerator_m06_host_only.yml runs Python syntax, all M06 unit tests, inherited M01–M05 source regressions, and asserts no physical evidence claim. Prior M05 original XSim test outputs and original signed32 HLS remain unchanged.

## Precise boundary before physical PS/DDR or vendor-AXI claims

Work still REQUIRED (M06, not M05): correct canonical page IDs and owner lease in a real PS/PL allocation; address layout and physical OS reserved-memory ownership on actual chosen board; actual AXI DMA/SmartConnect downsize 256→128 with burst LEN/SIZE, WSTRB, ID, USER, response, stalls, reset and timeouts; **63 unwaived original BD warnings**, only one proved intentional OCM exclusion; real memory transfer traces; atomically committed state across interrupted transfers; synaptic working-set placement and sparse fanout/data movement; exact M02 numerical parity under page eviction and restore; tag/control/dirty capacity, concurrency and hardware timing. No assumption that a DDR_LOW mapping is allocated DDR memory. No physical board programming, DDR reads/writes, Linux MMIO, JTAG, bitstream, FSBL or AXI DMA execution is authorized at this source-only stage.

Do not automatically execute the older M05.12d.4 read-only simulator-source discovery. It is a useful M06 diagnostic tool once deciding whether to attempt vendor-generated memory SmartConnect simulation, but should not become an unbounded sequence of warning-parser submilestones. Choose a **specific executable functional AXI acceptance experiment** or record the actual vendor simulation/library blocker.

## Owner Ubuntu / VS Code commands (entirely software-only)

    cd ~/Git/Thesis
    git status --short
    git fetch origin
    git switch agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git pull --ff-only origin agent/neuromorphic-accelerator-v1-m06-ddr-residency
    git rev-parse HEAD
    git status --short

    cd Neuromorphic_Accelerator/v1
    python3 -m compileall -q src scripts tests
    python3 -m unittest discover -s tests -p 'test_m06*.py' -v
    python3 -m unittest discover -s tests -p 'test_m05*.py' -q
    python3 -m unittest discover -s tests -p 'test_m04*.py' -q
    python3 -m unittest discover -s tests -p 'test_m03*.py' -q
    python3 -m unittest discover -s tests -p 'test_m02*.py' -q
    python3 -m unittest discover -s tests -p 'test_m01*.py' -q

These tests use only Python standard library and CPU. They never call Vivado, touch original accepted Thes​is_Evidence artifacts, or read/write physical DDR. M06 acceptance remains open until actual end-to-end residency transfer and numerical correctness have genuine independent evidence.

## Engineering next actions (no new submilestone numbering)

Keep the first real M06 executable/observable target small: on-chip 1–2 resident blocks with 3–4 distinct logical blocks forcing a dirty eviction/restore; compare exact state bytes and M02 outputs against an independent oracle; measure counters. Then move from in-memory canonical image to a *separately authorized* simulated AXI transport backed by AMD vendor-generated IP, with concrete fail-closed cases. Only after real simulator evidence and an OS-reserved/owned DDR memory-provenance plan should physical board use be considered with separate user approval. Retain the M01 A/C controls for later comparisons, not hardcoded assumptions of B's superiority.
