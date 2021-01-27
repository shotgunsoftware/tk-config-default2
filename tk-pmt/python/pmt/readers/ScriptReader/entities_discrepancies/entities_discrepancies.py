# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

from __future__ import (
    annotations,
)  # Need to import annotations from future to be able to type hint method return value with the type of enclosing class in Python 3.7

from collections import Counter
from typing import List, Set, Tuple

from readers.ScriptReader.entities import *


class PMTEntitiesDiscrepancies:
    """Useful to report the discrepancies between 2 PMT Projects.
    The class method `analyze` must be used to create a PMTEntitiesDiscrepancies instance.
    """

    @classmethod
    def analyze(
        cls, left_pmt_project: Project, right_pmt_project: Project
    ) -> PMTEntitiesDiscrepancies:
        """
        Build a `PMTEntitiesDiscrepancies` instance, checking the entities missing or with differing children.

        :param left_pmt_project: A PMT Project, the left operand of the equality comparison
        :param  right_pmt_project:  A PMT Project, the right operand of the equality comparison
        :returns: A `PMTEntitiesDiscrepancies` instance, with the missing and differing children
        """

        left_counter = Counter(left_pmt_project.children)
        right_counter = Counter(right_pmt_project.children)

        left_missing = right_counter - left_counter
        right_missing = left_counter - right_counter
        left_missing_set = set(left_missing.keys())
        right_missing_set = set(right_missing.keys())
        differing_children: List[Tuple[PMTEntity, PMTEntity]] = []

        to_remove_from_left_missing: Set[PMTEntity] = set()
        to_remove_from_right_missing: Set[PMTEntity] = set()
        # Are the entities truly missing, or the children differ?
        for left_miss_ent in left_missing_set:
            for right_miss_ent in right_missing_set:
                if (
                    type(left_miss_ent) == type(right_miss_ent)
                    and left_miss_ent.name == right_miss_ent.name
                ):
                    # Special case for Asset, the asset_type attribute must be identical
                    if isinstance(left_miss_ent, Asset) and isinstance(
                        right_miss_ent, Asset
                    ):
                        if (
                            left_miss_ent.asset_type
                            == right_miss_ent.asset_type
                        ):
                            to_remove_from_left_missing.add(left_miss_ent)
                            to_remove_from_right_missing.add(right_miss_ent)
                            # left_miss_ent is missing on the right side, and vice versa
                            differing_children.append(
                                (right_miss_ent, left_miss_ent)
                            )

                    else:
                        to_remove_from_left_missing.add(left_miss_ent)
                        to_remove_from_right_missing.add(right_miss_ent)
                        # The left entity is missing on the right side, and vice versa
                        differing_children.append(
                            (right_miss_ent, left_miss_ent)
                        )
        left_missing_set -= to_remove_from_left_missing
        right_missing_set -= to_remove_from_right_missing

        return cls(
            left_missing=list(left_missing_set),
            right_missing=list(right_missing_set),
            differing_children=differing_children,
        )

    def __init__(
        self,
        left_missing: List[PMTEntity] = None,
        right_missing: List[PMTEntity] = None,
        differing_children: List[Tuple[PMTEntity, PMTEntity]] = None,
    ):

        self.left_missing = left_missing or []
        self.right_missing = right_missing or []
        self.differing_children = differing_children or []

    def __eq__(self, other: object) -> bool:

        if not isinstance(other, PMTEntitiesDiscrepancies):
            return NotImplemented

        if (
            self.left_missing == other.left_missing
            and self.right_missing == other.right_missing
            and self.differing_children == other.differing_children
        ):
            return True

        return False

    def report(self) -> str:
        """
        Make a text report detailing the entities that are present in a PMT Project,
        but not in the other, and also the entities that are present in both Projects,
        but do not contain the same children. The two PMT Projects metnionned here are
        the ones passed to the `PMTEntitiesDiscrepancies.analyze` method.
        """
        report = ""
        if self.left_missing:
            report += "Missing in left Project:\n"
            report += "\n".join(
                [
                    "- " + str(left_missing)
                    for left_missing in sorted(
                        self.left_missing,
                        key=lambda ent: (str(type(ent)), ent.name),
                    )
                ]
            )
            report += "\n"
        if self.right_missing:
            report += "Missing in right Project:\n"
            report += "\n".join(
                [
                    "- " + str(right_missing)
                    for right_missing in sorted(
                        self.right_missing,
                        key=lambda ent: (str(type(ent)), ent.name),
                    )
                ]
            )
            report += "\n"
        if self.differing_children:
            report += "Differing Children:\n"
            for differing_pair in self.differing_children:
                if isinstance(differing_pair[0], Sequence) and isinstance(
                    differing_pair[1], Sequence
                ):
                    report += (
                        f"- {differing_pair[0]} in left Project contains:\n"
                    )
                    report += "\n".join(
                        [
                            "    - " + str(child)
                            for child in sorted(
                                differing_pair[0].assets,
                                key=lambda asset: asset.name,
                            )
                        ]
                    )
                    report += f"\n  while {differing_pair[1]} in right Project contains:\n"
                    report += "\n".join(
                        [
                            "    - " + str(child)
                            for child in sorted(
                                differing_pair[1].assets,
                                key=lambda asset: asset.name,
                            )
                        ]
                    )
                    report += "\n"

        return report
