![PMT](resources/pmt_logo.jpg "PMT")

# PMT 

The Pipeline Multi-Tool (PMT) is a series of readers and writers that allow
transporting data from various sources to various targets.

For example, the PMT can be used to read a movie script and generate a structured 
project, written as a JSON file. With this JSON file, you can then use the UnrealWriter to generate an associated
UE4 project already populated with actors, sequencers, shots, cameras, etc.

You can also use a Connector script to read the script and write the UE4 project in one
step, skipping the intermediary JSON file.

## Requirements
* Windows 10
* Unreal 4.26
* Python 3.7.x x64

## Setup
* Install Python 3
* Verify it is properly installed by running:\
`py -3.7 -V`\
Typical output:
```
$ py -3.7 -V
Python 3.7.5
```
* From a Windows command prompt, create a virtual environment (here we create 
it under `D:\virtualEnvs\PMT`): \
`set PMT_VENV_PATH=D:\virtualEnvs\PMT` \
`py -3.7 -m venv %PMT_VENV_PATH%`
* Clone this repo and go to its root directory. Install the PMT by running this command: \
`%PMT_VENV_PATH%\scripts\pip install .` \
* Verify the installation by running: \
`%PMT_VENV_PATH%\scripts\pmt_dump` 

Typical output:
```
2020-11-19 13:13:16,942:INFO:root:initialize:Logging configured to stdout and to file: C:\Users\David Lassonde\AppData\Local\imgspc\pmt\log.txt
2020-11-19 13:13:16,960:INFO:pmt.pmt:dump:Readers:
{'Script': <class 'readers.ScriptReader.screenplay_parser.ScreenplayParser'>}
2020-11-19 13:13:16,960:INFO:pmt.pmt:dump:Writers:
{'Unreal': <class 'writer.UEWriter'>}
```

## Converting a script to an Unreal project
### From the UnrealEngine editor
Following these steps will populate the UnrealEngine current project with assets coming from a text script.

1. Make sure that the `PMT_VENV_PATH` environment variable points to the PMT 
Python 3 virtual environment root directory 
(see the [Setup](#Setup) section above)
2. Open the UnrealEngine editor and one of your projects
3. Copy the `writers/UnrealWriter` directory under your project's `Plugins` directory. The resulting directory should be `Plugins/UnrealWriter`. Allow the Plugin to compile (you might need to restart the UnrealEngine editor).
4. Execute this console command in the editor:

`PY "../../Plugins/UnrealWriter/Content/Python/scripts/script_to_UE.py"`

![Console Command](resources/console_cmd.jpg "Console Command")

A File Open dialog will show up. Select a script text file and open it. The `Contents/LevelSequences` area of the project should be populated according to 
the selected script.

### From the command line
If you want to create a new UnrealEngine project with assets coming from a script, you can use the `script_to_UE4` connector script. It will take an existing (template) project, make a copy and populate it from script assets. Simply follow these steps from a Windows Command Prompt shell:

1. Copy the `writers/UnrealWriter` directory under your template project's `Plugins` directory. The resulting directory should be `Plugins/UnrealWriter`.
2. Set these environment variables: \
`PMT_UNREAL_ENGINE_ROOT`: Engine folder, e.g. C:\Program Files\Epic Games\UE_4.25\Engine \
`PMT_PROJECT_BASE`: Path to an Unreal project that will be copied before being populated by script assets \
`PMT_OUTPUT_PROJECT_PATH`: Path where the resulting project will be moved at the end of the process 
3. Execute the connector
`%PMT_VENV_PATH%\Scripts\script_to_UE4.exe <path_to_script_file>`

The Unreal editor associated with `PMT_UNREAL_ENGINE_ROOT` will be launched. 
After it exits, the generated project will be located at 
`PMT_OUTPUT_PROJECT_PATH`\\<script_name\>

#### Example
* The script to convert is located at `D:\scripts\sample_script.txt`
* UnrealEngine has been compiled in `D:\projects\UnrealEngine\Engine`
* The project to use as a base is located at `D:\UnrealProjects\EmptyVirtualProd`
* We want the project to be generated at `D:\UnrealProjects\sample_script`

These commands, entered in a Command Prompt shell, will meet these requirements:
```
set PMT_UNREAL_ENGINE_ROOT=D:\projects\UnrealEngine\Engine
set PMT_PROJECT_BASE=D:\UnrealProjects\EmptyVirtualProd
set PMT_OUTPUT_PROJECT_PATH=D:\UnrealProjects

%PMT_VENV_PATH%\Scripts\script_to_UE4.exe D:\scripts\sample_script.txt
```

## Reading data
The `pmt_read` is a convenience script that will invoke a reader and generate a JSON file with its results.

```
usage: pmt_read [-h] [--reader_args READER_ARGS] [--output OUTPUT] reader

positional arguments:
  reader                Name of the reader to use. Use pmt_dump to get the
                        list of available readers

optional arguments:
  -h, --help            show this help message and exit
  --reader_args READER_ARGS
                        Dictionary of arguments to be passed to the reader,
                        e.g.: --reader_args={"file_path":
                        "c:/scripts/sample_script.txt"}
  --output OUTPUT       Output file path (JSON file)
  ```

### Example
This command will parse `D:\Temp\sample_script.txt` and write the results in `D:\Temp\sample_script.json`:

```
%PMT_VENV%\Scripts\pmt_read Script --reader_args={'file_path':'d:\Temp\sample_script.txt'} --output=d:\Temp\sample_script.json
```

## Readers

Readers' ouput is a pmt-json file. A reader can read data from a production database (Shotgun, ftrack), a DCC, a script... The data is converted as a project in the pmt-json format.

## Writers

Writers take for input a pmt-json file. The pmt file is used to create or update an existing project in a DCC (Unreal Engine, Unity) or in a production database (Shotgun, ftrack).

## Connectors

`pmt.py` is where the translation logic between writers and readers take place. Importing the `pmt` module is all that is required to run a translation.
For instance, to read a script and write it as an Unreal project, you can simply use the following snippet inside Unreal Engine's Python console:

```python
pmt.translate(
    reader = "screenplay",
    reader_args = {"input": "/path/to/script.txt"},
    writer = "unreal",
    writer_args = {} # implicitly use reader output
)
```

If it is required to operate this kind of translation, but without directly using the embedded Python, connectors will take care of that.
Connectors will launch subprocesses for the readers and writers, and also take care of the logistic of the translation (creation of temporary directories, moving files...).
For instance, the `screenplay_to_unreal_project` connector first copies a base template project in a temporary folder, launches an Unreal Engine subprocess with that project, then calls `pmt.translate` inside the UE subprocess, saves the created LevelSequences, and finally move the temporary project directory to the output destination.

## Testing the PMT

### Running the tests

The PMT and its various readers and writers are tested using Python `unittest` framework.
All the tests can be run from the PMT's root directory. `unittest` will discover all the tests in the folder hierarchy:

```console
$ py -3 -m unittest discover
```

### Coverage

To establish the coverage of the tests, the the Python `coverage` module is used. It is nicely integrated with `unittest`:

```console
$ py -3 -m coverage run --source=. -m unittest discover
```

To see the coverage report, just do:

```console
$ py -3 -m coverage report
```

An interactive HTML report can also be created:

```console
$ py -3 -m coverage html
```

It will create a `htmlcov` directory.

Make sure to open a Jira defect if coverage goes under 80% for one module

### Mypy

Use `mypy` to statically type check the PMT code.

```console
$ py -3 -m mypy .
```
