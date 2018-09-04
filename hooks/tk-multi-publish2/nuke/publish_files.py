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
import nuke
import sgtk
import itertools
from dd.runtime import api
api.load("frangetools")
import frangetools

HookBaseClass = sgtk.get_hook_baseclass()


class NukePublishFilesDDValidationPlugin(HookBaseClass):
    """
    Inherits from NukePublishFilesPlugin
    """
    def __init__(self, parent, **kwargs):
        """
        Construction
        """
        # call base init
        super(NukePublishFilesDDValidationPlugin, self).__init__(parent, **kwargs)
        self.visited_dict = {}

    def _build_dict(self, seq, key):
        """
        Creating a dictionary based on a key.

        :param seq: list of dictionaries
        :param key: dictionary key from which to create the dictionary
        :return: dict with information for that particular key
        """
        return dict((d[key], dict(d, index=index)) for (index, d) in enumerate(seq))


    def _framerange_to_be_published(self, item):
        """
        Since users have the option to render only a subset of frames,
        adding validation to check if the full frame range is being published.

        :param item: Item to process
        :return: True if yes false otherwise
        """
        lss_path = item.properties['node']['cached_path'].value()
        lss_data = frangetools.getSequence(lss_path)

        # Since lss_data will be a list of dictionaries,
        # building a dictionary from key value for the ease of fetching data.
        info_by_path = self._build_dict(lss_data, key="path")
        missing_frames = info_by_path.get(lss_path)['missing_frames']
        root = nuke.Root()

        # If there are no missing frames, then checking if the first and last frames match with root first and last
        # Checking with root because _sync_frame_range() will ensure root is up to date with shotgun
        if missing_frames:
            self.logger.warning("Renders Mismatch! Incomplete renders on disk.")
            nuke.message("WARNING!\n"+item.properties['node'].name()+"\nRenders Mismatch! Incomplete renders on disk.")
        else:
            first_rendered_frame = info_by_path.get(lss_path)['frame_range'][0]
            last_rendered_frame = info_by_path.get(lss_path)['frame_range'][1]
            if (first_rendered_frame < root.firstFrame()) or (last_rendered_frame < root.lastFrame()):
                self.logger.warning("Renders Mismatch! Incomplete renders on disk.")
                nuke.message("WARNING!\n"+item.properties['node'].name()+"\nRenders Mismatch! Incomplete renders on disk.")
            elif (first_rendered_frame > root.firstFrame()) or (last_rendered_frame > root.lastFrame()):
                self.logger.warning("Renders Mismatch! Extra renders on disk.")
                nuke.message("WARNING!\n"+item.properties['node'].name()+"\nRenders Mismatch! Extra renders on disk.")
        return True


    def _sync_frame_range(self, item):
        """
        Checks whether frame range is in sync with shotgun.

        :param item: Item to process
        :return: True if yes false otherwise
        """
        context = item.context
        entity = context.entity

        # checking entity validity since it can be invalid/empty in case of Project Level item
        if entity:
            frame_range_app = self.parent.engine.apps.get("tk-multi-setframerange")
            if not frame_range_app:
                # return valid for asset/sequence entities
                self.logger.warning("Unable to find tk-multi-setframerange app. "
                                    "Not validating frame range.")
                return True

            sg_entity_type = entity["type"]
            sg_filters = [["id", "is", entity["id"]]]
            in_field = frame_range_app.get_setting("sg_in_frame_field")
            out_field = frame_range_app.get_setting("sg_out_frame_field")
            fields = [in_field, out_field]

            # get the field information from shotgun based on Shot
            # sg_cut_in and sg_cut_out info will be on Shot entity, so skip in case this info is not present
            data = self.sgtk.shotgun.find_one(sg_entity_type, filters=sg_filters, fields=fields)
            if in_field not in data or out_field not in data:
                return True
            elif data[in_field] is None or data[out_field] is None:
                return True

            # compare if the frame range set at root level is same as the shotgun cut_in, cut_out
            root = nuke.Root()
            if root.firstFrame() != data[in_field] or root.lastFrame() != data[out_field]:
                self.logger.warning("Frame range not synced with Shotgun.")
                nuke.message("WARNING! Frame range not synced with Shotgun.")
        return True


    def _non_sgtk_writes(self):
        """
        Checks for non SGTK write nodes present in the scene.

        :return: True if yes false otherwise
        """
        write_nodes = ""
        # get all write and write geo nodes
        write = nuke.allNodes('Write') + nuke.allNodes('WriteGeo')

        if write:
            for item in range(len(write)):
                write_nodes += "\n" + write[item].name()
            self.logger.error("Non SGTK write nodes detected here.",
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Info",
                                      "tooltip": "Show non sgtk write node(s)",
                                      "text": "Non SGTK write nodes:\n{}".format(write_nodes)
                                  }
                              }
                              )
            return False
        return True


    @staticmethod
    def _check_for_knob(node, knob):
        try:
            node[knob]
        except NameError:
            return False
        else:
            return True


    def _collect_nodes_in_graph(self, node, file_paths, valid_paths, show_path):
        if self.visited_dict[node] == 0:
            # check for file parameter in the node if its neither a dot nor disabled
            # get the file path if exists
            # validate the file path
            if (self._check_for_knob(node, 'disable')) and (node['disable'].value() == 0):
                if self._check_for_knob(node, 'file'):
                    node_file_path = node['file'].value()
                    if node_file_path:
                        sg_data = sgtk.util.find_publish(self.parent.sgtk, [node_file_path])
                        # if the file is in the show location but not at SHARED or on shotgun, unpublished
                        # if the file is not in show location as well, invalid
                        if (show_path in node_file_path) and not sg_data and not (any(path in node_file_path for path in valid_paths.itervalues())):
                            file_paths['unpublished'].append(node)
                        elif show_path not in node_file_path and not (any(path in node_file_path for path in valid_paths.itervalues())):
                            file_paths['invalid'].append(node)
            # set visited to 1 for the node so as not to revisit
            self.visited_dict[node] = 1
            dep = node.dependencies()
            if dep:
                for item in dep:
                    self._collect_nodes_in_graph(item, file_paths, valid_paths, show_path)

        return file_paths


    def _read_and_camera_file_paths(self, item):
        """
        Checks if the files loaded are published or from valid locations i.e
        /dd/shows/<show>/SHARED, dd/shows/<show>/<seq>/SHARED, dd/shows/<show>/<seq>/<shot>/SHARED
        or
        /dd/shows/<show>, /dd/library

        :param item: Item to process
        :return: True if paths are published or valid false otherwise
        """
        context = item.context
        fields = context.as_template_fields()

        show = os.path.join(os.environ['DD_SHOWS_ROOT'], os.environ['DD_SHOW'])
        valid_paths = {
            'dd_library': os.path.join(os.environ['DD_ROOT'], 'library'),           # dd library path
            'show_pub': os.path.join(show, 'SHARED'),                               # show published location
            }
        if 'Sequence' in fields:
            valid_paths['seq'] = os.path.join(show, fields['Sequence'])             # seq published location
        if 'Shot' in fields:
            valid_paths['shot'] = os.path.join(valid_paths['seq'], fields['Shot'])  # shot published location

        # Collect all the nodes associated with a write node
        # For all the read, readgeo and camera nodes present in the write node graph, check for 'file' knob.
        # If its populated, get the file path.
        file_paths = {
            'unpublished': [],
            'invalid': [],
        }

        self._collect_nodes_in_graph(item.properties['node'], file_paths, valid_paths, show)

        if file_paths['invalid']:
            paths = ""
            for item in file_paths['invalid']:
                paths += "\n" + item.name() + ": " + item['file'].value()
            self.logger.error("Invalid paths! Try loading from Shotgun menu -> Load.",
                              extra={
                                  "action_show_more_info": {
                                      "label": "Show Info",
                                      "tooltip": "Show invalid path(s)",
                                      "text": "Paths not in {}:\n{}".format(valid_paths, paths)
                                  }
                              }
                              )
            return False

        if file_paths['unpublished']:
            unpublished = ""
            for path in file_paths['unpublished']:
                unpublished += "\n" + path.name() + ":  " + path['file'].value()
            self.logger.warning(
                "Unpublished files found.",
                extra={
                    "action_show_more_info": {
                        "label": "Show Info",
                        "tooltip": "Show unpublished files",
                        "text": "Unpublished files.{}".format(unpublished)
                    }
                }
            )
            nuke.message("WARNING!\n{} node".format(item.properties[
                'node'].name()) + "\nUnpublished files found.{}".format(unpublished))
        return True


    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish. Returns a
        boolean to indicate validity.

        :param task_settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process
        :returns: True if item is valid, False otherwise.
        """
        status = True
        # Segregating the checks, specifically for write nodes and for general nuke script
        if item.type == 'file.nuke':

            allnodes = nuke.allNodes()
            self.visited_dict = {node: 0 for node in allnodes}

            status = self._non_sgtk_writes() and status
            status = self._sync_frame_range(item) and status
        else:
            status = self._read_and_camera_file_paths(item) and status
            status = self._framerange_to_be_published(item) and status

        if not status:
            return status

        return super(NukePublishFilesDDValidationPlugin, self).validate(task_settings, item)

