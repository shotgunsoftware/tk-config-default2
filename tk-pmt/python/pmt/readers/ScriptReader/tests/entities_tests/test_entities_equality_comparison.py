import unittest

from readers.ScriptReader.entities import *

from .pmt_entity_test_case import PMTEntityTestCase


class PMTEntityTestCaseTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.pmt_entity_test_case = PMTEntityTestCase()

    def test_getAssertEqualityFunc_returns_assertPMTEntityEqual(self):
        assertion_func = self.pmt_entity_test_case._getAssertEqualityFunc(
            Asset("", ""), Asset("", "")
        )
        self.assertEqual(
            assertion_func.__name__,
            PMTEntityTestCase.assertPMTEntityEqual.__name__,
        )

        assertion_func = self.pmt_entity_test_case._getAssertEqualityFunc(
            Sequence(""), Sequence("")
        )
        self.assertEqual(
            assertion_func.__name__,
            PMTEntityTestCase.assertPMTEntityEqual.__name__,
        )

        assertion_func = self.pmt_entity_test_case._getAssertEqualityFunc(
            Project(""), Project("")
        )
        self.assertEqual(
            assertion_func.__name__,
            PMTEntityTestCase.assertPMTEntityEqual.__name__,
        )

    def test_assertPMTEntityEqual_calls_TestCase_fail_with_PMTEntitiesDiscrepancies_report_result_as_msg(
        self,
    ):

        proj_a = Project("Project")
        seq1_a = Sequence("s001")
        seq2_a = Sequence("s002")
        proj_a.add_children([seq1_a, seq2_a])
        alice_a = Asset("Alice", "Character")
        bob_a = Asset("Bob", "Character")
        seq1_a.add_children([alice_a, bob_a])

        proj_b = Project("Project")
        seq1_b = Sequence("s001")
        proj_b.add_child(seq1_b)
        alice_b = Asset("Alice", "Character")
        seq1_b.add_child(alice_b)

        expected_exp_msg = """Missing in right Project:
- Asset(Bob -- Character)
- Sequence(s002)
Differing Children:
- Sequence(s001) in left Project contains:
    - Asset(Alice -- Character)
    - Asset(Bob -- Character)
  while Sequence(s001) in right Project contains:
    - Asset(Alice -- Character)
 : Project(Project) is not equal to Project(Project)"""

        with self.assertRaises(
            self.pmt_entity_test_case.failureException
        ) as exp_ctx:
            self.pmt_entity_test_case.assertPMTEntityEqual(proj_a, proj_b)

        self.assertEqual(str(exp_ctx.exception), expected_exp_msg)


if __name__ == "__main__":
    unittest.main()
