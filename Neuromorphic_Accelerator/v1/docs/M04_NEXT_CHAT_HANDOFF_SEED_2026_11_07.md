# AUTHORITATIVE NEXT-CHAT HANDOFF SEED — Neuromorphic Accelerator v1, start M04

**Prepared:** 2026-11-07 (America/Denver; CI may display 2026-11-08 UTC). **Status:** M01, M02 and M03 user-accepted in their explicitly PC-only scopes. The user authorized closing M03 and merging PR #77 into main. **Next milestone: M04 — HLS evaluation-engine audit/reuse feasibility; NOT STARTED.** Before new development confirm PR #77 really merged and obtain its actual main merge commit; do not guess a final SHA.

**Sources of truth:** Neuromorphic_Accelerator/v1/roadmap.md, this handoff, accepted M02 revision-1 numerical contract, and M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md. The old Loihi_Digital_Twin/v3/docs/P08_B_NEXT_CHAT_HANDOFF_SEED_2026_11_05.md is HISTORICAL. Do not execute its retired JTAG/board procedures.

## 1. Research program, accepted work and claim boundaries

Repository: Xtimetraveler-Prime/Thesis. Independent first-generation research program: Neuromorphic_Accelerator/v1, NOT Loihi_Digital_Twin/v4. Questions: (1) performance cost to virtualize a larger network and amount recovered by sparse execution; (2) interaction of DDR-backed virtualization and event-driven sparsity with active-state locality, scalability, and FPGA efficiency. Original Loihi v1-v3 historical source, evidence and roadmap remain frozen; v3 did not establish a matched on-chip versus DDR speedup. Official MNIST TEST remains sealed.

**M01 COMPLETE, merged PR #75:** User-reported 20 native tests PASS and reversible configurable block/group-based neuron-state residency accepted as a provisional physical baseline. Retain individual-neuron and hybrid alternatives as comparisons. Keep neuron-state and synaptic-connectivity placement separate design axes. This is PC-only memory-traffic accounting, not physical DDR timing.

**M02 COMPLETE, merged PR #76:** User-reported 21 native tests PASS and accepts the initial v1 LIF numerical reference for the time being (revision 1). Signed W-bit integer stored membrane (16-bit default), rational decay truncating toward zero every tick, per-neuron bias/threshold/reset, sum all signed incoming currents before saturation, inclusive threshold, synaptic delay >=1 including recurrence/self loops. No refractory, separate decaying synaptic current, plasticity or asserted equivalence to Loihi silicon/YANA. Two independent numerical references:
- Neuromorphic_Accelerator/v1/src/neuromorphic_accelerator_v1/m02_dense_reference.py
- Neuromorphic_Accelerator/v1/src/neuromorphic_accelerator_v1/m02_event_reference.py
- Numerical contract: Neuromorphic_Accelerator/v1/docs/M02_PROVISIONAL_LIF_CONTRACT.md (historical filename; contents approved revision 1).

**M03 COMPLETE, user accepted for PC-only scope, PR #77 authorized to merge:** User reports **28 M03 + 21 M02 + 20 M01 native tests PASS** and requests milestone closure. At pre-closeout commit bdf2b85476222ecd4715e3f1fc95886987064ee1, GitHub Actions showed 69 tests PASS plus the two original modeled JSON reports, a default 36-pair seeded synthetic sweep, and no-overwrite/invalid-config gates; documentation closeout introduces later commits, so recheck head CI and merged main. User-local original JSON SHA256s were NOT furnished; do not invent them.

M03 built seeded role-isomorphic clustered/dispersed synthetic networks (identical signed weights, delays, external input and every canonical voltage/spike state after ID remapping); an exact-skip CPU evaluator for M02 revision-1 (previous voltage=0, bias=0, no incoming current → no update needed); and four analytical **PC models** timestep/onchip, event/onchip, timestep/DDR and event/DDR. State traffic and idealized adjacency reads counted separately, plus model cache/queue and source/trace hashes. Over-capacity onchip control is explicitly UNAVAILABLE. These are NOT 4 realized FPGA variants, real CSR/AXI traffic, measured runtime, hardware FIFO occupancy, trained accuracy, or energy data.

Core M03 evidence/notes:
- Neuromorphic_Accelerator/v1/docs/M03_WORKLOAD_AND_MEASUREMENT_CONTRACT.md
- Neuromorphic_Accelerator/v1/docs/M03_TESTS_EXPLAINED.md
- Neuromorphic_Accelerator/v1/docs/M03_PC_ONLY_VERIFICATION.md
- Neuromorphic_Accelerator/v1/src/neuromorphic_accelerator_v1/m03_traffic.py

