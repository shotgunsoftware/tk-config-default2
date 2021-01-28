import sys
from readers.ScriptReader.tests.utils import contain_same_values

from readers.ScriptReader.entities import *
from .pmt_entity_test_case import PMTEntityTestCase


class EntityTest(PMTEntityTestCase):
    def test_eq(self):

        self.assertEqual(Sequence("S000"), Sequence("S000"))
        self.assertNotEqual(Sequence("S000"), Sequence("S001"))

        self.assertEqual(Asset("bob", "character"), Asset("bob", "character"))
        self.assertNotEqual(Asset("bob", "character"), Asset("bob", "prop"))

        seq1 = Sequence("S000")
        seq2 = Sequence("S000")
        seq1.assets.add(Asset("JOHN", "character"))
        self.assertNotEqual(seq1, seq2)

        seq2.assets.add(Asset("JOHN", "character"))
        self.assertEqual(seq1, seq2)

        proj1 = Project("Truman Show")
        proj2 = Project("Truman Show")
        self.assertEqual(proj1, proj2)

        proj1.add_child(seq1)
        self.assertNotEqual(proj1, proj2)

        proj2.add_child(seq2)
        self.assertEqual(proj1, proj2)

        seq1.assets.add(Asset("ERIK", "character"))
        self.assertNotEqual(proj1, proj2)

        proj3 = Project("Project")
        proj4 = Project("Project")

        seq01 = Sequence("S000")
        seq02 = Sequence("S000")

        chara1 = Asset("MANUEL", "character")
        chara2 = Asset("PAULINE", "character")

        seq01.assets.add(chara1)
        seq01.assets.add(chara2)

        seq02.assets.add(chara2)
        seq02.assets.add(chara1)

        proj3.add_child(seq01)
        proj4.add_child(seq02)
        # The two projects are equal, whatever the order the assets were added to the sequence
        self.assertEqual(proj3, proj4)

    def test_add_child_does_set_parent_attribute(self):

        project = Project("Project")
        seq = Sequence("Sequence")
        asset = Asset("TONIO", "character")

        project.add_child(seq)
        seq.add_child(asset)

        self.assertEqual(seq.parent, project)
        # Assets are always parented to Project
        self.assertEqual(asset.parent, project)

    def test_Sequence_add_asset(self):

        sequence = Sequence("S000")
        sequence._add_asset(Asset("JOHN", "character"))

        self.assertEqual(sequence.assets, {Asset("JOHN", "character")})

        # Asset are properly hashed to be unique in a set
        sequence._add_asset(Asset("JOHN", "character"))
        self.assertEqual(sequence.assets, {Asset("JOHN", "character")})

        sequence._add_asset(Asset("CATHERINE", "character"))

        self.assertEqual(
            sequence.assets,
            {Asset("JOHN", "character"), Asset("CATHERINE", "character")},
        )

        self.assertRaises(
            TypeError, sequence._add_asset, Project("The Truman Show")
        )

    def test_project_to_pmt_dict(self):

        project = Project("The Best Project")

        project_expected_dict = {
            "type": "Project",
            "name": "The Best Project",
            "children": [],
        }

        self.assertEqual(project.to_pmt_dict(), project_expected_dict)

    def test_sequence_to_pmt_dict(self):

        seq = Sequence("S000")

        sequence_expected_dict = {
            "type": "Sequence",
            "name": "S000",
            "assets": [],
            "children": [],
        }

        self.assertEqual(seq.to_pmt_dict(), sequence_expected_dict)

    def test_asset_to_pmt_dict(self):

        asset = Asset("JOHN", "character")

        asset_expected_dict = {
            "type": "Asset",
            "name": "JOHN",
            "asset_type": "character",
            "children": [],
        }

        self.assertEqual(asset.to_pmt_dict(), asset_expected_dict)

    def test_project_structure_to_pmt_dict(self):

        truman = Asset("JOHN", "character")
        meryl = Asset("CATHERINE", "character")
        spencer = Asset("ERIK", "character")

        seq1 = Sequence("S000")
        seq2 = Sequence("S001")

        project = Project("The Truman Show")
        project.add_child(seq1)
        project.add_child(seq2)

        seq1.add_child(truman)
        seq1.add_child(meryl)

        seq2.add_child(truman)
        seq2.add_child(meryl)
        seq2.add_child(spencer)

        project_expected_dict = {
            "type": "Project",
            "name": "The Truman Show",
            "children": [
                {
                    "type": "Asset",
                    "name": "JOHN",
                    "asset_type": "character",
                    "children": [],
                },
                {
                    "type": "Asset",
                    "name": "CATHERINE",
                    "asset_type": "character",
                    "children": [],
                },
                {
                    "type": "Sequence",
                    "name": "S000",
                    "assets": ["JOHN", "CATHERINE"],
                    "children": [],
                },
                {
                    "type": "Sequence",
                    "name": "S001",
                    "assets": ["JOHN", "CATHERINE", "ERIK"],
                    "children": [],
                },
                {
                    "type": "Asset",
                    "name": "ERIK",
                    "asset_type": "character",
                    "children": [],
                },
            ],
        }

        project_dict = project.to_pmt_dict()

        self.assertCountEqual(project_expected_dict, project_dict)
        self.assertTrue(
            contain_same_values(project_expected_dict, project_dict)
        )
