# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Before App Launch Hook
This hook is executed prior to application launch and is useful if you need
to set environment variables or run scripts as part of the app initialization.
"""

import os
from sgtk.util import shotgun
import sgtk


class BeforeAppLaunch(sgtk.Hook):
    """
    Hook to set up the system prior to app launch.
    """

    def execute(self, app_path, app_args, version, engine_name, **kwargs):
        # Get ShotGrid connection
        sg = shotgun.get_sg_connection()

        # Finding current project name
        current_engine = sgtk.platform.current_engine()
        current_context = current_engine.context
        project_name = current_context.project["name"]

        # Get template
        primary_location = self.parent.sgtk.roots.get('primary')

        # Get core
        tk = sgtk.sgtk_from_path(primary_location)

        # Get OCIO path
        ocio_template = tk.templates["ocio_config"]
        ocio_path = ocio_template.apply_fields(current_context).replace(os.sep, '/')

        if os.path.isfile(ocio_path):
            os.environ["OCIO"] = ocio_path
            self.parent.log_info("OCIO config found, set environment")

        if engine_name == "tk-houdini":
            ########################################
            """Setting render engine environment"""

            # Finding render engine entity
            render_engine = sg.find_one("Project", [["name", "is", project_name]], ["sg_render_engine"]).get(
                'sg_render_engine')

            # Setting render engine environment
            if not render_engine is None:
                self.parent.log_info("Set render_engine environment to %s" % render_engine)
                os.environ["RENDER_ENGINE"] = render_engine

            else:
                self.parent.log_info("No render engine entity set in ShotGrid project")

            ########################################
            """Setting OTL scan path"""

            # Get template
            houdini_otls_template = tk.templates["houdini_otls"]
            otls_path = houdini_otls_template.apply_fields(current_context).replace(os.sep, '/')

            # Add environment
            sgtk.util.append_path_to_env_var("HOUDINI_OTLSCAN_PATH ", otls_path)

            self.parent.log_info("Added otlscan path %s" % otls_path)