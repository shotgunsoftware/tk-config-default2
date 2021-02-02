# ScriptReader

### Limitations
The ScriptReader works with scripts, but not shooting scripts, where the scenes have numbers assigned.

### Setup
* Install Python 3
* From a Windows command prompt: \
`set PYTHON3=C:\Users\<user>\AppData\Local\Programs\Python\Python37\python.exe`
* Create a virtual environment (here we create it under `c:\temp\venv\ScriptReader`): \
`set VENV_PATH=c:\temp\venv\ScriptReader` \
`%PYTHON3% -m venv %VENV_PATH%` 
* Install the ScriptReader: \
`%VENV_PATH%\scripts\pip install .`


### Type Checking
**Requirements:**
* Install mypy: \
`%VENV_PATH%\scripts\pip install mypy`


Using a local installation (see Setup section above), run this: \
`%VENV_PATH%/Scripts/mypy.exe --disallow-untyped-defs screenplay_parser.py`

### Tests
In a shell, in the root directory of the repo, run the command:

Using a local installation (see Setup section above), run this: \
`%VENV_PATH%/Scripts/python -m unittest discover .\tests\`

