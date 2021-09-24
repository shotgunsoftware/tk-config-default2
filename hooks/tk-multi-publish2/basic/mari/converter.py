import os
import sys
import json
import logging
import tempfile
from subprocess import Popen, PIPE, STDOUT, call

# pype_root = os.getenv('SSVFX_PIPELINE').replace('\\', '/').split('/Pipeline')[0]
pype_root = '//10.80.8.252/VFX_Pipeline'
MAKETX_PATH = pype_root + '/Pipeline/ssvfx_maya_external/modules/arnold/mtoadeploy/2018/bin/maketx.exe'
ICONVERT = 'C:/Program Files/Side Effects Software/Houdini 17.5.460/bin/iconvert.exe'
DEADLINE_CMD = 'C:/Program Files/Thinkbox/Deadline10/bin/deadlinecommand.exe'

# logging.basicConfig(format='%(message)s')
# logg = logging.getLogger('exr_converter')
# logg.setLevel(logging.DEBUG)

def exec_(cmd):
    ''' '''
    try:
        output = call(cmd)
        output = str(output)
        print(output)
    except Exception as e:
        print(e)

def convert(json_path):
    ''' '''
    exrs = json.load(open(json_path, 'r'))
    for exr_path in exrs:
        if not os.path.isfile(exr_path):
            continue
        if os.path.isfile(MAKETX_PATH):
            tx_path = os.path.splitext(exr_path)[0] + '.tx'
            cmd = [MAKETX_PATH, '-u', '--oiio', exr_path, '-o', tx_path]
            exec_(cmd)
        else:
            print('Unable to find maketx!')
            return
        if os.path.isfile(ICONVERT):
            rat_path = os.path.splitext(exr_path)[0] + '.rat'
            cmd = [ICONVERT, '-d', 'half', exr_path, rat_path]
            exec_(cmd)
        else:
            print('Unable to find iconvert!')
            return

def get_info_file(python_job_info):
    ''' Saves a temporary deadline info file
        and returns a path to it.
    '''
    job_info_file = tempfile.NamedTemporaryFile(suffix='.job', delete=False).name
    with open(job_info_file, 'a') as job_info:
        for line in python_job_info:
            job_info.write(line + '\n')
    return job_info_file

def make_job_info(job_name, frames, directory):
    python_job_info = (
        'Plugin=Python',
        'Name=' + job_name,
        'Blacklist=',
        'EventOptIns=',
        'Comments=',
        'Departments=',
        'Pool=vfx_3d',
        'SecondaryPool=vfx_mari',
        'Group=artist',
        'Priority=50',
        'MachineLimit=1',
        'OnJobComplete=Nothing',
        'Frames=' + frames,
        'Region=',
        'ChunkSize=1',
        'TaskTimeoutMinutes=0',
        'EnableAutoTimeout=False',
        'ConcurrentTasks=1',
        'LimitConcurrentTasksToNumberOfCpus=True',
        'OutputDirectory0=' + directory,
        # 'EnvironmentKyeValue0=',
        # '',
    )

    return get_info_file(python_job_info)

def make_plugin_info(script_path, arguments):

    python_plugin_info = (
        'ScriptFile=' + script_path,
        'SingleFrameOnly=False',
        'Version=2.7',
        'Arguments=' + ' '.join(arguments),
    )

    return get_info_file(python_plugin_info)

def init_deadline_job(json_path, frames=None):
    ''' Composes deadline info files and sends it to Deadline.
    frames example: '1001-1020'
    '''
    directory, job_name = os.path.split(json_path)
    # Make a python job info file
    job_info_file = make_job_info(
        job_name=job_name.split('.', 1)[0],
        frames='1',
        directory=directory)
    if not job_info_file or not os.path.isfile(job_info_file):
        return
    # Make a python plugin info file
    plugin_info_file = make_plugin_info(
        script_path=os.path.realpath(__file__),
        arguments=[json_path])
    if not plugin_info_file or not os.path.isfile(plugin_info_file):
        return
    cmd = [DEADLINE_CMD, job_info_file, plugin_info_file]
    output = Popen(cmd, stdout=PIPE, stderr=STDOUT)
    while True:
        line = output.stdout.readline()
        if not line:
            break
        line = str(line)
        if 'RuntimeError' in line:
            sys.exit(line)
        print(line)
        sys.stdout.flush()


if __name__ == '__main__':
    path = sys.argv[1:][0]
    if os.path.isfile(path) and path.endswith('.json'):
        convert(path)
