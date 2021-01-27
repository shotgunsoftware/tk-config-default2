# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import enum
import os

RULES_DATA_FOLDER = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "rules", "data")
)


@enum.unique
class TokensRule(enum.Enum):
    """Define which production rules to use when tokenizing a screenplay

    Available:
        - DEFAULT: the default one, that works with a majority of scripts
        - BLANK_LINE_NOT_DELIMITER: same logic as DEFAULT, except that the blanklines do not
            indicate the end of a dialog
    """

    DEFAULT = os.path.join(RULES_DATA_FOLDER, "default.txt")

    BLANK_LINE_NOT_DELIMITER = os.path.join(
        RULES_DATA_FOLDER, "blank_line_not_delimiter.txt"
    )

    def __str__(self) -> str:
        return self.value
