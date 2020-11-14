# Configuration file for jupyterhub.
#Imports

import os
import sys
from subprocess import check_call
import shutil

# Script to be called at docker spawning, this just run the script bootstrap_user_dir.sh
# Giving username as argument
def create_dir_hook(spawner):
    username = spawner.user.name # get the username
    volume_path = os.path.join('/opt/jupyterhub/user_volumes/', username) 
    if not os.path.exists(volume_path):
        check_call(['/opt/jupyterhub/etc/jupyterhub/bootstrap_user_dir.sh', f"{username}"])
        os.chmod(volume_path, 0o755)

c = get_config()

c.JupyterHub.log_level = 'DEBUG'

# We chose dockerspawner as spawner
c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'

# Image to be spawn to users
c.DockerSpawner.image = 'jupyter/scipy-notebook'

# Commands to pass to docker spawning, our user will have LAB as default jupyter style
spawn_cmd = os.environ.get('DOCKER_SPAWN_CMD', "start-singleuser.sh --SingleUserNotebookApp.default_url=/lab")
c.DockerSpawner.extra_create_kwargs.update({ 'command': spawn_cmd })

# Network for communication between Docker and JupyterHub
network_name = 'bridge'
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.network_name = network_name

# Resource Management for docker!
c.DockerSpawner.extra_host_config = {
    'network_mode': network_name,
    'mem_limit': '300m',
    'memswap_limit': '300m',
    'mem_swappiness': 0
}

## pre spawn user volume! bootstrap_user_dir.sh
c.DockerSpawner.pre_spawn_hook = create_dir_hook

# Data persistence, it is on dockerspawner doc pages
notebook_dir = os.environ.get('DOCKER_NOTEBOOK_DIR') or '/home/jovyan'
c.DockerSpawner.notebook_dir = notebook_dir

# This is where we mounted user volumes with lvm
host_dir = '/opt/jupyterhub/user_volumes/{username}'
c.DockerSpawner.volumes = { host_dir: notebook_dir }

c.DockerSpawner.remove_containers = True
c.DockerSpawner.debug = True

# Machine IP not 127.0.0.1!!!
c.JupyterHub.hub_ip = 'IP_ADDRESS'
c.JupyterHub.hub_port = 8080

# User access with admin!
c.Authenticator.whitelist = whitelist = set()
c.Authenticator.admin_users = admin = set()
c.JupyterHub.admin_access = True
pwd = os.path.dirname(__file__)
with open('/opt/jupyterhub/etc/jupyterhub/userlist') as f:
    for line in f:
        if not line:
            continue
        parts = line.split()
        # in case of newline at the end of userlist file
        if len(parts) >= 1:
            name = parts[0]
            whitelist.add(name)
            if len(parts) > 1 and parts[1] == 'admin':
                admin.add(name)

# anti idle:
c.JupyterHub.services = [
    {
        'name': 'idle-culler',
        'admin': True,
        'command': [
            sys.executable,
            '-m', 'jupyterhub_idle_culler',
            '--timeout=3600'
        ],
    }
]
