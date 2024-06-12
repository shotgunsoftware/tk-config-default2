import argparse
import json
import os
import pprint
import sys

from general import basic_utils

logger = basic_utils.get_logger(__name__)


def run_post_fix(json_data):
    """
    Postfix main process
    Args:
        json_data(dict): Data loaded from json deadline submission. Must be
            constructed using json_dl_submit_tools.py.

    Returns: Updated json_data dictionary

    """
    processes = json_data.get("processes")
    if not processes:
        _error = (
            "Error, 'processes' key is empty. Cannot continue with postfix process, "
            "exiting."
        )
        logger.error(_error)
        return _error

    # Shared entity data
    project_data = json_data.get("project") or {}
    entity_data = json_data.get("entity") or {}
    task_data = json_data.get("task") or {}

    total = len(processes.keys())
    count = 0
    for job_key, job_data in processes.items():
        count += 1
        logger.info("***********************")
        logger.info(f"{count} of {total} - {job_key}")
        logger.info("***********************")

        template_settings = job_data.get("template_settings")
        if not template_settings:
            logger.warning("\t> No Template settings, bypassing.")
            continue

        # Version entity data
        version_data = job_data.get("version") or {}

    return json_data


def get_parser():
    """
    Get argument parser for json deadline submit postfix.
    Returns: argparse.ArgumentParser object
    """
    parser = argparse.ArgumentParser(
        prog="pump_project_postfix",
        description="Runs the generic project post-fix process.",
    )
    parser.add_argument(
        "json_filepath",
        help="Absolute path to a .json file containing the json_dl_submit data."
    )
    parser.add_argument(
        "--dry_run",
        "-dr",
        action="store_true",
        help="Used for testing. Changes will not be made but the tool will report "
             "the changes that would be made."
    )
    return parser


def main():
    """command line entrypoint for json_dl_submit postfix process"""
    logger.info("----------------------------------")
    logger.info(f"Python Version: {sys.version}")

    parser = get_parser()
    args = parser.parse_args()
    json_filepath = args.json_filepath
    dry_run = args.dry_run

    logger.info("ARGS:")
    logger.info(f"\t json_filepath: {json_filepath}")
    logger.info(f"\t dry_run: {str(dry_run)}")
    logger.info("----------------------------------")

    # Exit if json filepath wasn't provided.
    if not json_filepath:
        _error = "ERROR! No Json filepath provided! Cannot continue, exiting."
        logger.error(_error)
        return _error

    if not os.path.exists(json_filepath):
        _error = (
            f"ERROR! Json Filepath does not exist! Cannot continue, exiting. "
            f"Filepath: {json_filepath}"
        )
        logger.error(_error)
        return _error

    # Load json data
    logger.info("Loading submission data")
    with open(json_filepath, "r") as read_file:
        json_data = json.load(read_file)

    # Exit if the Json file is empty.
    if not json_data:
        _error = (
            f"Json file is empty! Cannot continue. Filepath: {json_filepath}"
        )
        logger.error(_error)
        return _error

    if dry_run:
        logger.info("+++++ DRY RUN +++++")
        logger.info(
            "DRY RUN: No changes will be made on disk or in shotgrid, instead "
            "they will be logged to the terminal."
        )
        logger.info("+++++++++++++++++++")

    result = run_post_fix(json_data=json_data)
    if not isinstance(result, dict):
        return result

    if not dry_run:
        json_object = json.dumps(json_data, indent=4)
        with open(json_filepath, "w") as outfile:
            outfile.write(json_object)
            outfile.close()
        logger.info("Updated json data saved.")

    else:
        # Log process data
        logger.info("+++++ DRY RUN +++++")
        logger.info("Would save updated submission data. Logging processes:")
        logger.info("----------")
        for name, data in result["processes"].items():
            logger.info(name)
            logger.info(f"\n{pprint.pformat(data)}")
            logger.info("----------")
        logger.info("+++++++++++++++++++")

    return 0


if __name__ == "__main__":
    sys.exit(main())
