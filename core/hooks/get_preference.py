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
Hook which looks up a DD Preference value.
"""

import sgtk
HookBaseClass = sgtk.get_hook_baseclass()

from dd.runtime import api
api.load("preferences")
import preferences

# Explicitly set the effective level for the preferences module logger to INFO
# as the debug output is overly verbose and not relevant
import logging
preferences.logger.setLevel(logging.INFO)


class GetPreference(HookBaseClass):

    def execute(self, setting, settings_type, bundle_obj, extra_params, **kwargs):
        """
        Uses the Preferences system to lookup a value for the passed in key
        """
        key = '%s.%s' % (bundle_obj.name, setting)
        default = dict(enumerate(extra_params)).get(0, None)
        prefs = preferences.Preferences(package="sgtk_config")

        value = prefs.get(key, default)
        if settings_type == "int":
            value = int(value)
        elif settings_type == "bool":
            value = bool(value)
        elif settings_type == "str":
            value = str(value)

        return value
