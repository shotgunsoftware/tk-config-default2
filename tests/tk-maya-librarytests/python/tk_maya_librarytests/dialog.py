# Copyright (c) 2020 Shotgun Software Inc.
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
from tank.util import sgre as re

# by importing QT from sgtk rather than directly, we ensure that
# the code will be compatible with both PySide and PyQt.
from sgtk.platform.qt import QtCore, QtGui
from .ui.dialog import Ui_Dialog
from .widget_list_item import ListItemWidget

import maya.cmds as cmds

# Import the shotgun_model module from the shotgun utils framework.
shotgun_model = sgtk.platform.import_framework("tk-framework-shotgunutils",
                                               "shotgun_model")
task_manager = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "task_manager"
)
shotgun_globals = sgtk.platform.import_framework(
    "tk-framework-shotgunutils", "shotgun_globals"
)


class AppDialog(QtGui.QWidget):
    """
    Main application dialog window
    """

    def __init__(self):
        """
        Constructor
        """
        # first, call the base class and let it do its thing.
        QtGui.QWidget.__init__(self)

        # now load in the UI that was created in the UI designer
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.update_button.clicked.connect(self.update_references)

        # most of the useful accessors are available through the Application class instance
        # it is often handy to keep a reference to this. You can get it via the following method:
        self._app = sgtk.platform.current_bundle()

        # create a background task manager
        # self._task_manager = task_manager.BackgroundTaskManager(
        #     self, start_processing=True, max_threads=2
        # )
        # shotgun_globals.register_bg_task_manager(self._task_manager)

        # get the maya references
        ref_list = cmds.file(q=1, reference=1)

        # from this list, get the associated published files
        self.local_refs, self.external_refs = self._clean_ref_list(ref_list)

        # update the UI
        self._update_local_refs()
        self._update_external_refs()


    # def closeEvent(self, event):
    #     """
    #     Executed when the main dialog is closed.
    #     All worker threads and other things which need a proper shutdown
    #     need to be called here.
    #     """
    #     shotgun_globals.unregister_bg_task_manager(self._task_manager)
    #     self._task_manager.shut_down()
    #     event.accept()

    def _clean_ref_list(self, ref_list):
        """
        """

        local_refs = []
        external_refs = []

        # Get the list of ref path
        published_files = find_publishes(ref_list)

        # then filter by path and add additional info
        for ref in ref_list:
            norm_path = sgtk.util.ShotgunPath.normalize(ref).replace("\\", "/")
            if norm_path in published_files.keys():
                node_name = cmds.referenceQuery(ref, referenceNode=1)
                ref_data = {
                    "node_name": node_name,
                    "path": norm_path,
                    "sg_data": published_files[norm_path]
                }
                # check if the file is from the current project or another one
                if published_files[norm_path]["project"]["id"] == self._app.context.project["id"]:
                    local_refs.append(ref_data)
                else:
                    external_refs.append(ref_data)

        return local_refs, external_refs

    def _update_local_refs(self):
        """
        """
        self.__local_ref_items = {}
        for r in self.local_refs:
            item = ListItemWidget()
            item.set_path(r["path"])
            item.set_project(r["sg_data"]["project"]["name"])
            self.ui.verticalLayout_2.insertWidget(0, item)
            self.__local_ref_items[r["path"]] = item

    def _update_external_refs(self):
        """
        """
        self.__external_ref_items = {}
        for r in self.external_refs:
            item = ListItemWidget()
            item.set_path(r["path"])
            item.set_project(r["sg_data"]["project"]["name"])
            self.ui.verticalLayout_3.insertWidget(0, item)
            self.__external_ref_items[r["path"]] = item

    def update_references(self):
        """
        """

        # first start with local references
        for r in self.local_refs:
            sg_filters = [
                ["entity", "is", r["sg_data"]["entity"]],
                ["name", "is", r["sg_data"]["name"]],
                ["task", "is", r["sg_data"]["task"]],
                ["published_file_type", "is", r["sg_data"]["published_file_type"]]
            ]
            sg_fields = ["path", "version_number"]
            sg_order = [{"field_name": "version_number", "direction": "desc"}]
            all_published_files = self._app.shotgun.find(
                "PublishedFile",
                filters=sg_filters,
                fields=sg_fields,
                order=sg_order
            )
            for pf in all_published_files:
                if os.path.isfile(pf["path"]["local_path"]):
                    item = self.__local_ref_items.get(r["path"])
                    if item:
                        # update the ref in Maya and the UI
                        cmds.file(pf["path"]["local_path"], loadReference=r["node_name"])
                        item.set_path(pf["path"]["local_path"])
                    break

        # then do the same with external references
        for r in self.external_refs:
            sg_filters = [
                ["entity", "is", r["sg_data"]["entity"]],
                ["name", "is", r["sg_data"]["name"]],
                ["task", "is", r["sg_data"]["task"]],
                ["published_file_type", "is", r["sg_data"]["published_file_type"]]
            ]
            sg_fields = ["path", "version_number"]
            sg_order = [{"field_name": "version_number", "direction": "desc"}]
            all_published_files = self._app.shotgun.find(
                "PublishedFile",
                filters=sg_filters,
                fields=sg_fields,
                order=sg_order
            )
            new_path = None
            for pf in all_published_files:
                if not os.path.isfile(pf["path"]["local_path"]):
                    continue
                if pf["path"]["local_path"] == r["path"]:
                    print("Already updated!")
                    break
                new_path = pf["path"]["local_path"]
                break

            if new_path:
                item = self.__external_ref_items.get(r["path"])
                if item:
                    # update the ref in Maya and the UI
                    cmds.file(new_path, loadReference=r["node_name"])
                    item.set_path(new_path)


