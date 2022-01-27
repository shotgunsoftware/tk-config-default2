
nuke.pluginAddPath( './callbacks')
nuke.pluginAddPath( './icons')
nuke.pluginAddPath( './gizmos' )
nuke.pluginAddPath( './plugins' )
nuke.pluginAddPath( './python' )

###### Project specific settings
# SG Nuke will include this file as part of the startup process
# Change settings as required as per the Projects specs

#### Color
nuke.knobDefault('Root.colorManagement', 'Nuke')
nuke.knobDefault('Root.OCIO_config', 'nuke-default')

nuke.knobDefault('Root.monitorLut', 'rec709')
nuke.knobDefault('Root.monitorOutLut', 'rec709')
nuke.knobDefault('Root.int8Lut', 'sRGB')
nuke.knobDefault('Root.int16Lut', 'rec709')
nuke.knobDefault('Root.logLut', 'AlexaV3LogC')
nuke.knobDefault('Root.floatLut', 'rec709')


