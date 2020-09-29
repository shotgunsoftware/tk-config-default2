# Pipeline tools
import ExportNodes
menubar = nuke.menu("Nuke")
pipelinemenu = menubar.addMenu("Pipeline")
pipelinemenu.addCommand("Export nodes as node or template", ExportNodes.main, "Ctrl+alt+S")
