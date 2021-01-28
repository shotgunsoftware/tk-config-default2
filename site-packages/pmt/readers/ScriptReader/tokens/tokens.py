# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import List, Optional

from .. import config

CHARACTER_NAME_WORDS_LIMIT = 6
# Some lines that should be considered action lines are written with only uppercase characters.
# To avoid that, we set a limit to the number of words a character name can contain.
# The limit should be high enough so that elements like "GROUP OF ANGRY PROTESTERS" can be matched


class ScreenplayParserToken(ABC):
    @classmethod
    @abstractmethod
    def tokenize(cls, line: str) -> Optional[ScreenplayParserToken]:
        raise NotImplementedError

    @abstractmethod
    def __eq__(self, other: object) -> bool:
        if not isinstance(other, self.__class__):
            return NotImplemented
        return True

    @abstractmethod
    def __repr__(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def __add__(
        self, other: ScreenplayParserToken
    ) -> Optional[ScreenplayParserToken]:
        if not isinstance(other, self.__class__):
            raise TypeError("Cannot add two tokens of different types")
        return None


class ShotInstruction(ScreenplayParserToken):
    """A ShotInstruction is a transition. Examples:
    FADE IN:
    CUT TO:
    ...
    """

    SHOT_INSTRUCTION_RE = re.compile(r"^(?P<instruction>[A-Z ]+):$")
    # This regex will match anything that is a mix of uppercase characters and whitespaces, if it ends with a colon

    @classmethod
    def tokenize(cls, line: str) -> Optional[ShotInstruction]:
        match = cls.SHOT_INSTRUCTION_RE.match(line)
        if match:
            return ShotInstruction(match.group("instruction"))
        return None

    __slots__ = "instruction"

    def __init__(self, instruction: str):
        self.instruction = instruction

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            # for static type checking with mypy
            # we could also use `# type: ignore [attr-defined]`
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return self.instruction == other.instruction
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.instruction})"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        super().__add__(other)
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
            )
        return ShotInstruction(self.instruction + "\n" + other.instruction)


class SceneHeading(ScreenplayParserToken):
    """A SceneHeading has a set element (where the action occurs) and, almost always, a lighting scenario.
    It could be:
    "INT. GUARD HOUSE - DAY"
    """

    SCENE_HEADING_RE = re.compile(
        #                                v hyphen, en dash & em dash
        "(?P<location>^(FLASHBACK\s+(?:-|–|—)\s+)?(INT|EXT|INT\.?\/EXT)\..+?)"
        "(?:(?:-|–|—)"
        "(?P<lighting>[A-Z .]+)([A-Z() ]+)?)?$"
    )
    # To match, scene heading must be uppercase, starts with "INT" or "EXT" or "INT/EXT" and have at least two parts separated by an hyphen
    # It may start with or ends with  "FLASHBACK".
    # Matches:
    # EXT. COURTHOUSE - DEWY MORNING
    # INT. JAIL CELL - NOON
    # EXT. DOCKS - NIGHT
    # INT.    KITCHEN - MORNING. (extraneous whitespaces and ends with a dot)
    # EXT.    JOHN'S HOUSE - DAY. (`'` single quote)
    # INT./EXT.    JOHN'S CAR - SEAHAVEN.    DAY.
    # INT. HARLAN THROMBEY'S STUDY - NIGHT - FLASHBACK -> will be matched, but the lighting element will be FLASHBACK instead of NIGHT
    # FLASHBACK – EXT. TRAIN TRACKS – DAY
    # EXT. TRAIN TRACKS - DAY (FLASHBACK)
    # INT. HOSPITAL - DAY – BACK TO PRESENT DAY
    # INT. HOSPITAL - DAY (BACK TO PRESENT DAY)
    # INT. COURTHOUSE (sometimes, there is no lighting scenario)

    @classmethod
    def tokenize(cls, line: str) -> Optional[SceneHeading]:
        matches = cls.SCENE_HEADING_RE.match(line)
        if matches:
            return SceneHeading(
                matches.group("location"), matches.group("lighting") or ""
            )
        return None

    __slots__ = ("location", "lighting_scenario")

    def __init__(self, location: str, lighting_scenario: str):
        self.location = " ".join(
            location.split()
        )  # removes any extraneous whitespace, like strip but also inside the str
        self.lighting_scenario = " ".join(lighting_scenario.split())

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return (
                self.location == other.location
                and self.lighting_scenario == other.lighting_scenario
            )
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.location} - {self.lighting_scenario})"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        raise TypeError(f"{self.__class__.__name__} cannot be added")


