import os
import sys
import traceback

# handle imports
path_to_sgtk = sys.argv[1]

sys.path.insert(0, path_to_sgtk)
import sgtk
from sgtk.util.filesystem import copy_file, ensure_folder_exists


def validate(entity_type, entity_id, publish_template, template_fields):
    """
    """

    # Get the current authenticated user and use it for the current session
    sa = sgtk.authentication.ShotgunAuthenticator()
    user = sa.get_user()
    sgtk.set_authenticated_user(user)

    # Build a tank instance
    config_root_path = os.path.normpath(os.path.join(path_to_sgtk, "..", "..", ".."))
    tk = sgtk.sgtk_from_path(config_root_path)

    # Get the template we want to use
    publish_template = tk.templates.get(publish_template)
    if not publish_template:
        sys.exit(2)

    # Get some template fields from the context
    ctx = tk.context_from_entity(entity_type, entity_id)
    template_fields.update(ctx.as_template_fields(publish_template))

    if publish_template.missing_keys(template_fields):
        sys.exit(2)


def publish(entity_type, entity_id, publish_template, work_path, template_fields, description, publish_name,
            publish_user, thumbnail_path, publish_type):
    """
    """

    # Get the current authenticated user and use it for the current session
    sa = sgtk.authentication.ShotgunAuthenticator()
    user = sa.get_user()
    sgtk.set_authenticated_user(user)

    # Build a tank instance
    config_root_path = os.path.normpath(os.path.join(path_to_sgtk, "..", "..", ".."))
    tk = sgtk.sgtk_from_path(config_root_path)

    # Get the template we want to use
    publish_template = tk.templates.get(publish_template)

    ctx = tk.context_from_entity(entity_type, entity_id)
    template_fields.update(ctx.as_template_fields(publish_template))

    # TODO: what version do we want to use for the library published file?
    #  for now, rely on paths on disk
    publish_paths = tk.paths_from_template(publish_template, template_fields, skip_keys=["version"])
    if not publish_paths:
        template_fields["version"] = 1
    else:
        highest_version = 0
        for p in publish_paths:
            fields = publish_template.get_fields(p)
            if fields["version"] > highest_version:
                highest_version = fields["version"]
        template_fields["version"] = highest_version + 1

    publish_file = publish_template.apply_fields(template_fields)

    # TODO: manage frame sequence

    # copy the path to the publish location
    try:
        publish_folder = os.path.dirname(publish_file)
        ensure_folder_exists(publish_folder)
        copy_file(work_path, publish_file)
    except Exception:
        raise Exception(
            "Failed to copy work file from '%s' to '%s'.\n%s"
            % (work_path, publish_file, traceback.format_exc())
        )

    # register the file to Shotgun
    publish_data = {
        "tk": tk,
        "context": ctx,
        "comment": description,
        "path": publish_file,
        "name": publish_name,
        "created_by": publish_user,
        "version_number": template_fields["version"],
        "thumbnail_path": thumbnail_path,
        "published_file_type": publish_type,
    }
    sgtk.util.register_publish(**publish_data)


if __name__ == "__main__":
    """
    Main script entry point
    """

    # we don't want this process to have any traces of
    # any previous environment
    if "TANK_CURRENT_PC" in os.environ:
        del os.environ["TANK_CURRENT_PC"]

    # Make sure we have a clean shutdown.
    if sgtk.platform.current_engine():
        sgtk.platform.current_engine().destroy()

    # unpack file with arguments payload
    arg_data_file = sys.argv[2]
    with open(arg_data_file, "rb") as fh:
        arg_data = sgtk.util.pickle.load(fh)

    if arg_data["action"] == "validate":
        validate(
            entity_type=arg_data["entity_type"],
            entity_id=arg_data["entity_id"],
            publish_template=arg_data["publish_template"],
            template_fields=arg_data["template_fields"],
        )
    elif arg_data["action"] == "publish":
        publish(
            entity_type=arg_data["entity_type"],
            entity_id=arg_data["entity_id"],
            publish_template=arg_data["publish_template"],
            work_path=arg_data["work_path"],
            template_fields=arg_data["template_fields"],
            description=arg_data["description"],
            publish_name=arg_data["publish_name"],
            publish_user=arg_data["publish_user"],
            thumbnail_path=arg_data["thumbnail_path"],
            publish_type=arg_data["publish_type"],
        )
