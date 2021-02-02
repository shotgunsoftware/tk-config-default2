# ImgSpc-PMT. Copyright 2020 Imaginary Spaces. All Rights Reserved.

import argparse
import os
import shlex
import shutil
import subprocess
import sys
import tempfile

if sys.platform == "win32":
    from ctypes import create_unicode_buffer, windll


# Engine folder, e.g. C:\Program Files\Epic Games\UE_4.25\Engine
PMT_UNREAL_ENGINE_ROOT = os.getenv("PMT_UNREAL_ENGINE_ROOT")
# Path to an Unreal project that will be copied before being populated by
# script assets
PMT_PROJECT_BASE = os.getenv("PMT_PROJECT_BASE")
# Path where the resulting project will be moved at the end of the process
PMT_OUTPUT_PROJECT_PATH = os.getenv("PMT_OUTPUT_PROJECT_PATH")

if not PMT_UNREAL_ENGINE_ROOT:
    raise KeyError(
        "Missing PMT_UNREAL_ENGINE_ROOT in the environment "
        "(Engine folder, e.g. C:\\Program Files\\Epic Games\\UE_4.25\\Engine)"
    )

if not PMT_PROJECT_BASE:
    raise KeyError(
        "Missing PMT_PROJECT_BASE in the environment "
        "(Path to an Unreal project that will be copied before being populated by script assets)"
    )

if not PMT_OUTPUT_PROJECT_PATH:
    raise KeyError(
        "Missing PMT_OUTPUT_PROJECT_PATH in the environment "
        "(Path where the resulting project will be moved at the end of the process)"
    )


PMT_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
    )
)
# Path to the UnrealWriter plugin script
PMT_UNREAL_WRITER_SCRIPT = os.path.join(
    PMT_PATH, "writers", "UnrealWriter", "Content", "Python", "cli_writer.py"
)


def find_uproject_file(project_dir):
    ue_project_file = next(
        f for f in os.listdir(project_dir) if f.endswith(".uproject")
    )
    return os.path.join(project_dir, ue_project_file)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("screenplay")
    args = parser.parse_args()

    # Project's name will be screenplay's filename
    # Whitespaces are removed
    # (UE4Editor-Cmd  does not handle well paths with whitesapces, even if enclosed in quotes)
    project_name = os.path.splitext(os.path.basename(args.screenplay))[
        0
    ].replace(" ", "")

    # Make sure the desired output project does not already exist
    output_project_dir = os.path.join(PMT_OUTPUT_PROJECT_PATH, project_name)
    if os.path.exists(output_project_dir):
        raise ValueError(
            "The desired output directory already exists ({}). Please specify "
            "a different PMT_OUTPUT_PROJECT_PATH or use a different "
            "script.".format(output_project_dir)
        )

    # Copy base project into a temporary directory
    temp_dir = tempfile.TemporaryDirectory()  #  tempfile.mkdtemp()#
    project_dir = os.path.join(temp_dir.name, project_name)
    # For debug, can create a temp directory that won't be rmed automatically at the end of the process:
    # temp_dir = tempfile.mkdtemp()
    # project_dir = os.path.join(temp_dir, project_name)
    shutil.copytree(PMT_PROJECT_BASE, project_dir)
    print("Temporary project directory: " + project_dir, flush=True)
    # Find the .uproject file in the copied directory
    ue_project_file = find_uproject_file(project_dir)
    base_ue_project_name = os.path.splitext(os.path.basename(ue_project_file))[
        0
    ]

    # TODO: platform dependant command
    ue4editor_cmd = os.path.join(
        PMT_UNREAL_ENGINE_ROOT, "Binaries", "Win64", "UE4Editor-Cmd.exe"
    )

    # On Windows, we must ensure the path of temp directory that contains the copied project dir
    # is a long path name, and not a short one (8.3 filename).
    # The created temporary directory with tempfile.mkdtemp() or tempfile.TemporaryDirectory()
    # will be located into "C:\Users\User Name\AppData\Local\Temp\".
    # Unfortunately, the returned path (string) from those calls will be a short path,
    # so something like "C:\Users\USER~1\AppData\Local\Temp\".
    # The problem is that the LaunchEngineLoop won't launch UE because one of its checks failed
    # due to one part of the path ("USER~1") not being equal to what it is supposed to be ("User Name").
    # See UE sources: Engine/Source/Runtime/Launch/Private/LaunchEngineLoop.cpp, method LaunchFixProjectPathCase
    if sys.platform == "win32":
        ubuffer_max = 300
        ubuffer = create_unicode_buffer(ubuffer_max)
        windll.kernel32.GetLongPathNameW(ue_project_file, ubuffer, ubuffer_max)
        ue_project_file = ubuffer.value

    # TODO: ensure no whitespaces in ExecutePythonScriptand no bacckslashes, just '/'
    cmd = '"{ue4editor_cmd}" "{project}" -ExecutePythonScript="{pmt_unreal_writer} {pmt_module} {screenplay}"'.format(
        ue4editor_cmd=ue4editor_cmd,
        project=ue_project_file,
        pmt_unreal_writer=PMT_UNREAL_WRITER_SCRIPT,
        pmt_module=PMT_PATH,
        screenplay=args.screenplay,
    )
    print("Command to be executed: {cmd}".format(cmd=cmd), flush=True)

    process = subprocess.Popen(
        shlex.split(cmd),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    process.wait()
    if process.returncode == 0:
        # Copy UE project to output folder
        print(
            "Copying resulting UE Project to {}...".format(output_project_dir)
        )
        shutil.copytree(project_dir, output_project_dir)
        # # Rename .uproject file
        ue_project_file = find_uproject_file(output_project_dir)
        base_ue_project_name = os.path.splitext(
            os.path.basename(ue_project_file)
        )[0]
        os.rename(
            ue_project_file,
            ue_project_file.replace(base_ue_project_name, project_name),
        )
    else:
        print("Something went wrong:")
        out, err = process.communicate()
        print("OUT:")
        print(out)
        print("ERR:")
        print(err)

    # TemporaryDirectory is automatically removed when the object is deleted


if __name__ == "__main__":
    main()
