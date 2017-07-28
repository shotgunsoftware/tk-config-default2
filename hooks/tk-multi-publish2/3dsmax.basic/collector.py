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
import MaxPlus
import sgtk
from sgtk.platform.qt import QtGui

HookBaseClass = sgtk.get_hook_baseclass()


class MaxSessionCollector(HookBaseClass):
    """
    Collector that operates on the max session. Should inherit from the basic
    collector hook.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the current session open in Max and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # create an item representing the current max session
        item = self.collect_current_max_session(parent_item)
        project_root = item.properties["project_root"]

        # look at the render layers to find rendered images on disk
        # TODO
        #self.collect_rendered_images(item)

        # if we can determine a project root, collect other files to publish
        if project_root:

            self.logger.info(
                "Current Max project is: %s." % (project_root,),
                extra={
                    "action_button": {
                        "label": "Change Project",
                        "tooltip": "Change to a different Max project",
                        "callback": _set_project
                    }
                }
            )

            self.collect_previews(item, project_root)
            self.collect_exports(item, project_root)

        else:

            self.logger.warning(
                "Could not determine the current Max project.",
                extra={
                    "action_button": {
                        "label": "Set Project",
                        "tooltip": "Set the Max project",
                        "callback": _set_project
                    }
                }
            )

    def collect_current_max_session(self, parent_item):
        """
        Creates an item that represents the current max session.

        :param parent_item: Parent Item instance
        :returns: Item of type max.session
        """

        publisher = self.parent

        path = MaxPlus.FileManager.GetFileNameAndPath()

        # determine the display name for the item
        if path:
            file_info = publisher.util.get_file_path_components(path)
            display_name = file_info["filename"]
        else:
            display_name = "Current Max Session"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "3dsmax.session",
            "3dsmax Session",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "3dsmax.png"
        )
        session_item.set_icon_from_path(icon_path)

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = MaxPlus.PathManager.GetProjectFolderDir()
        session_item.properties["project_root"] = project_root

        self.logger.info("Collected current 3dsMax session")

        return session_item

    def collect_exports(self, parent_item, project_root):
        """
        Creates items for exported files

        :param parent_item: Parent Item instance
        :param str project_root: The Max project root to search for exports
        """

        # ensure the alembic cache dir exists
        cache_dir = os.path.join(project_root, "export")
        if not os.path.exists(cache_dir):
            return

        self.logger.info(
            "Processing export folder: %s" % (cache_dir,),
            extra={
                "action_show_folder": {
                    "path": cache_dir
                }
            }
        )

        # look for alembic files in the cache folder
        for filename in os.listdir(cache_dir):
            export_path = os.path.join(cache_dir, filename)

            # allow the base class to collect and create the item. it knows how
            # to handle various files
            super(MaxSessionCollector, self)._collect_file(
                parent_item,
                export_path
            )

    def collect_previews(self, parent_item, project_root):
        """
        Creates items for previews.

        Looks for a 'project_root' property on the parent item, and if such
        exists, look for movie files in a 'movies' subfolder.

        :param parent_item: Parent Item instance
        :param str project_root: The Max project root to search for previews
        """

        # ensure the movies dir exists
        movies_dir = MaxPlus.PathManager.GetPreviewDir()
        if not os.path.exists(movies_dir):
            return

        self.logger.info(
            "Processing movies folder: %s" % (movies_dir,),
            extra={
                "action_show_folder": {
                    "path": movies_dir
                }
            }
        )

        # look for movie files in the movies folder
        for filename in os.listdir(movies_dir):

            # do some early pre-processing to ensure the file is of the right
            # type. use the base class item info method to see what the item
            # type would be.
            item_info = self._get_item_info(filename)
            if item_info["item_type"] != "file.video":
                continue

            movie_path = os.path.join(movies_dir, filename)

            # allow the base class to collect and create the item. it knows how
            # to handle movie files
            item = super(MaxSessionCollector, self)._collect_file(
                parent_item,
                movie_path
            )

            # the item has been created. update the display name to include
            # the an indication of what it is and why it was collected
            item.name = "%s (%s)" % (item.name, "preview")


def _set_project():
    """
    Pop up a Qt file browser to select a path. Then set that as the project root
    """

    # max doesn't provide the set project browser via python, so open our own
    # Qt file dialog.
    file_dialog = QtGui.QFileDialog(
        parent=QtGui.QApplication.activeWindow(),
        caption="Save As",
        directory=MaxPlus.PathManager.GetProjectFolderDir(),
        filter="3dsMax Files (*.max)"
    )
    file_dialog.setFileMode(QtGui.QFileDialog.DirectoryOnly)
    file_dialog.setLabelText(QtGui.QFileDialog.Accept, "Set")
    file_dialog.setLabelText(QtGui.QFileDialog.Reject, "Cancel")
    file_dialog.setOption(QtGui.QFileDialog.DontResolveSymlinks)
    file_dialog.setOption(QtGui.QFileDialog.DontUseNativeDialog)
    if not file_dialog.exec_():
        return
    path = file_dialog.selectedFiles()[0]
    MaxPlus.PathManager.SetProjectFolderDir(path)

