"""M08.5 source-only provenance and scientific-matching gate.

An accepted historical hardware receipt is *not* a matched timing observation.
This module never opens original ~/Thesis_Evidence, touches the KV260, issues
JTAG/AXI transactions or certifies DDR ownership. In particular, a populated
row describing the M32Q tick-service FIFO is not proof of physically sparse
neuron-update skipping.
"""
from __future__ import annotations

from copy import deepcopy
from hashlib import sha256
import json
import re

SCHEMA = "m08-5-matched-experiments-source-contract-v1"
REFERENCE = "M06_G3_3_M02_DENSE_EVENT_M03_SPARSE_SIGNED16"
CELLS = (
    "timestep/onchip",
    "event/onchip",
    "timestep/jtag_host_paged",
    "event/jtag_host_paged",
    "timestep/ps_pl_ddr",
    "event/ps_pl_ddr",
)
SHA = re.compile(r"[0-9a-f]{64}\Z")
DDR_BLOCKERS = (
    "exact_connected_ps_pl_master_or_verified_ps_pager",
    "bound_kernel_device_and_owner",
    "device_dma_mask_and_address_translation",
    "kernel_owned_buffer_allocation_mapping_and_lifetime",
    "cache_coherency_or_explicit_cpu_device_sync",
    "quiesce_reset_fault_containment_and_recovery",
    "owner_original_source_bitstream_and_hardware_evidence",
)
BIT_D2C = "244d304a44af6b1eda1943c18e7b5a3bed302cae2308c28a11944ede7eadf932"
BIT_D2E = "2c443c3d80e86e5e9488b457110a45b0db96881016e9f87a5c801a72ec7527dc"
BIT_M084 = "6a4a71f255adcc79a4131401a3f75eb64f253d3431f5ad1babc0da48479f6494"


class ContractError(ValueError):
    """A claim or comparison lacks required exact provenance."""


def _positive_int(x: object) -> bool:
    return type(x) is int and x > 0


def _digest(text: object) -> bool:
    return isinstance(text, str) and SHA.fullmatch(text) is not None


def witness_from_original(*, neuron_pages: tuple[tuple[int, ...], ...],
                          edge_page: tuple[int, ...],
                          event_records: tuple[tuple[int, int, int], ...],
                          golden_words: tuple[int, ...],
                          reference_source_sha256: dict[str, str]) -> dict:
    """Hash the *existing* independently derived input pages and oracle.

    The caller obtains these from scripts/m08_paged_m06_lif_fixture.py,
    which in turn requires the original M02 dense/event + M03 sparse G3.3
    numerical agreement. Golden words are comparison-only, not input pages.
    """
    import struct
    if (len(neuron_pages) != 6 or any(len(page) != 64 for page in neuron_pages)
            or len(edge_page) != 64 or len(event_records) != 17
            or len(golden_words) != 512):
        raise ContractError("original 6-page / 17-event / 512-word geometry changed")
    if any(type(w) is not int or not 0 <= w < (1 << 32)
           for page in (*neuron_pages, edge_page) for w in page):
        raise ContractError("input word outside unsigned32 wire range")
    if any(type(w) is not int or not 0 <= w < (1 << 32) for w in golden_words):
        raise ContractError("golden word outside unsigned32 wire range")
    if any(type(e) is not tuple or len(e) != 3
           or any(type(v) is not int for v in e) for e in event_records):
        raise ContractError("invalid ordered raw event record")
    if (not reference_source_sha256 or
            any(not isinstance(k, str) or not _digest(v)
                for k, v in reference_source_sha256.items())):
        raise ContractError("independent M02/M03 source identity missing")

    def words_sha(words: tuple[int, ...]) -> str:
        return sha256(struct.pack(f"<{len(words)}I", *words)).hexdigest()

    return {
        "reference": REFERENCE,
        "state_bits": 16,
        "leak_num": 3, "leak_den": 4,
        "leak_rounding": "truncate_toward_zero",
        "state_saturation": "signed16",
        "neuron_count": 32, "ticks": 4, "synapses": 5,
        "raw_event_count": 17,
        "ordered_event_stream_sha256": sha256(
            json.dumps(event_records, separators=(",", ":")).encode("ascii")
        ).hexdigest(),
        "host_input_neural_page_sha256": [words_sha(p) for p in neuron_pages],
        "host_input_edge_page_sha256": words_sha(edge_page),
        "independent_512_word_oracle_sha256": words_sha(golden_words),
        "independent_reference_source_sha256": dict(sorted(reference_source_sha256.items())),
        "logical_page_bytes": 256,
        "logical_page_count": 6,
        "logical_neurons_per_page": [6, 6, 6, 6, 6, 2],
        "oracle_words_never_loaded_as_inputs": True,
    }


