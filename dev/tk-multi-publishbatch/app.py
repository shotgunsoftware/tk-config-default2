# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import subprocess
import sys

import sgtk


class PublishBatchApp(sgtk.platform.Application):
    """"""

    def init_app(self):
        """
        Called as the application is being initialized
        """

        tk_multi_publishbatch = self.import_module("tk_multi_publishbatch")

        cb = lambda tree_file=None: tk_multi_publishbatch.show_dialog(self, tree_file)
        self.engine.register_command(
            "Batch Publish Report...", cb, {"short_name": "batch_publish"}
        )
