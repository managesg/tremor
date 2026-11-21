import json
import unittest
from unittest.mock import patch

from lab import r1_public_arithmetic_mutants as corpus


class PublicArithmeticMutantTests(unittest.TestCase):
    def test_public_cases_have_distinct_inputs_and_a_clean_null(self):
        taskset = corpus._taskset()
        clean = corpus.alloc.oracle_log(taskset)
        cases = corpus._cases(clean)
        self.assertEqual(len(cases), len({json.dumps(rows, sort_keys=True) for rows, _ in cases.values()}))
        result = corpus.evaluate()
        changed = {name for name, case in result["cases"].items() if case["changed"]}
        self.assertGreaterEqual(len(changed), 10)
        self.assertEqual(set(cases) - changed, {"reordered_distinct_work"})
        self.assertFalse(result["protected_n2"])

    def test_accepting_wrong_arithmetic_in_a_scorer_fails_the_corpus(self):
        original = corpus.alloc.score

        def accept_any_integer(log, taskset):
            log = [row | {"answer": 1} if row.get("task") == "sum-a" and type(row.get("answer")) is int
                   else row for row in log]
            return original(log, taskset)

        with patch.object(corpus.alloc, "score", accept_any_integer):
            with self.assertRaisesRegex(ValueError, "alloc disagrees"):
                corpus.evaluate()