class Action(ScreenplayParserToken):
    """Action lines are generic lines that describe what's happening in the scene. It could be:
    "Arthur takes a deep breath, and just smiles."
    There is no regex to match against: Action must be placed at the last position of the parsing order.
    It is the default value if nothing else matches.
    """

    @classmethod
    def tokenize(cls, line: str) -> Optional[Action]:
        return Action(line)

    __slots__ = "content"

    def __init__(self, content: str):
        self.content = " ".join(content.split())

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return self.content == other.content
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.content})"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        super().__add__(other)
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
            )
        return Action(self.content + " " + other.content)


class BlankLine(ScreenplayParserToken):
    """If the screenplays's parsed line is empty, it will be a `BlankLine`.
    BlankLines are useful to provide current context information. For instance:
    '''
    SOPHIE (OS)
    Wait!!

    He puts his foot out with some panache to stop the closing
    door-- He's a romantic at heart. Ding.
    '''
    Thanks to the blank line after "Wait!!", we know we exit the character's dialogue context.
    """

    @classmethod
    def tokenize(cls, line: str) -> Optional[BlankLine]:
        if not line.strip():
            return BlankLine()
        return None

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return True
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        raise TypeError(f"{self.__class__.__name__} cannot be added")


class Discardable(ScreenplayParserToken):
    """A default token, used when nothing else match. It is only used when the parser is looking for
    the start of the screenplay, i.e. the first `SceneHeading`.
    We can generally find the screenplay's title, writers' names and other content before the start of the screenplay.
    `Discardable` is just used for those elements.
    """

    @classmethod
    def tokenize(cls, line: str) -> Optional[Discardable]:
        # Objects are empty, we are not interested by the content of what is discarded
        return Discardable()

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return True
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}()"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        raise TypeError(f"{self.__class__.__name__} cannot be added")