Illustration only: same N128/K16/T16 synthetic problem yields 2048 dense versus 213 sparse safe-necessary neuron evaluations; event/DDR grouped model = clustered 69 versus dispersed 491 idealized transactions. NEVER claim those are measured speedups or KV260 DDR bursts. Separate user-local original report hashes were not provided, and no physical session ran.

## 2. NEXT TASK — M04 engineering scope, NOT a completed hardware engine

**Objective:** Decide based on actual source and tests whether to (A) extract existing v3 self-authored LIF arithmetic, (B) wrap the old HLS core with buffering/event adapters or (C) develop a fresh streaming per-neuron update engine for the v1 reference. Preserve exact accepted M02 voltage/spike behavior; do not inherit v3 fixed 27 logical cores, per-core per-timestep A53 calls or proprietary/third-party algorithms by default. Clearly separate logical neuron, virtual group/cache block, and physical compute pipeline.

Start **M04 on a NEW branch from accepted main**, suggested name agent/neuromorphic-accelerator-v1-m04-hls-audit, never work on the merged M03 branch.

**M04.1 — Read-only source/interface audit, first:**
- Loihi_Digital_Twin/v3/hls/core_v2/src/loihi_core_v2.cpp
- Loihi_Digital_Twin/v3/hls/core_v2/include/loihi_core_v2.hpp
- Loihi_Digital_Twin/v3/hls/core_v2/tb/test_loihi_core_v2.cpp
- Loihi_Digital_Twin/v3/hls/core_v2/tb/test_p04_two_core.cpp
- Loihi_Digital_Twin/v3/hls/core_v2/hls_config.cfg and hls/core_v2/README.md; inspect existing run_csim.sh, run_synth_cosim.sh but do not assume they are currently executable.
- Loihi_Digital_Twin/v3/rtl/p03_memory_fabric.v, p05_virtualized_controller.v and p08_paged_dispatch_controller.v as historical interface examples, not implementation requirements.
- Read original v3 P02/P03 architecture and acceptance docs and HLS logs before making resource, timing or physical validation claims. Do not run v3 hardware scripts.

**M04.2 — Numerical/architecture difference matrix:** Itemize v3 versus M02 revision-1 integer widths, rounding, decay/leak, synaptic current state, reset, spike timing, ordering, state layout, HLS ports, AXI/AXIS memory model, command/control overhead and per-core assumptions. Determine exactly which arithmetic primitives can be extracted without changing behavior. Draft minimal v1 neuron-update request/response interface including logical neuron ID/tick, old state, aggregate signed input, neuron parameters, next state and spike; specify ordering, invalid IDs, saturation and any queue/event grouping.

**M04.3 — Host-only functional candidates:** Build small standalone functional C/C++/HLS-compatible tests comparing extraction/wrapper/new cases against independently hand-calculated M02 vectors (negative leak, saturation, threshold equality, reset, bias-only spike, multiple signed events, recurrent positive delays). Do not automatically equate v3 behavior with the newly defined v1 mathematical contract. No blind conversion of Python to HDL: Vitis HLS primarily compiles synthesizable C/C++, not arbitrary Python.

**M04.4 — Synthesis feasibility (only if available):** Optionally run genuine **offline local** Vitis HLS C simulation/synthesis on a new isolated v1 kernel using installed tools. Record tool version, target part, synthesis command/log/report SHA, achieved *estimated* II, latency/resource and clock target, explicitly distinguishing them from real post-route timing and board execution. If tooling is unavailable, mark synthesis NOT RUN and recommend based on available source/host tests without fabricated Vivado measurements.

**M04 exit:** Evidence-backed **extract / wrap / new** decision with numerical risks, precise interface, resource uncertainties and tests. M04 user native verification + express acceptance required before merge. No M05 architecture freeze or physical operation is implied by starting M04.

## 3. MANDATORY DEVELOPMENT WORKFLOW FOR EVERY NEW MILESTONE — especially test explanations

**The user specifically wants the test-by-test explanation documentation continued. This section is a permanent milestone gate for M04–M09 and any separately testable submilestone.**

