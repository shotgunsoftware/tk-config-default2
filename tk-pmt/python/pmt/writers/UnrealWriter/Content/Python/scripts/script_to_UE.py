# UnrealWriter. Copyright 2020 Imaginary Spaces. All Rights Reserved.

"""
This script is intended to be run from the UnrealEngine editor, with Python 2.7

It will show a file open dialog for the user to choose a script text file.
The text file will be converted to Unreal assets.
"""
import os
import sys
import unreal


def main():
    # Make sure our packages are in PYTHONPATH
    venv = os.environ.get("PMT_VENV_PATH")
    if not venv:
        raise KeyError(
            "The 'PMT_VENV_PATH' environment variable needs to be set and point"
            " to the PMT Python virtual environment root folder"
        )

    venv_packages = os.path.join(venv, "Lib", "site-packages")
    if venv_packages not in sys.path:
        sys.path.append(venv_packages)

    from pmt import pmt

    # Ask the user to pick a text file
    picked_files = unreal.UnrealWriterPythonAPI.open_file_dialog(
        dialog_title="Select a Script Text File", file_types="Text Files|*.txt"
    )

    if not picked_files:
        raise ValueError(
            "You need to select a script text file. Please start again"
        )

    cwd = os.getcwd()
    script_path = os.path.join(cwd, picked_files[0])
    script_path = os.path.normpath(script_path)

    if not script_path:
        raise ValueError(
            "You need to select a script text file. Please start again"
        )

    pmt.translate(
        reader="screenplay",
        reader_args={"input": script_path},
        writer="unreal",
        writer_args={},
    )


if __name__ == "__main__":
    main()