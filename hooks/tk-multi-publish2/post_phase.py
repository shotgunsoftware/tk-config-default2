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
    """
    This hook defines methods that are executed after each phase of a publish: validation, publish, and finalization.
    Each method receives the PublishTree tree instance being used by the publisher,
    giving full control to further curate the publish tree including the publish items and the tasks attached to them.
    See the PublishTree documentation for additional details on how to traverse the tree and manipulate it.
    """

    def post_publish(self, publish_tree):
        """
        This method is executed after the publish pass has completed for each
        item in the tree, before the finalize pass.

        A :ref:`publish-api-tree` instance representing the items that were
        published is supplied as an argument. The tree can be traversed in this
        method to inspect the items and process them collectively.

        To glean information about the publish state of particular items, you
        can iterate over the items in the tree and introspect their
        :py:attr:`~.api.PublishItem.properties` dictionary. This requires
        customizing your publish plugins to populate any specific publish
        information that you want to process collectively here.

        .. warning:: You will not be able to use the item's
            :py:attr:`~.api.PublishItem.local_properties` in this hook since
            :py:attr:`~.api.PublishItem.local_properties` are only accessible
            during the execution of a publish plugin.

        :param publish_tree: The :ref:`publish-api-tree` instance representing
            the items to be published.
        """

        # ------------------------------------------------------------------------
        # Manage background publishing process
        # ------------------------------------------------------------------------

        monitor_data = {
            "items": [],
            "session_name": publish_tree.root_item.properties.get("session_name", ""),
        }

        current_engine = sgtk.platform.current_engine()
        bg_publish_app = current_engine.apps.get("tk-multi-bg-publish")

        bg_processing = publish_tree.root_item.properties.get("bg_processing")
        in_bg_process = publish_tree.root_item.properties.get("in_bg_process")

        # we only want to run the actions if we're going to publish in background but we're not already in the
        # background publishing process
        if not bg_processing or in_bg_process:
            return

        # modify the publish tree in order to add a new property/setting on the fly in order to give
        # the item/task a unique identifier
        # this will be very useful to track the tasks progress on the monitor side
        # we can't rely on names here as some items/tasks can have the same name
        # at the same time, start to build the monitor tree
        for item in publish_tree:

            item_uuid = str(uuid.uuid4())
            item_data = {
                "name": item.name,
                "uuid": item_uuid,
                "status": bg_publish_app.constants.WAITING_TO_START,
                "tasks": [],
                "is_parent_root": item.parent.is_root,
            }

            for task in item.tasks:
                if task.active:

                    # as we can't create a PublishSetting object using the Publish API, convert the task to a dict then
                    # add the new setting to finally reset the task from the dict
                    uuid_setting = {
                        "name": "Task UUID",
                        "type": "str",
                        "default_value": None,
                        "description": "UUID of the current task",
                        "value": str(uuid.uuid4()),
                    }
                    dummy_task_dict = task.to_dict()
                    dummy_task_dict["settings"]["Task UUID"] = uuid_setting
                    dummy_task = task.from_dict(dummy_task_dict, None)
                    task.settings["Task UUID"] = dummy_task.settings["Task UUID"]

                    item_data["tasks"].append(
                        {
                            "name": task.name,
                            "uuid": uuid_setting["value"],
                            "status": bg_publish_app.constants.WAITING_TO_START,
                        }
                    )

            if item_data["tasks"]:
                item.properties.uuid = item_uuid
                monitor_data["items"].append(item_data)

        # get the path to the folder where all the files used by the background publishing process will be stored
        root_folder_path = os.path.join(
            bg_publish_app.cache_location, current_engine.name
        )
        if not os.path.exists(root_folder_path):
            os.makedirs(root_folder_path)
        tmp_folder_path = tempfile.mkdtemp(dir=root_folder_path)

        # build the path to these files
        self.__TREE_FILE_PATH = os.path.join(tmp_folder_path, "publish_tree.yml")
        monitor_file_path = os.path.join(tmp_folder_path, "monitor.yml")

        # finally, save the publish tree and the monitor data to the files
        publish_tree.save_file(self.__TREE_FILE_PATH)
        with open(monitor_file_path, "w+") as fp:
            yaml.safe_dump(monitor_data, fp)

        self.logger.info(
            "Background Publish files have been saved on disk.",
            extra={"action_show_folder": {"path": tmp_folder_path}},
        )

        # ------------------------------------------------------------------------

    def post_finalize(self, publish_tree):
        """
        This method is executed after the finalize pass has completed for each
        item in the tree.

        A :ref:`publish-api-tree` instance representing the items that were
        published and finalized is supplied as an argument. The tree can be
        traversed in this method to inspect the items and process them
        collectively.

        To glean information about the finalize state of particular items, you
        can iterate over the items in the tree and introspect their
        :py:attr:`~.api.PublishItem.properties` dictionary. This requires
        customizing your publish plugins to populate any specific finalize
        information that you want to process collectively here.

        .. warning:: You will not be able to use the item's
            :py:attr:`~.api.PublishItem.local_properties` in this hook since
            :py:attr:`~.api.PublishItem.local_properties` are only accessible
            during the execution of a publish plugin.

        :param publish_tree: The :ref:`publish-api-tree` instance representing
            the items to be published.
        """

        bg_processing = publish_tree.root_item.properties.get("bg_processing")
        in_bg_process = publish_tree.root_item.properties.get("in_bg_process")

        # we only want to run the actions if we're going to publish in background mode but we're not already in the
        # background publishing process
        if bg_processing and not in_bg_process:
            current_engine = sgtk.platform.current_engine()
            bg_publish_app = current_engine.apps.get("tk-multi-bg-publish")
            # launch the background publishing process and show the monitor app
            bg_publish_app.launch_publish_process(self.__TREE_FILE_PATH)
            bg_publish_app.create_panel()
