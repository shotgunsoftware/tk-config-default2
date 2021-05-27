# Copyright (c) 2021 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import sgtk


HookBaseClass = sgtk.get_hook_baseclass()


class BatchPublishPlugin(HookBaseClass):
    """
    Plugin for publishing in a batch session session.

    This hook relies on functionality found in the base file publisher hook in
    the publish2 app and should inherit from it in the configuration. The hook
    setting for this plugin should look something like this::

        hook: "{self}/publish_file.py:{engine}/tk-multi-publish2/basic/publish_session.py"

    """

    # NOTE: The plugin icon and name are defined by the base file plugin.

    def __init__(self, *args, **kwargs):
        """"""
        super(BatchPublishPlugin, self).__init__(*args, **kwargs)

        # if we are in the batch publish session, we need to attach the hook logger instance to the
        # tk-multi-publishbatch app log handlers in order to be able to see the logs in the UI and and the log file
        if self._is_batch_publish():
            batch_app = self.parent.engine.apps.get("tk-multi-publishbatch")
            if batch_app:
                tk_multi_publishbatch = batch_app.import_module("tk_multi_publishbatch")
                for handler in batch_app.logger.handlers:
                    if isinstance(handler, tk_multi_publishbatch.log_handler.QtHandler):
                        self.logger.addHandler(handler)
                    elif isinstance(
                        handler, sgtk.LogManager()._SafeRotatingFileHandler
                    ):
                        self.logger.addHandler(handler)

    @staticmethod
    def _is_batch_publish():
        """
        Check if we're running the script on the main publish process or if we're executing the process in a batch mode

        :returns: True if we're running the publish actions in batch mode, False otherwise
        """
        is_batch_publish = os.environ.get("SGTK_BATCH_PUBLISH", False)
        if is_batch_publish in [
            True,
            "True",
        ]:  # Maya environment variables only accept strings
            return True
        return False
