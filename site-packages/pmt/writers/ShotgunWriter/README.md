# ShotgunWriter

Tool that allows reading and writing projects to various platforms. 
Current features:

* Ability to create a Shotgun project from a json file


Limitations:

* Currently only supported on a Windows platform


Requirements:

* Python 3.7.x installed with python.exe saved as an environment variable, e.g:
        
        set PMT_PYTHON3="C:/Program Files/Python37/python.exe"

* Git installed and git.exe in PATH

**Developers Guide to Working on Project**

1. Download/clone this git repo and set the PMT_LOCATION environment variable accordingly, e.g. 

		set PMT_LOCATION=D:/Projects/project-migration-tool/

2. Choose a location for your Python virtual environment and set the PMT_PY_VENV environment variable accordingly, e.g.

		set PMT_PY_VENV=D:/virtual_env/pmt

3. Create a Python virtual environment

		%PMT_PYTHON3% -m venv %PMT_PY_VENV%

4. Install the PMT into your virtual environment.

		%PMT_PY_VENV%/Scripts/pip install -e %PMT_LOCATION%

Now the PMT should be installed into the venv.

**Users Guide**

1. Choose a location for your Python virtual environment and set the PMT_PY_VENV environment variable accordingly

		set PMT_PY_VENV=D:/virtual_env/pmt

2. Create a Python virtual environment
		
		python -m venv %PMT_PY_VENV%

3. Install the pmt into your virtual environment

		%PMT_PY_VENV%/Scripts/pip install git+https://bitbucket.org/imaginaryspaces/project-migration-tool.git

**Using the ShotgunWriter**

   1. Requires a Shotgun config file (shotgun_config.json) with the following template:
    
```json
{
  "SERVER_PATH" :  "https://your_site_name.shotgunstudio.com/",
  "SCRIPT_NAME" : "script_name",
  "SCRIPT_KEY" : "script_key",
  "MAPPING_FILE":  "path to mapping file (relative to this file's directory or an absolute path)",
  "PIPELINE_CONFIGURATION_NAME": "Name of Customer's Pipeline Config (as displayed in Shotgun), e.g: Primary",
  "FILESYSTEMLOCATION_TEMPLATES": {
    "doc": ["ToolKit default file locations, corresponds to the templates in the projects config under /core/templates.yml"],
    "Sequence": "sequences/{Sequence}/{Shot}/{Step}",
    "Asset": "assets/{sg_asset_type}/{Asset}/{Step}",
    "Shot": "sequences/{Sequence}/{Shot}/{Step}"
  },
  "USERS": {
    "doc": ["These users will be used / created for assigning users to entities.",
      "Names can be edited, but these default users exist in our imgspc database.",
      "Add a user entry {User's Role: User's name} under their permission group, e.g. Artist",
      "A user must have at least a first and last name (middle names will be grouped to the last name)",
      "User Roles must be Unique. i.e only one PRODUCER across all permission groups."],

    "Admin": {},
    "Artist": {
       "ANIMATOR": "Annie Mader",
       "LIGHTER": "Lai Tso",
        "MODELLER": "Maude Ella",
        "TEXTURER": "Tagir Shulga",
        "PRODUCER": "Promi Duha",
        "RIGGER": "Ricky Gervais"
    },
    "Manager": {}
   }
}
```  

2. Requires that thimble.zip is extracted in your Shotgun primary local storage location. For example, if your primary 
local file storage location is defined as P:\imgspc\Production, then the Thimble production data files need 
to be located at P:\imgspc\Production\thimble

To run the ``sg_writer``, provide the necessary arguments (path to project data's JSON file and the Shotgun config file) 
e.g:
		
		%PMT_PY_VENV%/Scripts/sg_writer %PMT_LOCATION%/thimble_data/thimble.json shotgun_config.json
		
 The default mappings file can be found at ``%PMT_LOCATION%/pmt/shotgun/mappings.json``	
 
**Running Tests**

Requires:

* the Shotgun config information should be saved as environment variables as follows:

        set PMT_TEST_SERVER_PATH=https://your_site_name.shotgunstudio.com/
        set PMT_TEST_SCRIPT_NAME=script_name
        set PMT_TEST_SCRIPT_KEY=script_key
        
Run this command to run the test suite:
        
        %PMT_PY_VENV%/Scripts/python -m unittest tests.test_pmt.ShotgunWriterTester

**Code Coverage**

Install the coverage package:

        %PMT_PY_VENV%/Scripts/pip install coverage

Change directories to ``PMT_LOCATION`` and run coverage:
       
        cd %PMT_LOCATION% && %PMT_PY_VENV%/Scripts/coverage run -m unittest tests.test_pmt.ShotgunWriterTester

Follow up with either of these commands to visualize results:
    
    %PMT_PY_VENV%/Scripts/coverage report
    
    %PMT_PY_VENV%/Scripts/coverage html

(html results can be found in ``%PMT_LOCATION%/htmlcov/index.html``)

**Development Tips**

All the scripts that can be executed are under PMT_LOCATION/pmt

setup.py:
under entry_points
'console_scripts': defines the exe(s) that will be created once the pmt package is installed.

        'console_scripts': [
            'exe_name = pmt.script_under_pmt:function_in_script',
        ],

So when the pmt package is installed, an exe named exe_name is created, and this exe runs function_in_script, which is 
defined in script_under_pmt (a script in the pmt file).
Editing the module will automatically update the exe in the virtual environment, so you don't need to re-install pmt 
after every change.


Things to Note

* only supports published files created through toolkit, whose path is relative to the local storage
* If getting SSL error messages when using the Shotgun Python API (``CERTIFICATE_VERIFY_FAILED``), see: [https://developer.shotgunsoftware.com/c593f0aa/]