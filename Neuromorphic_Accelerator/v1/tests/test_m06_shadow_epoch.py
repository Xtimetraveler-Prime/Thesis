"""M06 software-only shadow epoch tests, not physical DDR atomicity evidence."""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from neuromorphic_accelerator_v1.m02_dense_reference import evaluate_dense
from neuromorphic_accelerator_v1.m02_types import InputCurrent, Network, Neuron, Synapse
from neuromorphic_accelerator_v1.m06_block_residency import CanonicalImage, Geometry
from neuromorphic_accelerator_v1.m06_axi_transport import AXIFault, AXIModelError
from neuromorphic_accelerator_v1.m06_shadow_epoch import ShadowEpoch, EpochError


def sample(n=32, *, both=True):
    neurons = tuple(Neuron(bias=1 if i == 0 or (both and i == n-1) else 0,
                           threshold=30, reset_v=0)
                    for i in range(n))
    return Network(neurons=neurons, synapses=(),
                   decay_num=1, decay_den=1)


def baseline(net=None):
    if net is None:
        net = sample()
    g = Geometry(logical_neurons=len(net.neurons),
                 bytes_per_neuron=2, neurons_per_block=16,
                 resident_budget_bytes=32, max_model_transfer_bytes=32)
    initial = b"".join(n.initial_v.to_bytes(2, "little", signed=True)
                       for n in net.neurons)
    store = CanonicalImage(g, emulated_owner="MODEL", initial=initial)
    return net, store


