# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook which looks up the default saveas name for tk-multi-workfiles2.
"""
import urllib

import sgtk
HookBaseClass = sgtk.get_hook_baseclass()


class GetDefaultSaveAsName(HookBaseClass):

    def execute(self, setting, settings_type, bundle_obj, extra_params, **kwargs):
        """
        Uses the Preferences system to lookup a value for the passed in key
        """
        try:
            return urllib.quote(bundle_obj.context.task["name"].replace(" ", "_").lower(), safe='')
        except Exception:
            pass

        return "main"
