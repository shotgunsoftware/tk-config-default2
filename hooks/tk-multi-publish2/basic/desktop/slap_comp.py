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

import os
import pprint
import sgtk
import datetime

from ss_config.hooks.tk_multi_publish2.general.upload_version import SsUploadVersionPlugin

class SlapCompPlugin(SsUploadVersionPlugin):
    """
    Plugin for generating slap_comp quicktimes and images for review.
    """
    @property
    def icon(self):
        """
        Path to an png icon on disk
        """

        # look for icon one level up from this hook's folder in "icons" folder
        return os.path.join(
            self.disk_location,
            "icons",
            "slap.png"
        )

    @property
    def name(self):
        """
        One line display name describing the plugin
        """
        return "Slap Comp for review"

    @property
    def description(self):
        """
        Verbose, multi-line description of what the plugin does. This can
        contain simple html for formatting.
        """

        publisher = self.parent

        shotgun_url = publisher.sgtk.shotgun_url

        media_page_url = "%s/page/media_center" % (shotgun_url,)
        review_url = "https://www.shotgunsoftware.com/features/#review"

        return """
        A Slap Comp will be created using a predefined nuke script.<br><br>


        A <b>Version</b> entry will then be created in Shotgun and a transcoded
        copy of the file will be attached to it. The file can then be reviewed
        via the project's <a href='%s'>Media</a> page, <a href='%s'>RV</a>, or
        the <a href='%s'>Shotgun Review</a> mobile app.
        """ % (media_page_url, review_url, review_url)

    @property
    def item_filters(self):
        """
        List of item types that this plugin is interested in.

        Only items matching entries in this list will be presented to the
        accept() method. Strings can contain glob patters such as *, for example
        ["maya.*", "file.maya"]
        """

        # we use "video" since that's the mimetype category.
        return ["file.image", "file.video", "file.image.sequence"]

    def accept(self, settings, item):
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

        :param settings: Dictionary of Settings. The keys are strings, matching
            the keys returned in the settings property. The values are `Setting`
            instances.
        :param item: Item to process

        :returns: dictionary with boolean keys accepted, required and enabled
        """
        accept = {"accepted": False}

        self.logger.warning(">>>>> slap_comp accept")
        
        if 'sg_slap_comp' not in item.properties.keys():
            return accept

        publisher = self.parent
        file_path = item.properties["path"]

        file_info = publisher.util.get_file_path_components(file_path)
        extension = file_info["extension"].lower()

        valid_extensions = []


        for ext in settings["File Extensions"].value.split(","):
            ext = ext.strip().lstrip(".")
            valid_extensions.append(ext)
        if extension in valid_extensions:
            # return the accepted info
            accept = {"accepted": True}
            if item.properties.get("sg_slap_comp"):
                accept.update({'checked': False})
                # log the accepted file and display a button to reveal it in the fs
                self.logger.info(
                    "Slap Comp plugin accepted: %s" % (file_path,),
                    extra={
                        "action_show_folder": {
                            "path": file_path
                        }
                    }
                )                
            else:
                accept.update({'checked': False})
                accept.update({'enabled': False})
                accept.update({'visible': False})
                accept = {"accepted": False}   

        else:
            self.logger.debug(
                "%s is not in the valid extensions list for Version creation" %
                (extension,)
            )
        
        exclude_descriptors = [ "distort", "undistort", "persp", "cones" ]
        exclude_templates = [ "incoming_outsource_shot_nuke_render", 
                                "incoming_outsource_shot_matchmove_render", 
                                "incoming_outsource_shot_undistorted" 
                                ]
        # reject distort/undistort outsource items
        if item.properties.get('template'):
            if item.properties.get('template').name in exclude_templates:
                if 'descriptor' in item.properties["fields"].keys():
                    if item.properties.fields['descriptor'] in exclude_descriptors:
                        self.logger.debug(
                                        "Removing template %s : %s from Version for Review" % (
                                            item.properties.get('template').name,
                                            item.properties.fields['descriptor']
                                            )
                                        )
                        accept.update({'checked': False})
                        accept.update({'enabled': False})
                        accept.update({'visible': False})
                        accept = {"accepted": False}
                else:
                    self.logger.debug(
                                    "Removing template %s from Version for Review as Undistort" % (
                                        item.properties.get('template').name,
                                        )
                                    )
                    accept.update({'checked': False})
                    accept.update({'enabled': False})
                    accept.update({'visible': False})
                    accept = {"accepted": False}

        return accept
