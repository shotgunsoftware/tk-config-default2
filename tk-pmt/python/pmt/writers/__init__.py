# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.
"""
NOTE: This module might be imported from Python 2.7 or Python 3.7
"""
# This initializes the pmt (e.g. logging, ...)
from .. import pmt

import os
import sys

# Make sure the UE plugin Python Content directory is in sys.path
python_content = os.path.split(__file__)[0]
python_content = os.path.join(
    python_content, "UnrealWriter", "Content", "Python"
)
python_content = os.path.normpath(python_content)
if python_content not in sys.path:
    sys.path.append(python_content)


from ue_writer import UEWriter


"""
In the future writers will be discovered by traversing the writers
directory and looking for Writer classes
"""
_writer_classes = {"Unreal": UEWriter}


def get_writer_classes():
    return _writer_classes


def get_writer_class(writer_name):
    return _writer_classes.get(writer_name, None)
