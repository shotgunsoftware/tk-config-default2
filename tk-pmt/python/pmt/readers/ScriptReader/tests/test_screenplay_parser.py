import json
import os
import sys
import unittest

from readers.ScriptReader.entities import *
from readers.ScriptReader.screenplay_parser import ScreenplayParser, config
from readers.ScriptReader.tokens import *

from readers.ScriptReader.tests.utils import contain_same_values
from readers.ScriptReader.tests.entities_tests.pmt_entity_test_case import (
    PMTEntityTestCase,
)


class ScreenplayParserTest(PMTEntityTestCase):
    @classmethod
    def setUpClass(cls):
        screenplay_parser_tests_dir = os.path.dirname(__file__)
        cls.screenplay_txt_file = os.path.join(
            screenplay_parser_tests_dir, "data", "Sample Screenplay.txt"
        )
        cls.screenplay_json_file = os.path.join(
            screenplay_parser_tests_dir, "data", "Sample Screenplay.json"
        )
        cls.uppercase_test_screenplay = os.path.join(
            screenplay_parser_tests_dir,
            "data",
            "Uppercase Characters in Action Lines Screenplay.txt",
        )
        cls.screenplay_all_caps_dialog = os.path.join(
            screenplay_parser_tests_dir, "data", "all_caps_dialog.txt"
        )
        cls.screenplay_blanklines = os.path.join(
            screenplay_parser_tests_dir,
            "data",
            "Sample Screenplay BlankLines.txt",
        )

    def test_tokenize_screenplay(self):

        tokenized_sample_screenplay = [
            ShotInstruction("FADE IN"),
            SceneHeading("EXT. COURTHOUSE", "DEWY MORNING"),
            Action(
                "We are introduced to our first location: a small courthouse buried in the middle of the city."
            ),
            Action(
                "We slowly enter the building through a window. Inside, a stout JUDGE slams their gavel as a rowdy CROWD watches."
            ),
            SceneHeading("INT. COURTHOUSE", "DEWY MORNING"),
            Character("JUDGE"),
            Dialog(
                "Order in the court! I will not have the trouble of this husting bustle!"
            ),
            Action(
                "The CROWD quiets down as we slowly make our way to the front of the room, where the DEFENDANT sits idle."
            ),
            Action("A sleazy DEFENSE ATTORNEY comes forward."),
            Character("DEFENSE ATTORNEY"),
            Dialog("Now now, there is no need for this upset."),
            Character("DEFENDANT"),
            Parenthetical("Very angry"),
            Dialog(
                "They can be as upset as they want, this trial is complete malarkey! An absolute sham!"
            ),
            Action(
                "The defense attorney squirms a little at the temperament of their client."
            ),
            Character("DEFENDANT"),
            Dialog(
                "I waive my right to an attorney, I don't need this sleaze representing me anymore!"
            ),
            SceneHeading("INT. JAIL CELL", "NOON"),
            Action("The DEFENDANT sits idle in their cell."),
            Character("DEFENDANT"),
            Parenthetical("Muttering"),
            Dialog("What a crock of rubbish..."),
            Character("PRISON GUARD"),
            Parenthetical("Disdainful"),
            Dialog("Hey, you've got company."),
            Action(
                "The cell door opens and THE FIXER walks in. A little gaunt but sharply dressed, they mean business."
            ),
            Character("THE FIXER"),
            Dialog("Heard you ditched your last lawyer?"),
            Character("DEFENDANT"),
            Parenthetical("Put on the spot"),
            Dialog("He was useless anyways."),
            Character("THE FIXER"),
            Dialog("Eh. The boss won't like that at all."),
            SceneHeading("EXT. DOCKS", "NIGHT"),
            Action("THE FIXER dumps a carpet in the bay."),
        ]

        parser = ScreenplayParser(self.screenplay_txt_file)

        self.assertEqual(parser.tokenize(), tokenized_sample_screenplay)

    def test_parsing_with_uppercase_dialog(self):

        tokenized_sample_screenplay = [
            SceneHeading("INT. HOUSE", "MORNING"),
            Character("MARK"),
            Dialog("IF YOU'RE TIRED OF BREAKFAST BUT NOT HUNGRY FOR LUNCH,"),
            Dialog("MICROWAVE YOURSELF A HEALTHY BOWL OF BRUNCH!"),
        ]

        parser = ScreenplayParser(self.screenplay_all_caps_dialog)

        self.assertEqual(parser.tokenize(), tokenized_sample_screenplay)

    def test_replace_false_characters_tokens(self):

        tokens = [
            Character("UPPERCASE BUT NOT A CHARACTER"),
            Action("bla bla"),
            Character("DR TRUE CHARACTER"),
            Dialog("small talk"),
            Character("PROF ALSO TRUE CHARACTER"),
            Parenthetical("pedantic"),
            Dialog("I am a test"),
            Character("CHARACTER NEEDS TO SPEAK"),
        ]

        expected_result = [
            ShotInstruction("UPPERCASE BUT NOT A CHARACTER"),
            Action("bla bla"),
            Character("DR TRUE CHARACTER"),
            Dialog("small talk"),
            Character("PROF ALSO TRUE CHARACTER"),
            Parenthetical("pedantic"),
            Dialog("I am a test"),
            ShotInstruction("CHARACTER NEEDS TO SPEAK"),
        ]

        self.assertEqual(
            ScreenplayParser.replace_false_characters_tokens(tokens),
            expected_result,
        )

    def test_merge_adjacent_tokens(self):

        tokens = [
            Action("As Arthur approaches his building, he sees AN AMBULANCE"),
            Action(
                "PARKED in front. Lights flashing. Hit with a sense of dread"
            ),
            Action("he runs toward the building--"),
            SceneHeading("EXT. STREET, APARTMENT BUILDING", "NIGHT"),
            Action(
                "FROM ABOVE, Arthur pushing through the crowd, rushes to his"
            ),
            Action("mother's side--"),
            Character("ARTHUR"),
            Parenthetical("following as they wheel"),
            Parenthetical("her, leaning over"),
            Parenthetical("stretcher"),
            Dialog("Mom? Mom, what happened?"),
            Dialog("What happened to her?"),
        ]

        expected_result = [
            Action(
                "As Arthur approaches his building, he sees AN AMBULANCE PARKED in front. Lights flashing. Hit with a sense of dread he runs toward the building--"
            ),
            SceneHeading("EXT. STREET, APARTMENT BUILDING", "NIGHT"),
            Action(
                "FROM ABOVE, Arthur pushing through the crowd, rushes to his mother's side--"
            ),
            Character("ARTHUR"),
            Parenthetical(
                "following as they wheel her, leaning over stretcher"
            ),
            Dialog("Mom? Mom, what happened? What happened to her?"),
        ]

        res = ScreenplayParser.merge_adjacent_tokens(tokens)
        self.assertEqual(res, expected_result)

    def test_to_pmt_project(self):

        parser = ScreenplayParser(self.screenplay_txt_file)

        crowd = Asset("CROWD", "undefined")
        judge = Asset("JUDGE", "character")
        defendant = Asset("DEFENDANT", "character")
        attorney = Asset("DEFENSE ATTORNEY", "character")
        guard = Asset("PRISON GUARD", "character")
        fixer = Asset("THE FIXER", "character")

        project = Project("Sample Screenplay")

        seq0 = Sequence("0010")
        seq1 = Sequence("0020")
        seq2 = Sequence("0030")
        seq3 = Sequence("0040")

        project.add_child(seq0)
        project.add_child(seq1)
        project.add_child(seq2)
        project.add_child(seq3)

        seq0.add_child(crowd)
        seq0.add_child(judge)
        seq1.add_child(judge)
        seq1.add_child(crowd)
        seq1.add_child(defendant)
        seq1.add_child(attorney)
        seq2.add_child(defendant)
        seq2.add_child(guard)
        seq2.add_child(fixer)
        seq3.add_child(fixer)

        self.assertEqual(
            parser.to_pmt_project(keep_undefined_assets=True), project
        )

    def test_only_tokenize_as_characters_speaking_ones(self):

        parser = ScreenplayParser(self.uppercase_test_screenplay)

        thomas = Asset("THOMAS", "character")
        ray = Asset("RAY", "character")
        children = Asset("CHILDREN", "undefined")
        ball = Asset("BALL", "undefined")
        castle = Asset("SAND CASTLE", "undefined")

        project = Project(
            os.path.splitext(os.path.basename(self.uppercase_test_screenplay))[
                0
            ]
        )

        seq0 = Sequence("0010")
        seq1 = Sequence("0020")
        seq2 = Sequence("0030")

        project.add_child(seq0)
        project.add_child(seq1)
        project.add_child(seq2)

        seq0.add_child(thomas)
        seq0.add_child(children)
        seq0.add_child(ball)
        seq0.add_child(castle)
        seq1.add_child(ray)
        seq1.add_child(children)
        seq2.add_child(thomas)
        seq2.add_child(ray)

        self.assertEqual(
            parser.to_pmt_project(keep_undefined_assets=True), project
        )

    def test_blank_line_not_a_delimiter_rules(self):

        config.TOKEN_PARSING_RULES = config.TokensRule.BLANK_LINE_NOT_DELIMITER

        parser = ScreenplayParser(self.screenplay_blanklines)
        tokens = parser.tokenize()

        expected_tokens = [
            ShotInstruction("FADE IN"),
            SceneHeading("EXT. COURTHOUSE", "DEWY MORNING"),
            Action(
                "We are introduced to our first location: a small courthouse buried in the middle of the city."
            ),
            Action(
                "We slowly enter the building through a window. Inside, a stout JUDGE slams their gavel as a rowdy CROWD watches."
            ),
            SceneHeading("INT. COURTHOUSE", "DEWY MORNING"),
            Character("JUDGE"),
            Dialog(
                "Order in the court! I will not have the trouble of this husting bustle!"
            ),
            Action(
                "The CROWD quiets down as we slowly make our way to the front of the room, where the DEFENDANT sits idle."
            ),
            Action("A sleazy DEFENSE ATTORNEY comes forward."),
            Character("DEFENSE ATTORNEY"),
            Dialog("Now now, there is no need for this upset."),
            Character("DEFENDANT"),
            Parenthetical("Very angry"),
            Dialog(
                "They can be as upset as they want, this trial is complete malarkey! An absolute sham!"
            ),
            Action(
                "The defense attorney squirms a little at the temperament of their client."
            ),
            Character("DEFENDANT"),
            Dialog(
                "I waive my right to an attorney, I don't need this sleaze representing me anymore!"
            ),
            SceneHeading("INT. JAIL CELL", "NOON"),
            Action("The DEFENDANT sits idle in their cell."),
            Character("DEFENDANT"),
            Parenthetical("Muttering"),
            Dialog("What a crock of rubbish..."),
            Character("PRISON GUARD"),
            Parenthetical("Disdainful"),
            Dialog("Hey, you've got company."),
            Action(
                "The cell door opens and THE FIXER walks in. A little gaunt but sharply dressed, they mean business."
            ),
            Character("THE FIXER"),
            Dialog("Heard you ditched your last lawyer?"),
            Character("DEFENDANT"),
            Parenthetical("Put on the spot"),
            Dialog("He was useless anyways."),
            Character("THE FIXER"),
            Dialog("Eh. The boss won't like that at all."),
            SceneHeading("EXT. DOCKS", "NIGHT"),
            Action("THE FIXER dumps a carpet in the bay."),
        ]

        self.assertEqual(expected_tokens, tokens)

        config.TOKEN_PARSING_RULES = config.TokensRule.DEFAULT

    def test_to_json(self):

        with open(self.screenplay_json_file, "r") as f:
            screenplay_project_struct = json.load(f)

        parser = ScreenplayParser(self.screenplay_txt_file)
        parsed_project_struct = json.loads(parser.to_json(True))
        self.assertTrue(
            contain_same_values(
                parsed_project_struct, screenplay_project_struct
            )
        )


if __name__ == "__main__":
    unittest.main()
