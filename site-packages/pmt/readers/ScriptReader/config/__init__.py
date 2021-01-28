# ScriptReader. Copyright 2020 Imaginary Spaces. All Rights Reserved.

from .multiple_characters_speaking import MultipleCharactersSpeaking
from .tokens_rules import TokensRule

MULTIPLE_CHARACTERS_SPEAKING = MultipleCharactersSpeaking.KEEP_FIRST_CHAR

TOKEN_PARSING_RULES = TokensRule.DEFAULT

# Sequence Naming Convention:
INITIAL_SEQUENCE_NB = 1
SEQUENCE_NAME = "{seq_count:03}0"