def _check_witness(w: dict) -> None:
    if not isinstance(w, dict):
        raise ContractError("missing independent numerical witness")
    required = dict(reference=REFERENCE, state_bits=16, leak_num=3, leak_den=4,
                    leak_rounding="truncate_toward_zero", state_saturation="signed16",
                    neuron_count=32, ticks=4, synapses=5, raw_event_count=17,
                    logical_page_bytes=256, logical_page_count=6,
                    logical_neurons_per_page=[6, 6, 6, 6, 6, 2],
                    oracle_words_never_loaded_as_inputs=True)
    if any(w.get(k) != v or type(w.get(k)) is not type(v)
           for k, v in required.items()):
        raise ContractError("signed16 M06 neural workload/geometry has drifted")
    for name in ("ordered_event_stream_sha256", "host_input_edge_page_sha256",
                 "independent_512_word_oracle_sha256"):
        if not _digest(w.get(name)):
            raise ContractError(f"invalid reference digest: {name}")
    pages = w.get("host_input_neural_page_sha256")
    sources = w.get("independent_reference_source_sha256")
    if (not isinstance(pages, list) or len(pages) != 6
            or any(not _digest(x) for x in pages)
            or not isinstance(sources, dict) or len(sources) < 4
            or any(not isinstance(k, str) or not _digest(v)
                   for k, v in sources.items())):
        raise ContractError("input pages or independent reference source SHAs incomplete")


def classify_ddr_observation(observation: dict | None = None) -> dict:
    """A read-only inventory alone can NEVER establish a DMA ownership lease.

    NOT_AVAILABLE is reserved for a separately documented owner observation
    of a missing path, not inferred from an absent sysfs entry. VERIFIED
    will need a future *separate* original source/driver/lease auditor.
    """
    if observation is not None and not isinstance(observation, dict):
        raise ContractError("DDR observation must be a mapping")
    observation = observation or {}
    if observation.get("physical_dma_ready") is True or observation.get("AVAILABLE_VERIFIED") is True:
        raise ContractError("read-only inventory cannot self-certify real DDR/DMA")
    if observation.get("owner_verified_path_absent") is True:
        if not _digest(observation.get("owner_absence_receipt_sha256")):
            raise ContractError("owner-verified absence requires a receipt digest")
        state = "NOT_AVAILABLE"
    else:
        state = "UNKNOWN"
    return {
        "status": state,
        "available_verified": False,
        "read_only_inventory_not_ownership": True,
        "no_dma_or_mmio_access_performed": True,
        "unresolved_ownership_gates": list(DDR_BLOCKERS),
        "actual_ddr_read_bytes": None,
        "actual_ddr_write_bytes": None,
    }


def _row(cell: str, *, availability: str, ingress: str | None = None,
         hardware_bit_sha256: str | None = None,
         acceptance_record: str | None = None,
         fpga_current: int = 0, host_current: int = 0,
         fpga_voltage: int = 0, fpga_spike: int = 0,
         fpga_recurrent: int = 0, actual_page_dispatches: int | None = None,
         resident_page_banks: int | None = None,
         all_neurons_advanced_each_tick: bool | None = None) -> dict:
    strategy, placement = cell.split("/")
    historical = availability == "HISTORICAL_PHYSICAL_NOT_MATCHED"
    return {
        "cell": cell,
        "execution_label": strategy,
        "state_placement": placement,
        "availability": availability,
        "measurement_origin": "OWNER_REPORTED_KV260_FIRST_ORIGINAL" if historical else "NOT_MEASURED",
        "original_owner_evidence_reopened_here": False,
        "independent_owner_acceptance_record": acceptance_record,
        "original_bitstream_sha256": hardware_bit_sha256,
        "input_ingress": ingress,
        "actual_sparse_neuron_skip_verified": False,
        "all_neurons_advanced_each_tick": all_neurons_advanced_each_tick,
        "resident_page_banks": resident_page_banks,
        "resident_state_capacity_bytes": 256 if placement == "jtag_host_paged" else None,
        "physical_page_dispatches": actual_page_dispatches,
        "host_current_checks": host_current,
        "fabric_current_checks": fpga_current,
        "fabric_voltage_checks": fpga_voltage,
        "fabric_spike_checks": fpga_spike,
        "fabric_recurrent_checks": fpga_recurrent,
        "physical_neural_computations_checked": fpga_voltage + fpga_spike + fpga_recurrent,
        "historical_checked_quantities": host_current + fpga_current +
                                          fpga_voltage + fpga_spike + fpga_recurrent,
        "owner_original_raw_measurement_manifest_sha256": None,
        "matched_resource_envelope_sha256": None,
        "actual_jtag_host_transferred_bytes": None,
        "actual_ps_pl_ddr_read_bytes": None,
        "actual_ps_pl_ddr_write_bytes": None,
        "actual_ps_pl_ddr_transactions": None,
        "measured_pl_active_cycles": None,
        "measured_end_to_end_ns": None,
        "measured_clock_hz": None,
        "matched_timing_window": None,
        "real_ddr_ownership_verified": False,
        "quantitatively_comparable": False,
    }