def find_publishes(paths):
    """
    :param paths:
    :return:
    """
    storage_paths = {}

    current_engine = sgtk.platform.current_engine()
    sg = current_engine.shotgun
    tk = current_engine.sgtk

    # Normalize the paths
    paths = [sgtk.util.ShotgunPath.normalize(p).replace("\\", "/") for p in paths]

    # Get the tank_name for all the active projects
    sg_projects = sg.find(
        "Project",
        filters=[
            ["archived", "is", False],
            ["is_template", "is", False],
            ["tank_name", "is_not", None]
        ],
        fields=["id", "tank_name"]
    )
    tank_names = [p["tank_name"] for p in sg_projects]

    # Get the SG root paths
    storage_roots = tk.pipeline_configuration.get_local_storage_roots()

    # For each path, try to determine its path cache and its path cache storage
    for p in paths:
        for root_name, root_path in storage_roots.items():
            is_matching = False
            for t in tank_names:

                # normalize the root path
                root_path_obj = sgtk.util.ShotgunPath.from_current_os_path(root_path)
                norm_root_path = root_path_obj.current_os.replace(os.sep, "/")

                # append project and normalize
                proj_path = root_path_obj.join(t).current_os
                proj_path = proj_path.replace(os.sep, "/")

                if p.lower().startswith(proj_path.lower()):
                    # our path matches this storage!

                    # Remove parent dir plus "/" - be careful to handle the case where
                    # the parent dir ends with a '/', e.g. 'T:/' for a Windows drive
                    path_cache = p[len(norm_root_path):].lstrip("/")

                    # group by storage root
                    storage_info = storage_paths.get(root_name, {})
                    storage_info[path_cache] = p
                    storage_paths[root_name] = storage_info

                    is_matching = True
                    continue

            if is_matching:
                continue

    # Get Local Storage entities
    (mapped_roots, unmapped_roots) = tk.pipeline_configuration.get_local_storage_mapping()

    published_files = {}
    for root_name, publish_paths in storage_paths.items():

        local_storage = mapped_roots.get(root_name)
        if not local_storage:
            continue

        sg_filters = []
        sg_fields = ["path_cache", "project", "entity", "name", "task", "published_file_type"]
        sg_filters.append(["path_cache", "in", publish_paths.keys()])
        sg_filters.append(["path_cache_storage", "is", local_storage])
        published_files[root_name] = sg.find("PublishedFile", sg_filters, sg_fields)

    # Reorganize the results
    matches = {}
    for local_storage_name, publishes in published_files.items():
        for p in publishes:
            path_cache = p["path_cache"]
            if path_cache in storage_paths[local_storage_name].keys():
                p.pop("path_cache")
                matches[storage_paths[local_storage_name][path_cache]] = p

    return matches
