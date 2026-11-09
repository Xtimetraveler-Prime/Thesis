"""M06 role-isomorphic neural workload vs SOFTWARE AXI-backed state paging.

M01's locality comparison now passes through M02-exact sparse neural
inference, M06 block residency, and an explicit *modeled* AXI 256->128
transport. Same logical spike/event roles, not identical neuron-ID networks.
These are byte/transaction accounting predictions, NOT FPGA time, energy,
DMA correctness, or any evidence of real 2025.2 SmartConnect behavior.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json

from .m02_dense_reference import evaluate_dense
from .m02_types import InputCurrent, Network, Neuron
from .m06_axi_transport import AXIModelImage
from .m06_block_residency import BlockCache, Geometry
from .m06_paged_replay import replay_with_paging

SOURCE_SCOPE = "M06_ROLE_ISOMORPHIC_SOURCE_ONLY_B_RESIDENCY_STUDY_V1"
TICK_COUNT = 8
LOGICAL_NEURONS = 64
ACTIVE_ROLES = 8
STATE_BYTES = 16


def matched_network(locality: str) -> tuple[Network, tuple[InputCurrent, ...], tuple[int, ...]]:
    if locality not in ("clustered", "dispersed"):
        raise ValueError("expected clustered or dispersed predeclared role map")
    ids = tuple(range(ACTIVE_ROLES) if locality == "clustered"
                else (i*LOGICAL_NEURONS//ACTIVE_ROLES for i in range(ACTIVE_ROLES)))
    network = Network(
        neurons=tuple(Neuron(initial_v=0, threshold=5, reset_v=0)
                      for _ in range(LOGICAL_NEURONS)),
        synapses=(), state_bits=16, decay_num=1, decay_den=1)
    # The same eight roles spike once on every tick, under both ID maps.
    currents = tuple(InputCurrent(tick=t, neuron=ids[role], current=7)
                     for t in range(TICK_COUNT) for role in range(ACTIVE_ROLES))
    return network, currents, ids


def source_only_sweep() -> dict:
    rows = []
    reference_role_pattern = None
    for group_neurons in (4, 8, 16):
        for budget in (256, 512):
            for locality in ("clustered", "dispersed"):
                net, inputs, ids = matched_network(locality)
                group_bytes = group_neurons*STATE_BYTES
                config = Geometry(
                    logical_neurons=LOGICAL_NEURONS,
                    bytes_per_neuron=STATE_BYTES,
                    neurons_per_block=group_neurons,
                    resident_budget_bytes=budget,
                    max_model_transfer_bytes=group_bytes,
                )
                image = AXIModelImage(
                    config, emulated_owner="SYNTHETIC_ONLY",
                    initial=bytes(config.image_bytes),
                    logical_bus_base=0, ready_delay_every=3)
                cache = BlockCache(image, owner="SYNTHETIC_ONLY")
                result = replay_with_paging(net, inputs, ticks=TICK_COUNT,
                                            cache=cache)
                golden = evaluate_dense(net, inputs, ticks=TICK_COUNT)
                if result.trace != golden:
                    raise AssertionError("M06 page-churn spike/voltage differs from M02 oracle")
                role_for_id = {logical_id: role for role, logical_id in enumerate(ids)}
                role_pattern = tuple(tuple(role_for_id[x] for x in tick)
                                     for tick in result.trace.spike_rows)
                if reference_role_pattern is None:
                    reference_role_pattern = role_pattern
                if reference_role_pattern != role_pattern:
                    raise AssertionError("role-isomorphic neural work changed")
                if cache.poisoned or image.uncertain_pages:
                    raise AssertionError("unexpected software AXI canonical state quarantine")
                # Independent final-state check includes per-neuron
                # persisted last-update watermarks (t+1), not only voltage.
                # Each predeclared role is evaluated on every one of 8 ticks;
                # all other silent neurons retain the initial zero stamp.
                active_ids = set(ids)
                expected_final = b"".join(
                    int(v).to_bytes(2, "little", signed=True)
                    + ((TICK_COUNT if i in active_ids else 0).to_bytes(4, "little"))
                    + bytes(STATE_BYTES-6)
                    for i, v in enumerate(result.trace.voltage_rows[-1]))
                if image.snapshot(owner="SYNTHETIC_ONLY") != expected_final:
                    raise AssertionError("paged final canonical image differs from oracle")
                counters = asdict(cache.counters)
                expected_total = counters["accesses"]
                if counters["hits"] + counters["misses"] != expected_total:
                    raise AssertionError("cache hit/miss conservation")
                if (counters["read_transactions"]
                        != sum(b["direction"] == "READ" for b in image.burst_log)):
                    raise AssertionError("read burst count does not match AXI source trace")
                if (counters["write_transactions"]
                        != sum(b["direction"] == "WRITE" for b in image.burst_log)):
                    raise AssertionError("write burst count does not match AXI source trace")
                rows.append({
                    "group_neurons": group_neurons,
                    "resident_budget_bytes": budget,
                    "locality": locality,
                    "active_roles": ACTIVE_ROLES,
                    "logical_neurons": LOGICAL_NEURONS,
                    "ticks": TICK_COUNT,
                    "neural_spikes": sum(map(len, result.trace.spike_rows)),
                    "neuron_evaluations": result.evaluations,
                    "source_only_model_transfer_bytes": (counters["read_bytes"]
                                                         + counters["write_bytes"]),
                    "source_only_model_transactions": (
                        counters["read_transactions"] + counters["write_transactions"]),
                    "axi_channel_ready_stalls": sum(image.stalls.values()),
                    "axi_downstream_128bit_handshakes": (
                        image.handshakes.get("D_R", 0) +
                        image.handshakes.get("D_W", 0)),
                    "cache_counters": counters,
                    "independent_m02_neural_oracle": "PASS_SOURCE_ONLY",
                    "vendor_smartconnect": "NOT_SIMULATED",
                    "physical_ddr": "NOT_ACCESSED",
                })
    return {
        "scope": SOURCE_SCOPE,
        "model_only": True,
        "neural_role_signature_sha256": hashlib.sha256(
            json.dumps(reference_role_pattern, separators=(",", ":")).encode()).hexdigest(),
        "matched_workload_caveat": "role-isomorphic signed events, different neuron-ID placement",
        "independent_golden": "M02 dense scalar Python, not vendor RTL",
        "schema_rows": len(rows),
        "rows": rows,
        "calibrated_physical_latency": None,
        "calibrated_bandwidth": None,
        "physical_board": "NOT_AUTHORIZED",
    }
