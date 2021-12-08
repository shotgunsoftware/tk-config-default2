# Copyright (c) 2015 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.
# ### OVERRIDDEN IN SSVFX_SG ###

from ss_config.hooks.tk_multi_publish2.general.upload_version import SsUploadVersionPlugin


class UploadVersionPlugin(SsUploadVersionPlugin):
    """
    Plugin for sending quicktimes and images to shotgun for review.
    """
    pass