1. **Branch and plan:** Read latest roadmap, this authoritative handoff and accepted dependencies; create a fresh milestone-specific branch from accepted main. Keep all Loihi historical assets and original evidence unchanged. Work through sequential submilestones as feasible; stop for user approval of pivotal numerical, hardware or measurement decisions.
2. **Define interfaces and provenance:** Record neural contract, data layout, test input format, authoritative reference/trace hashes, risks, and separate known prior art (YANA, SENECA, HiAER-Spike, basic caches and LIF) from project's original engineering contributions. Never copy third-party code without checking attribution and license.
3. **Implement and test:** Run host-only or documented offline simulation/synthesis with *independent* expected results, negative tests and parameter-edge cases; keep full M02 voltage/spike parity wherever functional neural behavior is involved. Retain accepted M01/M02/M03 PC regressions. Never claim a simulation or HLS report is physical KV260 evidence.
4. **MANDATORY TEST EXPLANATION DOCUMENT:** For EACH milestone MXX, create Neuromorphic_Accelerator/v1/docs/MXX_TESTS_EXPLAINED.md **before requesting signoff**. Explain the **actual tests that ran**: exact test names or groups, purpose, setup and fixtures, how each is performed, expected/asserted outcomes, failure/negative cases, source and CI evidence, local user replication steps, number of tests and what the test does NOT prove. Explain any discovered failures/fixes and distinguish computer-only CI, operator native runs, hardware synthesis and physically measured data. If a milestone is document/audit-only, explain the source reviews and consistency checks actually done, rather than inventing functional testing. Link this from roadmap, the verification runbook, README and the next handoff seed. Existing examples: docs/M01_TESTS_EXPLAINED.md, docs/M02_TESTS_EXPLAINED.md, docs/M03_TESTS_EXPLAINED.md.
5. **MANDATORY USER VS CODE COMMANDS:** After every substantive code change, provide precise Git fetch/switch/pull and native test commands, plus accepted regression commands and optional unique evidence output. Original files belong under $HOME/Thesis_Evidence with timestamped, exclusive-create outputs; record git commit SHA and original SHA256. Never overwrite evidence or treat CI as user-local verification.
6. **Acceptance/merge:** Update roadmap deliverables/status and link explanatory documentation. Keep PR unmerged pending user's native test confirmation AND **explicit authorization**; then mark complete, verify current HEAD CI, merge into main, confirm new main SHA, and only start the next branch when asked.
7. **Future KV260 safety:** Programming PL, halting A53 or writing DDR requires new session-specific operator approval, PS/Linux ownership safeguards, immutable bitstream/ELF/source hashes and a physical power-cycle after every JTAG attempt. No old v3 JTAG script reuse. Official MNIST TEST remains sealed; no energy claims without calibrated sensor and boundary.

## 4. FIRST READ-ONLY COMMANDS FOR NEXT CHAT / USER

The next chat should check that user-authorized PR #77 really merged into main and that M03 is COMPLETE before branching. In an Ubuntu VS Code terminal (read-only to the physical board):

~~~bash
cd ~/Git/Thesis
git status --short
git fetch origin
git switch main
git pull --ff-only origin main
git rev-parse HEAD
git log -4 --oneline
sed -n '1,180p' Neuromorphic_Accelerator/v1/roadmap.md
sed -n '1,260p' Neuromorphic_Accelerator/v1/docs/M04_NEXT_CHAT_HANDOFF_SEED_2026_11_07.md

cd Neuromorphic_Accelerator/v1
python3 -m unittest discover -s tests -p 'test_m03*.py' -q
python3 -m unittest discover -s tests -p 'test_m02*.py' -q
python3 -m unittest discover -s tests -p 'test_m01*.py' -q
~~~

Do not run archived Loihi physical scripts. Once M04 branch has new source, provide its own exact branch, build and simulation commands separately.

## 5. DIRECT REQUEST TO NEXT CHAT INSTANCE

Begin M04.1 on a **new development branch from merged main**, by inspecting the v3 HLS source/interface and testbench, documenting differences against accepted M02 LIF reference and how an event-driven streaming update boundary could be verified. Continue into numerical difference table and host-only functional proof as far as possible without needing operator input or new design decisions. Create M04 tests, M04_TESTS_EXPLAINED.md, operator PC verification runbook, and an updated roadmap, then leave a draft PR unmerged pending user verification/approval. **Do not** re-open M01–M03, change LIF semantics silently, execute real FPGA/JTAG, or claim unmeasured speedups.


## Post-handoff M04 working-branch status (not part of original 2026-11-07 seed)

M04 branch `agent/neuromorphic-accelerator-v1-m04-hls-audit` was created from accepted main merge SHA `2ceac0372ed6ec11fb09c764277e4532b4807e46`. **M04.1/M04.2 review and M04.3 bounded host C++ candidate are in development, not accepted/merged; M04.4 Vitis synthesis was NOT RUN.** Live working-branch references: [audit/difference matrix](M04_HLS_ENGINE_AUDIT.md), [M04_TESTS_EXPLAINED.md](M04_TESTS_EXPLAINED.md), [native PC-only verification](M04_PC_ONLY_VERIFICATION.md), [M04 test source](../tests/test_m04_eval.py), and [updated roadmap](../roadmap.md). Use the new M04 runbook rather than the seed's old `main` branch commands when verifying this development work. The seed's original historical status above describes the starting point, not acceptance of M04.
