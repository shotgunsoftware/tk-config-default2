# Copyright (c) 2017 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

# in-built modules
import os

# external modules
from xml.dom import minidom

# package modules
import sgtk
# for jsmk before we actually write out the CC files!
from sgtk.util.filesystem import ensure_folder_exists

HookBaseClass = sgtk.get_hook_baseclass()


class IngestCDLFilesPlugin(HookBaseClass):
    """
    Inherits from PublishFilesPlugin
    """

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this plugin expects to receive
        through the settings parameter in the accept, validate, publish and
        finalize methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts
        as part of its environment configuration.
        """
        schema = super(IngestCDLFilesPlugin, self).settings_schema
        schema["Item Type Filters"]["default_value"] = ["file.cdl"]
        return schema

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        return """
        Plugin to process CDL files, once the files are processed it publishes an avid_grade.cc, after validating that
        'Slope', 'Offset', 'Power', 'Saturation' fields are intact in the input file.
        """

    def accept(self, task_settings, item):
        """
        Method called by the publisher to determine if an item is of any
        interest to this plugin. Only items matching the filters defined via the
        item_filters property will be presented to this method.

        A publish task will be generated for each item accepted here. Returns a
        dictionary with the following booleans:

            - accepted: Indicates if the plugin is interested in this value at
                all. Required.
            - enabled: If True, the plugin will be enabled in the UI, otherwise
                it will be disabled. Optional, True by default.
            - visible: If True, the plugin will be visible in the UI, otherwise
                it will be hidden. Optional, True by default.
            - checked: If True, the plugin will be checked in the UI, otherwise
                it will be unchecked. Optional, True by default.

        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """

        # Run the parent acceptance method
        accept_data = super(IngestCDLFilesPlugin, self).accept(task_settings, item)

        if item.type == "file.cdl":
            accept_data["accepted"] = True
        else:
            accept_data["accepted"] = False

        return accept_data

    def validate(self, task_settings, item):
        """
        Validates the given item to check that it is ok to publish.

        Returns a boolean to indicate validity.

        :param task_settings: Dictionary of settings
        :param item: Item to process

        :returns: True if item is valid, False otherwise.
        """

        fields = item.properties["fields"]

        # to override the name of the published file
        # Our OCIO config setup is supposed to read avid_grade.cc files, since we get these(ccc or cc) files from the
        # client with different names, the name field resolves to a different value and we are simply
        # correcting it here, before publish.
        if fields["name"] != "avid_grade":
            fields["name"] = "avid_grade"

        status = super(IngestCDLFilesPlugin, self).validate(task_settings, item)

        # validate/read the CDL file
        cc_dict = self.read_cdl(item)

        if isinstance(cc_dict, str):
            self.logger.error(cc_dict)
            return False

        item.properties["cc_data"] = cc_dict

        self.logger.info(
            "CC file for %s will be created with attributes." % item.name,
            extra={
                "action_show_more_info": {
                    "label": "Show attributes",
                    "tooltip": "Show the CC file data.",
                    "text": item.properties["cc_data"]
                }
            }
        )

        return status

    def publish_files(self, task_settings, item, publish_path):
        """
        Overriding this method to process cdl files, instead of simply copying it to the publish location.

        This method handles copying an item's path(s) to a designated location.
        """
        cc_dict = item.properties["cc_data"]

        # ensure that the folder actually exists!
        dest_folder = os.path.dirname(publish_path)
        ensure_folder_exists(dest_folder)

        self.write_cc(cc_path=publish_path, **cc_dict)

        return [publish_path]

    def read_cdl(self, item):
        """
        This method will check for ccc or cc files only

        ccc file:
            Validation: Checks weather file has multiple "ColorCorrection" IDs exists or not. If exists then
                        function will return False else returns data required to write cc file
        cc file:
            Validation: Checks weather 'Slope', 'Offset', 'Power', 'Saturation' has values or not. If not exists then
                        function will return False else returns data required to write cc file

        :param item:
        :return: return a dictionary containing values to write in cc file
        """
        # get data from ccc file to write cc file
        cc_dict = {}
        file_path = item.properties["path"]
        xmldoc = minidom.parse(file_path)

        if file_path.endswith('.ccc'):
            tag = xmldoc.getElementsByTagName("ColorCorrectionCollection")[0]

            # return None if ccc file has multiple 'ColorCorrection' tags
            cc_tags = tag.getElementsByTagName('ColorCorrection')
            if len(cc_tags) > 1:
                return "CCC file is invalid, because it contains multiple CC IDs..."
            cc_dict['description'] = str(tag.getElementsByTagName('ColorCorrection')[0].getAttribute('id'))
            
        else:
            line = ''
            tag = xmldoc.getElementsByTagName("ColorCorrection")[0]
            for e_tag in ['Slope', 'Offset', 'Power', 'Saturation']:
                tag_value = tag.getElementsByTagName(e_tag)[0].childNodes[0].data
                if not tag_value:
                    line = line + '%s missing value' % e_tag + "\n"
            if line:
                return line
            cc_dict['description'] = str(tag.getAttribute('id'))

        # if ccc file has only one 'ColorCorrection' tag then return data
        for e_tag in ['Slope', 'Offset', 'Power', 'Saturation']:
            cc_dict[e_tag.lower()] = str(tag.getElementsByTagName(e_tag)[0].childNodes[0].data)

        return cc_dict

    @staticmethod
    def write_cc(cc_path, description, slope, offset, power, saturation):
        """
        Export the CC file to cc_path.

        :param cc_path:  path to write cc file
        :param description:
        :param slope:
        :param offset:
        :param power:
        :param saturation:
        :return:
        """

        doc = minidom.Document()

        root = doc.createElement("ColorCorrection")
        root.setAttribute("id", description)
        doc.appendChild(root)

        SOPNode_tag = doc.createElement("SOPNode")
        root.appendChild(SOPNode_tag)

        Slope_tag = doc.createElement("Slope")
        SOPNode_tag.appendChild(Slope_tag)
        info_tag = doc.createTextNode(slope)
        Slope_tag.appendChild(info_tag)

        Slope_tag = doc.createElement("Offset")
        SOPNode_tag.appendChild(Slope_tag)
        info_tag = doc.createTextNode(offset)
        Slope_tag.appendChild(info_tag)

        Slope_tag = doc.createElement("Power")
        SOPNode_tag.appendChild(Slope_tag)
        info_tag = doc.createTextNode(power)
        Slope_tag.appendChild(info_tag)

        SatNode_tag = doc.createElement("SatNode")
        root.appendChild(SatNode_tag)

        Saturation_tag = doc.createElement("Saturation")
        SatNode_tag.appendChild(Saturation_tag)
        info_tag = doc.createTextNode(saturation)
        Saturation_tag.appendChild(info_tag)

        doc.writexml(open(cc_path, 'w'), indent="  ", addindent="  ", newl='\n')
        doc.unlink()
