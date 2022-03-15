# Copyright (c) 2022 Autodesk, Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.

import copy
import os
import tempfile
import uuid

import sgtk
from tank_vendor import yaml

HookBaseClass = sgtk.get_hook_baseclass()


class PostPhase(HookBaseClass):
    def post_publish(self, tree):
        """"""

        monitor_data = {"items": []}

        current_engine = sgtk.platform.current_engine()
        batch_app = current_engine.apps.get("tk-multi-batchprocess")

        batch_processing = tree.root_item.properties.get("batch_processing")
        in_batch_process = tree.root_item.properties.get("in_batch_process")

        if not batch_processing or in_batch_process:
            return

        tmp_folder = os.path.join(tempfile.gettempdir(), "sgtk_batch_publish")
        if not os.path.exists(tmp_folder):
            os.makedirs(tmp_folder)
        fp = tempfile.NamedTemporaryFile(
            prefix="publish_tree", suffix=".yml", dir=tmp_folder, delete=False
        )
        fp.close()
        self.__TREE_FILE_PATH = fp.name
        monitor_file_path = self.__TREE_FILE_PATH.replace(".yml", "_monitor.yml")

        # we need to modify the publish tree in order to add extra settings and properties
        for item in tree:

            item_uuid = str(uuid.uuid4())
            item_data = {
                "name": item.name,
                "uuid": item_uuid,
                "status": batch_app.constants.WAITING_TO_START,
                "tasks": [],
            }

            for task in item.tasks:

                if task.active:

                    # get the first setting we can find to copy it in order to create new settings
                    first_setting = next(iter(task.settings.values()))

                    uuid_settings = copy.deepcopy(first_setting)
                    uuid_settings.default_value = None
                    uuid_settings.description = "UUID of the current task"
                    uuid_settings.name = "Task UUID"
                    uuid_settings.type = "str"
                    uuid_settings.value = str(uuid.uuid4())
                    task.settings["Task UUID"] = uuid_settings

                    item_data["tasks"].append(
                        {
                            "name": task.name,
                            "uuid": uuid_settings.value,
                            "status": batch_app.constants.WAITING_TO_START,
                        }
                    )

            if item_data["tasks"]:
                item.properties.uuid = item_uuid
                monitor_data["items"].append(item_data)

        tree.save_file(self.__TREE_FILE_PATH)
        with open(monitor_file_path, "w+") as fp:
            yaml.safe_dump(monitor_data, fp)

        self.logger.info(
            "Publish tree have been saved on disk.",
            extra={"action_show_folder": {"path": tmp_folder}},
        )

    def post_finalize(self, tree):
        """"""

        batch_processing = tree.root_item.properties.get("batch_processing")
        in_batch_process = tree.root_item.properties.get("in_batch_process")

        if batch_processing and not in_batch_process:
            current_engine = sgtk.platform.current_engine()
            batch_app = current_engine.apps.get("tk-multi-batchprocess")
            batch_app.launch_publish_process(self.__TREE_FILE_PATH)
            batch_app.create_panel()
