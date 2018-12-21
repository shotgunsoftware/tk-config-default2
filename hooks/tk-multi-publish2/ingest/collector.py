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
    "file": {
        "id": "sg_snapshot_id",
        "notes": "description",
        "user": "snapshot_user",
        "name": "manifest_name",
        "version": "snapshot_version",
    },
    "note": {
        "notes": "description",
        "name": "snapshot_name",
        "user": "snapshot_user",
        "version": "snapshot_version",
        "body": "content",
    },
}

# This is a dictionary of note_type values to item type.
DEFAULT_NOTE_TYPES_MAPPINGS = {
    "kickoff": "kickoff",
    "role supervisor": "annotation",
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
            "default_value": self.parent.settings["default_snapshot_type"].value,
        }
        items_schema["default_fields"] = {
            "type": dict,
            "values": {
                "type": "str",
            },
            "allows_empty": True,
            "default_value": {},
            "description": "Default fields to use, with this item"
        }
        schema["Manifest SG Mappings"] = {
            "type": "dict",
            "values": {
                "type": "dict",
                "values": {
                    "type": "str",
                },
            },
            "default_value": DEFAULT_MANIFEST_SG_MAPPINGS,
            "allows_empty": True,
            "description": "Mapping of keys in Manifest to SG template keys."
        }
        schema["Note Type Mappings"] = {
            "type": "dict",
            "values": {
                "type": "str",
            },
            "default_value": DEFAULT_NOTE_TYPES_MAPPINGS,
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
        work_path_template = self._get_work_path_template_from_settings(settings,
                                                                         item.type,
                                                                         os.path.basename(path))
        if work_path_template:
            return work_path_template

        return super(IngestCollectorPlugin, self)._resolve_work_path_template(settings, item)

    def _add_note_item(self, settings, parent_item, fields, is_sequence=False, seq_files=None):
        """
        Process the supplied list of attachments, and create a note item.

        :param dict settings: Configured settings for this collector
        :param parent_item: parent item instance
        :param fields: Fields from manifest

        :returns: The item that was created
        """

        publisher = self.parent

        note_type_mappings = settings["Note Type Mappings"].value

        raw_item_settings = settings["Item Types"].raw_value

        manifest_note_type = fields["note_type"]

        if manifest_note_type not in note_type_mappings:
            self.logger.error(
                "Note type not recognized %s" % manifest_note_type,
                extra={
                    "action_show_more_info": {
                        "label": "Valid Types",
                        "tooltip": "Show Valid Note Types",
                        "text": "Valid Note Type Mappings: %s" % (pprint.pformat(note_type_mappings),)
                    }
                }
            )
            return

        path = fields["sg_version"]["name"] + ".%s" % note_type_mappings[manifest_note_type]
        display_name = path + ".notes"

        item_type = "notes.entity.%s" % note_type_mappings[manifest_note_type]

        relevant_item_settings = raw_item_settings[item_type]
        raw_template_name = relevant_item_settings.get("work_path_template")
        envs = self.parent.sgtk.pipeline_configuration.get_environments()

        # type_display = relevant_item_settings.get("type_display", "File")
        # work_path_template = None
        # icon_path = relevant_item_settings.get("icon", "{self}/hooks/icons/file.png")
        work_path_template = None

        template_names_per_env = [
            sgtk.platform.resolve_setting_expression(raw_template_name, self.parent.engine.instance_name, env_name) for
            env_name in envs]

        templates_per_env = [self.parent.get_template_by_name(template_name) for template_name in
                             template_names_per_env if self.parent.get_template_by_name(template_name)]
        for template in templates_per_env:
            if template.validate(path):
                # we have a match!
                work_path_template = template.name

        if work_path_template:
            # calculate the context and give to the item
            context = self._get_item_context_from_path(work_path_template, path, parent_item)

            file_item = self._add_file_item(settings, parent_item, path, item_name=display_name,
                                            item_type=item_type, context=context)

            return file_item
        else:
            self.logger.warning("No matching template found for %s with raw template %s" % (path,
                                                                                            raw_template_name))
            return

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
            if publisher.settings["manifest_file_name"].value in os.path.basename(path):
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

            item_info = self._get_item_type_info(settings, file_item.type)

            if "snapshot_type" not in fields:
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

            # check for default fields those and add those fields if not already present on item.
            if "default_fields" in item_info:
                for key, value in item_info["default_fields"].iteritems():
                    if key not in fields:
                        fields[key] = value

        return file_items

    def _process_manifest_file(self, settings, path):
        """
        Do the required processing on the yaml file, sanitisation or validations.
        conversions mentioned in Manifest Types setting of the collector hook.

        :param path: path to yaml file
        :return: list of processed snapshots, in the format
        [{file(type of collect method to run):
            {'fields': {'context_type': 'maya_model',
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
            }
        }]
        """

        processed_snapshots = list()
        manifest_mappings = settings["Manifest SG Mappings"].value

        file_item_manifest_mappings = manifest_mappings["file"]
        note_item_manifest_mappings = manifest_mappings["note"]
        # yaml file stays at the base of the package
        base_dir = os.path.dirname(path)

        snapshots = list()
        notes = list()
        notes_index = 0

        with open(path, 'r') as f:
            try:
                contents = yaml.load(f)
                snapshots = contents["snapshots"]
                if "notes" in contents:
                    notes = contents["notes"]
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
            data["fields"] = {file_item_manifest_mappings[k] if k in file_item_manifest_mappings else k: v
                              for k, v in snapshot.iteritems()}

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

            processed_snapshots.append({"file": data})

        for note in notes:
            # first replace all the snapshot with the Manifest SG Mappings

            data = dict()
            snapshot_data = dict()
            data["fields"] = {note_item_manifest_mappings[k] if k in note_item_manifest_mappings else k: v
                              for k, v in note.iteritems()}

            # every note item has a corresponding snapshot associated with it
            if notes_index >= len(snapshots):
                break

            note_snapshot = snapshots[notes_index]
            snapshot_data["fields"] = {file_item_manifest_mappings[k] if k in file_item_manifest_mappings else k: v
                                       for k, v in note_snapshot.iteritems()}

            # pop the files from snapshot_data they are not useful
            snapshot_data["fields"].pop("file_types")

            # update the item fields with snapshot_data fields
            data["fields"].update(snapshot_data["fields"])

            # let's process the attachments now!
            data["files"] = dict()
            attachments = data["fields"].pop("attachments")

            if attachments:
                # add one path of attachment for template parsing
                append_path = os.path.join(base_dir, attachments[0]["path"])

                if append_path not in data["files"]:
                    data["files"][append_path] = list()

            # re-create the attachments field for later use by publish
            data["fields"]["attachments"] = list()

            for attachment in attachments:
                data["fields"]["attachments"].append(os.path.join(base_dir, attachment["path"]))

            processed_snapshots.append({"note": data})

            # move to the next snapshot
            notes_index += 1

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
        processed_entities = self._process_manifest_file(settings, path)

        file_items = list()

        for entity in processed_entities:
            for hook_type, item_data in entity.iteritems():
                files = item_data["files"]
                for p_file, tags in files.iteritems():
                    # fields and items setup
                    fields = item_data["fields"].copy()
                    new_items = list()

                    # file type entity
                    if hook_type == "file":
                        # we need to add tag entities to this field.
                        # let's query/create those first.
                        fields["tags"] = self._query_associated_tags(tags)
                        if os.path.isdir(p_file):
                            items = self._collect_folder(settings, parent_item, p_file)
                            if items:
                                new_items.extend(items)
                        else:
                            item = self._collect_file(settings, parent_item, p_file)
                            if item:
                                new_items.append(item)
                    # note type item
                    elif hook_type == "note":
                        # create a note item
                        item = self._add_note_item(settings, parent_item, fields=fields)
                        if item:
                            if "snapshot_name" in fields:
                                item.description = fields["snapshot_name"]

                            new_items.append(item)

                    # inject the new fields into the item
                    for new_item in new_items:
                        item_fields = new_item.properties["fields"]
                        item_fields.update(fields)

                        if not new_item.description:
                            # adding a default description to item
                            new_item.description = "Created by shotgun_ingest on %s" % str(datetime.date.today())

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

    def _get_work_path_template_from_settings(self, settings, item_type, path):
        """
        Helper method to get the work_path_template from the collector settings object.
        """
        # first try with filename
        work_path_template = super(IngestCollectorPlugin, self)._get_work_path_template_from_settings(settings,
                                                                                                      item_type,
                                                                                                      os.path.basename(path))
        if work_path_template:
            return work_path_template

        return super(IngestCollectorPlugin, self)._get_work_path_template_from_settings(settings,
                                                                                        item_type,
                                                                                        path)

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
