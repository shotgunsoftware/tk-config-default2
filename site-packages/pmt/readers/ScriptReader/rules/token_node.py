# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

from __future__ import annotations

from collections import Counter
from typing import Dict, Union

from ..tokens import *

TABS = 4


class TokenNode:
    """A `TokenNode` stores a `Token`, and it can have other TokenNodes as children.
    When parsing a script, we start from the root node (the only one with
    `self.token == None`). Then we look into its children to find the next matching Token,
    and we repeat this process until the end of the script.
    A graph made of TokenNodes is, finally, the definition of the parsing rules
    used to parse a script. It does not need to store any state, just to represent
    the "parsing flow".

    This class is made to contain circular references. That's why magic __hash__ does
    not operate on children (otherwise infinite recurstion), it only compares
    the token and name. Hence the parsing rules text files can contain only one
    node of the same Token class. If no name is provided to a TokenNode in __init__,
    it takes the name of the token class. So if several tokens of the same type
    must be included in a parser parsing rules file, they must be given different
    unique names.
    """

    @classmethod
    def from_txt(cls, file_path: str) -> TokenNode:
        """Reads a parsing rules text file to generate the `TokenNode` graph
            of these rules.

        :param file_path: parsing rules text file path
        """
        with open(file_path, "r", encoding="utf-8") as graph_file:
            lines = graph_file.read().splitlines()

        root = cls._parse_graph_txt_line(lines[0])
        all_nodes = {root}
        all_nodes_hashes = {hash(root)}

        current_tab_lvl = TABS
        current_parent = root
        sublevel_found = True
        while True:
            node = None
            for line in lines[1:]:
                if (
                    line.startswith(" " * current_tab_lvl)
                    and line[current_tab_lvl] != " "
                ):
                    node = cls._parse_graph_txt_line(line)

                    if not hash(node) in all_nodes_hashes:
                        all_nodes.add(node)
                        all_nodes_hashes.add(hash(node))
                        current_parent.add_children([node])
                    else:
                        node = next(
                            nod
                            for nod in all_nodes
                            if nod.token == node.token and nod.name == node.name
                        )
                        current_parent.add_children([TokenNodeReference(node)])

                elif (
                    line.startswith(" " * (current_tab_lvl - TABS))
                    and line[current_tab_lvl - TABS] != " "
                ):
                    parent_copy = cls._parse_graph_txt_line(line)
                    current_parent = next(
                        node
                        for node in all_nodes
                        if node.token == parent_copy.token
                        and node.name == parent_copy.name
                    )

            # Nothing found, no more sub tab levels
            if not node:
                break
            current_tab_lvl += TABS

        return root

    @classmethod
    def _parse_graph_txt_line(cls, line: str) -> TokenNode:
        split_line = line.lstrip().split(", ")
        if len(split_line) == 1:
            return TokenNode(eval(split_line[0]))
        else:
            return TokenNode(eval(split_line[0]), eval(split_line[1]))

    def __init__(self, token: ScreenplayParserToken, name: str = None):
        self.token = token
        self.name = name or token.__class__.__name__
        self.children: List[Union[TokenNode, TokenNodeReference]] = []

    def __hash__(self) -> int:
        """We cannot hash self.children, or we would enter an infinite recursion loop.
        This __hash__ implementation is however useful for quick lookup, to know if
        a `TokenNode` with the same name and `Token` class already exists.
        """
        return hash(self.token) + hash(self.name)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TokenNode):
            return NotImplemented
        return (
            self.token == other.token
            and self.name == other.name
            and self.children == other.children
        )

    def __str__(self, tab: int = 0) -> str:
        node_str = f"{tab * ' '}{self.token}, {self.name}\n"
        for child in self.children:
            node_str += child.__str__(tab + 4)
        return node_str

    def add_children(
        self, children: List[Union[TokenNode, TokenNodeReference]]
    ) -> None:
        """Adds the passed `children` TokenNodes to `self.children`

        :param children: TokenNodes to as children nodes of `self`.
        """
        self.children.extend(children)


class TokenNodeReference:
    """When a `TokenNode` (unique `Token` and `name`) has already been included
    in the graph and it is referenced at another place in the parsing rules,
    a `TokenNodeReference` is added instead, avoiding infinite circular references.

    To behave like a normal `TokenNode`, the property methods `token`, `children`
    and `name` returns the referent `token`, `name` and `children` attributes.
    """

    def __init__(self, token_node_to_ref: TokenNode):
        self.ref = token_node_to_ref

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TokenNodeReference):
            return NotImplemented
        return hash(self.ref) == hash(other.ref)

    def __hash__(self) -> int:
        return hash("reference") + hash(self.ref)

    def __str__(self, tab: int = 0) -> str:
        return f"{tab * ' '}Ref to {self.ref.token} {self.ref.name}\n"

    @property
    def token(self) -> ScreenplayParserToken:
        return self.ref.token

    @property
    def name(self) -> str:
        return self.ref.name

    @property
    def children(self) -> List:
        return self.ref.children
