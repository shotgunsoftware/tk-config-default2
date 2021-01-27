# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import argparse
import json
import logging
import os
import pprint
import shlex
import subprocess
import sys
import tempfile

from ..writers import get_writer_class

PMT_PATH = os.path.dirname(__file__)
PMT_PATH = os.path.abspath(os.path.join(PMT_PATH, os.path.pardir))

_LOG = logging.getLogger(__name__)


def translate(reader, reader_args, writer, writer_args):

    # Hardcoded ATM, later we will dynamically query readers and writers at init time
    if reader == "screenplay":
        # UE only supports Python 2 at the moment.
        # screenplay_parser is written in Python 3.
        # So we cannot use the ScreenplayParser class in process directly.
        if sys.version_info.major == 3:
            from ..readers import get_reader_class

            parser = get_reader_class("Script")(reader_args["input"])
            pmt_project = parser.to_pmt_project()
        # Instead we launch a subprocess that will output the pmt json data // Or create a temporary json file with the pmt data
        else:
            # Create a temp directory where the pmt_project JSON file will be
            # written
            tmp_dir = tempfile.mkdtemp()
            tmp_file_name = os.path.join(tmp_dir, "result.json")

            py_cmd = """
import json
import logging
import sys

_LOG = logging.getLogger('ScriptReader_out_of_process')

sys.path.append('{pmt_path}')
from readers import get_reader_class

parser = get_reader_class('Script')(\'{script_path}\')

_LOG.info('Creating tmp file: {tmp_file_name}')
with open('{tmp_file_name}', 'w') as f:
    pmt_project_json = parser.to_json()
    json.dump(json.loads(parser.to_json()), f)

_LOG.info('Done')
                """.format(
                pmt_path=PMT_PATH.replace("\\", "/"),
                script_path=reader_args["input"].replace("\\", "/"),
                tmp_file_name=tmp_file_name.replace("\\", "/"),
            )

            # Determine which interpreter to use
            # If PMT_VENV_PATH is set, it means that we should use it
            pmt_python3 = os.environ.get("PMT_VENV_PATH")
            if pmt_python3:
                pmt_python3 = os.path.join(pmt_python3, "Scripts", "python.exe")
                pmt_python3 = os.path.normpath(pmt_python3)

                # Forward slashes to avoid losing the backslahes
                pmt_python3 = pmt_python3.replace("\\", "/")
                if not os.path.exists(pmt_python3):
                    raise KeyError(
                        "PMT_VENV_PATH exists in the environment but '{}' does "
                        "not point to a valid Python venv".format(pmt_python3)
                    )
            else:
                # We try py.exe. It should invoke the right interpreter if it
                # was installed properly. It also needs to have the PMT
                # pip-installed.
                pmt_python3 = "py -3.7"

            cmd = pmt_python3 + ' -c "{py_cmd}"'.format(py_cmd=py_cmd)
            _LOG.info("Command to execute: {}".format(cmd))

            process = subprocess.Popen(
                shlex.split(cmd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            process.wait()
            if process.returncode == 0:
                process.communicate()

                with open(tmp_file_name, "r") as f:
                    pmt_project = json.load(f)

                # Clean-up the temporary file+directory
                os.remove(tmp_file_name)
                os.rmdir(tmp_dir)
            else:
                _LOG.error("Something wrong happened:")
                out, err = process.communicate()
                _LOG.error("OUT:")
                _LOG.error(out)
                _LOG.error("ERR:")
                _LOG.error(err)
                exit()

        if writer == "unreal":
            ue_writer = get_writer_class("Unreal")(pmt_project)
            ue_writer.write(headless_mode=True)


def dump():
    import pprint

    import readers
    import writers

    _LOG.info(
        "Readers: \n{}".format(pprint.pformat(readers.get_reader_classes()))
    )
    _LOG.info(
        "Writers: \n{}".format(pprint.pformat(writers.get_writer_classes()))
    )


def read():
    """
    Entry point of the pmt_read executable.
    Command-line arguments:
    reader: Name of the reader to use
    reader_args: dictionary of arg data that will be passed to the reader
    """
    if sys.version_info.major != 3:
        raise EnvironmentError(
            "pmt_read needs to be run with a Python 3 interpreter"
        )

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "reader",
        help="Name of the reader to use. Use pmt_dump to get the list of "
        "available readers",
    )
    parser.add_argument(
        "--reader_args",
        default="{}",
        help="Dictionary of arguments to be passed to the reader, "
        'e.g.: --reader_args={"file_path": "c:/scripts/sample_script.txt"}',
    )
    parser.add_argument(
        "--output",
        default="",
        help="Output file path (resulting JSON file)",
    )

    args = parser.parse_args()

    try:
        reader_args = eval(args.reader_args)
    except:
        raise KeyError(
            "Invalid --reader_args value: {}. Needs to be a dictionary".format(
                args.reader_args
            )
        )

    output_path = args.output
    if not output_path:
        output_path = "pmt_read_output.json"
    _LOG.info(
        'Using reader "{}" with args "{}" and output "{}"'.format(
            args.reader, args.reader_args, output_path
        )
    )

    from readers import get_reader_class

    reader = get_reader_class(args.reader)(**reader_args)

    _LOG.info("Reading with '{}' reader".format(args.reader))
    pmt_project_json = reader.to_json()

    _LOG.info("Generating JSON file ({})...".format(output_path))
    with open(output_path, "w") as f:
        json.dump(pmt_project_json, f)

    _LOG.info("Done.")
