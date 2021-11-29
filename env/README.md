Overview of tk-config-default2 environment structure
====================================================

The `tk-config-default2` config has a different structure than previous
configurations provided by toolkit. It has been reorganized based on client
feedback and observation to help maximize efficiency when needing to manually
curate your production environments.

Top-level environments
----------------------

There are 7 top-level files that provide the entry points to environment
configuration. The names of these files correspond to one of the strings
returned by the `pick_environment` hook. These files are:

* `asset.yml` - Asset context without a pipeline step. Typically used when
    building menus in the SG web interface.
* `asset_step.yml` - Asset context with a pipeline step. This is the environment
    typically associated with an artist's Asset work area.
* `project.yml` - A ShotGrid project context. Often used when launching a
    DCC from SG Desktop, providing apps for further refining the context.
* `publishedfile_version.yml` - A context for providing functionality when
    viewing PublishedFile or Version entities, typically in SG web interface.
* `sequence.yml` - A context used for sequence-based workflows.
* `shot.yml` - Shot context without a pipeline step. Typically used when
    building menus in the SG web interface.
* `shot_step.yml` - Shot context with a pipeline step. This is the environment
    typically associated with an artist's Shot work area.

Each of these files provides an outline of the engines configured for that
environment. These file don't typically need to be modified unless you're adding
a new engine configuration into one of the environments.

The structure of these files is as follows:

```yaml
includes:
# include all frameworks
- ./includes/frameworks.yml
# include each of the engine configurations used in this environment
- ./includes/settings/<engine>.yml
- ./includes/settings/<engine>.yml
...

engines:
  # reference each of the included engine environment configurations
  <engine>: "@settings.<engine>.<environment>"
  <engine>: "@settings.<engine>.<environment>"
  ...

# reference all of the frameworks
frameworks: "@frameworks"
```

The `tk-config-default2` heavily relies on the Toolkit configuration includes
and references. The `includes` section references files that define regular
`YAML` key/value pairs. These keys can then be referenced with the `"@<key>"`
syntax seen above. Have a look at one of the top-level environment files for a
concrete example of how this works.

Engine Settings
---------------

The top-level environments include engine settings from
`includes/settings/<engine>.yml` files. In `tk-config-default2`, all
engine-specific configurations live in that engine's settings file. This
makes it straight forward to know where to go to change how an engine is
configured. For example, if you need to change how the Maya engine is
configured, simply edit the `includes/settings/tk-maya.yml` file.

The structure of these files is as follows:

```yaml
includes:
# include the file that defines app locations
- ../app_locations.yml
# include the file that defines engine locations
- ../engine_locations.yml
# include each of the app configurations used in this environment
- ./<app>.yml
- ./<app>.yml
...

# <environment> specific configuration
settings.<engine>.<environment>:
  apps:
    # list of apps for this engine in the specific environment
    <app>:
      # some simple apps only need to specify a location descriptor
      location: "@apps.<app>.location"
    # other apps need more configuration, referenced from the included app file
    <app>: "@settings.<app>.<engine>.<environment>"
    ...
  # engine settings are defined/edited here
  location: "@engines.tk-maya.location"

# other environment configurations
...
```

Here you can see where the engine-specific environment keys (
`settings.<engine>.<environment>`) are defined and then included into the
top-level environment files. Take a look at one of the engine configuration
files for a concrete example.

App Settings
------------

Similar to the engine configuration files, any apps that require more than a
location descriptor have a settings file in `includes/settings`. For example, to
make changes to the Nuke Write Node app, all of the different configurations
(for all environments) are defined in the
`includes/settings/tk-nuke-writenode.yml` file.

The structure of these files is as follows:

```yaml
includes:
# include the files that defines the app location
- ../app_locations.yml

# define each of the different configurations for the app.
# for an app that is built for a specific engine, it may be defined this way:
settings.<app>.<environment>:
    # settings defined here...
    location: "@apps.<app>.location"

# for multi apps, the settings key may be defined with an engine name
settings.<app>.<engine>.<environment>:
    # settings defined here...
    location: "@apps.<app>.location"
```

The keys defined in this file are the ones referenced in the engine
configuration files. Have a look at one of the app configuration files to see
a concrete example.

App & Engine Locations
----------------------

One of the changes made for `tk-config-basic2` was to centralize the location
descriptors for apps and engines. By default, this configuration defines the
location for each app and engine being used in exactly one file.

For engines, the `includes/engine_locations.yml` file defines location
descriptors for all engines. These location descriptors are then included and
referenced anywhere an engine is used. This can be overridden, of course, by
explicitly defining a location descriptor in one of the engine configuration
files.

Similarly, all app location descriptors are defined in the
`includes/app_locations.yml` file. This file is then included by any
engine or app configuration that need to define an app's location.

Centralizing these location descriptors makes it extremely easy to test and
rollout new integrations onto production.

Frameworks
----------

Like the app and engine locations file, the `includes/frameworks.yml`
file defines a single, top-level `@frameworks` key that can be included
and used wherever frameworks are required (typically in the top-level
enviornment configuration files). This is the only file that defines location
descriptors for frameworks.

Software Paths
--------------

The `paths.yml` file found in older configurations has been renamed to
`software_paths.yml` and lives in the `includes` folder. This file has
been significantly reduced in terms of content because of the new Software
entity and the ability of many of the latest Toolkit engines to scan the user's
filesystem for installed software. What's left in this file is software that
does not have an engine that supports the new Software entity.

The file still defines software paths for various operating systems, but the
keys used has been modified for consistency. The file takes the form:

```yaml
# <software>
path.linux.<software>: "/path/to/the/software/on/linux/software"
path.mac.<software>: "/Applications/<Software>.app"
path.windows.<software>: C:\Path\to\the\Software.exe

# <software>
...
```

These paths are typically included and used by apps like `tk-multi-launchapp`.
See the `software_paths.yml` and
`includes/settings/tk-multi-launchapp.yml` files to see concrete examples
of how this file is used.

Questions?
----------

If you have any questions or concerns about the structure of this configuration,
or if you have any ideas for how to improve it, please send an email to
[https://knowledge.autodesk.com/contact-support](https://knowledge.autodesk.com/contact-support).
