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

    print( ">>>>> Navigating sub-dictionaries for: %s" % "->".join(sequence) )
    sub_dict = dictionary
    for key in sequence:
        sub_dict = sub_dict.get(key)

        if key == sequence[-1]:
            return sub_dict

        if not isinstance(sub_dict, dict):
            return sub_dict

# Read in the relevant json file
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

    logger.info( ">>>>> Completed revisions for %s" % job_key )
    
logger.info( ">>>>> Completed Postfix Process, writing json..." )

# re-write JSON file
json_object = json.dumps( json_data, indent=4 )
with open(json_file, "w") as outfile:
    outfile.write(json_object)
    outfile.close()

logger.info( ">>>>> Postfix JSON write complete. Resuming submission_process.py" )