def build_contract(witness: dict, *, observation: dict | None = None) -> dict:
    _check_witness(witness)
    ddr = classify_ddr_observation(observation)
    rows = [
        _row(CELLS[0], availability="HISTORICAL_PHYSICAL_NOT_MATCHED",
             ingress="HOST_COALESCED_17_INPUT_CURRENTS", hardware_bit_sha256=BIT_D2C,
             acceptance_record="docs/M08_D3D2C_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md",
             fpga_voltage=128, fpga_spike=128, fpga_recurrent=128,
             all_neurons_advanced_each_tick=True),
        _row(CELLS[1], availability="HISTORICAL_PHYSICAL_NOT_MATCHED",
             ingress="RAW_17_EVENTS_FABRIC_FIFO_TICK_SERVICE", hardware_bit_sha256=BIT_D2E,
             acceptance_record="docs/M08_D3D2E_OWNER_PHYSICAL_ACCEPTANCE_2026_11_20.md",
             fpga_current=128, fpga_voltage=128, fpga_spike=128,
             fpga_recurrent=128, all_neurons_advanced_each_tick=True),
        _row(CELLS[2], availability="HISTORICAL_PHYSICAL_NOT_MATCHED",
             ingress="HOST_COALESCED_17_INPUT_CURRENTS", hardware_bit_sha256=BIT_M084,
             acceptance_record="docs/M08_4_FIRST_OWNER_PAGED_NEURAL_PHYSICAL_2026_11_20.md",
             host_current=128, fpga_voltage=128, fpga_spike=128,
             fpga_recurrent=128, actual_page_dispatches=24, resident_page_banks=1,
             all_neurons_advanced_each_tick=True),
        _row(CELLS[3], availability="UNAVAILABLE_NOT_BUILT"),
        _row(CELLS[4], availability="BLOCKED_DDR_OWNERSHIP"),
        _row(CELLS[5], availability="BLOCKED_DDR_OWNERSHIP"),
    ]
    result = {
        "schema": SCHEMA,
        "scope": "SOURCE_ONLY_CONTRACT_WITH_HISTORICAL_OWNER_ACCEPTED_ANCHORS",
        "m08_4_status": "OWNER_PHYSICALLY_ACCEPTED_CLOSED",
        "same_original_m02_m03_neural_oracle": deepcopy(witness),
        "ddr_readiness": ddr,
        "rows": rows,
        "historical_sources_are_not_replayed": True,
        "new_fpga_programming_authorized": False,
        "new_fpga_run_performed": False,
        "source_only_contract_not_new_hardware_evidence": True,
        "full_matched_performance_pairs_available": 0,
    }
    check_contract(result)
    return result


