#  JupyterHub + Dockerspawner 
This project want to help others who may be searching for something similar to my solution I needed to teach python to my students.
This guide is based on Debian 10

###First of ALL all the original projects, and thanks to them all:
- [Jupyter](https://github.com/jupyter "Jupyter")
- [JupyterHub](https://jupyter.org/hub "JupyterHub")
- [DockerSpawner](https://github.com/jupyterhub/dockerspawner "DockerSpawner")
- [jupyterhub-idle-culler](https://github.com/jupyterhub/jupyterhub-idle-culler "AntiIdle")

###What I needed:
- A base jupyterHub, without external authentication.
- Every Student with his JupyterLab environment
- Limited resources for each student (RAM, Disk).
- Easy user management with python script

###Missing:
- Documents persistence for student is granted, but not the "pip install"
- RestApi to manage students (only local script)

### immagine brutta


## Let's Begin
### Steps
1. Environment Setup
	a. Prerequisites
	b. Python
	c. LVM
	d. StartupServices
1. JupyterHub + DockerHub
	a. Installation
	b. Startup Services
1. User Management


####1 - Environment Setup
it is better not to reinvent the wheel, and will use [This awesome guide ](https://jupyterhub.readthedocs.io/en/stable/installation-guide-hard.html "This awesome guide ") as base to develop the project further.
###### 1.a - Prerequisites
Some package will be needed beforehand:
```
apt update
apt install curl build-essential zlib1g-dev libncurses5-dev libgdbm-dev libnss3-dev  libsqlite3-dev libreadline-dev libffi-dev libbz2-dev  libssl-dev
```
###### 1.b - Python
I want two things: latest stable release, and a virtual environment
Now the latest stable release is Python 3.8.6, we will have it as alternative inside our system
Check here for new/correct link: https://www.python.org/ftp/python/
```
mkdir /tmp/python3.8.6
cd /tmp/python3.8.6
curl -O https://www.python.org/ftp/python/3.8.6/Python-3.8.6.tgz
tar -xf Python-3.8.6.tgz
cd Python-3.8.6
./configure --enable-optimizations
# Get result of:
nproc
# Use it insted of X
make -j X
# We will use altinstall, and it's absolutely recommened to not overwrite system default python3!!!!
make altinstall
```
###### 1.c - LVM
There 2 cases: 
1. You already use logical volumes
2. You don't.

I will help follow second hypotesis since most of the times VPS doesn't come with this type of configurations.

Steps are simple:
- Create a big zero file
- Use it to mount our filesystem
- Create our logical volume environment

This solution is really efficient with SSD (often used with VPS!)
```
# Note: BS is the lengh and count, the times you make the lenght.
# 1M 100 will be 100M
# I will use 4M 2560 --> 10240M -> 10G
dd if=/dev/zero of=/root/user_dd bs=4M count=2560
# Now we create a loop device based on our zero file
los=$(losetup -f); losetup -fP /root/user_dd
# we have in $los the loop device now: /dev/loopX based on your actual system and we can use it as variable to create our logical things
pvcreate $los
vgcreate user_vg $los
# DONE
```
We won't create any user volume now, we want it to be managed automatically!
And here we go with out startup service, in case of restart!

###### 1.d - StartupServices
We need our volumes loaded if the system reboot, we don't want to crate new user volumes, we want to retrive them for user data persistence!
Teh startup script will be Appended everytime a new user will be created.

I will user `mount-jupy-user-volumes.service` as my service name.
I tried to use names I would remeber later, but you can change all of them.
The file: `/etc/systemd/system/mount-jupy-user-volumes.service`
```
[Unit]
Before=multi-user.target
After=jupyterhub.service
Wants=network-online.target

[Service]
Type=forking
Restart=no
TimeoutSec=10
GuessMainPID=no
RemainAfterExit=yes
ExecStart=/bin/bash /etc/systemd/mount_dd_and_volumes
ExecStop=/bin/bash /etc/systemd/umount_dd_and_volumes

[Install]
WantedBy=multi-user.target
```
As you can see we have 2 scripts: `mount_dd_and_volumes` and `umount_dd_and_volumes`
here they are:
file `/etc/systemd/mount_dd_and_volumes`
```
## initialize loop device user_dd
losetup -fP /root/user_dd 

## volume research
pvscan
vgscan
lvscan

## User volume mount
```
we will append in THIS file above the mounts

The file: `/etc/systemd/umount_dd_and_volumes`
```
# this file should be aligned with umount of the user volumes

```

We are ready to JupyterHub and DockerSpawner conf

####2 - JupyterHub + DockerHub
There really few commands here:
```
# i expect python3.8 to be my alt install!
python3.8 -m venv /opt/jupyterhub/
/opt/jupyterhub/bin/python3 -m pip install wheel
/opt/jupyterhub/bin/python3 -m pip install jupyterhub jupyterlab
/opt/jupyterhub/bin/python3 -m pip install ipywidgets
/opt/jupyterhub/bin/python3 -m pip install dockerspawner
/opt/jupyterhub/bin/python3 -m pip install jupyterhub-idle-culler
# we will need this for user management!
/opt/jupyterhub/bin/python3 -m pip install passgen 

# Then we need Node, Npm and proxy:
apt install nodejs npm
npm install -g configurable-http-proxy
```
Don't warry abount node warnings

Now we can set up our folders:
```
mkdir -p /opt/jupyterhub/etc/jupyterhub/
mkdir /opt/jupyterhub/user_volume/
```
And our configuration file should be in `cd /opt/jupyterhub/etc/jupyterhub/`
This is where I stop following the ground up guide.
The next code will be long! I will try to comment the more I can!
file: `/opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py`
```python
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
```

file `/opt/jupyterhub/etc/jupyterhub/userlist`
```
raikoug admin
friend1
friend2
```

file `/opt/jupyterhub/etc/jupyterhub/bootstrap_user_dir.sh`
```
#!/bin/bash

USER=$1
if [ "$USER" == "" ]; then
    exit 1
fi
echo "Check volumes for $USER ..."

BASE_DIRECTORY=/opt/jupyterhub/user_volumes/

USER_DIRECTORY=$BASE_DIRECTORY/$USER

if [ -d "$USER_DIRECTORY" ]; then
    echo "... Volume already exists, bye"
    exit 0
else
    echo "... no volume, begin: $USER_DIRECTORY"
    # create the mount destination, the user volume for docker
    mkdir $USER_DIRECTORY
    # create volume with only 100M
    lvcreate -L 100M -n $USER user_vg
    USER_VOLUME=/dev/user_vg/$user
    # actual mount
    mount $USER_VOLUME $USER_DIRECTORY

    # chown THIS part is tricky!
    chown -R USER_NOT_NAME:users $USER_DIRECTORY
  
    # startup script alignment!!!
    echo "mount $USER_VOLUME $USER_DIRECTORY" >> /etc/systemd/mount_dd_and_volumes
    echo "chown -R USER_NOT_NAME:users $USER_DIRECTORY" >> /etc/systemd/mount_dd_and_volumes
    echo "" >> /etc/systemd/mount_dd_and_volumes
        

fi

exit 0
```
I'm sorry, and still, don't know how "USER_NOT_NAME" is chosen... I made this procedure in 2 different system and in the first one all volumes needed to be chowned to "raikoug" to be used by dockers, and the next one with another username "userpy" i had previously there.. I never used them in the procedures, I just use root (i'm a bad guy..)

