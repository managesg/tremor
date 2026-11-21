import unittest

from lab import advisor_controls, frontier_advisor, topology


class AdvisorControlTests(unittest.TestCase):
    def test_cost_and_result_pairing_in_all_cells(self):
        cells = advisor_controls.compare()["cells"]
        self.assertEqual(len(cells), 72)
        for cell in cells:
            with self.subTest(fixture=cell["fixture"], mode=cell["mode"],
                              access=cell["evidence_access"], advisor=cell["advisor"]):
                self.assertEqual(cell["spent"], sum(event["cost"] for event in cell["trace"]))
                self.assertEqual(cell["spent"] + cell["unused"], topology.BUDGET)
                self.assertEqual(cell["advice_cost"], cell["attempts"] * 2)
                self.assertEqual(len(cell["recovery"]), cell["attempts"])
                if cell["advisor"] == "local_only":
                    self.assertEqual(cell["attempts"], 0)

    def test_advice_stays_with_worker_and_requires_common_verifier(self):
        requests = []

        def collect(request):
            requests.append(request)
            return frontier_advisor.available(request)

        fixture = topology.FIXTURES[2]
        shared = topology.run(fixture, "peers", evidence_access="shared", advisor=collect)
        self.assertIn(frontier_advisor.Request("b", "middle", ("root",)), requests)
        self.assertEqual(shared["verified_union"], ["final", "middle", "root"])
        accepted = [shared["trace"][event["submission"]]
                    for event in shared["trace"] if event["kind"] == "verify" and event["accepted"]]
        self.assertEqual(sorted(event["task"] for event in accepted), shared["verified_union"])
        own = topology.run(fixture, "peers", evidence_access="own", advisor=collect)
        self.assertEqual(own["verified_union"], ["root"])

    def test_unavailability_is_charged_and_preserves_local_recovery(self):
        fixture = topology.FIXTURES[2]
        baseline = topology.run(fixture, "peers", evidence_access="shared")
        available = topology.run(fixture, "peers", evidence_access="shared", advisor=frontier_advisor.available)
        unavailable = topology.run(fixture, "peers", evidence_access="shared", advisor=frontier_advisor.unavailable)
        self.assertEqual(baseline["verified_union"], unavailable["verified_union"])
        self.assertEqual(available["verified_union"], unavailable["verified_union"])
        self.assertLess(available["blocked_dependencies"], unavailable["blocked_dependencies"])
        self.assertEqual({row["status"] for row in advisor_controls._measure(unavailable)["recovery"]},
                         {"unavailable"})
        self.assertEqual(sorted(row["rounds_until_verified"] for row in advisor_controls._measure(unavailable)["recovery"]),
                         [1, 2])

    def test_budget_reserves_result_and_merge_before_any_consult(self):
        fixture = topology.FIXTURES[2]
        for budget in range(1, topology.BUDGET):
            with self.subTest(budget=budget):
                run = topology.run(fixture, "peers", budget, evidence_access="shared", advisor=frontier_advisor.available)
                advice = advisor_controls._measure(run)
                self.assertEqual(advice["advice_cost"], advice["attempts"] * 2)
                self.assertLessEqual(run["spent"], budget)
                self.assertEqual(run["trace"][-1]["kind"], "merge")
