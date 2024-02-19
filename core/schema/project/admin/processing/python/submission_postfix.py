import argparse
import json
import os
import sys

# Add ssvfx_scripts to env if not already there
if "SSVFX_PIPELINE" not in os.environ.keys():
    error = "ERROR! Missing SSVFX_PIPELINE Environment variable! Aborting."
    print(error)
    raise ImportError(error)

dev_root = os.environ.get("SSVFX_PIPELINE_DEV", "")
if os.path.exists(dev_root):
    pipeline_root = dev_root
else:
    pipeline_root = os.environ["SSVFX_PIPELINE"]

repos = ["ssvfx_scripts", "ssvfx_sg"]
for repo in repos:
    repo_path = os.path.join(pipeline_root, "master", repo)
    if not os.path.exists(repo_path):
        repo_path = os.path.join(pipeline_root, repo)

    if repo_path not in sys.path:
        sys.path.append(repo_path)
        print(
            "Added {repo} path to environment: {path}".format(repo=repo, path=repo_path)
        )

from general.basic_utils import get_logger
from general.file_functions import json_reader

logger = get_logger(__name__)

logger.info("Python Version: {}".format(sys.version))
logger.info("----------------------------------\n")


def dict_nav(dictionary, sequence):
    """
    Simplified navigator for nested dictionaries
    returns first non-dictionary value or None

    :dictionary: starting dictionary to navifate
    :sequence: ordered sequence of keys to test in list form
    """
    if not dictionary or not sequence:
        return None

    print(">>>>> Navigating sub-dictionaries for: %s" % "->".join(sequence))
    sub_dict = dictionary
    for key in sequence:
        sub_dict = sub_dict.get(key)

        if key == sequence[-1]:
            return sub_dict

        if not isinstance(sub_dict, dict):
            return sub_dict


def run_post_fix(json_filepath):
    """
        Default submission post-fix process
        Args:
            json_filepath: Full path to a valid pump json file.

        Returns: 0 if process completes without errors.

        """
    logger.info("Loading json data...")
    with open(json_filepath, "r") as file_read:
        json_data = json_reader.json_load_version_check(file_read)

    logger.info("Loaded Json data successfully.")
    logger.info("---")

    processes = json_data["processes"]
    if not processes:
        logger.warning("Warning there are no processes to loop!")

    # Corrective Loop to add nuke node values to JSON file
    total = len(processes.keys())
    count = 0
    for job_key, job_data in processes.items():
        count += 1
        logger.info("***********************")
        logger.info(
            "{count} of {total} - {job_key}".format(
                count=count, total=total, job_key=job_key
            )
        )
        logger.info("***********************")

        nuke_settings = job_data.get('nuke_settings')

        # remove color for Matchmove submissions
        step_id = dict_nav(json_data, ["entity_info", "step_info", "id"])
        if step_id in [4, 5]:
            nuke_settings['color_switch'] = {"which": 0}
            logger.info( ">>>>> color_switch for matchmove: %s" % nuke_settings['color_switch'] )

        logger.info(">>>>> Completed revisions for %s" % job_key)

    logger.info("---")
    logger.info(">>>>> Completed Postfix Process, writing json...")

    # re-write JSON file
    json_object = json.dumps(json_data, indent=4)
    with open(json_filepath, "w") as outfile:
        outfile.write(json_object)
        outfile.close()

    logger.info(">>>>> Postfix JSON write complete. Resuming submission_process.py")
    return 0


def get_parser():
    """
    Get argument parser for Pump project post-fix.
    Returns: argparse.ArgumentParser object
    """
    parser = argparse.ArgumentParser(
        prog="pump_project_postfix",
        description="Runs the generic project post-fix process.",
    )
    parser.add_argument("json_filepath", help="Path to the submitted .json file.")
    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()

    json_filepath = args.json_filepath
    logger.info("ARGS: json_filepath: {}\n".format(json_filepath))
    if not os.path.exists(json_filepath):
        _error = "ERROR! Json Filepath does not exist! Cannot continue, exiting. Filepath: {}".format(
            json_filepath
        )
        logger.error(_error)
        return _error

    result = run_post_fix(json_filepath)
    return result


if __name__ == "__main__":
    sys.exit(main())
