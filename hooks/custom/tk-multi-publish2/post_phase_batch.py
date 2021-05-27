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
import tempfile

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class PostPhase(HookBaseClass):
    def post_publish(self, tree):
        """"""

        if self._is_batch_publish():
            return

        tmp_folder = tempfile.mkdtemp(prefix="sgtk_publish")
        self.__TREE_FILE_PATH = os.path.join(tmp_folder, "publish_tree.yml")

        tree.save_file(self.__TREE_FILE_PATH)

        self.logger.info(
            "Publishing context and state have been saved on disk.",
            extra={"action_show_folder": {"path": tmp_folder}},
        )

    def post_finalize(self, tree):
        """"""

        if self._is_batch_publish():
            return

        current_engine = sgtk.platform.current_engine()
        current_engine.commands["Batch Publish Report..."]["callback"](
            self.__TREE_FILE_PATH
        )
