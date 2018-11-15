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
import datetime
import traceback
import pprint

import sgtk
import tank
from tank_vendor import yaml

HookBaseClass = sgtk.get_hook_baseclass()

# This is a dictionary of fields in snapshot from manifest and it's corresponding field on the item.
DEFAULT_MANIFEST_SG_MAPPINGS = {
    "id": "sg_snapshot_id",
    "notes": "description",
    "name": "snapshot_name",
    "user": "snapshot_user",
    "version": "snapshot_version",
}


class IngestCollectorPlugin(HookBaseClass):
    """
    Collector that operates on the current set of ingestion files. Should
    inherit from the basic collector hook.

    This instance of the hook uses manifest_file_name, default_entity_type, default_snapshot_type from app_settings.

    """

    @property
    def settings_schema(self):
        """
        Dictionary defining the settings that this collector expects to receive
        through the settings parameter in the process_current_session and
        process_file methods.

        A dictionary on the following form::

            {
                "Settings Name": {
                    "type": "settings_type",
                    "default_value": "default_value",
                    "description": "One line description of the setting"
            }

        The type string should be one of the data types that toolkit accepts as
        part of its environment configuration.
        """
        schema = super(IngestCollectorPlugin, self).settings_schema
        items_schema = schema["Item Types"]["values"]["items"]
        items_schema["default_snapshot_type"] = {
            "type": "str",
            "description": "",
            "allows_empty": True,
            "default_value": self.parent.settings["default_snapshot_type"],
        }
        schema["Manifest SG Mappings"] = {
            "type": "dict",
            "values": {
                "type": "str",
            },
            "default_value": DEFAULT_MANIFEST_SG_MAPPINGS,
            "allows_empty": True,
            "description": "Mapping of keys in Manifest to SG template keys."
        }
        return schema

    def _resolve_work_path_template(self, settings, item):
        """
        Resolve work_path_template from the collector settings for the specified item.

        :param dict settings: Configured settings for this collector
        :param item: The Item instance
        :return: Name of the template.
        """
        path = item.properties.get("path")
        if not path:
            return None

        # try using the basename for resolving the template
        work_path_template = self.__get_work_path_template_from_settings(settings,
                                                                         item.type,
                                                                         os.path.basename(path))
        if work_path_template:
            return work_path_template

        return super(IngestCollectorPlugin, self)._resolve_work_path_template(settings, item)

    def process_file(self, settings, parent_item, path):
        """
        Analyzes the given file and creates one or more items
        to represent it.

        :param dict settings: Configured settings for this collector
        :param parent_item: Root item instance
        :param path: Path to analyze

        :returns: The main item that was created, or None if no item was created
            for the supplied path
        """

        publisher = self.parent

        file_items = list()

        # handle Manifest files, Normal files and folders differently
        if os.path.isdir(path):
            items = self._collect_folder(settings, parent_item, path)
            if items:
                file_items.extend(items)
        else:
            if publisher.settings["manifest_file_name"] in os.path.basename(path):
                items = self._collect_manifest_file(settings, parent_item, path)
                if items:
                    file_items.extend(items)
            else:
                item = self._collect_file(settings, parent_item, path)
                if item:
                    file_items.append(item)

        # make sure we have snapshot_type field in all the items!
        # this is to make sure that on publish we retain this field to figure out asset creation is needed or not.
        for file_item in file_items:
            fields = file_item.properties["fields"]
            if "snapshot_type" not in fields:
                item_info = self._get_item_type_info(settings, item.type)

                fields["snapshot_type"] = item_info["default_snapshot_type"]
                # CDL files should always be published as Asset entity with nuke_avidgrade asset_type
                # this is to match organic, and also for Avid grade lookup on shotgun
                # this logic has been moved to _get_item_type_info by defining default_snapshot_type for each item type
                # if file_item.type == "file.cdl":
                #     fields["snapshot_type"] = "nuke_avidgrade"

                self.logger.info(
                    "Injected snapshot_type field for item: %s" % file_item.name,
                    extra={
                        "action_show_more_info": {
                            "label": "Show Info",
                            "tooltip": "Show more info",
                            "text": "Updated fields:\n%s" %
                                    (pprint.pformat(file_item.properties["fields"]))
                        }
                    }
                )

        return file_items

    def _process_manifest_file(self, settings, path):
        """
        Do the required processing on the yaml file, sanitisation or validations.
        conversions mentioned in Manifest Types setting of the collector hook.

        :param path: path to yaml file
        :return: list of processed snapshots, in the format
        [{'fields': {'context_type': 'maya_model',
                    'department': 'model',
                    'description': 'n/a',
                    'instance_name': None,
                    'level': None,
                    'snapshot_name': 'egypt_riser_a',
                    'snapshot_type': 'maya_model',
                    'sg_snapshot_id': 1002060803L,
                    'subcontext': 'hi',
                    'type': 'asset',
                    'snapshot_user': 'rsariel',
                    'snapshot_version': 1},
         'files': {'/dd/home/gverma/work/SHARED/MODEL/enviro/egypt_riser_a/hi/maya_model/egypt_riser_a_hi_tag_v001.xml': ['tag_xml'],
                   '/dd/home/gverma/work/SHARED/MODEL/enviro/egypt_riser_a/hi/maya_model/egypt_riser_a_hi_transform_v001.xml': ['transform_xml'],
                   '/dd/home/gverma/work/SHARED/MODEL/enviro/egypt_riser_a/hi/maya_model/egypt_riser_a_hi_v001.mb': ['main', 'mayaBinary']}
         }]
        """

        processed_snapshots = list()
        manifest_mappings = settings['Manifest SG Mappings'].value
        # yaml file stays at the base of the package
        base_dir = os.path.dirname(path)

        with open(path, 'r') as f:
            try:
                snapshots = yaml.load(f)
                snapshots = snapshots["snapshots"]
            except Exception:
                self.logger.error(
                    "Failed to read the manifest file %s" % path,
                    extra={
                        "action_show_more_info": {
                            "label": "Show Error Log",
                            "tooltip": "Show the error log",
                            "text": traceback.format_exc()
                        }
                    }
                )
                return processed_snapshots

        for snapshot in snapshots:
            # first replace all the snapshot with the Manifest SG Mappings
            data = dict()
            data["fields"] = {manifest_mappings[k] if k in manifest_mappings else k: v for k, v in snapshot.items()}

            # let's process file_types now!
            data["files"] = dict()
            file_types = data["fields"].pop("file_types")
            for file_type, files in file_types.iteritems():
                if "frame_range" in files:
                    p_file = files["files"][0]["path"]
                    p_file = os.path.join(base_dir, p_file)
                    # let's pick the first file and let the collector run _collect_folder on this
                    # since this is already a file sequence
                    append_path = os.path.dirname(p_file)
                    # list of tag names
                    if append_path not in data["files"]:
                        data["files"][append_path] = list()
                    data["files"][append_path].append(file_type)
                # not a file sequence store the file names, to run _collect_file
                else:
                    p_files = files["files"]
                    for p_file in p_files:
                        append_path = os.path.join(base_dir, p_file["path"])

                        # list of tag names
                        if append_path not in data["files"]:
                            data["files"][append_path] = list()
                        data["files"][append_path].append(file_type)

            processed_snapshots.append(data)

        return processed_snapshots

    def _query_associated_tags(self, tags):
        """
        Queries/Creates tag entities given a list of tag names.

        :param tags: List of tag names.
        :return: List of created/existing tag entities.
        """

        tag_entities = list()

        fields = ["name", "id", "code", "type"]
        for tag_name in tags:
            tag_entity = self.sgtk.shotgun.find_one(entity_type="Tag", filters=[["name", "is", tag_name]], fields=fields)
            if tag_entity:
                tag_entities.append(tag_entity)
            else:
                try:
                    new_entity = self.sgtk.shotgun.create(entity_type="Tag", data=dict(name=tag_name))
                    tag_entities.append(new_entity)
                except Exception:
                    self.logger.error(
                        "Failed to create Tag: %s" % tag_name,
                        extra={
                            "action_show_more_info": {
                                "label": "Show Error log",
                                "tooltip": "Show the error log",
                                "text": traceback.format_exc()
                            }
                        }
                    )
        return tag_entities

    def _collect_manifest_file(self, settings, parent_item, path):
        """
        Process the supplied manifest file.

        :param dict settings: Configured settings for this collector
        :param parent_item: parent item instance
        :param path: Path to analyze

        :returns: The item that was created
        """

        # process the manifest file first, replace the fields to relevant names.
        # collect the tags a file has too.
        snapshots = self._process_manifest_file(settings, path)

        file_items = list()

        for snapshot in snapshots:
            files = snapshot["files"]
            for p_file, tags in files.iteritems():
                fields = snapshot["fields"].copy()
                # we need to add tag entities to this field.
                # let's query/create those first.
                fields["tags"] = self._query_associated_tags(tags)
                new_items = list()
                if os.path.isdir(p_file):
                    items = self._collect_folder(settings, parent_item, p_file)
                    if items:
                        new_items.extend(items)
                else:
                    item = self._collect_file(settings, parent_item, p_file)
                    if item:
                        new_items.append(item)

                # inject the new fields into the item
                for new_item in new_items:
                    item_fields = new_item.properties["fields"]
                    item_fields.update(fields)

                    self.logger.info(
                        "Updated fields from snapshot for item: %s" % new_item.name,
                        extra={
                            "action_show_more_info": {
                                "label": "Show Info",
                                "tooltip": "Show more info",
                                "text": "Updated fields:\n%s" %
                                        (pprint.pformat(new_item.properties["fields"]))
                            }
                        }
                    )

                    # we can't let the user change the context of the file being ingested using manifest files
                    new_item.context_change_allowed = False

                # put the new items back in collector
                file_items.extend(new_items)

        return file_items

    def _get_item_context_from_path(self, work_path_template, path, parent_item, default_entities=list()):
        """Updates the context of the item from the work_path_template/template, if needed.

        :param work_path_template: The work_path template name
        :param item: item to build the context for
        :param parent_item: parent item instance
        :param default_entities: a list of default entities to use during the creation of the
        :class:`sgtk.Context` if not found in the path
        """
        publisher = self.parent

        sg_filters = [
            ['short_name', 'is', "vendor"]
        ]

        # TODO-- this is not needed right now, since our keys only depend on short_name key of the Step
        # make sure we get the correct Step!
        # if base_context.entity:
        #     # this should handle whether the Step is from Sequence/Shot/Asset
        #     sg_filters.append(["entity_type", "is", base_context.entity["type"]])
        # elif base_context.project:
        #     # this should handle pro
        #     sg_filters.append(["entity_type", "is", base_context.project["type"]])

        fields = ['entity_type', 'code', 'id']

        # add a vendor step to all ingested files
        step_entity = self.sgtk.shotgun.find_one(
            entity_type='Step',
            filters=sg_filters,
            fields=fields
        )

        default_entities = [step_entity]

        work_tmpl = publisher.get_template_by_name(work_path_template)
        if work_tmpl and isinstance(work_tmpl, tank.template.TemplateString):
            # use file name if we got TemplateString
            path = os.path.basename(path)

        return super(IngestCollectorPlugin, self)._get_item_context_from_path(work_path_template,
                                                                              path,
                                                                              parent_item,
                                                                              default_entities)

    def _get_template_fields_from_path(self, item, template_name, path):
        """
        Get the fields by parsing the input path using the template derived from
        the input template name.
        """

        work_path_template = item.properties.get("work_path_template")

        if work_path_template:
            work_tmpl = self.parent.get_template_by_name(work_path_template)
            if work_tmpl and isinstance(work_tmpl, tank.template.TemplateString):
                # use file name if the path was parsed using TemplateString
                path = os.path.basename(path)

        fields = super(IngestCollectorPlugin, self)._get_template_fields_from_path(item,
                                                                                   template_name,
                                                                                   path)
        # adding a description to item
        item.description = "Created by shotgun_ingest on %s" % str(datetime.date.today())
        return fields
