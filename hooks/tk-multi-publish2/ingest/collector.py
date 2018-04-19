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

# This is a dictionary of file type info that allows the basic collector to
# identify common production file types and associate them with a display name,
# item type, and config icon.
DEFAULT_MANIFEST_SG_MAPPINGS = {
    "id": "sg_snapshot_id",
    "notes": "description",
    "name": "snapshot_name",
    "user": "snapshot_user",
}


class IngestCollectorPlugin(HookBaseClass):
    """
    Collector that operates on the current set of ingestion files. Should
    inherit from the basic collector hook.

    This instance of the hook uses manifest_file_name from app_settings.


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

    def _resolve_work_path_template(self, properties, path):
        """
        Resolve work_path_template from the properties.
        The signature uses properties, so that it can resolve the template even if the item object hasn't been created.

        :param properties: properties that have/will be used to build item object.
        :param path: path to be used to get the templates, using template_from_path,
         in this class we use os.path.basename of the path.
        :return: Name of the template.
        """

        # try using file name for resolving templates
        work_path_template = super(IngestCollectorPlugin, self)._resolve_work_path_template(properties,
                                                                                            os.path.basename(path))
        # try using the full path for resolving templates
        if not work_path_template:
            work_path_template = super(IngestCollectorPlugin, self)._resolve_work_path_template(properties, path)

        return work_path_template

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

        # handle files and folders differently
        if os.path.isdir(path):
            return self._collect_folder(settings, parent_item, path)
        else:
            if os.path.basename(path) == publisher.settings["manifest_file_name"]:
                return self._collect_manifest_file(settings, parent_item, path)
            else:
                item = self._collect_file(settings, parent_item, path)
                return [item] if item else []

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
                    'name': 'egypt_riser_a',
                    'sg_asset_type': 'maya_model',
                    'sg_snapshot_id': 1002060803L,
                    'subcontext': 'hi',
                    'type': 'asset',
                    'user': 'rsariel',
                    'version': 1},
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
                p_file = files["files"][0]["path"]
                p_file = os.path.join(base_dir, p_file)
                # let's pick the first file and let the collector run _collect_folder on this
                # since this is already a file sequence
                if "frame_range" in files:
                    append_path = os.path.dirname(p_file)
                # not a file sequence store the file name, to run _collect_file
                else:
                    # list of tags
                    append_path = p_file

                # list of tags
                if append_path not in data["files"]:
                    data["files"][append_path] = list()
                data["files"][append_path].append(file_type)

            processed_snapshots.append(data)

        return processed_snapshots

    def _collect_manifest_file(self, settings, parent_item, path):
        """
        Process the supplied manifest file.

        :param dict settings: Configured settings for this collector
        :param parent_item: parent item instance
        :param folder: Path to analyze

        :returns: The item that was created
        """

        snapshots = self._process_manifest_file(settings, path)

        file_items = list()

        for snapshot in snapshots:
            files = snapshot["files"]
            for p_file, tags in files.iteritems():
                fields = snapshot["fields"].copy()
                fields["tags"] = tags
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

                    # we can't let the user change the context of the ingested file
                    new_item.context_change_allowed = False

                # put the new items back in collector
                file_items.extend(new_items)

        return file_items

    def _get_item_context_from_path(self, parent_item, properties, path, default_entities=list()):
        """Updates the context of the item from the work_path_template/template, if needed.

        :param properties: properties of the item.
        :param path: path to build the context from, in this class we use os.path.basename of the path.
        """

        sg_filters = [
            ['short_name', 'is', "vendor"]
        ]

        fields = ['entity_type', 'code', 'id']

        step_entity = self.sgtk.shotgun.find_one(
            entity_type='Step',
            filters=sg_filters,
            fields=fields
        )
        default_entities = [step_entity]

        work_path_template = self._resolve_work_path_template(properties, path)

        if work_path_template:
            work_tmpl = self.parent.get_template_by_name(work_path_template)
            if work_tmpl and isinstance(work_tmpl, tank.template.TemplateString):
                # use file name if we got TemplateString
                path = os.path.basename(path)

        item_context = super(IngestCollectorPlugin, self)._get_item_context_from_path(parent_item,
                                                                                      properties,
                                                                                      path,
                                                                                      default_entities)

        return item_context

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
