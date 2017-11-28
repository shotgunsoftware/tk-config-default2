# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import shutil
import sgtk

# DD
from sgtk import dd_jstools_utils

HookClass = sgtk.get_hook_baseclass()

class CopyFile(HookClass):
    """
    Hook called when a file needs to be copied
    """

    def execute(self, source_path, target_path, **kwargs):
        """
        Main hook entry point

        :param source_path: String
                            Source file path to copy

        :param target_path: String
                            Target file path to copy to

        """

        # create the folder if it doesn't exist
        dirname = os.path.dirname(target_path)
        if not os.path.isdir(dirname):
            old_umask = os.umask(0)
            # os.makedirs(dirname, 0777)
            # USE JSTOOLS INSTEAD
            dd_jstools_utils.makedir_with_jstools(dirname)
            os.umask(old_umask)

        shutil.copy(source_path, target_path)
