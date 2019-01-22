# Copyright (c) 2015 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that loads defines all the available actions, broken down by publish type. 
"""

import glob
import os
import re
import pymel.core as pm
import maya.cmds as cmds
import maya.mel as mel
import sgtk
import urllib

from functools import partial

HookBaseClass = sgtk.get_hook_baseclass()

# LOOKDEV group name
SHADER_GROUP_NAME = "LOOKDEV"
IMPORTABLE_ATTR_NAME = "imported_name"


class CustomMayaActions(HookBaseClass):

    def generate_actions(self, sg_publish_data, actions, ui_area):
        """
        Returns a list of action instances for a particular publish.
        This method is called each time a user clicks a publish somewhere in the UI.
        The data returned from this hook will be used to populate the actions menu for a publish.

        The mapping between Publish types and actions are kept in a different place
        (in the configuration) so at the point when this hook is called, the loader app
        has already established *which* actions are appropriate for this object.

        The hook should return at least one action for each item passed in via the
        actions parameter.

        This method needs to return detailed data for those actions, in the form of a list
        of dictionaries, each with name, params, caption and description keys.

        Because you are operating on a particular publish, you may tailor the output
        (caption, tooltip etc) to contain custom information suitable for this publish.

        The ui_area parameter is a string and indicates where the publish is to be shown.
        - If it will be shown in the main browsing area, "main" is passed.
        - If it will be shown in the details area, "details" is passed.
        - If it will be shown in the history area, "history" is passed.

        Please note that it is perfectly possible to create more than one action "instance" for
        an action! You can for example do scene introspection - if the action passed in
        is "character_attachment" you may for example scan the scene, figure out all the nodes
        where this object can be attached and return a list of action instances:
        "attach to left hand", "attach to right hand" etc. In this case, when more than
        one object is returned for an action, use the params key to pass additional
        data into the run_action hook.

        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :param actions: List of action strings which have been defined in the app configuration.
        :param ui_area: String denoting the UI Area (see above).
        :returns List of dictionaries, each with keys name, params, caption and description
        """
        app = self.parent

        # get the existing action instances
        action_instances = super(CustomMayaActions, self).generate_actions(sg_publish_data, actions, ui_area)

        action_names = [action_instance["name"] for action_instance in action_instances]

        if "replace_reference" in actions and "replace_reference" not in action_names:
            action_instances.append({"name": "replace_reference",
                                     "params": None,
                                     "caption": "Replace Reference",
                                     "description": "Replaces the selected reference in your maya scene with the one "
                                                    "from loader."})

        if "create_reference_with_shaders" in actions and "create_reference_with_shaders" not in action_names:
            action_instances.append({"name": "create_reference_with_shaders",
                                     "params": None,
                                     "caption": "Create Reference (With Shaders)",
                                     "description": "Tries to connect the referenced files to the 'LOOKDEV' group in "
                                                    "the maya scene."})

        if "replace_reference_with_shaders" in actions and "replace_reference_with_shaders" not in action_names:
            action_instances.append({"name": "replace_reference_with_shaders",
                                     "params": None,
                                     "caption": "Replace Reference (With Shaders)",
                                     "description": "Tries to connect the referenced files to the 'LOOKDEV' group in "
                                                    "the maya scene."})

        if "texture_node_with_frames" in actions and "texture_node_with_frames" not in action_names:
            action_instances.append({"name": "texture_node_with_frames",
                                     "params": None,
                                     "caption": "Create Texture Node (Frames)",
                                     "description": "Creates a file texture node, which reads the frames as per "
                                                    "timeline for the selected item.."})

        if "create_importable_reference" in actions and "create_importable_reference" not in action_names:
            action_instances.append({"name": "create_importable_reference",
                                     "params": None,
                                     "caption": "Create Importable Reference",
                                     "description": "Creates a Reference node that can be localized by our shelf button"
                                                    "This should allow users to rename the top group if needed."})

        return action_instances

    def execute_action(self, name, params, sg_publish_data):
        """
        Execute a given action. The data sent to this be method will
        represent one of the actions enumerated by the generate_actions method.

        :param name: Action name string representing one of the items returned by generate_actions.
        :param params: Params data, as specified by generate_actions.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        :returns: No return value expected.
        """

        app = self.parent

        # call the actions from super
        super(CustomMayaActions, self).execute_action(name, params, sg_publish_data)

        # resolve path
        # toolkit uses utf-8 encoded strings internally and Maya API expects unicode
        # so convert the path to ensure filenames containing complex characters are supported
        path = self.get_publish_path(sg_publish_data).decode("utf-8")

        if name == "replace_reference":
            self._replace_reference(path, sg_publish_data)

        if name == "create_reference_with_shaders":
            self._create_reference_with_shaders(path, sg_publish_data)

        if name == "replace_reference_with_shaders":
            self._replace_reference_with_shaders(path, sg_publish_data)

        if name == "texture_node_with_frames":
            self._create_texture_node_with_frames(path, sg_publish_data)

        if name == "create_importable_reference":
            self._create_importable_reference(path, sg_publish_data)

    ##############################################################################################################
    # helper methods which can be subclassed in custom hooks to fine tune the behaviour of things

    def _create_texture_node_with_frames(self, path, sg_publish_data):
        """
        Create a file texture node for a texture

        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """

        # use mel command instead, since that creates the corresponding place2dtexture node with connections
        # file_node = cmds.shadingNode('file', asTexture=True)
        file_node = mel.eval('createRenderNodeCB -as2DTexture "" file ""')

        has_frame_spec, path = self._find_first_frame(path)
        cmds.setAttr("%s.fileTextureName" % file_node, path, type="string")

        if has_frame_spec:
            # setting the frame extension flag will create an expression to use
            # the current frame.
            cmds.setAttr("%s.useFrameExtension" % (file_node,), 1)
        return file_node

    def _create_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a texture
        
        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """

        # use mel command instead, since that creates the corresponding place2dtexture node with connections
        # file_node = cmds.shadingNode('file', asTexture=True)
        file_node = mel.eval('createRenderNodeCB -as2DTexture "" file ""')

        has_frame_spec, path = self._find_first_frame(path)
        # use the first frame instead of %04d, else maya errors out with "File Doesn't exist".
        cmds.setAttr("%s.fileTextureName" % file_node, path, type="string")
        return file_node

    def _create_udim_texture_node(self, path, sg_publish_data):
        """
        Create a file texture node for a UDIM (Mari) texture
        
        :param path:             Path to file.
        :param sg_publish_data:  Shotgun data dictionary with all the standard publish fields.
        :returns:                The newly created file node
        """
        # create the normal file node:
        file_node = self._create_texture_node(path, sg_publish_data)
        if file_node:
            # path is a UDIM sequence so set the uv tiling mode to 3 ('UDIM (Mari)')
            cmds.setAttr("%s.uvTilingMode" % file_node, 3)
            # and generate a preview:
            mel.eval("generateUvTilePreview %s" % file_node)
        return file_node

    def _find_first_frame(self, path):
        has_frame_spec = False
        # replace any %0#d format string with a glob character. then just find
        # an existing frame to use. example %04d => *
        frame_pattern = re.compile("(%0\dd)")
        frame_match = re.search(frame_pattern, path)
        if frame_match:
            has_frame_spec = True
            frame_spec = frame_match.group(1)
            glob_path = path.replace(frame_spec, "*")
            frame_files = glob.glob(glob_path)
            if frame_files:
                return has_frame_spec, frame_files[0]
            else:
                return has_frame_spec, None
        return has_frame_spec, path

    def _create_image_plane(self, path, sg_publish_data):
        """
        Create a file texture node for a UDIM (Mari) texture

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard
            publish fields.
        :returns: The newly created file node
        """

        app = self.parent

        has_frame_spec, path = self._find_first_frame(path)
        if not path:
            self.parent.logger.error(
                "Could not find file on disk for published file path %s" %
                (path,)
            )
            return

        # create an image plane for the supplied path, visible in all views
        (img_plane, img_plane_shape) = cmds.imagePlane(
            fileName=path,
            showInAllViews=True
        )
        app.logger.debug(
            "Created image plane %s with path %s" %
            (img_plane, path)
        )

        if has_frame_spec:
            # setting the frame extension flag will create an expression to use
            # the current frame.
            cmds.setAttr("%s.useFrameExtension" % (img_plane_shape,), 1)

    def _create_reference(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody
        namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")

        created_ref = pm.system.createReference(path, loadReferenceDepth="all", mergeNamespacesOnClash=False,
                                                namespace=namespace)

        return created_ref

    def _replace_reference(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """
        if not os.path.exists(path):
            raise Exception("File not found on disk - '%s'" % path)

        selected_objects = cmds.ls(sl=True, long=True)
        if not selected_objects:
            raise Exception("No Objects selected in the outliner.")

        # get unique references from the selection
        references_selected = list(set(
            [cmds.referenceQuery(selected_object, referenceNode=True, topReference=True) for selected_object in
             selected_objects]))
        if not references_selected:
            raise Exception("Selected objects are not referenced!")

        reference_object_mapping = dict(zip(references_selected, selected_objects))

        # make a name space out of entity name + publish name
        # e.g. bunny_upperbody
        namespace = "%s %s" % (sg_publish_data.get("entity").get("name"), sg_publish_data.get("name"))
        namespace = namespace.replace(" ", "_")

        # get the resolved file paths so it can be used to rename the correct Reference Node
        for selected_reference, selected_object in reference_object_mapping.iteritems():
            print 'file -loadReference "%s" "%s"' % (selected_reference, path)

            # reference the new file
            mel.eval('file -loadReference "%s" "%s"' % (selected_reference, path))

            # required to replace the namespace correctly, get the updated resolved path to update the RN
            resolved_file_path = cmds.referenceQuery(selected_reference, f=True)

            print 'file -e -namespace "%s" -referenceNode "%s" "%s"' % (
                namespace, selected_reference, resolved_file_path)

            # update the namespace of the file reference node
            mel.eval('file -e -namespace "%s" -referenceNode "%s" "%s"' % (
                namespace, selected_reference, resolved_file_path))

        print references_selected
        # return the references that the user modified.
        return references_selected

    def _create_reference_with_shaders(self, path, sg_publish_data):
        """
        Create a reference with the same settings Maya would use
        if you used the create settings dialog.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        created_ref = self._create_reference(path, sg_publish_data)
        self._connect_shaders_with_objects(created_ref, path, sg_publish_data)

    def _replace_reference_with_shaders(self, path, sg_publish_data):
        """
        re a reference with the same settings Maya would use
        if you used the create settings dialog.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        replaced_ref_list = self._replace_reference(path, sg_publish_data)
        self._connect_shaders_with_objects(replaced_ref_list, path, sg_publish_data)

    def _create_importable_reference(self, path, sg_publish_data):
        """
        Creates a Reference node that can be localized by our shelf button
        This should allow users to rename the top group if needed.

        :param path: Path to file.
        :param sg_publish_data: Shotgun data dictionary with all the standard publish fields.
        """

        created_ref = self._create_reference(path, sg_publish_data)

        # get all the top nodes in the above reference
        top_nodes = pm.ls("%s:*" % created_ref.namespace, assemblies=True)

        for top_node in top_nodes:
            if not top_node.hasAttr(IMPORTABLE_ATTR_NAME):
                # create the imported_name attr
                top_node.addAttr(IMPORTABLE_ATTR_NAME, dt="string")
                # ask the user for the name to be used after import
                self._create_ui(top_node)

    def _create_ui(self, node):
        result = cmds.promptDialog(
            title='Rename Object',
            message='Name after import for %s:' % node.name(),
            button=['Create Reference'])

        if result == 'Create Reference':
            imported_name = cmds.promptDialog(query=True, text=True)

            if not imported_name:
                response = cmds.confirmDialog(title='Imported Name is Empty!',
                                              message='Are you sure, you do NOT want to rename after import?',
                                              button=['Yes', 'No'], defaultButton='Yes',
                                              cancelButton='No', dismissString='No')

                if response == "No":
                    self._create_ui(node)

            else:
                # set the attr on the node, also create a safe string
                cmds.setAttr("%s.%s" % (node.name(), IMPORTABLE_ATTR_NAME),
                             urllib.quote(imported_name.replace(" ", "_"), safe=''),
                             type="string")

    def _connect_shaders_with_objects(self, ref_node_or_list, path, sg_publish_data):
        # get the shader shader_group
        shader_group = cmds.ls(SHADER_GROUP_NAME, long=True)
        if not shader_group:
            raise Exception("There is no %s group in the scene" % SHADER_GROUP_NAME)

        # this dict is mapping of {asset_id: {namespace_stripped_mesh_name: [shaders]}}
        src_mtl_mapping = dict()

        [src_mtl_mapping.update(self._get_mtl_mapping(lookdev_asset)) for lookdev_asset in
         cmds.listRelatives(shader_group, children=True, path=True)]

        if isinstance(ref_node_or_list, list):
            # process this as a list of references
            for ref_node in ref_node_or_list:
                self._assign_shaders_to_objects(src_mtl_mapping, ref_node)
        else:
            # this is a single reference just use it as it is
            self._assign_shaders_to_objects(src_mtl_mapping, ref_node_or_list)

    def _get_relevant_objects_from_ref_node(self, src_mtl_mapping, ref_node):

        child_nodes = cmds.referenceQuery(ref_node, nodes=True)

        relevant_nodes = list()
        # we need the object that matches objects from src_mtl_mapping
        for child in child_nodes:
            ns_stripped_object_name = pm.PyNode(child).stripNamespace()

            if ns_stripped_object_name in src_mtl_mapping:
                relevant_nodes.append(child)
            # if not cmds.listRelatives(child, parent=True):
            #     return child

        return relevant_nodes

    def _get_mtl_mapping(self, object_name, strip_mesh_namespace=True):
        src_mtl_mapping = dict()

        ns_stripped_object_name = pm.PyNode(object_name).stripNamespace()

        src_mtl_mapping[ns_stripped_object_name] = dict()

        # meshes contained inside the given object
        asset_meshes = cmds.listRelatives(object_name, ad=1, type=["mesh"])
        # this is the mapping of ns_stripped_mesh_name <-> shaders
        mesh_mtl_mapping = {
            pm.PyNode(asset_mesh).stripNamespace() if strip_mesh_namespace else asset_mesh: cmds.listConnections(
                asset_mesh,
                et=True,
                t='shadingEngine')
            for asset_mesh in asset_meshes}

        src_mtl_mapping[ns_stripped_object_name].update(mesh_mtl_mapping)

        return src_mtl_mapping

    def _assign_shaders_to_objects(self, src_mtl_mapping, ref_node):
        # get the base object of the ref node to query the current assignments.
        relevant_objects = self._get_relevant_objects_from_ref_node(src_mtl_mapping, ref_node)

        if not relevant_objects:
            raise Exception("No objects found in the reference that need shaders from Lookdev assets in the scene.")

        for relevant_object in relevant_objects:

            ns_stripped_object_name = pm.PyNode(relevant_object).stripNamespace()

            relevant_shaders = src_mtl_mapping[ns_stripped_object_name]

            # preserve the mesh full names since we need to assign the shader to these
            # current_assignments = self._get_mtl_mapping(relevant_object, strip_mesh_namespace=False).values()[0]

            # meshes contained inside the given object
            relevant_meshes = cmds.listRelatives(relevant_object, ad=1, type=["mesh"])
            # this is the mapping of ns_stripped_mesh_name <-> shaders
            mesh_identifier_mapping = {pm.PyNode(relevant_mesh).stripNamespace(): relevant_mesh for relevant_mesh in
                                       relevant_meshes}

            new_assignments = {relevant_mesh: relevant_shaders[identifier] for identifier, relevant_mesh in
                               mesh_identifier_mapping.iteritems()}
            # below method could give us wrong results since it's not an ordereddict
            # new_assignments = dict(zip(mesh_identifier_mapping.values(), relevant_shaders.values()))

            # do the assignments
            # https://forum.highend3d.com/t/python-how-to-assign-shader-to-an-object/48778/3

            for mesh_name, shader_list in new_assignments.iteritems():
                # mc.sets(objList, e=True, forceElement=shaderSG)
                print "Assigning %s with %s" % (mesh_name, shader_list)
                for shader in shader_list:
                    try:
                        cmds.sets(mesh_name, e=True, forceElement=shader)
                    except:
                        print "%s Shader assignment failed for %s" % (shader, mesh_name)
