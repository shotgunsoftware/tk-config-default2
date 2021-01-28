import unittest

from readers.ScriptReader.entities import *
from readers.ScriptReader.entities_discrepancies import *


class PMTEntitiesDiscrepanciesTest(unittest.TestCase):
    def _create_test_entities(self):
        return (
            Project("Project"),
            Sequence("s001"),
            Sequence("s002"),
            Asset("Alice", "character"),
            Asset("Bob", "character"),
        )

    def test__eq__(self):
        proj_a, seq1_a, seq2_a, alice_a, bob_a = self._create_test_entities()
        proj_a.add_children([seq1_a, seq2_a])
        seq1_a.add_children([bob_a, alice_a])
        seq2_a.add_child(bob_a)

        proj_b, seq1_b, seq2_b, alice_b, bob_b = self._create_test_entities()
        proj_b.add_children([seq1_b, seq2_b])
        seq1_b.add_children([bob_b, alice_b])
        seq2_b.add_children([bob_b, alice_b])

        discrepancy_1 = PMTEntitiesDiscrepancies(
            differing_children=[(seq2_a, seq2_b)],
        )
        discrepancy_2 = PMTEntitiesDiscrepancies(
            differing_children=[(seq2_a, seq2_b)],
        )
        self.assertEqual(discrepancy_1, discrepancy_2)

        discrepancy_3 = PMTEntitiesDiscrepancies(
            left_missing=[alice_b],
            right_missing=[bob_a],
            differing_children=[(seq2_a, seq2_b)],
        )
        discrepancy_4 = PMTEntitiesDiscrepancies(
            left_missing=[alice_b],
            right_missing=[bob_a],
            differing_children=[(seq2_a, seq2_b)],
        )
        self.assertEqual(discrepancy_3, discrepancy_4)

        discrepancy_5 = PMTEntitiesDiscrepancies(
            left_missing=[alice_b],
            right_missing=[bob_a],
            differing_children=[(seq2_a, seq2_b)],
        )
        discrepancy_6 = PMTEntitiesDiscrepancies(
            left_missing=[alice_b],
            right_missing=[alice_b, bob_a],
            differing_children=[(seq2_a, seq2_b)],
        )
        self.assertNotEqual(discrepancy_5, discrepancy_6)

    def test_analyze_differing_1(self):
        proj_a, seq1_a, seq2_a, alice_a, bob_a = self._create_test_entities()
        proj_a.add_children([seq1_a, seq2_a])
        seq1_a.add_children([bob_a, alice_a])
        seq2_a.add_child(bob_a)

        proj_b, seq1_b, seq2_b, alice_b, bob_b = self._create_test_entities()
        proj_b.add_children([seq1_b, seq2_b])
        seq1_b.add_children([bob_b, alice_b])
        seq2_b.add_children([bob_b, alice_b])

        expected_discrepancy = PMTEntitiesDiscrepancies(
            differing_children=[(seq2_a, seq2_b)],
        )
        res = PMTEntitiesDiscrepancies.analyze(proj_a, proj_b)
        self.assertEqual(
            PMTEntitiesDiscrepancies.analyze(proj_a, proj_b),
            expected_discrepancy,
        )

    def test_analyze_differing_2(self):
        proj_a, seq1_a, seq2_a, alice_a, bob_a = self._create_test_entities()
        proj_a.add_children([seq1_a, seq2_a])
        seq1_a.add_children([bob_a, alice_a])
        seq2_a.add_children([bob_a, alice_a])

        proj_b, seq1_b, seq2_b, alice_b, bob_b = self._create_test_entities()
        proj_b.add_children([seq1_b, seq2_b])
        seq1_b.add_children([bob_b, alice_b])
        seq2_b.add_child(bob_b)

        expected_discrepancy = PMTEntitiesDiscrepancies(
            differing_children=[(seq2_a, seq2_b)],
        )

        self.assertEqual(
            PMTEntitiesDiscrepancies.analyze(proj_a, proj_b),
            expected_discrepancy,
        )

    def test_analyze_missing_left(self):
        proj_a, seq1_a, _, _, _ = self._create_test_entities()
        proj_a.add_child(seq1_a)

        proj_b, seq1_b, seq2_b, _, _ = self._create_test_entities()
        proj_b = Project("Project")
        seq1_b = Sequence("s001")
        seq2_b = Sequence("s002")
        proj_b.add_children([seq1_b, seq2_b])

        expected_discrepancy = PMTEntitiesDiscrepancies(left_missing=[seq2_b])

        self.assertEqual(
            PMTEntitiesDiscrepancies.analyze(proj_a, proj_b),
            expected_discrepancy,
        )

    def test_analyze_missing_right(self):
        proj_a, seq1_a, seq2_a, _, _ = self._create_test_entities()
        proj_a.add_children([seq1_a, seq2_a])

        proj_b, seq1_b, _, _, _ = self._create_test_entities()
        proj_b.add_child(seq1_b)

        expected_discrepancy = PMTEntitiesDiscrepancies(right_missing=[seq2_a])

        self.assertEqual(
            PMTEntitiesDiscrepancies.analyze(proj_a, proj_b),
            expected_discrepancy,
        )

    def test_analyze(self):
        proj_a, seq1_a, seq2_a, alice_a, bob_a = self._create_test_entities()
        proj_a.add_children([seq1_a, seq2_a])
        charlie_a = Asset("Charlie", "character")
        seq1_a.add_children([bob_a, alice_a])
        seq2_a.add_children([bob_a, alice_a, charlie_a])

        proj_b, seq1_b, seq2_b, alice_b, bob_b = self._create_test_entities()
        seq3_b = Sequence("s003")
        proj_b.add_children([seq1_b, seq2_b, seq3_b])
        seq1_b.add_children([bob_b, alice_b])
        seq2_b.add_child(bob_b)

        expected_discrepancy = PMTEntitiesDiscrepancies(
            differing_children=[(seq2_a, seq2_b)],
            left_missing=[seq3_b],
            right_missing=[charlie_a],
        )
        self.assertEqual(
            PMTEntitiesDiscrepancies.analyze(proj_a, proj_b),
            expected_discrepancy,
        )

    def test_report(self):
        proj_a, seq1_a, seq2_a, alice_a, bob_a = self._create_test_entities()
        proj_a.add_children([seq1_a, seq2_a])
        charlie_a = Asset("Charlie", "character")
        seq1_a.add_children([bob_a, alice_a])
        seq2_a.add_children([bob_a, alice_a, charlie_a])

        proj_b, seq1_b, seq2_b, alice_b, bob_b = self._create_test_entities()
        seq3_b = Sequence("s003")
        proj_b.add_children([seq1_b, seq2_b, seq3_b])
        seq1_b.add_children([bob_b, alice_b])
        seq2_b.add_child(bob_b)

        discrepancies = PMTEntitiesDiscrepancies(
            differing_children=[(seq2_a, seq2_b)],
            left_missing=[seq3_b],
            right_missing=[charlie_a],
        )

        expected_report = """Missing in left Project:
- Sequence(s003)
Missing in right Project:
- Asset(Charlie -- character)
Differing Children:
- Sequence(s002) in left Project contains:
    - Asset(Alice -- character)
    - Asset(Bob -- character)
    - Asset(Charlie -- character)
  while Sequence(s002) in right Project contains:
    - Asset(Bob -- character)
"""

        self.assertEqual(discrepancies.report(), expected_report)


if __name__ == "__main__":
    unittest.main()
