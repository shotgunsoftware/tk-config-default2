# UnrealWriter
A Python module to easily assemble sequences in Unreal given a JSON file configuring its content.

## Getting Started
To start using the UnrealWriter, follow these steps:

1. Open a new project in Unreal 4.25 (any template can be chosen).
2. In your project directory, create a folder called Plugins and clone this repository to that location.
3. Restart the Editor to load your plugin in Unreal.

If you have the [Python Toolbar Button & Menu Creator](https://www.unrealengine.com/marketplace/en-US/product/python-toolbar-button-menu-creator) plugin installed and enabled within your project, you should see a new toolbar button with a dropdown menu to "Generate Sequence from Screenplay Breakdown". By selecting this menu item you can load a screenplay breakdown JSON file provided by the Imaginary Spaces PMT to create an Unreal sequence.

Otherwise, the UnrealWriter can be executed via the Editor Python console by calling `writer.do_assemble_sequence` with a path to the JSON file specifying the screenplay breakdown.

```
import writer

writer.do_assemble_sequence(
    file_path = `...\Plugins\UnrealWriter\Resources\Sample Screenplay.json`,
)
```

## Configuring the Sequencer Structure

The UnrealWriter uses a client configuration JSON file to customize the resulting sequence structure. By modifying the following settings in the `client_configuration.json` file found in the plugin's Resources folder, you can manipulate the generated assets and tracks.

* `MASTER_SEQUENCE`: Name of the master sequence asset.
* `SEQUENCE_DIR`: The folder where the master sequence and top-level shot sequences will be stored.

* `SEQUENCE_PATH`: Path to the location of shot sequence assets.
* `SEQUENCE_NAME`: Tokenized string denoting the naming convention for shots.
* `SCUBSCENE_TRACKS`: A list of subsequences that will be generated and added to a Subscenes track for every shot.
* `SHOT_LENGTH`: The length of shots added to shot tracks.

* `ASSET_PATH`: Tokenized string denoting the naming convention for assets.
* `DEPARTMENT_TASK_MAPPINGS`: Dictionary structure of departments and tasks for which folders will be created under the assets directory.
* `DUMMY_ACTOR_ASSET`: Path to an asset that will be used as a placeholder for characters in each scene.

```json
{
    "MASTER_SEQUENCE": "S1E1",
    "SEQUENCE_DIR": "/Game/shots/",

    "SEQUENCE_PATH": "/Game/shots/{shot}/",
    "SEQUENCE_NAME": "S1E1_{shot}",
    "SUBSCENE_TRACKS": ["anim", "lighting", "environment", "FX"],
    "SHOT_LENGTH": 30,
    
    "ASSET_PATH": "/Game/assets/{asset_type}/{asset_name}/{department}",
    "DEPARTMENT_TASK_MAPPINGS" : {
        "rig": [],
        "model": [],
        "surface": ["texture", "material"]
    },
    "DUMMY_ACTOR_ASSET": "/UnrealWriter/Assets/Character.Character",
}
```