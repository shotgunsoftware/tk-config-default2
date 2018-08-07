import os
import sgtk
import copy
import pprint
import re

from xml.dom import minidom

HookBaseClass = sgtk.get_hook_baseclass()

# This is a dictionary containing name of folder next to dd/library as key and regex pattern as values.
# Regex pattern should have at least two capture groups because first capture group will be snapshot type
# and second will be name. To add more regex pattern add in sgtk_config_envioronments_library .
DEFAULT_VALID_LIBRARY_ELEMENTS = {
    "elem": ["^\/dd\/library\/elem\/(.*)\/(.*)\/(.*)\/orig"]
}


class LibraryIngestCollectorPlugin(HookBaseClass):
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
        schema = super(LibraryIngestCollectorPlugin, self).settings_schema
        schema["Valid Library Elements"] = {
            "type": "dict",
            "values": {
                "type": "str",
            },
            "default_value": DEFAULT_VALID_LIBRARY_ELEMENTS,
            "allows_empty": True,
            "description": "List of Library elements this collector can ingest."
        }

        return schema

    def _process_manifest_file(self, settings, path):
        """
        Do the required processing on the yaml file, sanitisation or validations.
        conversions mentioned in Manifest Types setting of the collector hook.

        :param dict settings: Configured settings for this collector
        :param path: path to mxp file
        :return: list of processed snapshots, in the format
        [{'fields': {'name': '111C_TILE_1_pt2', 'snapshot_type': 'terrain_forest'},
          'files': {'/dd/library/elem/terrain/forest/111c_tile_1_pt2/orig/': ['terrain',
                                                                      'forest',
                                                                      '111C_TILE_1_pt2',
                                                                      'BRIAR',
                                                                      'maleficent',
                                                                      'trees',
                                                                      'forest',
                                                                      'tile']}}]
        """

        # mxp processing
        template = {'fields': {'name': '', 'snapshot_type': ''}, 'files': {}}

        xmldoc = minidom.parse(path)

        doc_element = xmldoc.documentElement
        frame_tags = doc_element.getElementsByTagName("item")

        template_list = []

        for frame_tag in frame_tags:
            template_copy = copy.deepcopy(template)

            attrs = frame_tag.attributes

            lst = ['Name', 'Category', 'Subcategory', 'OriginalsPath', 'Keywords']
            store_attr = {}

            # get attributes from mxp and stores it in a dictionary and then the key value pair is used to make template
            # dictionary that can be processed by shotgun
            for attr, value in attrs.items():
                if attr in lst:
                    store_attr[str(attr)] = str(value)

            originals_path = store_attr.get('OriginalsPath')
            if ' ' in originals_path:
                originals_path = originals_path.replace(' ', '')

            valid_library_elements, key_category = self.validate_library_path(settings, originals_path)

            if os.path.exists(store_attr.get('OriginalsPath')):

                if valid_library_elements:
                    template_copy['fields']['name'] = self.invalid_char_to_underscore(store_attr.get('Name').strip())
                    template_copy['fields']['snapshot_type'] = \
                        self.invalid_char_to_underscore(key_category + "_" + store_attr.get('Category').strip())
                    tags = []

                    if store_attr.get('Keywords') and ',' in store_attr.get('Keywords'):
                        tag_list = filter(None, [store_attr.get('Category'), store_attr.get('Subcategory'), store_attr.get('Name')]+store_attr.get('Keywords').split(','))
                    else:
                        tag_list = filter(None, [store_attr.get('Category'), store_attr.get('Subcategory'), store_attr.get('Name')])

                    # update tags
                    [tags.append(self.invalid_char_to_underscore(each.strip())) for each in tag_list]

                    template_copy['files'][store_attr.get('OriginalsPath')] = tags

                    template_list.append(template_copy)
                else:
                    self.logger.error(
                        "Path %s does not match with template." % store_attr.get('OriginalsPath'))
            else:
                self.logger.error(
                    "Path %s does not exist." % store_attr.get('OriginalsPath'))

        return template_list


    @staticmethod
    def invalid_char_to_underscore(value):
        """
        Removes whitespace and special characters from string
        :param value: string
        :return: string having special characters replaced with underscore.
        """
        if re.match("^[a-zA-Z0-9_]*$", value):
            return value
        else:
            return re.sub('[^a-zA-Z0-9]+', '_', value)

    def folder_crawl(self, settings, path):
        """
        takes path having at least two capture groups as string input and returns a dictionary
        for ex -
                 path =         /dd/library/elem/[1]/[2]/orig
                 return dict =  {'name': [2], 'snapshot_type': elem_[1]}

        :param dict settings: Configured settings for this collector
        :param path: path to files
        :return: snapshot dict

        """

        fields = {}
        # get regex match object in valid_lib_path_pattern
        valid_lib_path_pattern, key_category = self.validate_lib_path_pattern(settings, path)
        if valid_lib_path_pattern:
            get_dir_name = valid_lib_path_pattern.groups()
            fields = {'name': self.invalid_char_to_underscore(get_dir_name[-1].strip()),
                      'snapshot_type': self.invalid_char_to_underscore((key_category + '_'
                                                                        + str(get_dir_name[0])).strip())}
            # fields = {'name': get_dir_name[-1]}
        else:
            self.logger.error("Path %s does not match with template." % path)

        return fields

    def validate_lib_path_pattern(self, settings, path):
        """
        takes path having at least two capture groups as string input and checks for /dd/library in path and matches it
        with the regex defined in sgtk_config_environments_library.yaml and then
        returns -
                 lib_path_pattern - regex match object
                 key_category     - folder name next to /dd/library as string.

        :param dict settings: Configured settings for this collector
        :param path: path to files
        :return: regex match object after comparing path with regex pattern and name of folder next to /dd/library.
        """

        publisher = self.parent

        # get regex pattern from tk-multi-publish2 template
        library_base_path = publisher.settings["library_base_path"]
        lib_path_pattern = None
        reg = re.compile(library_base_path)
        # get list of path regex from sgtk_config_templates_library template
        valid_library_elements = settings['Valid Library Elements'].value
        matched_path = reg.match(path)
        key_category = None
        if matched_path:
            key_category = (matched_path.groups())[0]
            path_pattern_list = valid_library_elements.get(key_category)
            for path_pattern in path_pattern_list:
                path_pattern_reg = re.compile(path_pattern)
                lib_path_pattern = path_pattern_reg.match(path)
                if lib_path_pattern:
                    break
            # print lib_path_pattern

        return lib_path_pattern, key_category

    def validate_library_path(self, settings, path):
        """
        takes path having at least two capture groups as string input and returns capture groups from the path as
        path_tags and name of folder next to /dd/library/ as key_category

        :param dict settings: Configured settings for this collector
        :param path: path to files
        :return: name of varying folders in path as list of strings and name of folder next to /dd/library.
        """

        path_tags = None
        # get regex match object in valid_lib_path_pattern
        valid_lib_path_pattern, key_category = self.validate_lib_path_pattern(settings, path)
        if valid_lib_path_pattern:
            path_tags = list(valid_lib_path_pattern.groups())

        return path_tags, key_category

    def update_item_field(self, settings, item, path, valid_library_elements):
        """
        update the new fields in item.

        :param dict settings: Configured settings for this collector
        :param item: Root item instance
        :param path: path to files
        :param valid_library_elements: name of varying folders in path as list of strings
        :return: name of varying folders in path as list of strings.
        """

        new_items = list()

        add_fields = self.folder_crawl(settings, path)
        tags = [self.invalid_char_to_underscore(each.strip()) for each in valid_library_elements]
        add_fields["tags"] = self._query_associated_tags(tags)
        try:
            new_items.extend(item)
        except TypeError:
            new_items.append(item)

        # inject the new fields into the item
        for new_item in new_items:
            item_fields = new_item.properties["fields"]
            item_fields.update(add_fields)
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
        return new_items

    def _valid_extensions_list(self, settings):
        """
        checks extensions defined in Item types of sgtk_config_environments_library.yaml and return it as a tuple.

        :param dict settings: Configured settings for this collector
        :return: tuple of extensions intialized in template .
        """

        extensions = set()

        # get Item Types from sgtk_config_templates_library template
        DEFAULT_ITEM_TYPES = settings["Item Types"].value

        for file_type, k in DEFAULT_ITEM_TYPES.iteritems():
            extensions.update(DEFAULT_ITEM_TYPES[file_type]["extensions"])

        return tuple(extensions)

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

        include_extensions = self._valid_extensions_list(settings)

        # handle Manifest files, Normal files and folders differently
        if os.path.isdir(path):
            valid_library_elements, key_category = self.validate_library_path(settings, path)
            get_frame_sequences = publisher.util.get_frame_sequences(path)
            files_in_dir = []
            files_in_seq = []
            if valid_library_elements:
                items = self._collect_folder(settings, parent_item, path)
                for each in os.listdir(path):
                    if each.endswith(include_extensions):
                        files_in_dir.append(os.path.join(path, each))

                for seq_path, seq_files in get_frame_sequences:
                    for files in seq_files:
                        files_in_seq.append(files)

                files_in_dir = list(set(files_in_dir)-set(files_in_seq))

                if files_in_dir:
                    for each in files_in_dir:
                        item = self._collect_file(settings, parent_item, each)
                        if item:
                            new_items = self.update_item_field(settings, item, each, valid_library_elements)
                            file_items.extend(new_items)

                if items:
                    # file_items.extend(items)
                    new_items = self.update_item_field(settings, items, path, valid_library_elements)
                    file_items.extend(new_items)
            else:
                self.logger.error(
                    "Path %s does not match with template." % path)

        else:
            if publisher.settings["manifest_file_name"] in os.path.basename(path):
                items = self._collect_manifest_file(settings, parent_item, path)
                if items:
                    file_items.extend(items)
            else:
                valid_library_elements, key_category = self.validate_library_path(settings, path)
                if valid_library_elements:
                    item = self._collect_file(settings, parent_item, path)
                    if item:
                        new_items = self.update_item_field(settings, item, path, valid_library_elements)
                        file_items.extend(new_items)
                else:
                    self.logger.error(
                        "Path %s does not match with template." % path)

        # make sure we have snapshot_type field in all the items!
        # this is to make sure that on publish we retain this field to figure out asset creation is needed or not.
        for file_item in file_items:
            fields = file_item.properties["fields"]

            # since we can't get a context without entities but with a step :\
            # add the missing Step key in the fields
            if "Step" not in fields:
                sg_filters = [
                    ['short_name', 'is', "library"]
                ]

                query_fields = ['entity_type', 'code', 'id', 'short_name']

                # add a library step to all ingested files
                step_entity = self.sgtk.shotgun.find_one(
                    entity_type='Step',
                    filters=sg_filters,
                    fields=query_fields
                )

                if step_entity:
                    fields["Step"] = step_entity["short_name"]

            # add the missing snapshot_type field
            if "snapshot_type" not in fields:
                item_info = self._get_item_info(settings=settings,
                                                path=file_item.properties["path"],
                                                is_sequence=file_item.properties["is_sequence"])

                fields["snapshot_type"] = item_info["default_snapshot_type"]
                # CDL files should always be published as Asset entity with nuke_avidgrade asset_type
                # this is to match organic, and also for Avid grade lookup on shotgun
                # this logic has been moved to _get_item_info by defining default_snapshot_type for each item type
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
