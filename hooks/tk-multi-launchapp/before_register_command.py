# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class BeforeRegisterCommand(HookBaseClass):
    """
    Before Register Command Hook

    This hook is run prior to launchapp registering launcher commands with
    the parent engine. Note: this hook is only run for Software entity
    launchers.
    """

    def determine_engine_instance_name(self, software_version, engine_instance_name):
        """
        Hook method to intercept SoftwareLauncher and engine instance name data prior to
        launcher command registration and alter the engine instance name should that
        be required.

        :param software_version: The software version instance constructed when
            the scan software routine was run.
        :type: :class:`sgtk.platform.SoftwareVersion`
        :param str engine_instance_name: The name of the engine instance that will
            be used when SGTK is bootstrapped during launch.

        :returns: The desired engine instance name.
        :rtype: str
        """
        # We're going to end up getting a SoftwareVersion for Nuke Studio that
        # wants to route us to the tk-nuke engine instance. We don't want that, so
        # we'll redirect to tk-nukestudio.
        if software_version.product == "NukeStudio":
            engine_instance_name = "tk-nukestudio"

        return engine_instance_name
