# Copyright (c) 2017 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

import glob
import mari
import os
import sgtk

from tank import TankError
from tank import TemplatePath
from tank.templatekey import (IntegerKey, SequenceKey, StringKey)

HookBaseClass = sgtk.get_hook_baseclass()


class MariSessionCollector(HookBaseClass):
    """
    Collector that operates on the mari session. Should inherit from the basic
    collector hook.
    """

    def process_current_session(self, parent_item):
        """
        Analyzes the current session open in Mari and parents a subtree of
        items under the parent_item passed in.

        :param parent_item: Root item instance
        """

        # create an item representing the current mari session
        item = self.collect_current_mari_session(parent_item)
        project_root = item.properties["project_root"]

        # collect all the layer files
        self._collect_files(item)

        # if we can determine a project root, collect other files to publish
        if project_root:

            self.logger.info(
                "Current Mari project is: %s." % (project_root,),
                extra={
                    "action_button": {
                        "label": "Change Project",
                        "tooltip": "Change to a different Mari project, select it from the projects tab.",
                        "callback": lambda: mari.app.setActiveTab("Projects")
                    }
                }
            )

        else:

            self.logger.warning(
                "Could not determine the current Mari project.",
                extra={
                    "action_button": {
                        "label": "Set Project",
                        "tooltip": "Set the Mari project",
                        "callback": lambda: mari.app.setActiveTab("Projects")
                    }
                }
            )

    def collect_current_mari_session(self, parent_item):
        """
        Creates an item that represents the current mari session.

        :param parent_item: Parent Item instance
        :returns: Item of type mari.session
        """

        if not mari.projects.current():
            raise TankError("You must be in an open Mari project to be able to publish!")

        publisher = self.parent

        # get the path to the current file
        path = _project_path()

        # determine the display name for the item
        if path:
            display_name = mari.current.project().name()
        else:
            display_name = "Current Mari Project"

        # create the session item for the publish hierarchy
        session_item = parent_item.create_item(
            "mari.project",
            "Mari Project",
            display_name
        )

        # get the icon path to display for this item
        icon_path = os.path.join(
            self.disk_location,
            os.pardir,
            "icons",
            "mari.png"
        )
        session_item.set_icon_from_path(icon_path)

        # discover the project root which helps in discovery of other
        # publishable items
        project_root = _session_path()
        session_item.properties["project_root"] = project_root

        self.logger.info("Collected current Mari project")

        return session_item

    def _collect_files(self, parent_item):
        """
        Collect texture files to be published
        :param parent_item:   Parent Item instance
        """

        # check that we are currently inside a project:
        if not mari.projects.current():
            raise TankError("You must be in an open Mari project to be able to publish!")
        
        fields = {}

        #This template and keys are hard coded for now. They will be addressed in ticket # 44077
        publish_template_keys = {'Asset': StringKey('Asset'),
                                 'Step': StringKey('Step'), 
                                 'channel': StringKey('channel'), 
                                 'layer': StringKey('layer'), 
                                 'name': StringKey('name'), 
                                 'sg_asset_type': StringKey('sg_asset_type'), 
                                 'version': IntegerKey('version', format_spec='03')}
        publish_template = TemplatePath('assets/{sg_asset_type}/{Asset}/{Step}/publish/mari/{name}_{channel}[_{layer}].v{version}.tif', 
                                        publish_template_keys,
                                        self.tank.roots["primary"],
                                        None,
                                        None)

        # Get fields from the current context
        ctx_fields = self.parent.context.as_template_fields(publish_template)
        fields.update(ctx_fields)

        publisher = self.parent

        # Look for all layers for all channels on all geometry.  Create items for both
        # the flattened channel as well as the individual layers
        for geo in mari.geo.list():
            geo_name = geo.name()
            fields["name"] = geo_name
            
            for channel in geo.channelList():
                channel_name = channel.name()
                fields["channel"] = channel_name

                # find all publishable layers:
                publishable_layers = self._find_publishable_layers_r(channel.layerList())
                if not publishable_layers:
                    # no layers to publish!
                    continue

                # add item for whole flattened channel:
                item_name = "%s, %s" % (geo.name(), channel.name())
                
                # add item for each publishable layer:
                found_layer_names = set()
                for layer in publishable_layers:
                    
                    # for now, duplicate layer names aren't allowed!
                    layer_name = layer.name()
                    if layer_name in found_layer_names:
                        # we might want to handle this one day...
                        pass
                    found_layer_names.add(layer_name)

                    if layer:
                        fields["layer"] = layer_name

                    publish_name_fields = fields.copy()
                    publish_name_fields["version"] = 0
                    publish_name = publisher.util.get_publish_name(publish_template.apply_fields(publish_name_fields))

                    existing_publishes = self._find_publishes(self.parent.context, publish_name, "Tif File")
                    version = max([p["version_number"] for p in existing_publishes] or [0]) + 1
                    fields["version"] = version

                    publish_path = publish_template.apply_fields(fields)

                    # allow the base class to collect and create the item. it knows how
                    # to handle alembic files
                    item = super(MariSessionCollector, self)._collect_file(parent_item, publish_path)

                    item.properties["geo_publish_name"] = geo_name
                    item.properties["channel_publish_name"] = channel_name
                    item.properties["layer_publish_name"] = layer_name

    def _find_publishable_layers_r(self, layers):
        """
        Find all publishable layers within the specified list of layers.  This will return
        all layers that are either paintable or procedural and traverse any layer groups
        to find all grouped publishable layers
        :param layers:  The list of layers to inspect
        :returns:       A list of all publishable layers
        """
        publishable = []
        for layer in layers:
            # Note, only paintable or procedural layers are exportable from Mari - all
            # other layer types are only used within Mari.
            if layer.isPaintableLayer() or layer.isProceduralLayer():
                # these are the only types of layers that are publishable
                publishable.append(layer)
            elif layer.isGroupLayer():
                # recurse over all layers in the group looking for exportable layers:
                grouped_layers = self._find_publishable_layers_r(layer.layerStack().layerList())
                publishable.extend(grouped_layers or [])
    
        return publishable

    def _find_publishes(self, ctx, publish_name, publish_type):
        """
        Given a context, publish name and type, find all publishes from Shotgun
        that match.
        
        :param ctx:             Context to use when looking for publishes
        :param publish_name:    The name of the publishes to look for
        :param publish_type:    The type of publishes to look for
        
        :returns:               A list of Shotgun publish records that match the search
                                criteria        
        """
        publish_entity_type = sgtk.util.get_published_file_entity_type(self.parent.sgtk)
        if publish_entity_type == "PublishedFile":
            publish_type_field = "published_file_type.PublishedFileType.code"
        else:
            publish_type_field = "tank_type.TankType.code"
        
        # construct filters from the context:
        filters = [["project", "is", ctx.project]]
        if ctx.entity:
            filters.append(["entity", "is", ctx.entity])
        if ctx.task:
            filters.append(["task", "is", ctx.task])
            
        # add in name & type:
        if publish_name:
            filters.append(["name", "is", publish_name])
        if publish_type:
            filters.append([publish_type_field, "is", publish_type])
            
        # retrieve a list of all matching publishes from Shotgun:
        sg_publishes = []
        try:
            query_fields = ["version_number"]
            sg_publishes = self.parent.shotgun.find(publish_entity_type, filters, query_fields)
        except Exception, e:
            raise TankError("Failed to find publishes of type '%s', called '%s', for context %s: %s" 
                            % (publish_name, publish_type, ctx, e))
        return sg_publishes

def _project_path():
    """
    Return the path to the current session
    :return:
    """
    path = None
    current_project = mari.projects.current()
    if current_project:
        path = current_project.info().projectPath()

    if isinstance(path, unicode):
        path = path.encode("utf-8")

    return path

def _session_path():
    """
    Return the path to the current session
    :return:
    """
    path = None
    current_project = mari.projects.current()
    if current_project:
        path = current_project.uuid()

    if isinstance(path, unicode):
        path = path.encode("utf-8")

    return path
