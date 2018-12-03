# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

import hiero.core
import hiero.ui
import os

HookBaseClass = sgtk.get_hook_baseclass()


class HieroCustomizeExportUI(HookBaseClass):
    """
    This class defines methods that can be used to customize the UI of the various
    Shotgun-related exporters. Each processor has its own set of create/get/set
    methods, allowing for customizable UI elements for each type of export.
    """
    # For detailed documentation of the methods available for this hook, see
    # the documentation at http://developer.shotgunsoftware.com/tk-hiero-export/

    def get_default_version_number(self):
    
        version_number = 1

        # version number from workfiles app
        workfiles_app = self.parent.engine.apps.get("tk-multi-workfiles2")
        if not workfiles_app:
            self.parent.logger.error("Unable to get default version number. The tk-multi-workfiles2 app isn't loaded.")
            return version_number
        work_template = workfiles_app.get_work_template()

        # from selected project
        view = hiero.ui.activeView()
        if hasattr(view, 'selection'):
            selection = view.selection()

            if isinstance(view, hiero.ui.BinView):
                item = selection[0]

                # iterate until you get project
                while hasattr(item, 'parentBin') and item != isinstance(item.parentBin(), hiero.core.Project):
                    item = item.parentBin()

                project_path = item.path()
                if not work_template.validate(project_path):
                    self.parent.logger.warning("Using default version number. The selected Project '%s' does not match the work template '%s'" % (item.name(), str(work_template)))
                    return version_number
                fields = work_template.get_fields(project_path)
                version_number = fields.get('version', version_number)

        return version_number

    def get_default_preset_properties(self):

        properties = {

            'shotgunShotCreateProperties': {
                'sg_cut_type': 'Boards',
                'collateSequence': False,
                'collateShotNames': False,
                'collateTracks': False,
                'collateCustomStart': True,
            },

            'cutLength': True,
            'cutUseHandles': False,
            'cutHandles': 12,
            'includeRetimes': False,
            'startFrameSource': 'Custom',
            'startFrameIndex': 1001,
        }

        return properties

    def get_transcode_exporter_ui_properties(self):

        return [

            dict(
                name="burninDataEnabled",
                value=True,
            ),
            dict(
                name="burninData",
                value={
                    'burnIn_bottomRight': '[frame]',
                    'burnIn_topLeft': '',
                    'burnIn_topMiddle': '',
                    'burnIn_padding': 120,
                    'burnIn_topRight': '',
                    'burnIn_bottomMiddle': '[frames {first}]-[frames {last}]',
                    'burnIn_bottomLeft': '{sequence}_{shot}',
                    'burnIn_textSize': 28,
                    'burnIn_font': os.path.join(os.environ["DD_FACILITY_ROOT"], "lib", "fonts", "Arial Bold.ttf"),
                    },
            ),
        ]






