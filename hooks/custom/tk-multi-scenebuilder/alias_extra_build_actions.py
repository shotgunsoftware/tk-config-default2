# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import alias_api
import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class ExtraBuildActions(HookBaseClass):

    TAG_LIST = ["High", "Basic"]

    def post_build_action(self, preset, items):
        """
        This method is executed just after the files have been loaded into the current scene.

        :param preset: Name of the selected preset
        :param items:  List of dictionaries where each item represents a loaded file. Each dictionary contains a
                       *sg_data* key to store the Shotgun data and an *action_name* referring to the name of the action
                       used to load the file.
        """

        if preset == "Default":
            for item in items:

                if item["action_name"] != "import_as_reference":
                    continue

                if not item["sg_data"].get("entity.Asset.tags"):
                    continue

                # get the Alias reference
                ref_path = item["sg_data"]["path"]["local_path"]
                ref = alias_api.get_reference_by_path(ref_path)
                if not ref:
                    self.logger.warning(
                        "Couldn't get Alias reference for {}".format(ref_path)
                    )
                    continue

                for asset_tag in item["sg_data"]["entity.Asset.tags"]:

                    if asset_tag["name"] not in self.TAG_LIST:
                        continue

                    # get the Alias alternative corresponding to the tag name. If the alternative doesn't exist,
                    # create it
                    alternative = alias_api.get_alternative_by_name(asset_tag["name"])
                    if not alternative:
                        alternative = alias_api.create_alternative(asset_tag["name"])

                    # finally, add the reference to the alternative
                    alternative.add_reference(ref)
