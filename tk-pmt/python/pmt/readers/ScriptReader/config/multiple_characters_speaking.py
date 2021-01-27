# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import enum


@enum.unique
class MultipleCharactersSpeaking(enum.Enum):
    """Define how multiple characters speaking at the same time will be parsed.

    Example:
    ```
    CHARACTER 1 & CHARACTER 2
    Bla bla bla
    ```
    If KEEP_FIRST_CHAR, a Character named 'CHARACTER 1' will be added.
    If KEEP_ALL, a Character named 'CHARACTER 1 & CHARACTER 2' will be added.
    """

    KEEP_FIRST_CHAR = enum.auto()

    KEEP_ALL = enum.auto()

    def __str__(self) -> str:
        return self.name.lower()
