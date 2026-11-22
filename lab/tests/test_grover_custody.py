from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import product
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from lab import topology
from lab.quantum import custody
from lab.quantum.transfer_fixtures import Fixture, Stage


def block(label, fixture):
    results = fixture.reference_results()
    earlier = {}
    stages = []
    for stage in fixture.stages:
        answer = results[stage.name]["first"]
        effective = stage.task(earlier).target
        branch = "no_hit" if answer is None else "boundary" if answer[1] == effective else "hit"
        stages.append({
            "id": stage.name, "qubits": stage.qubits, "iteration_cap": stage.cap, "target": str(stage.target),
            "marks": {source: sorted(indices) for source, indices in stage.marks}, "solvers": list(stage.solvers),
            "prerequisite": stage.prerequisite, "branch": branch,
        })
        earlier[stage.name] = answer
    return {
        "id": label, "family": f"{label}-family", "instance": f"{label}-instance", "structure": f"{label}-structure",
        "regime": fixture.regime, "budget": 32, "worker_order": ["a", "b", "c"],
        "order": [list(pair) for pair in product(topology.MODES, topology.EVIDENCE_ACCESS)],
        "stages": stages, "projections": custody.projections(fixture),
    }


def documents():
    development = {"schema": custody.DEVELOPMENT, "blocks": [block("development", Fixture(
        "complementary", (Stage("join", 3, 1, Fraction(1), (("a", (0,)), ("b", (1,))), ("c",)),),
    ))]}
    holdout = block("rehearsal", Fixture("sequential", (
        Stage("scout", 3, 2, Fraction(4, 5), (("a", (1,)),), ("a",)),
        Stage("confirm", 3, 1, Fraction(4, 5), (("b", (2,)),), ("b",), "scout"),
        Stage("final", 2, 1, Fraction(1), (("c", (3,)),), ("c",), "confirm"),
    )))
    document = {
        "schema": custody.MANIFEST, "inventory_id": "synthetic-example", "protocol_sha256": "1" * 64,
        "generator_revision": "synthetic-1", "generator_config_sha256": "2" * 64,
        "split_rule_sha256": "3" * 64, "development_inventory_sha256": sha256(custody.canonical(development)).hexdigest(),
        "blocks": [holdout],
    }
    return development, document


class GroverCustodyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(self.enterContext(TemporaryDirectory()))
        self.development, self.document = documents()
        self.opening = bytes(range(32))

    def bundle(self):
        self.paths = {name: self.root / name for name in ("manifest", "nonce", "receipt", "development")}
        raw = custody.canonical(self.document)
        self.paths["manifest"].write_bytes(raw)
        self.paths["nonce"].write_bytes(self.opening)
        self.paths["development"].write_bytes(custody.canonical(self.development))
        self.receipt = {
            "schema": custody.RECEIPT, "inventory_id": self.document["inventory_id"],
            "commitment": custody.commitment(raw, self.opening), "protocol_sha256": self.document["protocol_sha256"],
            "split_rule_sha256": self.document["split_rule_sha256"], "custodian_id": "synthetic-reviewer",
            "issuance_index": 3, "issued_utc": "2026-11-21T21:00:00Z",
        }
        self.pins = {"protocol_sha256": "1" * 64, "split_rule_sha256": "3" * 64, "custodian_id": "synthetic-reviewer"}
        self.write_receipt()

    def write_receipt(self):
        raw = custody.canonical(self.receipt)
        self.paths["receipt"].write_bytes(raw)
        self.pins["receipt_sha256"] = sha256(raw).hexdigest()

    def verify(self):
        return custody.verify(**self.paths, **self.pins)

    def expected_quotas(self):
        return {
            "schema": "grover_custody_rehearsal_expectations_v1",
            "inventory_id": "synthetic-example",
            "protocol_sha256": "1" * 64,
            "split_rule_sha256": "3" * 64,
            "generator_revision": "synthetic-1",
            "generator_config_sha256": "2" * 64,
            "development_inventory_sha256": sha256(custody.canonical(self.development)).hexdigest(),
            "block_ids": ["rehearsal"],
            "manifest_commitment": custody.commitment(custody.canonical(self.document), self.opening),
            "branches_by_regime": {
                "complementary": {"hit": 0, "no_hit": 0, "boundary": 0},
                "redundant": {"hit": 0, "no_hit": 0, "boundary": 0},
                "sequential": {"hit": 1, "no_hit": 1, "boundary": 1},
            },
        }

    def verify_expected(self, expected):
        path = self.root / "expectations"
        raw = custody.canonical(expected)
        path.write_bytes(raw)
        return custody.verify(**self.paths, **self.pins, expectations=path,
                              expectations_sha256=sha256(raw).hexdigest())

    def test_frozen_comparison_keeps_rehearsal_scope(self):
        self.bundle()
        expected = self.expected_quotas()
        result = self.verify_expected(expected)
        self.assertEqual(result["expectations_sha256"], sha256(custody.canonical(expected)).hexdigest())
        self.assertEqual(result["branches_by_regime"], expected["branches_by_regime"])
        for flag in ("custodian_authenticated", "authorizes_execution", "scientific_result"):
            self.assertFalse(result[flag])
        self.assertNotIn("expectations_sha256", self.verify())
        self.assertNotIn("block_ids", result)

    def test_recommitted_opening_cannot_change_frozen_generator_or_block_set(self):
        expected = self.expected_quotas()
        original = deepcopy(self.document)
        for field, value in (("generator_revision", "synthetic-2"), ("generator_config_sha256", "4" * 64),
                             ("inventory_id", "other-inventory")):
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, field):
                self.document = {**original, field: value}
                self.bundle()
                self.verify_expected(expected)
        self.document = deepcopy(original)
        self.document["blocks"][0]["id"] = "other-block"
        self.bundle()
        with self.assertRaisesRegex(ValueError, "ordered block IDs"):
            self.verify_expected(expected)
        self.document = deepcopy(original)
        self.document["blocks"][0]["order"].reverse()
        self.bundle()
        with self.assertRaisesRegex(ValueError, "manifest commitment differs"):
            self.verify_expected(expected)

    def test_repinned_quotas_refuse_mismatches_with_the_same_aggregate(self):
        self.bundle()
        expected = self.expected_quotas()
        quotas = expected["branches_by_regime"]
        quotas["sequential"]["hit"] -= 1
        quotas["redundant"]["hit"] += 1
        with self.assertRaisesRegex(ValueError, "quotas differ"):
            self.verify_expected(expected)
        expected = self.expected_quotas()
        expected["branches_by_regime"]["sequential"]["boundary"] = True
        with self.assertRaisesRegex(ValueError, "nonnegative integer"):
            self.verify_expected(expected)

    def test_expectations_path_and_external_pin_must_be_paired(self):
        self.bundle()
        path = self.root / "expectations"
        path.write_bytes(custody.canonical(self.expected_quotas()))
        for args in ({"expectations": path}, {"expectations_sha256": "4" * 64}):
            with self.subTest(args=args), self.assertRaisesRegex(ValueError, "supplied together"):
                custody.verify(**self.paths, **self.pins, **args)
        with self.assertRaisesRegex(ValueError, "expectations digest does not match"):
            custody.verify(**self.paths, **self.pins, expectations=path, expectations_sha256="4" * 64)

    def test_exact_opening_counts_boundaries_and_no_hit_without_disclosing_inputs(self):
        self.bundle()
        expected = self.verify()
        self.bundle()
        self.assertEqual(expected, self.verify())
        self.assertEqual(expected["branches"], {"hit": 1, "no_hit": 1, "boundary": 1})
        self.assertEqual(expected["matched_arms"], 8)
        self.assertFalse(expected["custodian_authenticated"])
        self.assertFalse(expected["authorizes_execution"])
        self.assertNotIn("nonce", expected)
        self.assertNotIn("projections", expected)

    def test_wrong_bytes_and_receipt_pin_fail(self):
        self.bundle()
        self.paths["nonce"].write_bytes(bytes(reversed(self.opening)))
        with self.assertRaisesRegex(ValueError, "opening differs"):
            self.verify()
        self.paths["nonce"].write_bytes(self.opening)
        self.paths["receipt"].write_bytes(custody.canonical({**self.receipt, "issuance_index": 99}))
        with self.assertRaisesRegex(ValueError, "receipt digest"):
            self.verify()
        self.bundle()
        self.paths["manifest"].write_bytes(custody.canonical(self.document) + b"\n")
        with self.assertRaisesRegex(ValueError, "canonical JSON"):
            self.verify()

    def test_wrong_protocol_split_and_custodian_fail_even_after_repinning(self):
        for field, value, message in (
            ("protocol_sha256", "a" * 64, "protocol_sha256 differs"),
            ("split_rule_sha256", "b" * 64, "split_rule_sha256 differs"),
            ("custodian_id", "another-role", "unexpected custodian"),
        ):
            with self.subTest(field=field):
                self.bundle()
                self.receipt[field] = value
                self.write_receipt()
                with self.assertRaisesRegex(ValueError, message):
                    self.verify()

    def test_projection_and_match_schedule_are_closed(self):
        original = deepcopy(self.document)
        for mutation, message in (
            (lambda row: row["projections"]["workers"]["a"].update(private_answer=[1, "1"]), "role projection"),
            (lambda row: row["projections"]["planner_eligibility"].update(private_seed=42), "role projection"),
            (lambda row: row["stages"][2].update(prerequisite="unknown"), "prerequisite"),
            (lambda row: row["stages"][1].update(branch="hit"), "exact scorer"),
            (lambda row: row["order"].append(row["order"][0]), "matched arm schedule"),
            (lambda row: row["stages"][0]["solvers"].append("a"), "solver roster"),
        ):
            with self.subTest(message=message):
                self.document = deepcopy(original)
                mutation(self.document["blocks"][0])
                self.bundle()
                with self.assertRaisesRegex(ValueError, message):
                    self.verify()

    def test_fresh_commitment_cannot_label_independent_work_as_a_coordination_regime(self):
        stages = (Stage("direct", 3, 2, Fraction(4, 5), (("a", (5,)),), ("a",)),)
        for regime in ("complementary", "redundant", "sequential"):
            with self.subTest(regime=regime), self.assertRaisesRegex(ValueError, "does not implement " + regime):
                self.document["blocks"] = [block("relabeled", Fixture(regime, stages))]
                self.bundle()
                self.verify()

    def test_redundancy_requires_a_shared_direct_stage_and_an_independent_stage(self):
        common = Stage("common", 3, 2, Fraction(4, 5), (("a", (3,)), ("b", (3,))), ("a", "b"))
        separate = Stage("separate", 3, 2, Fraction(1), (("c", (6,)),), ("c",))
        self.document["blocks"] = [block("redundancy", Fixture("redundant", (common, separate)))]
        self.bundle()
        self.assertEqual(self.verify()["matched_arms"], 8)
        self.document["blocks"] = [block("no-separate", Fixture("redundant", (common,)))]
        self.bundle()
        with self.assertRaisesRegex(ValueError, "does not implement redundant"):
            self.verify()

    def test_complementary_requires_marks_from_multiple_sources(self):
        join = Stage("join", 3, 2, Fraction(1), (("a", (0, 1)), ("b", (1,))), ("c",))
        self.document["blocks"] = [block("duplicated-shard", Fixture("complementary", (join,)))]
        self.bundle()
        with self.assertRaisesRegex(ValueError, "does not implement complementary"):
            self.verify()

        overlap = Stage("joint", 3, 2, Fraction(1), (
            ("a", (0, 1)), ("b", (1, 2)), ("c", (0, 2)),
        ), ("c",))
        self.document["blocks"] = [block("overlap", Fixture("complementary", (overlap,)))]
        self.bundle()
        self.assertEqual(self.verify()["matched_arms"], 8)

    def test_relabelled_index_positions_cannot_reuse_development_math_and_structure(self):
        aliases = Fixture("complementary", (Stage("other", 3, 1, Fraction(1), (
            ("a", (6,)), ("b", (7,)),
        ), ("c",)),))
        self.document["blocks"] = [block("new-labels", aliases)]
        self.bundle()
        with self.assertRaisesRegex(ValueError, "equivalent task structure and probability"):
            self.verify()

    def test_renamed_copies_cannot_inflate_rehearsal_block_or_branch_counts(self):
        duplicate = deepcopy(self.document["blocks"][0])
        duplicate.update(id="second", family="second-family", instance="second-instance", structure="second-structure")
        duplicate["order"].reverse()
        self.document["blocks"].append(duplicate)
        self.bundle()
        with self.assertRaisesRegex(ValueError, "duplicate equivalent task"):
            self.verify()

    def _two_redundant_stages(self):
        shared = Stage("common", 3, 2, Fraction(4, 5), (("a", (3,)), ("b", (3,))), ("a", "b"))
        separate = Stage("separate", 3, 2, Fraction(1), (("c", (6,)),), ("c",))
        return shared, separate

    def test_reversing_independent_stages_cannot_split_the_same_task_structure(self):
        shared, separate = self._two_redundant_stages()
        original = block("development-redundant", Fixture("redundant", (shared, separate)))
        reordered = block("held-redundant", Fixture("redundant", (separate, shared)))
        self.assertNotEqual(custody._block(original)[1], custody._block(reordered)[1])
        self.development["blocks"] = [original]
        self.document["development_inventory_sha256"] = sha256(custody.canonical(self.development)).hexdigest()
        self.document["blocks"] = [reordered]
        self.bundle()
        with self.assertRaisesRegex(ValueError, "equivalent task structure and probability"):
            self.verify()

    def test_reordering_parallel_branches_does_not_inflate_branch_quota(self):
        shared, separate = self._two_redundant_stages()
        following = Stage("following", 3, 1, Fraction(4, 5), (("b", (2,)),), ("b",), "common")
        first_order = Fixture("sequential", (shared, following, separate))
        second_order = Fixture("sequential", (separate, shared, following))
        self.document["blocks"] = [block("first", first_order), block("second", second_order)]
        self.bundle()
        with self.assertRaisesRegex(ValueError, "duplicate equivalent task"):
            self.verify()

    def test_different_prerequisite_with_equal_scorer_values_is_novel(self):
        left = Stage("left", 3, 2, Fraction(4, 5), (("a", (3,)),), ("a",))
        right = Stage("right", 3, 2, Fraction(4, 5), (("c", (6,)),), ("c",))
        left_child = Stage("following", 3, 1, Fraction(4, 5), (("b", (2,)),), ("b",), "left")
        right_child = Stage("following", 3, 1, Fraction(4, 5), (("b", (2,)),), ("b",), "right")
        self.document["blocks"] = [block("left-linked", Fixture("sequential", (left, right, left_child))),
                                   block("right-linked", Fixture("sequential", (left, right, right_child)))]
        self.assertEqual([row["branch"] for row in self.document["blocks"][0]["stages"]],
                         [row["branch"] for row in self.document["blocks"][1]["stages"]])
        self.bundle()
        self.assertEqual(self.verify()["blocks"], 2)

    def test_unreleased_shard_changes_only_its_own_source_projection(self):
        def observe(mark):
            fixture = Fixture("complementary", (Stage(
                "join", 3, 1, Fraction(1), (("a", (0,)), ("b", (mark,))), ("c",),
            ),))
            return custody.projections(fixture)

        before, after = observe(1), observe(7)
        self.assertEqual(before["planner_eligibility"], after["planner_eligibility"])
        self.assertEqual(before["workers"]["a"], after["workers"]["a"])
        self.assertEqual(before["workers"]["c"], after["workers"]["c"])
        self.assertNotEqual(before["workers"]["b"], after["workers"]["b"])

    def test_equal_physics_with_distinct_source_assignment_is_distinguishable(self):
        separate = Fixture("complementary", (Stage("join", 3, 1, Fraction(1), (
            ("a", (4,)), ("c", (5,)),
        ), ("b",)),))
        self.document["blocks"] = [block("different-routing", separate)]
        self.bundle()
        self.assertEqual(self.verify()["branches"]["boundary"], 1)

    def test_fixture_rejects_ambiguous_source_and_prerequisite_roles(self):
        for fixture, message in (
            (lambda: Fixture("complementary", (Stage(
                "join", 3, 1, Fraction(1), (("a", (0,)), ("a", (1,))), ("c",),
            ),)), "unique known workers"),
            (lambda: Fixture("sequential", (Stage(
                "join", 3, 1, Fraction(1), (("a", (0,)),), ("a",), "missing",
            ),)), "prerequisites must precede"),
        ):
            with self.subTest(message=message):
                with self.assertRaisesRegex(ValueError, message):
                    fixture()
