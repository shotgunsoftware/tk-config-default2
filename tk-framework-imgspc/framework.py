# This file is based on templates provided and copyrighted by Autodesk, Inc.
# This file has been modified by Epic Games, Inc. and is subject to the license
# file included in this repository.

"""
Global ImgSpc Framework.
For the moment, just used to store global variables.
"""

import sgtk
import sys
import os


class ImgSpcFramework(sgtk.platform.Framework):


    def init_framework(self):
        self.log_debug("{}: Initializing {}...".format(self, self.__class__.__name__))

    def destroy_framework(self):
        self.log_debug("{}: Destroying {}...".format(self, self.__class__.__name__))
