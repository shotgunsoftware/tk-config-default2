# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import copy
import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk
from sgtk.util import filesystem

# DD imports
import dd.runtime.api
dd.runtime.api.load('wam')
from wam.core import Workflow
from wam.datatypes.element import Element

dd.runtime.api.load('modelpublish')
from modelpublish.lib.introspection import findModelRootNodes
# TODO: replace with find_model_root_nodes from modelpublish-8.7.0+

# for validate workflow
dd.runtime.api.load('indiapipeline')

HookBaseClass = sgtk.get_hook_baseclass()

# TODO: move this to a config?
validation_action_ret_value = {
    "MultipleShapes": False,
    "DrawingOverride": False,
    "DuplicateNames": False,
    "CheckAssetName": False,
    "CheckGeoNames": False,
    "CleanNamespace": False,
    "ReferenceCheck": False,
    "DeleteColorSets": False,
    "CleanUpScene": False,
}

class MayaPublishSessionModelPlugin(HookBaseClass):
    """
    Inherits from MayaPublishSessionPlugin
    """
    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.
        Additional check for maya scene using validations from modelpublish.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """
        # create list of elements from maya nodes to collect results about
        workflow_data = {"elements": []}
        # TODO: replace with find_model_root_nodes from modelpublish-8.7.0+
        toplevel_objects = findModelRootNodes()
        valid_node_name = item.context.entity['name'].lower()

        # validate only assetname.lower() object
        if valid_node_name not in toplevel_objects:
            if not cmds.objExists("|{}".format(valid_node_name)):
                self.logger.error(
                    "Top-level object with name `{}` not found".format(valid_node_name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Objects",
                            "tooltip": "Show found top-level objects",
                            "text": "Toplevel objects found: {}".format(toplevel_objects)
                        }
                    }
                    )
            else:
                self.logger.error(
                    "Top-level object with name `{}` not valid".format(valid_node_name),
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error",
                            "tooltip": "Show error details",
                            "text": "Object may not have an lod transform as child. "
                                    "Please check terminal for details."
                        }
                    }
                )
            return False

        # assume all children are lod nodes (they should be, if hierarchy is correct)
        for child in cmds.listRelatives(valid_node_name, children=True):
            elem_dict = {
                "name": valid_node_name,
                "selection_node": valid_node_name,
                "lod": child
            }
            workflow_data["elements"].append(Element(**elem_dict))

        workflow = Workflow.loadFromFile("indiapipeline/model_validate.wam", search_contexts=True)
        return_data = workflow.run(workflow_data)
        wam_exception = return_data['wam_exit_reason']

        if wam_exception is not None:
            # something wrong with workflow execution or user clicked cancel
            self.logger.error("Error in modelpublish validations: {}".format(wam_exception.__class__.__name__),
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Error",
                                      "tooltip": "Show stacktrace from wam",
                                      "text": return_data['wam_exit_stack'] +
                                              "\nCheck terminal/logs for more details."
                                  }
                              }
                              )
            return False

        for element in return_data['elements']:
            for check, result in element.metadata["modelCleanupChecks"].items():
                if not result:
                    # if return value is not given, assume it should be a warning
                    # and don't block the publish
                    if not validation_action_ret_value.get(check, True):
                        self.logger.error("Failed modelpublish validation: {}".format(check))
                        return False
                    else:
                        self.logger.warning("Failed modelpublish validation: {}".format(check))

        return super(MayaPublishSessionModelPlugin, self).validate(task_settings, item)

    def publish_files(self, task_settings, item, publish_path):
        """
        This method publishes (copies) the item's path property to the publish location.
        For session override this to do cleanup and save to publish location instead,
        then discard the changes done during cleanup from the workfile so that they are
        not preserved while versioning up.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :param publish_path: The output path to publish files to
        """

        path = copy.deepcopy(item.properties.get("path"))
        if not path:
            raise KeyError("Base class implementation of publish_files() method requires a 'path' property.")

        # Save to publish path
        self.cleanup_file(item)
        self._save_session(publish_path, item.properties.get("publish_version"), item)

        # Determine if we should seal the copied files or not
        seal_files = item.properties.get("seal_files", False)
        if seal_files:
            filesystem.seal_file(publish_path)

        # Reopen work file and reset item property path, context
        cmds.file(new=True, force=True)
        cmds.file(path, open=True, force=True)

        item.properties.path = path
        self.parent.engine.change_context(item.context)

    def cleanup_file(self, item):
        # delete any item in outliner not named "assetname"
        valid_node_name = item.context.entity['name'].lower()
        toplevel_objects = cmds.ls(assemblies=True)
        toplevel_objects.remove(valid_node_name)

        self.logger.debug("Attempting to delete: {}".format(toplevel_objects))
        cmds.delete(toplevel_objects)
