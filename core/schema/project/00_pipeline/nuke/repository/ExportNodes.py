import nuke
import nukescripts
import os


def main():

    dirname = os.path.dirname(os.path.abspath(__file__))
    selection = nuke.selectedNodes()
    if selection == []:
        nuke.message("There are no nodes selected.")
    else:
        class TemplateCreation(nukescripts.PythonPanel):
            def __init__(self, node):

                nukescripts.PythonPanel.__init__(self, 'Template creation')
                self.tcNode = node
                self.typeKnob = nuke.Enumeration_Knob('exporttype', 'Export selected node(s) as', ['Node', 'Template'])
                self.elementKnob = nuke.String_Knob('expname', 'Name')
                for k in (self.typeKnob, self.elementKnob):
                    self.addKnob(k)

        tc = TemplateCreation(selection)
        if tc.showModalDialog():
            exptype = tc.typeKnob.value()
            expname = tc.elementKnob.value()

            if expname == '':
                nuke.message('There was no name specified.')
            else:
                nuke.message("Export as:" + exptype + " " + expname)
                if exptype == 'Template':
                    expfile = expname + '.nk'
                    exploc = os.path.join(dirname, "project_repo","Templates", expfile)
                    exploc_win = exploc.replace(os.sep, '/')
                    nuke.nodeCopy(exploc_win)
                    nuke.message("Exporting " + expname + " as template was successful.")
                if exptype == 'Node':
                    expfile = expname + '.nk'
                    exploc = os.path.join(dirname, "project_repo", "Nodes", expfile)
                    exploc_win = exploc.replace(os.sep, '/')
                    nuke.nodeCopy(exploc_win)
                    nuke.message("Exporting " + expname + " as node was successful.")
