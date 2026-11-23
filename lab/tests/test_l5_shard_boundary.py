import unittest

from lab import l5_shard_boundary as shard


class L5ShardBoundaryTests(unittest.TestCase):
    @staticmethod
    def response(fixture, worker, phase):
        key = (worker, phase)
        return {"items": [{"item": fixture.item_ids[key], "canary": fixture.canaries[key]}]}

    def test_four_and_eight_worker_clean_views_expose_exactly_the_current_owned_item(self):
        for size in (4, 8):
            fixture = shard.fixture(size)
            self.assertEqual(fixture.workers, tuple(f"a{index}" for index in range(size)))
            self.assertEqual(fixture.target, "a1")
            self.assertEqual(len(set(fixture.item_ids.values())), 2 * size)
            self.assertEqual(len(set(fixture.canaries.values())), 2 * size)
            for worker in fixture.workers:
                for phase in ("pre", "post"):
                    with self.subTest(size=size, worker=worker, phase=phase):
                        item = fixture.item_ids[(worker, phase)]
                        returned = shard.dispatch(fixture, worker, "environment:clean", phase, {"item": item})
                        self.assertEqual(returned, self.response(fixture, worker, phase))

    def test_disruption_removes_only_target_post_exposure_and_neutral_exposes_nothing(self):
        for size in (4, 8):
            fixture = shard.fixture(size)
            for worker in fixture.workers:
                for phase in ("pre", "post"):
                    with self.subTest(size=size, worker=worker, phase=phase):
                        request = {"item": fixture.item_ids[(worker, phase)]}
                        disrupted = shard.dispatch(fixture, worker, "environment:disrupted", phase, request)
                        target_withheld = worker == fixture.target and phase == "post"
                        self.assertEqual(disrupted, {"items": []} if target_withheld else
                                         self.response(fixture, worker, phase))
                        for condition in ("neutral:clean", "neutral:disrupted"):
                            self.assertEqual(shard.dispatch(fixture, worker, condition, phase, request), {"items": []})

    def test_wrong_item_unknown_bulk_and_forged_identity_have_identical_denials(self):
        for size in (4, 8):
            fixture = shard.fixture(size)
            worker, other = fixture.workers[:2]
            owned = fixture.item_ids[(worker, "pre")]
            theirs = fixture.item_ids[(other, "pre")]
            later = fixture.item_ids[(worker, "post")]
            requests = {
                "other worker": {"item": theirs},
                "wrong phase": {"item": later},
                "unknown item": {"item": "unknown-item"},
                "bulk selector": {"items": [owned, theirs]},
                "list as item": {"item": [owned, theirs]},
                "forged worker": {"worker": other, "item": theirs},
                "worker field alongside authorized item": {"worker": worker, "item": owned},
                "wildcard": {"item": "*"},
            }
            for label, request in requests.items():
                with self.subTest(size=size, denied_case=label):
                    result = shard.dispatch(fixture, worker, "environment:clean", "pre", request)
                    self.assertEqual(result, {"items": []})

    def test_invalid_host_selectors_are_rejected_as_configuration_errors(self):
        fixture = shard.fixture(4)
        owner = fixture.workers[0]
        request = {"item": fixture.item_ids[(owner, "pre")]}
        for selectors in (("outsider", "environment:clean", "pre"),
                          (owner, "unsupported:clean", "pre"),
                          (owner, "environment:clean", "unknown-phase")):
            with self.subTest(selectors=selectors), self.assertRaises(ValueError):
                shard.dispatch(fixture, *selectors, request)
