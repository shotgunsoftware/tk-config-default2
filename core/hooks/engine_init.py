# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Hook that gets executed every time an engine has fully initialized.

"""
from tank import Hook
import os
import sgtk
import socket

class EngineInit(Hook):
    
    def execute(self, engine, **kwargs):
        """
        Gets executed when a Toolkit engine has fully initialized.
        At this point, all applications and frameworks have been loaded,
        and the engine is fully operational.
        """
        if engine.name == "tk-nuke":
            import nuke
            nuke.tprint("Nuke settings define in core\hooks\engine_int.py")
            nroot = nuke.Root()

            # Get SG 
            ctx = engine.context
            project = ctx.project
            sg = engine.shotgun

            filters = [
            ['sg_status', 'in', ['Active', 'Development']],
            ['id', 'is', project['id']]
            ]
            fields = [
            'name',
            'sg_format_width',
            'sg_format_height',
            'sg_delivery_format_width',
            'sg_delivery_format_height',            
            'sg_format_pixel_aspect_ratio',
            'sg_pixel_aspect_ratio',
            'sg_frame_rate',
            'sg_short_name'
            ]
            project_info =  sg.find_one('Project', filters, fields)
            if project_info:
                if not(project_info['sg_frame_rate'] and 
                project_info['sg_format_width'] and
                project_info['sg_format_height'] and
                project_info['sg_format_pixel_aspect_ratio'] and 
                project_info['sg_short_name']):
                    nuke.tprint("!!!Missing important Project info to update Nuke. Please inform production!!!")
                    nuke.tprint("Project settings : ")
                    nuke.tprint("- Name: %s " % str(project_info['name']))              
                    nuke.tprint("- Format: %s x %s : %s" % (str(project_info['sg_format_width']), 
                                                            str(project_info['sg_format_height']), 
                                                            str(project_info['sg_format_pixel_aspect_ratio'])))
                    nuke.tprint("- FPS: %s" % str(project_info['sg_frame_rate']))                    
                    nuke.tprint("- ShortName: %s" % str(project_info['sg_short_name']))      
                    if (project_info['sg_delivery_format_width'] and
                        project_info['sg_delivery_format_height']):
                        nuke.tprint("- Delviery format: %s x %s" % (str(project_info['sg_delivery_format_width']), 
                                                                    str(project_info['sg_delivery_format_height'])))

                else:
                    nroot.knob('fps').setValue(float(project_info['sg_frame_rate']))
                    nuke.knobDefault("Root.fps", project_info['sg_frame_rate']) 
                    nuke.addFormat("%s %s %s %s" % (str(project_info['sg_format_width']), 
                                    str(project_info['sg_format_height']), 
                                    str(project_info['sg_format_pixel_aspect_ratio']), 
                                    (project_info['sg_short_name']+"_"+str(project_info['sg_format_width']))))
                    nuke.knobDefault("Root.format", 
                                    (project_info['sg_short_name']+"_"+str(project_info['sg_format_width']))) 

                    nuke.tprint("Project settings applied:")
                    nuke.tprint("- Name: %s " % project_info['name'])              
                    nuke.tprint("- Format: %s x %s : %s" % (str(project_info['sg_format_width']), 
                                                            str(project_info['sg_format_height']),
                                                            str(project_info['sg_format_pixel_aspect_ratio'])))
                    nuke.tprint("- FPS: %s" % project_info['sg_frame_rate'])
                    nuke.tprint("- ShortName: %s" % str(project_info['sg_short_name']))    
            else:
                nuke.tprint('Issue retrieving format settings for Project from SG.')        

        elif engine.name == "tk-desktop":
            
            self.logger.debug("Desktop engine init. Running processes.")
            try:
                # Get the machine info
                user_id = engine.context.user['id'] 
                machine_name = os.environ['COMPUTERNAME']
                ip_address = socket.gethostbyname(socket.gethostname())
                self.logger.debug("User ID %s has machine %s with IP of %s"% (str(user_id), machine_name, ip_address))

                # Submit info to SG
                sg = engine.shotgun
                data = {
                    'sg_machine': machine_name,
                    'sg_ip_address': str(ip_address)
                }
                result = sg.update('HumanUser', user_id, data)
                if result:
                    self.logger.debug("Updated the SG User info.")

            except:
                self.logger.debug("Problem updating the SG User info.")

        elif engine.name =="tk-maya":
            import maya.cmds as cmds

            # enable rolling autosave
            cmds.autoSave(
                        enable = 1,
                        interval = 1800,
                        destination = 1,
                        folder = "H:/MAYA_TEMP/autosaves/",
                        limitBackups = 1
                        )

        else:
            self.logger.debug("Could not get engine!") 