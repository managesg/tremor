import unittest

from lab import controller_common_cost as audit
from lab.tests import test_controller_shared_cost as fixtures


class ControllerCommonCostTests(unittest.TestCase):
    def setUp(self):
        self.case = case = fixtures.ControllerSharedCostTests()
        case.setUp()
        self.addCleanup(case.doCleanups)
        self.roles = case.write("roles.json", {
            "schema": audit.SCHEMA,
            "roles": {"score-0": "independent_scoring", "calibration-0": "calibration"},
        })

    def verify(self):
        case = self.case
        index, index_pin = case.write("index.json", {"schema": "controller_unit_charges_v1",
                                                     "receipts": case.charges})
        placement, placement_pin = case.write("placement.json", {
            "schema": "controller_cost_placement_v1", "charge_index_sha256": index_pin,
            "charges_by_scope": case.scopes,
        })
        path, pin = self.roles
        return audit.verify(placement, index, path, placement_sha256=placement_pin,
                            charge_index_sha256=index_pin, roles_sha256=pin)

    def test_role_labels_are_independently_bound_even_after_repinning_usage(self):
        self.assertEqual(self.verify()["by_role"]["independent_scoring"]["incremental_usage"]["gpu_wall_ns"], 4)
        self.case.charges[2]["role"] = "setup"
        self.assertEqual(self.case.verify()["by_scope"]["common"]["incremental_usage"]["gpu_wall_ns"], 4)
        with self.assertRaisesRegex(ValueError, "role differs from the independent declaration"):
            self.verify()

    def test_prior_and_unavailable_usage_stay_with_their_role(self):
        self.case.charges[2]["usage"] = None
        groups = self.verify()["by_role"]
        self.assertIsNone(groups["independent_scoring"]["incremental_usage"])
        self.assertEqual(groups["independent_scoring"]["unsettled_charge_ids"], ["score-0"])
        self.assertEqual(groups["calibration"]["known_prior_usage"]["gpu_wall_ns"], 15)
        self.assertEqual(groups["calibration"]["incremental_usage"]["gpu_wall_ns"], 0)
        self.case.charges.pop(2)
        groups = self.verify()["by_role"]
        self.assertEqual(groups["independent_scoring"]["missing_charge_ids"], ["score-0"])
        self.assertIsNone(groups["independent_scoring"]["incremental_usage"])

    def test_cannot_omit_a_declared_planned_charge(self):
        self.case.scopes["common"].pop()
        self.case.charges.pop()
        with self.assertRaisesRegex(ValueError, "common charge IDs"):
            self.verify()