class Character(ScreenplayParserToken):
    """A character name with uppercase characters alone on a line means that the following lines
     will be a dialogue, maybe with some parenthetical:
    '''
    YOUNG PENNY
    I'm just glad I got to know him.
    '''
    A character name can also be found in an Action line. It is uppercase if it it the first time
    we're introduced to the character:
    '''
    HARLAN THROMBEY himself. 85 years old. Slung across a
    white leather day bed.
    '''
    """

    CHARACTER_RE = re.compile(
        "^(?P<name>[A-Z.]{2,}[\.\-\–\— ]*?(?=[A-Z])[A-Z'\d&\-\–\— ]+(?![a-z]))"
        "( *?\([A-Za-z\.]+\))?"
        "( *?(\((cont'd|CONT'D)\)))?$"
    )
    # Matches a Character name. The name may sometimes be followed by an extension, an indication
    #    about the character's dialog
    # Extension is enclosed inside parentheses. It can be: (V.O.) = voice over; (O.C.) = off camera;
    #    (O.S.) = off screen, but not limited to that. (PHONE) or (TV) can also be matched
    # Sometimes, (CONT'D) is added at the end of the line, to indicate this dialogue is a direct
    #    continuation of a previous dialogue from the same character
    # Matches:
    # CROWD (simple char name)
    # PRISON GUARD (compound char name)
    # ANN-LOUISE  (compound name with an hyphen)
    # MERYL (O.S.) (simple name with extension)
    # PEDRO (o.s.) (extension can also be lowercase)
    # JAMY BURR(O.C.) (compound name with extension, no whitespace)
    # VOICE (TV)
    # DR. JOSEPH (title and name)
    # SOMEONE'S VOICE (possesive)
    # KENDEL (CONT'D)
    #
    # Also matches with numbered characters, like:
    # COP 1
    # COP 2
    #
    # To avoid considering single uppercase letter as a character (a sentence starting with an "A"),
    # compound names must have at least 2 letters in their first part. However, it will match if
    # another part than the first one contains only one uppercase letter. Some screenplays also
    # contain action lines uppercase only when highlighting a description. For instance:
    # A TALL MAN -> won't match
    # GUARD A -> will match

    CONTAINS_CHARACTER_RE = re.compile(
        "(?P<name>[A-Z.]{2,}[\.\-\–\— ]*?(?=[A-Z])[A-Z' ]+(?![a-z]))"
    )
    # Same as `CHARACTER_RE`, except it looks for the pattern inside a string (the string does not need to start with the pattern)
    # Also, it does not look for a possible extension after the name
    # (those extension can only be found when the character name marks the start of a dialog)

    @classmethod
    def tokenize(cls, line: str) -> Optional[Character]:
        match = cls.CHARACTER_RE.match(line)
        if match:
            content = match.group("name").strip()
            if not len(content.split()) > CHARACTER_NAME_WORDS_LIMIT:
                return cls._post_process(content)
        return None

    @classmethod
    def _post_process(cls, content: str) -> Character:
        if (
            config.MULTIPLE_CHARACTERS_SPEAKING
            == config.MultipleCharactersSpeaking.KEEP_ALL
        ):
            return Character(content)
        elif (
            config.MULTIPLE_CHARACTERS_SPEAKING
            == config.MultipleCharactersSpeaking.KEEP_FIRST_CHAR
        ):
            return Character(content.split("&")[0].rstrip())
        else:
            raise ValueError(
                f"MultipleCharactersSpeaking.{str(config.MULTIPLE_CHARACTERS_SPEAKING)} is not a valid config option."
            )

    @classmethod
    def find_characters(cls, line: str) -> List[Character]:
        """Returns all parts of `line` which match `CONTAINS_CHARACTER_RE` as `Character`"""
        matches = cls.CONTAINS_CHARACTER_RE.findall(line)
        return [Character(match.strip()) for match in matches]

    __slots__ = "name"

    def __init__(self, name: str):
        self.name = name

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return self.name == other.name
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        raise TypeError(f"{self.__class__.__name__} cannot be added")


class Parenthetical(ScreenplayParserToken):
    """Parentheticals occur after a character name and before a dialogue, or during a dialogue, to provide a description:
    '''
    GARY
    (interrupting)
    They didn't talk to me.
    ...
    RANDALL
    Oh, okay. Well, good for you.
    (beat)
    Listen, I don't know if you heard,
    ...
    MAUREEN
    (anxious; she does not
    want to be discovered)    <-- can be on several lines
    What are you doing here?
    '''
    """

    PARENTHETICAL_RE = re.compile("^\((?P<indication>.+?)\)$", re.DOTALL)
    # Captures all characters enclosed inside parentheses

    @classmethod
    def tokenize(cls, line: str) -> Optional[Parenthetical]:
        match = cls.PARENTHETICAL_RE.match(line)
        if match:
            return Parenthetical(" ".join(match.group("indication").split()))
        return None

    __slots__ = "indication"

    def __init__(self, indication: str):
        self.indication = indication

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return self.indication == other.indication
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.indication})"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        super().__add__(other)
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
            )
        return Parenthetical(self.indication + " " + other.indication)


class Dialog(ScreenplayParserToken):
    """A dialogue can only be found after a character name (and maybe a parenthetical). It ends with a blank line:
    '''
    GARY
    Hey Art, I heard what happened--
    I'm sorry man.

    '''
    Like `Action`, this is a default token.
    """

    @classmethod
    def tokenize(cls, line: str) -> Optional[Dialog]:
        return Dialog(line)

    __slots__ = "content"

    def __init__(self, content: str):
        self.content = " ".join(content.split())

    def __eq__(self, other: object) -> bool:
        if super().__eq__(other):
            if not isinstance(other, self.__class__):
                raise TypeError(
                    f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
                )
            return self.content == other.content
        return False

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.content})"

    def __add__(self, other: ScreenplayParserToken) -> ScreenplayParserToken:
        super().__add__(other)
        if not isinstance(other, self.__class__):
            raise TypeError(
                f"Cannot compare a {self.__class__.__name__} and a {other.__class__.__name__}"
            )
        return Dialog(self.content + " " + other.content)
