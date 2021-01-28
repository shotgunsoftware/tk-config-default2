# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import sys

if sys.version_info.major == 2:
    ModuleNotFoundError = ImportError

try:
    import unreal
except ModuleNotFoundError or ImportError as e:
    pass


def log(msg):
    unreal.log("UnrealWriter: {}".format(msg))
