# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.

# This initializes the pmt (e.g. logging, ...)
import pmt
from .ScriptReader import screenplay_parser

"""
In the future readers will be discovered by traversing the readers
directory and looking for Reader classes

NOTE: This module might be imported from Python 2.7 or Python 3.7
"""
_reader_classes = {"Script": screenplay_parser.ScreenplayParser}


def get_reader_classes():
    return _reader_classes


def get_reader_class(reader_name):
    return _reader_classes.get(reader_name, None)
