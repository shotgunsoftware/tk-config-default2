# -*- coding: utf-8 -*-

import operator
import unittest

import readers.ScriptReader.config
from readers.ScriptReader.tokens import *


class ScreenplayParserTokenTest(unittest.TestCase):
    def test_tokenize_scene_heading(self):

        scene_headings = [
            "INT. COURTHOUSE - DEWY MORNING",
            "EXT. COURTHOUSE - DEWY MORNING",
            "INT. JAIL CELL - NOON",
            "EXT. DOCKS - NIGHT",
            "INT.    KITCHEN - MORNING.",
            "EXT.    JOHN'S HOUSE - DAY.",
            "INT./EXT. THE VAN/JOEL'S APARTMENT BUILDING - DAY",
            "INT/EXT.    JOHN'S CAR - BEACH REFUGE.    DAY.",
            "INT. SECOND FLOOR LANDING - NIGHT OF PARTY",
            "INT. OMAR NORTHWOOD'S STUDY - NIGHT - FLASHBACK",
            "FLASHBACK – EXT. TRAIN TRACKS – DAY",
            "EXT. TRAIN TRACKS - DAY (FLASHBACK)",
            "INT. HOSPITAL - DAY – BACK TO PRESENT DAY",
            "INT. HOSPITAL - DAY (BACK TO PRESENT DAY)",
            "INT. COURTHOUSE",
        ]

        tokenized_scene_headings = [
            SceneHeading("INT. COURTHOUSE", "DEWY MORNING"),
            SceneHeading("EXT. COURTHOUSE", "DEWY MORNING"),
            SceneHeading("INT. JAIL CELL", "NOON"),
            SceneHeading("EXT. DOCKS", "NIGHT"),
            SceneHeading("INT. KITCHEN", "MORNING."),
            SceneHeading("EXT. JOHN'S HOUSE", "DAY."),
            SceneHeading("INT./EXT. THE VAN/JOEL'S APARTMENT BUILDING", "DAY"),
            SceneHeading("INT/EXT. JOHN'S CAR", "BEACH REFUGE. DAY."),
            SceneHeading("INT. SECOND FLOOR LANDING", "NIGHT OF PARTY"),
            SceneHeading("INT. OMAR NORTHWOOD'S STUDY - NIGHT", "FLASHBACK"),
            SceneHeading("FLASHBACK – EXT. TRAIN TRACKS", "DAY"),
            SceneHeading("EXT. TRAIN TRACKS", "DAY"),
            SceneHeading("INT. HOSPITAL - DAY", "BACK TO PRESENT DAY"),
            SceneHeading("INT. HOSPITAL", "DAY"),
            SceneHeading("INT. COURTHOUSE", ""),
        ]

        not_scene_headings = [
            "JUDGE",
            "(Very angry)",
            "We are introduced to our first location: a small courthouse buried in the middle of the city.",
            "THE FIXER dumps a carpet in the bay.",
            "INTO THE DENSENESS OF THE WOODS.",
        ]

        for i, scene_heading in enumerate(scene_headings):
            self.assertEqual(
                SceneHeading.tokenize(scene_heading),
                tokenized_scene_headings[i],
            )

        for scene_heading in not_scene_headings:
            self.assertIsNone(SceneHeading.tokenize(scene_heading))

    def test_tokenize_shot_instruction(self):

        shot_instructions = [
            "FADE IN:",
            "CUT OUT:",
            "DISSOLVE TO:",
            "BACK TO:",
            "CUT TO BLACK:",
        ]

        tokenized_shot_instructions = [
            ShotInstruction("FADE IN"),
            ShotInstruction("CUT OUT"),
            ShotInstruction("DISSOLVE TO"),
            ShotInstruction("BACK TO"),
            ShotInstruction("CUT TO BLACK"),
        ]

        not_shot_instructions = [
            "Heard you ditched your last lawyer?",
            "EXT. FIFTH AVENUE - DAY",
            "PRISONG GUARD",
            "From the Atlantic shore, the lush countryside extends for miles.",
            "A dark green van scoots down the highway:",
        ]

        for (i, shot_instruction) in enumerate(shot_instructions):
            self.assertEqual(
                ShotInstruction.tokenize(shot_instruction),
                tokenized_shot_instructions[i],
            )

        for not_shot_instruction in not_shot_instructions:
            self.assertIsNone(ShotInstruction.tokenize(not_shot_instruction))

    def test_tokenize_character(self):

        config.MULTIPLE_CHARACTERS_SPEAKING = (
            config.MultipleCharactersSpeaking.KEEP_ALL
        )

        characters = [
            "JUDGE",
            "CROWD",
            "PRISON GUARD",
            "CATHERINE (O.S.)",
            "FORREST  (V.O.)",
            "JAMY BURR(O.C.)",
            "MONIQUE (CONT'D)",
            "NAHUEL(cont'd)",
            "KENDEL (O.S.) (CONT'D)",
            "BUSTER (o.s.)",
            "SOMEONE'S VOICE (o.s.)",
            "S.S. OFFICER",
            "JOHN & SULLIVAN",
            "COP 1",
            "NERDY MAN-CHILD",
        ]

        tokenized_characters = [
            Character("JUDGE"),
            Character("CROWD"),
            Character("PRISON GUARD"),
            Character("CATHERINE"),
            Character("FORREST"),
            Character("JAMY BURR"),
            Character("MONIQUE"),
            Character("NAHUEL"),
            Character("KENDEL"),
            Character("BUSTER"),
            Character("SOMEONE'S VOICE"),
            Character("S.S. OFFICER"),
            Character("JOHN & SULLIVAN"),
            Character("COP 1"),
            Character("NERDY MAN-CHILD"),
        ]

        not_characters = [
            "I waive my right to an attorney, I don't need this sleaze representing me anymore!",
            "(Muttering)" "",
            "UPPERCASE LINES WITH TOO MUCH WORDS SHOULD NOT BE CONSIDERED CHARACTERS",
        ]

        for i, char in enumerate(characters):
            self.assertEqual(Character.tokenize(char), tokenized_characters[i])

        for not_char in not_characters:
            self.assertIsNone(Character.tokenize(not_char))

    def test_find_characters(self):

        strings_with_characters = [
            "A sleazy DEFENSE ATTORNEY comes forward.",
            "The cell door opens and THE FIXER walks in. A little gaunt but sharply dressed, they mean business.",
            "The CROWD quiets down as we slowly make our way to the front of the room, where the DEFENDANT sits idle.",
            "We slowly enter the building through a window. Inside, a stout JUDGE slams their gavel as a rowdy CROWD watches.",
            "We are in the darkness, looking into the LIGHT OF A CABIN WINDOW.",
        ]

        extracted_characters = [
            [Character("DEFENSE ATTORNEY")],
            [Character("THE FIXER")],
            [Character("CROWD"), Character("DEFENDANT")],
            [Character("JUDGE"), Character("CROWD")],
            [Character("LIGHT OF A CABIN WINDOW")],
        ]

        strings_without_characters = [
            "We are introduced to our first location: a small courthouse buried in the middle of the city.",
            "The defense attorney squirms a little at the temperament of their client.",
        ]

        for i, string in enumerate(strings_with_characters):
            self.assertEqual(
                Character.find_characters(string), extracted_characters[i]
            )

        for not_char in strings_without_characters:
            self.assertEqual(Character.find_characters(not_char), [])

    def test_tokenize_parenthetical(self):

        parentheticals = [
            "(Muttering)",
            "(Disdainful)",
            "(Put on the spot)",
            "(smug, TV smiles)",
            "(anxious; she does not\nwant to be discovered)",
        ]

        tokenized_parentheticals = [
            Parenthetical("Muttering"),
            Parenthetical("Disdainful"),
            Parenthetical("Put on the spot"),
            Parenthetical("smug, TV smiles"),
            Parenthetical("anxious; she does not want to be discovered"),
        ]

        not_parentheticals = [
            "PRISONG GUARD",
            "INT. JAIL CELL - NOON",
            "We are introduced to our first location: a small courthouse buried in the middle of the city.",
        ]

        for i, parenthetical in enumerate(parentheticals):
            self.assertEqual(
                Parenthetical.tokenize(parenthetical),
                tokenized_parentheticals[i],
            )

        for not_parenthetical in not_parentheticals:
            self.assertIsNone(Parenthetical.tokenize(not_parenthetical))

    def test_token_magic_add(self):

        self.assertEqual(Action("foo") + Action("bar"), Action("foo bar"))
        self.assertEqual(
            Parenthetical("muttering through") + Parenthetical("his coat"),
            Parenthetical("muttering through his coat"),
        )
        self.assertEqual(
            Dialog("I don't believe in anything. I just")
            + Dialog("thought it would be good for my")
            + Dialog("act."),
            Dialog(
                "I don't believe in anything. I just thought it would be good for my act."
            ),
        )
        self.assertEqual(
            ShotInstruction("CUT TO") + ShotInstruction("FADE IN"),
            ShotInstruction("CUT TO\nFADE IN"),
        )

        # cannot concat instances of different ScreenplayParserToken
        self.assertRaises(
            TypeError, operator.add, Action("foo"), Parenthetical("his coat")
        )
        self.assertRaises(
            TypeError,
            operator.add,
            Dialog("Hey!"),
            Action("Looking in the mirror"),
        )

        # Some classes of tokens cannot be concatenated
        self.assertRaises(
            TypeError,
            operator.add,
            SceneHeading("EXT. STREET, APARTMENT BUILDING", "NIGHT"),
            SceneHeading("INT. COURTHOUSE", "DEWY MORNING"),
        )
        self.assertRaises(
            TypeError, operator.add, Character("THE FIXER"), Character("JOHN")
        )

        # BlankLine and Discardable tokens are solely used to provide context information when parsing.
        # Since they are not added to the ScreenplayParser.tokenize result, there is no point to implement __add__ on them
        self.assertRaises(TypeError, operator.add, BlankLine(), BlankLine())
        self.assertRaises(TypeError, operator.add, Discardable(), Discardable())

    def test_tokenize_multiple_characters_speaking_at_same_time(self):

        config.MULTIPLE_CHARACTERS_SPEAKING = (
            config.MultipleCharactersSpeaking.KEEP_FIRST_CHAR
        )

        lines = [
            "JOE RED & MIKE BLUE",
            "MARIA-LUISA & JUAN-MANUEL",
            "JEAN & JACQUES",
        ]

        tokenized_characters = [
            Character("JOE RED"),
            Character("MARIA-LUISA"),
            Character("JEAN"),
        ]

        for i, line in enumerate(lines):
            self.assertEqual(Character.tokenize(line), tokenized_characters[i])

        config.MULTIPLE_CHARACTERS_SPEAKING = (
            config.MultipleCharactersSpeaking.KEEP_ALL
        )

        lines = [
            "JOE RED & MIKE BLUE",
            "MARIA-LUISA & JUAN-MANUEL",
            "JEAN & JACQUES",
        ]

        tokenized_characters = [
            Character("JOE RED & MIKE BLUE"),
            Character("MARIA-LUISA & JUAN-MANUEL"),
            Character("JEAN & JACQUES"),
        ]

        for i, line in enumerate(lines):
            self.assertEqual(Character.tokenize(line), tokenized_characters[i])


if __name__ == "__main__":
    unittest.main()
