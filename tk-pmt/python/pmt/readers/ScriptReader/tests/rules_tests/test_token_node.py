import os
import unittest

from readers.ScriptReader.rules import TokenNode, TokenNodeReference
from readers.ScriptReader.tokens import *


class TokenNodeTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        screenplay_parser_tests_dir = os.path.dirname(__file__)

        cls.token_references_test = os.path.join(
            screenplay_parser_tests_dir,
            "..",
            "data",
            "token_references_test.txt",
        )

        cls.token_test_yaml_graph = os.path.join(
            screenplay_parser_tests_dir, "..", "data", "token_test_graph.txt"
        )

    def test_eq(self):

        # None, "Start"
        #   SceneHeading
        #       BlankLine, "Start BlankLine"
        #   Discardable

        start1 = TokenNode(None, "Start")
        start2 = TokenNode(None, "Start")
        self.assertEqual(start1, start2)

        scene_heading1 = TokenNode(SceneHeading)
        scene_heading2 = TokenNode(SceneHeading)
        self.assertEqual(scene_heading1, scene_heading2)

        start_blank_line1 = TokenNode(BlankLine, "Start BlankLine")
        start_blank_line2 = TokenNode(BlankLine, "Start BlankLine")
        self.assertEqual(start_blank_line1, start_blank_line2)

        discardable = TokenNode(Discardable)
        start1.add_children([scene_heading1, discardable])
        scene_heading1.add_children([start_blank_line1])
        start2.add_children([scene_heading2, discardable])
        scene_heading2.add_children([start_blank_line2])
        self.assertEqual(start1, start2)

    def test_hash(self):
        blank_line = TokenNode(BlankLine)
        blank_line2 = TokenNode(BlankLine)

        self.assertEqual(hash(blank_line), hash(blank_line2))

        l = [blank_line]
        self.assertTrue(blank_line2 in l)

    def test_circular_references_stored_as_token_references(self):

        # None, "Start"
        #   BlankLine
        #       ShotInstruction
        #   ShotInstruction
        #       BlankLine

        exptected_root = TokenNode(None, "Start")
        blank_line = TokenNode(BlankLine)
        shot_instruction = TokenNode(ShotInstruction)
        exptected_root.add_children([blank_line, shot_instruction])
        blank_line.add_children([TokenNodeReference(shot_instruction)])
        shot_instruction.add_children([TokenNodeReference(blank_line)])

        root = TokenNode.from_txt(self.token_references_test)

        self.assertEqual(
            root.children[0].children[0], TokenNodeReference(shot_instruction)
        )
        self.assertNotEqual(
            root.children[0].children[0], TokenNodeReference(blank_line)
        )
        self.assertEqual(
            root.children[1].children[0], TokenNodeReference(blank_line)
        )
        self.assertNotEqual(
            root.children[1].children[0], TokenNodeReference(shot_instruction)
        )

    def test_eq_with_circular_references(self):

        # None, "Start"
        #   BlankLine
        #       ShotInstruction
        #   ShotInstruction
        #       BlankLine

        root1 = TokenNode(None, "Start")
        blank_line1 = TokenNode(BlankLine)
        shot_instruction1 = TokenNode(ShotInstruction)
        root1.add_children([blank_line1, shot_instruction1])
        blank_line1.add_children([TokenNodeReference(shot_instruction1)])
        shot_instruction1.add_children([TokenNodeReference(blank_line1)])

        root2 = TokenNode(None, "Start")
        blank_line2 = TokenNode(BlankLine)
        shot_instruction2 = TokenNode(ShotInstruction)
        root2.add_children([blank_line2, shot_instruction2])
        blank_line2.add_children([TokenNodeReference(shot_instruction2)])
        shot_instruction2.add_children([TokenNodeReference(blank_line2)])

        self.assertEqual(root1, root2)

    def test_from_txt(self):

        start = TokenNode(None, "Start")
        start_blank_line = TokenNode(BlankLine, "Start BlankLine")
        start_shot_instruction = TokenNode(
            ShotInstruction, "Start ShotInstruction"
        )
        scene_heading = TokenNode(SceneHeading)
        discardable = TokenNode(Discardable)

        start.add_children(
            [
                start_blank_line,
                start_shot_instruction,
                scene_heading,
                discardable,
            ]
        )
        start_blank_line.add_children(
            [
                TokenNodeReference(start_blank_line),
                TokenNodeReference(start_shot_instruction),
                TokenNodeReference(scene_heading),
                TokenNodeReference(discardable),
            ]
        )
        start_shot_instruction.add_children(
            [
                TokenNodeReference(scene_heading),
                TokenNodeReference(start_blank_line),
            ]
        )

        character = TokenNode(Character)
        action = TokenNode(Action)
        scene_shot_instruction = TokenNode(
            ShotInstruction, "Scene ShotInstruction"
        )
        scene_blank_line = TokenNode(BlankLine, "Scene BlankLine")

        scene_heading.add_children(
            [character, scene_shot_instruction, scene_blank_line, action]
        )

        discardable.add_children(
            [
                TokenNodeReference(start_blank_line),
                TokenNodeReference(start_shot_instruction),
                TokenNodeReference(scene_heading),
                TokenNodeReference(discardable),
            ]
        )

        parenthetical = TokenNode(Parenthetical)
        dialog = TokenNode(Dialog)
        character_blank_line = TokenNode(BlankLine, "Character BlankLine")
        character.add_children([parenthetical, dialog, character_blank_line])

        action.add_children(
            [
                TokenNodeReference(character),
                TokenNodeReference(scene_heading),
                TokenNodeReference(scene_shot_instruction),
                TokenNodeReference(scene_blank_line),
                TokenNodeReference(action),
            ]
        )

        scene_shot_instruction.add_children(
            [
                TokenNodeReference(character),
                TokenNodeReference(scene_heading),
                TokenNodeReference(scene_blank_line),
                TokenNodeReference(action),
            ]
        )

        scene_blank_line.add_children(
            [
                TokenNodeReference(scene_heading),
                TokenNodeReference(character),
                TokenNodeReference(scene_shot_instruction),
                TokenNodeReference(scene_blank_line),
                TokenNodeReference(action),
            ]
        )

        parenthetical.add_children(
            [
                TokenNodeReference(dialog),
                TokenNodeReference(character_blank_line),
            ]
        )

        dialog.add_children(
            [
                TokenNodeReference(scene_heading),
                TokenNodeReference(character),
                TokenNodeReference(scene_shot_instruction),
                TokenNodeReference(parenthetical),
                TokenNodeReference(character_blank_line),
                TokenNodeReference(dialog),
            ]
        )

        character_blank_line.add_children(
            [
                TokenNodeReference(scene_heading),
                TokenNodeReference(scene_shot_instruction),
                TokenNodeReference(character),
                TokenNodeReference(character_blank_line),
                TokenNodeReference(action),
            ]
        )

        self.assertEqual(TokenNode.from_txt(self.token_test_yaml_graph), start)

    def test_token_node_ref_token_property(self):

        action = TokenNode(Action)
        action.add_children([TokenNode(BlankLine)])
        ref_action = TokenNodeReference(action)

        self.assertEqual(id(action.token), id(ref_action.token))
        self.assertEqual(id(action.children[0]), id(ref_action.children[0]))
