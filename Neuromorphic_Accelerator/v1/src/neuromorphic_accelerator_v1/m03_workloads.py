"""M03 deterministic *isomorphic* clustered/dispersed synthetic LIF workloads.

The only difference between locality variants is a bijective relabeling of
the same active logical neuron roles. All synapses, external currents, delays,
time order, and weights are identical in role space. This is a synthetic
controlled experiment, NOT a real trained SNN/dataset.

No sealed MNIST TEST, device code, random global state or external packages.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
import random

from .m02_types import InputCurrent, Network, Neuron, Synapse, ReferenceTrace


def sha256_json(record: object) -> str:
    return hashlib.sha256(json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")).hexdigest()


@dataclass(frozen=True)
class WorkloadSpec:
    neuron_count: int = 128
    active_roles: int = 16
    fanout_per_active: int = 4
    external_events_per_tick: int = 6
    ticks: int = 16
    seed: int = 20261107
    state_bits: int = 16
    locality: str = "clustered"

    def validate(self) -> None:
        for name in ("neuron_count", "active_roles", "ticks", "state_bits"):
            value = getattr(self, name)
            if type(value) is not int or value <= 0:
                raise ValueError(f"{name} must be a positive integer")
        for name in ("fanout_per_active", "external_events_per_tick", "seed"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a nonnegative integer")
        if self.active_roles > self.neuron_count:
            raise ValueError("active_roles cannot exceed neuron_count")
        if self.fanout_per_active > self.active_roles:
            raise ValueError("fanout_per_active cannot exceed active_roles")
        if self.locality not in ("clustered", "dispersed"):
            raise ValueError("locality must be clustered or dispersed")
        if not 8 <= self.state_bits <= 32:
            raise ValueError("state_bits must be 8..32 for M03 fixtures")
        # Constructed stimulus/weights must fit in >=8-bit signed range.


@dataclass(frozen=True)
class Workload:
    spec: WorkloadSpec
    network: Network
    external_currents: tuple[InputCurrent, ...]
    role_to_neuron: tuple[int, ...]
    canonical_role_sha256: str
    relabeled_input_sha256: str


def build_workload(spec: WorkloadSpec) -> Workload:
    """Produce deterministically role-isomorphic, fully validated M02 inputs."""
    spec.validate()
    k, n = spec.active_roles, spec.neuron_count
    mapped = (tuple(range(k)) if spec.locality == "clustered"
              else tuple(role * n // k for role in range(k)))
    if len(set(mapped)) != k:
        raise AssertionError("dispersed role mapping not injective")

    rng = random.Random(spec.seed)
    # The roles specify the network before any physical-neuron-ID mapping.
    edges: list[tuple[int, int, int, int]] = []
    for pre_role in range(k):
        # The same number of *distinct* post roles per presynaptic role.
        targets = rng.sample(range(k), spec.fanout_per_active)
        for post_role in targets:
            edges.append((pre_role, post_role, rng.randint(-3, 5),
                          rng.randint(1, 3)))

    currents: list[tuple[int, int, int]] = []
    for tick in range(spec.ticks):
        for _ in range(spec.external_events_per_tick):
            currents.append((tick, rng.randrange(k), rng.randint(3, 10)))

    # Quiet neurons have no bias, initial voltage, outgoing edges or incoming
    # edges and therefore remain quiescent. Active roles use a simple positive
    # threshold; weights and currents are integers under the accepted M02 rule.
    cells = tuple(Neuron(initial_v=0, bias=0, threshold=7, reset_v=0)
                  for _ in range(n))
    synapses = tuple(Synapse(mapped[a], mapped[b], w, delay)
                     for a, b, w, delay in edges)
    inputs = tuple(InputCurrent(t, mapped[role], current)
                   for t, role, current in currents)
    net = Network(cells, synapses, decay_num=1, decay_den=2,
                  state_bits=spec.state_bits)

    canonical = {
        "schema": "m03-canonical-synthetic-role-workload-v1",
        "n": n, "active_roles": k, "fanout": spec.fanout_per_active,
        "events_per_tick": spec.external_events_per_tick,
        "ticks": spec.ticks, "seed": spec.seed, "state_bits": spec.state_bits,
        "neuron_contract": "all initial 0 bias 0 threshold 7 reset 0; leak 1/2",
        "role_edges": edges, "role_external_currents": currents,
    }
    packed = {
        "network": asdict(net),
        "external_currents": [asdict(evt) for evt in inputs],
        "ticks": spec.ticks,
    }
    return Workload(
        spec=spec,
        network=net,
        external_currents=inputs,
        role_to_neuron=mapped,
        canonical_role_sha256=sha256_json(canonical),
        relabeled_input_sha256=sha256_json(packed),
    )


def canonicalize_trace(workload: Workload, trace: ReferenceTrace) -> dict:
    """Compare neural dynamics across a pure neuron-ID relabeling.

    Only the active roles are mapped back. Verify all remaining quiet cells
    have voltage 0 and never emit a spike. Never compare raw ID-ordered voltage
    rows across differently permuted networks.
    """
    if len(trace.voltage_rows) != workload.spec.ticks:
        raise ValueError("trace length differs from requested ticks")
    active = workload.role_to_neuron
    inverse = {neuron: role for role, neuron in enumerate(active)}
    spike_role_rows = []
    voltage_role_rows = []
    for t, (voltage, spikes) in enumerate(zip(
        trace.voltage_rows, trace.spike_rows
    )):
        if len(voltage) != workload.spec.neuron_count:
            raise ValueError("voltage row wrong network width")
        if any(voltage[i] != 0 for i in range(workload.spec.neuron_count)
               if i not in inverse):
            raise AssertionError(f"quiet neuron unexpectedly active at tick {t}")
        if any(i not in inverse for i in spikes):
            raise AssertionError(f"quiet neuron unexpectedly spiked at tick {t}")
        voltage_role_rows.append([voltage[active[r]]
                                  for r in range(workload.spec.active_roles)])
        spike_role_rows.append(sorted(inverse[i] for i in spikes))
    result = {
        "voltage_role_rows": voltage_role_rows,
        "spike_role_rows": spike_role_rows,
    }
    result["canonical_trace_sha256"] = sha256_json(result)
    return result