class ShadowEpochTests(unittest.TestCase):
    def test_complete_epoch_does_not_publish_before_oracle_then_commits(self):
        net, canonical = baseline()
        prior = canonical.snapshot(owner="MODEL")
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="session-001")
        actual = epoch.run(net, (), ticks=4)
        self.assertEqual(actual.trace, evaluate_dense(net, (), ticks=4))
        self.assertEqual(epoch.status, "RAN_UNCOMMITTED")
        self.assertEqual(canonical.snapshot(owner="MODEL"), prior)
        with self.assertRaisesRegex(EpochError, "before independent"):
            epoch.commit()
        epoch.verify_against_independent_m02(net, (), ticks=4)
        self.assertEqual(epoch.status, "VALIDATED_UNCOMMITTED")
        self.assertEqual(canonical.snapshot(owner="MODEL"), prior)
        receipt = epoch.commit()
        self.assertEqual(receipt.status, "SOFTWARE_COMMITTED_NOT_PHYSICAL_DDR")
        self.assertEqual(receipt.changed_pages, (0, 1))
        self.assertEqual(epoch.status, "COMMITTED")
        self.assertEqual(int.from_bytes(canonical.snapshot(owner="MODEL")[:2],
                                        "little", signed=True), 4)
        self.assertEqual(canonical.version(0, owner="MODEL"), 1)
        self.assertEqual(canonical.version(1, owner="MODEL"), 1)

    def test_full_16byte_state_epoch_commits_watermarks_only_after_oracle(self):
        net = sample()
        g = Geometry(logical_neurons=32, bytes_per_neuron=16,
                     neurons_per_block=16, resident_budget_bytes=256,
                     max_model_transfer_bytes=256)
        canonical = CanonicalImage(g, emulated_owner="MODEL",
                                   initial=bytes(g.image_bytes))
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="state16")
        epoch.run(net, (), ticks=3)
        self.assertEqual(canonical.snapshot(owner="MODEL"), bytes(g.image_bytes))
        epoch.verify_against_independent_m02(net, (), ticks=3)
        receipt = epoch.commit()
        self.assertEqual(receipt.changed_pages, (0, 1))
        final = canonical.snapshot(owner="MODEL")
        for i in range(32):
            record = final[16*i:16*(i+1)]
            expected = 3 if i in (0, 31) else 0
            self.assertEqual(int.from_bytes(record[:2], "little", signed=True), expected)
            self.assertEqual(int.from_bytes(record[2:6], "little"), expected)
        self.assertEqual(receipt.status, "SOFTWARE_COMMITTED_NOT_PHYSICAL_DDR")

    def test_aborted_neural_replay_never_mutates_initial_canonical_state(self):
        net, canonical = baseline()
        old = canonical.snapshot(owner="MODEL")
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="abort")
        epoch.shadow.inject_axi_fault_once(AXIFault("WRITE", "RESPONSE_LOST"))
        with self.assertRaises(AXIModelError):
            epoch.run(net, (), ticks=2)
        self.assertEqual(epoch.status, "FAILED_REQUIRES_ABORT")
        self.assertTrue(epoch.cache.poisoned)
        self.assertTrue(epoch.shadow.uncertain_pages)
        evidence = epoch.abort()
        self.assertEqual(evidence["physical_ddr"], "NOT_ACCESSED")
        self.assertEqual(epoch.status, "ABORTED")
        self.assertEqual(canonical.snapshot(owner="MODEL"), old)
        with self.assertRaises(EpochError):
            epoch.commit()

    def test_corrupted_shadow_image_cannot_pass_independent_final_state(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="corrupt")
        epoch.run(net, (), ticks=3)
        epoch.shadow._bytes[0] ^= 0x10  # test-only injected memory corruption
        with self.assertRaisesRegex(EpochError, "shadow canonical bytes differ"):
            epoch.verify_against_independent_m02(net, (), ticks=3)
        self.assertEqual(epoch.status, "FAILED_REQUIRES_ABORT")
        epoch.abort()
        self.assertEqual(canonical.snapshot(owner="MODEL"), bytes(64))

    def test_wrong_oracle_input_detects_and_blocks_publication(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="wrong-golden")
        epoch.run(net, (), ticks=3)
        with self.assertRaisesRegex(EpochError, "independent M02 trace differs"):
            epoch.verify_against_independent_m02(net,
                (InputCurrent(0, 4, 7),), ticks=3)
        self.assertEqual(epoch.status, "FAILED_REQUIRES_ABORT")
        epoch.abort()
        self.assertEqual(canonical.snapshot(owner="MODEL"), bytes(64))

    def test_external_version_change_while_prepared_detected_at_commit(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="conflict")
        epoch.run(net, (), ticks=2)
        epoch.verify_against_independent_m02(net, (), ticks=2)
        canonical.external_edit_for_negative_test(0, b"\xaa"*32)
        with self.assertRaisesRegex(EpochError, "externally changed"):
            epoch.commit()
        self.assertEqual(epoch.status, "FAILED_REQUIRES_ABORT")
        epoch.abort()
        self.assertEqual(canonical.snapshot(owner="MODEL")[:32], b"\xaa"*32)

    def test_raw_external_mutation_without_version_is_also_detected(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="silent")
        epoch.run(net, (), ticks=2)
        epoch.verify_against_independent_m02(net, (), ticks=2)
        canonical._bytes[2] = 99  # adversarial bypass of versioning
        with self.assertRaisesRegex(EpochError, "without a version"):
            epoch.commit()
        epoch.abort()

    def test_duplicate_commit_and_abort_after_commit_refused(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="once")
        epoch.run(net, (), ticks=1)
        epoch.verify_against_independent_m02(net, (), ticks=1)
        epoch.commit()
        with self.assertRaises(EpochError):
            epoch.commit()
        with self.assertRaises(EpochError):
            epoch.abort()

    def test_double_run_and_double_abort_refused(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="single")
        epoch.run(net, (), ticks=1)
        with self.assertRaises(EpochError):
            epoch.run(net, (), ticks=1)
        epoch.abort()
        with self.assertRaises(EpochError):
            epoch.abort()
        with self.assertRaises(EpochError):
            epoch.run(net, (), ticks=1)

    def test_unsorted_external_on_epoch_causes_fail_no_canonical_mutation(self):
        net, canonical = baseline()
        epoch = ShadowEpoch(canonical, owner="MODEL", epoch_id="bad-order")
        bad = (InputCurrent(1, 0, 1), InputCurrent(0, 0, 1))
        with self.assertRaisesRegex(ValueError, "tick-sorted"):
            epoch.run(net, bad, ticks=2)
        self.assertEqual(epoch.status, "FAILED_REQUIRES_ABORT")
        epoch.abort()
        self.assertEqual(canonical.snapshot(owner="MODEL"), bytes(64))

    def test_epoch_geometry_and_token_fail_closed(self):
        net, canonical = baseline()
        with self.assertRaises(ValueError):
            ShadowEpoch(canonical, owner="MODEL", epoch_id="")
        with self.assertRaises(PermissionError):
            ShadowEpoch(canonical, owner="wrong", epoch_id="bad")
        cfg = Geometry(logical_neurons=4, bytes_per_neuron=2,
                       neurons_per_block=2, resident_budget_bytes=4,
                       max_model_transfer_bytes=4)
        store = CanonicalImage(cfg, emulated_owner="MODEL")
        with self.assertRaisesRegex(ValueError, "32-byte"):
            ShadowEpoch(store, owner="MODEL", epoch_id="badsize")


if __name__ == "__main__":
    unittest.main()