def check_contract(report: dict) -> None:
    if not isinstance(report, dict) or report.get("schema") != SCHEMA:
        raise ContractError("unsupported comparator schema")
    _check_witness(report.get("same_original_m02_m03_neural_oracle"))
    rows = report.get("rows")
    if not isinstance(rows, list) or [r.get("cell") for r in rows] != list(CELLS):
        raise ContractError("six placement × execution cells are required")
    if (report.get("new_fpga_programming_authorized") is not False
            or report.get("new_fpga_run_performed") is not False
            or report.get("historical_sources_are_not_replayed") is not True
            or report.get("full_matched_performance_pairs_available") != 0):
        raise ContractError("source-only report must not assert hardware release or speedups")
    ddr = report.get("ddr_readiness")
    if (not isinstance(ddr, dict) or ddr.get("status") not in
            ("UNKNOWN", "NOT_AVAILABLE") or ddr.get("available_verified") is not False):
        raise ContractError("real DDR ownership remains unverified")
    for row in rows:
        historical = row["availability"] == "HISTORICAL_PHYSICAL_NOT_MATCHED"
        cell = row["cell"]
        placement = cell.split("/")[1]
        if (row["execution_label"] != cell.split("/")[0]
                or row["state_placement"] != placement
                or row["original_owner_evidence_reopened_here"] is not False
                or row["real_ddr_ownership_verified"] is not False
                or row["actual_sparse_neuron_skip_verified"] is not False
                or row["quantitatively_comparable"] is not False):
            raise ContractError("incorrect physical or execution provenance")
        for key in ("owner_original_raw_measurement_manifest_sha256",
                    "matched_resource_envelope_sha256", "measured_pl_active_cycles",
                    "measured_end_to_end_ns", "measured_clock_hz",
                    "matched_timing_window", "actual_jtag_host_transferred_bytes",
                    "actual_ps_pl_ddr_read_bytes", "actual_ps_pl_ddr_write_bytes",
                    "actual_ps_pl_ddr_transactions"):
            if row[key] is not None:
                raise ContractError(f"unmeasured quantity is not null: {key}")
        if placement == "ps_pl_ddr" and row["availability"] != "BLOCKED_DDR_OWNERSHIP":
            raise ContractError("physical DDR row promoted without ownership proof")
        if historical and (not _digest(row["original_bitstream_sha256"]) or
                           not row["independent_owner_acceptance_record"]):
            raise ContractError("historical physical evidence must identify its own image")
        if not historical and (row["original_bitstream_sha256"] is not None
                               or row["historical_checked_quantities"] != 0):
            raise ContractError("unavailable comparator contains fabricated hardware data")
        counts = sum(row[k] for k in ("host_current_checks", "fabric_current_checks",
                                     "fabric_voltage_checks", "fabric_spike_checks",
                                     "fabric_recurrent_checks"))
        if counts != row["historical_checked_quantities"]:
            raise ContractError("neural source/provenance count accounting mismatch")
        if (row["physical_neural_computations_checked"] !=
                sum(row[k] for k in ("fabric_voltage_checks", "fabric_spike_checks",
                                     "fabric_recurrent_checks"))):
            raise ContractError("host currents must not be counted as PL neural work")
    if [r["historical_checked_quantities"] for r in rows] != [384, 512, 512, 0, 0, 0]:
        raise ContractError("historical 384/512/512 acceptance counts drifted")
    if [r["physical_page_dispatches"] for r in rows] != [None, None, 24,
                                                          None, None, None]:
        raise ContractError("24 M08.4 physical page dispatches misattributed")


def compare_structure(left: dict, right: dict, *, axis: str) -> dict:
    """Fail-closed metadata precheck; never returns a speedup.

    Only *future*, independently authenticated records may be considered.
    Two numerical PASS labels or matching bitstream SHAs are not enough.
    """
    if axis not in ("execution", "placement"):
        raise ContractError("declare one experimental axis")
    if left.get("cell") not in CELLS or right.get("cell") not in CELLS:
        raise ContractError("unknown comparator cell")
    ls, lp = left["cell"].split("/")
    rs, rp = right["cell"].split("/")
    if axis == "execution" and (lp != rp or ls == rs):
        raise ContractError("execution comparison must hold state placement fixed")
    if axis == "placement" and (ls != rs or lp == rp):
        raise ContractError("placement comparison must hold execution fixed")
    for name in ("neural_witness_sha256", "ordered_event_stream_sha256",
                 "precision_and_arithmetic", "synapse_and_event_work_sha256",
                 "input_ingress", "event_delivery_order_sha256",
                 "timing_boundary", "resource_envelope_sha256"):
        if not left.get(name) or left[name] != right.get(name):
            raise ContractError("not an apples-to-apples comparator: " + name)
    if left.get("input_ingress") not in (
        "RAW_17_EVENTS_FABRIC_FIFO_TICK_SERVICE",
        "HOST_COALESCED_17_INPUT_CURRENTS",
    ):
        raise ContractError("event ingress unaccounted")
    if not all(row.get("new_owner_raw_evidence_verified") is True
               for row in (left, right)):
        raise ContractError("original immutable evidence must be audited for both controls")
    for row in (left, right):
        if row.get("actual_sparse_neuron_skip_verified") is not True and row["cell"].startswith("event/"):
            raise ContractError("FIFO event acceptance is not sparse neuron execution")
        if row["cell"].endswith("ps_pl_ddr") and row.get("ddr_ownership_audited") is not True:
            raise ContractError("DDR ownership not audited")
    return {
        "status": "STRUCTURALLY_MATCHED_ONLY_NO_LATENCY_CLAIM",
        "axis": axis,
        "performance_comparable": False,
        "speedup": None,
        "measurement_receipts_still_required": True,
    }
