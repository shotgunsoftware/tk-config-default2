# Copyright 2021 Autodesk, Inc.  All rights reserved.
#
# Use of this software is subject to the terms of the Autodesk license agreement
# provided at the time of installation or download, or which otherwise accompanies
# this software in either electronic or hard copy form.

import alias_api
import sgtk

HookClass = sgtk.get_hook_baseclass()


class AliasSceneOperation(HookClass):
    """
    Hook called to perform an operation with the
    current file
    """

    def execute(
        self,
        operation,
        file_path,
        context=None,
        parent_action=None,
        file_version=None,
        read_only=None,
        **kwargs
    ):
        """
        Main hook entry point

        :param operation:       String
                                Scene operation to perform

        :param file_path:       String
                                File path to use if the operation
                                requires it (e.g. open)

        :param context:         Context
                                The context the file operation is being
                                performed in.

        :param parent_action:   This is the action that this scene operation is
                                being executed for.  This can be one of:
                                - open_file
                                - new_file
                                - save_file_as
                                - version_up

        :param file_version:    The version/revision of the file to be opened.  If this is 'None'
                                then the latest version should be opened.

        :param read_only:       Specifies if the file should be opened read-only or not

        :returns:               Depends on operation:
                                'current_path' - Return the current scene
                                                 file path as a String
                                'reset'        - True if scene was reset to an empty
                                                 state, otherwise False
                                all others     - None
        """

        ret = super(AliasSceneOperation, self).execute(
            operation,
            file_path,
            context=context,
            parent_action=parent_action,
            file_version=file_version,
            read_only=read_only,
            **kwargs
        )

        if operation == "prepare_new":
            if context and context.step and context.entity.get("type") == "Asset":

                # WORKFLOW 1 - MODELING STEP
                # create one layer by material library
                # if the material library is tagged as symmetric, create a second layer with the "_NS" suffix
                if context.step["name"] == "Modeling":

                    material_libraries = self.parent.shotgun.find(
                        "CustomEntity04",
                        [["project.Project.sg_type", "is", "Library"]],
                        ["code", "sg_symmetric"],
                    )

                    for m in material_libraries:
                        alias_api.create_layer(m["code"])
                        if m["sg_symmetric"]:
                            alias_api.create_layer("{}_NS".format(m["code"]))

                # WORKFLOW 2 - CLASS-A STEP
                # create one layer by sub-asset
                elif context.step["name"] == "Class-A":

                    sub_assets = self.parent.shotgun.find(
                        "Asset", [["parents", "is", context.entity]], ["code"]
                    )

                    for s in sub_assets:
                        alias_api.create_layer(s["code"])

        return ret
