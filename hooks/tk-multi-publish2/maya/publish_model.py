# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import maya.cmds as cmds
import maya.mel as mel
import sgtk
from sgtk.util.filesystem import ensure_folder_exists

# DD imports
import dd.runtime.api
dd.runtime.api.load('wam')
from wam.core import Workflow
from wam.datatypes.element import Element

dd.runtime.api.load('modelpublish')
from modelpublish.lib.introspection import findModelRootNodes

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

class MayaPublishFilesModelPlugin(HookBaseClass):
    """
    Inherits from MayaPublishFilesPlugin
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
        toplevel_objects = findModelRootNodes()
        # assume all children are lod nodes (they should be, if hierarchy is correct)
        for toplevel_object in toplevel_objects:
            for child in cmds.listRelatives(toplevel_object, children=True):
                elem_dict = {
                    "name": toplevel_object,
                    "selection_node": toplevel_object,
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
                                      "text": return_data['wam_exit_stack']
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

        return super(MayaPublishFilesModelPlugin, self).validate(task_settings, item)
