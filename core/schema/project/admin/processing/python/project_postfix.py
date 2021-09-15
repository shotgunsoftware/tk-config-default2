import os, sys, json
import logging
import logging.config

# set dev or primary ssvfx_script paths
ssvfx_script_path = os.path.join( "C:", "Users", os.getenv('username'), "Scripts", "Pipeline" )
if os.path.exists(ssvfx_script_path):
    pipeline_root = ssvfx_script_path
    ssvfx_script_path = os.path.join(pipeline_root,"ssvfx_scripts")
else:
    if os.environ.get('SSVFX_PIPELINE'): 
        pipeline_root =  os.environ["SSVFX_PIPELINE"]
        ssvfx_script_path = os.path.join(pipeline_root,"Pipeline", "ssvfx_scripts")
    else:
        print("SSVFX_PIPELINE not in env var keys. Using explicit")
        pipeline_root = "\\\\10.80.8.252\\VFX_Pipeline"
        ssvfx_script_path = os.path.join(pipeline_root,"Pipeline\\ssvfx_scripts")

try:
    # Get an instance of a logging
    logging.config.fileConfig(os.path.join(ssvfx_script_path,"logging.ini"))
    logger_config_file = os.path.join(ssvfx_script_path,"logging.ini")
    # create logger
    logger = logging.getLogger('ssvfxLogger')
    logger.info("Using ssvfxLogger!")
except:
    logger = logging.getLogger()
    logger.warning("Could not find global ssvfxLogger!")

def dict_nav( dictionary, sequence ):
    '''
    Simplified navigator for nested dictionaries
    returns first non-dictionary value or None

    :dictionary: starting dictionary to navifate
    :sequence: ordered sequence of keys to test in list form
    '''
    if not dictionary or not sequence:
        return None

    logger.info( ">>>>> Navigating sub-dictionaries for: %s" % "->".join(sequence) )
    sub_dict = dictionary
    for key in sequence:
        sub_dict = sub_dict.get(key)

        if not isinstance(sub_dict, dict):
            return sub_dict

json_file = sys.argv[-1]
json_file_open = open(json_file, "r")
file_str = json_file_open.read()
json_file_open.close()
json_data = json.loads(file_str)

process_jobs = json_data['processes']
process_keys = list(process_jobs.keys())

### Corrective Loop to add nuke node values to JSON file
for key in process_keys:
    job_key = str(key)
    job = process_jobs[key]

    # check for nuke settings, Entity info, sequence ccc info, and sequence ccc path
    # if all are present, generate node dictionary and save the json
    nuke_settings = process_jobs.get(job_key).get('nuke_settings')
    if not nuke_settings:
        logger.info( ">>>>> No Nuke Settings, bypassing: %s" % job_key )
        continue

    seq_ccc_path = (
        dict_nav( json_data, [ "entity_info", "sg_seq_ccc", "local_path_windows", ] ) 
        or dict_nav( json_data, [ "entity_info", "attributes", "sg_seq_ccc", "local_path_windows", ] )
        )
    if seq_ccc_path:
        nuke_settings['seq_ccc'] = {
                                    "read_from_file": True,
                                    "file": seq_ccc_path.replace("\\","/"),
                                    "disable": False
                                    }
        logger.info(">>>>> Found Sequence CCC Path: %s\n" % nuke_settings.get('seq_ccc') )

    ### Slate Fixes
    # Fix any silly filename/version name connections
    slate = nuke_settings.get("SSVFX_SLATE")
    if slate:
        # fix version name
        reset_version = slate.get('version')
        if reset_version:
            slate.update({
                "version": reset_version.split("/")[-1]
            })
    
        # find/fill slate frame range
        first_frame = ( dict_nav( json_data, [ "entity_info", "sg_head_in" ] )
            or dict_nav( json_data, [ "entity_info", "attributes", "sg_head_in" ] ) )
        last_frame = ( dict_nav( json_data, [ "entity_info", "sg_tail_out" ] )
            or dict_nav( json_data, [ "entity_info", "attributes", "sg_tail_out" ] ) )
        if first_frame and last_frame:
            slate.update({
                "start_frame": float(first_frame),
                "end_frame": float(last_frame)
            })

        # finally, set slate vendor name
        slate.update({
            "vendor": "SSVFX"
        })

        logger.info(">>>>> Updated Slate Node: %s" % slate)

logger.info( ">>>>> Completed Postfix Process, writing json..." )

# re-write JSON file
json_object = json.dumps( json_data, indent=4 )
with open(json_file, "w") as outfile:
    outfile.write(json_object)
    outfile.close()

logger.info( ">>>>> Postfix JSON write complete. Resuming pump_process.py" )