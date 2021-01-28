# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

from __future__ import annotations

import json
import logging
import os
from collections import OrderedDict, deque
from enum import Enum
from functools import partial, reduce
from itertools import dropwhile, groupby
from typing import Any, Dict, Iterator, List, Union

from . import config
from .entities import Asset, PMTEntity, Project, Sequence
from .rules import TokenNode, TokenNodeReference
from .tokens import (
    Action,
    BlankLine,
    Character,
    Dialog,
    Discardable,
    Parenthetical,
    SceneHeading,
    ScreenplayParserToken,
    ShotInstruction,
)

_LOG = logging.getLogger(__name__)


class ScreenplayParser(object):
    """Parse a screenplay into a json structure to be read by PMT"""

    __slots__ = ("_state", "_file_path", "_seq_cnt")

    def __init__(self, file_path: str):
        self._file_path = file_path
        self._seq_cnt = config.INITIAL_SEQUENCE_NB

        _LOG.info(
            "Initialized ScreenplayParser with file_path={}\n".format(
                self._file_path
            )
        )

    def tokenize(self, debug: bool = False) -> List[ScreenplayParserToken]:
        """Process each line of `self._file_path` as a `ScreenplayParserToken`
        Uses the parsing rules set with `config.TOKEN_PARSING_RULES`.
        """
        current_token_node: Union[
            TokenNode, TokenNodeReference
        ] = TokenNode.from_txt(str(config.TOKEN_PARSING_RULES))
        _LOG.debug(f"Using tokens rules: {config.TOKEN_PARSING_RULES}")

        tokenize_res = []
        with open(self._file_path, "r", encoding="utf-8") as screenplay_file:

            for (line_number, line) in enumerate(
                screenplay_file.read().splitlines(), start=1
            ):
                line = line.lstrip()

                token = None
                for child in current_token_node.children:
                    token = child.token.tokenize(line)
                    if token is not None:
                        current_token_node = child
                        break
                if token is None:
                    raise RuntimeError(
                        f"Could not tokenize line #{line_number}, current token node: {current_token_node.token} {current_token_node.name}"
                    )

                # No need to store blank lines, they are only useful to get information on current context (state)
                if not type(token) in [BlankLine, Discardable]:
                    tokenize_res.append(token)

                _LOG.debug(
                    f"Tokenized line '{line}' at #{line_number} as a `{type(token).__name__}`"
                )

        return tokenize_res

    @staticmethod
    def merge_adjacent_tokens(
        tokens: List[ScreenplayParserToken],
    ) -> List[ScreenplayParserToken]:
        """Merge all adjacent tokens of the same type into one
        [Action('foo'), Action('bar'), Character("John")] -> [Action('foo bar'), Character("John")]
        This is useful when a character name is on several lines in the input document
        """
        grouped_tokens = [
            list(same_type_tokens)
            for _type, same_type_tokens in groupby(
                tokens, lambda token: type(token)
            )
        ]
        return list(map(partial(reduce, lambda tok1, tok2: tok1 + tok2), grouped_tokens))  # type: ignore[arg-type]

    @staticmethod
    def replace_false_characters_tokens(
        tokens: List[ScreenplayParserToken],
    ) -> List[ScreenplayParserToken]:
        """The Character token regex has a certain flexibility, so it may produce some false positives.
        This method goes over the `tokens` to make sure any Character token is followed by a Dialog or
        Parenthetical token. If not, the false Character token is replaced with a ShotInstruction token.

        NB: This method is required because the ScreenplayParser "state machine" used when parsing only
        takes into account the previous token, there is no look ahead notion. If more methods that post-
        process tokens to discard false positives are needed, we should instead update the parser state
        machine so that it includes a look-ahead mechanism.
        """
        for idx, token in enumerate(tokens):
            if isinstance(token, Character):
                if idx + 1 == len(tokens):
                    # The end, there can be no dialog after
                    tokens[idx] = ShotInstruction(token.name)
                elif isinstance(tokens[idx + 1], (Parenthetical, Dialog)):
                    # It is indeed a Character
                    continue
                else:
                    tokens[idx] = ShotInstruction(token.name)

        return tokens

    def to_pmt_project(self, keep_undefined_assets: bool = False) -> Project:
        """Convert the parsed screenplay into a PMT compatible Project
        :param keep_undefined_assets: If True, assets that were not categorized as characters are
            kept and their type is undefined. If False (default), discard them.
        """

        def get_seq_name() -> str:
            seq_name = config.SEQUENCE_NAME.format(seq_count=self._seq_cnt)
            self._seq_cnt += 1
            return seq_name

        _LOG.info("Generating tokens...")
        token_list = self.merge_adjacent_tokens(
            self.replace_false_characters_tokens(self.tokenize())
        )

        project = Project(
            os.path.splitext(os.path.basename(self._file_path))[0]
        )

        # The first element to consider is the first `SceneHeading` instance: the start of the first sequence
        token_iter = dropwhile(
            lambda tok: not isinstance(tok, SceneHeading), token_list
        )

        token_deque = deque(token_iter)
        if not token_deque:
            return project
        # removes first SceneHeading instance
        token_deque.popleft()

        current_seq = Sequence(get_seq_name())
        project.add_child(current_seq)
        character_names = set()

        _LOG.info("Parsing tokens...")
        while token_deque:
            token = token_deque.popleft()
            if isinstance(token, Character):
                current_seq.add_child(Asset(token.name, "character"))
                character_names.add(token.name)
            # A Character can be contained inside an Action.content,
            # if it is the first time the screenplay introduces the Character
            # The regex used by `Character.find_characters` could also match other elements
            # than character names, as long as they are also in uppercase. Visual effects,
            # sounds or props, if deemed important, are generally highlighted this way.
            elif isinstance(token, Action):
                chars = (
                    Character.find_characters(token.content) if not None else []
                )
                for char in chars:
                    current_seq.add_child(Asset(char.name, "character"))
            # Start of a new sequence
            elif isinstance(token, SceneHeading):
                current_seq = Sequence(get_seq_name())
                project.add_child(current_seq)
            else:
                continue

        _LOG.info("Parsing Character Assets...")

        # Now that the screenplay has been entirely parsed, we can check if any Asset is actually
        # a character, by looking into all found characters. Otherwise, we remove it as a character
        # and add it as an undefined asset
        sequences = [
            child for child in project.children if isinstance(child, Sequence)
        ]
        for seq in sequences:
            assets_to_remove = set(
                asset
                for asset in seq.assets
                if not asset.name in character_names
            )
            for to_remove in assets_to_remove:
                if keep_undefined_assets:
                    _LOG.warning(
                        f"Adding Asset {to_remove.name} with type 'undefined': this value won't be recognized by the PMT."
                    )
                    seq.add_child(Asset(to_remove.name, "undefined"))
                seq.assets.remove(to_remove)
                # If an undefined Asset is cast in several sequences, it will be children of each seq,
                # but of course it can only be found once in the project.children
                if to_remove in project.children:
                    project.children.remove(to_remove)

        return project

    def to_json(self, keep_undefined_assets: bool = False) -> str:
        """Export the screenplay as a json file compatible with PMT

        :param keep_undefined_assets: If True, assets that were not categorized as characters are
            kept and their type is undefined. If False (default), discard them.
        """
        return json.dumps(
            self.to_pmt_project(keep_undefined_assets).to_pmt_dict(), indent=2
        )
