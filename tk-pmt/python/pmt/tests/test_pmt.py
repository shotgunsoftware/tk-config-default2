# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import os
import sys
import unittest
from unittest.mock import patch, MagicMock

from pmt import pmt
import readers
import writers


class PMTTest(unittest.TestCase):

    def test_translate_from_screenplay_to_ue(self):
        """pmt.translate does not return anything, so we test that it calls the relevant Readers and Writers,
        with appropriate parameters, depending on the passed arguments.
        """
        # Use the ScriptReader sample script
        screenplay_path = os.path.split(__file__)[0]
        screenplay_path = os.path.join(
            screenplay_path,
            "..",
            "readers",
            "ScriptReader",
            "tests",
            "data",
            "Sample Screenplay.txt",
        )

        # patch() works by (temporarily) changing the object that a name points
        # to with another one. There can be many names pointing to any individual
        # object, so for patching to work you must ensure that you patch the name
        # used by the system under test.
        # The basic principle is that you patch where an object is looked up,
        # which is not necessarily the same place as where it is defined.
        # (https://docs.python.org/3/library/unittest.mock.html#where-to-patch)
        # => Patching "readers.ScriptReader.ScreenplayParser" is ineffective in this case
        with patch.dict("readers._reader_classes", {"Script": MagicMock()}):
            with patch.dict("writers._writer_classes", {"Unreal": MagicMock()}):
                pmt.translate(
                    reader="screenplay",
                    reader_args={"input": screenplay_path},
                    writer="unreal",
                    writer_args={}, # no input, implicit (the readers output)
                )
                readers._reader_classes["Script"].assert_called_once_with(screenplay_path)
                readers._reader_classes["Script"].return_value.to_pmt_project.assert_called_once()
                writers._writer_classes["Unreal"].assert_called_once_with(
                    readers._reader_classes["Script"].return_value.to_pmt_project.return_value
                )
