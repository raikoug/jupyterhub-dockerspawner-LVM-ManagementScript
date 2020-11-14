#  JupyterHub + Dockerspawner 
This project wants to help others who may be searching for something similar to my solution I needed to teach python to my students.
This guide is based on Debian 10

### First of ALL the original projects, and thanks to them all:
- [Jupyter](https://github.com/jupyter "Jupyter")
- [JupyterHub](https://jupyter.org/hub "JupyterHub")
- [DockerSpawner](https://github.com/jupyterhub/dockerspawner "DockerSpawner")
- [jupyterhub-idle-culler](https://github.com/jupyterhub/jupyterhub-idle-culler "AntiIdle")

### What I needed:
- A base jupyterHub, without external authentication.
- Every Student with his JupyterLab environment
- Limited resources for each student (RAM, Disk).
- Easy user management with python script

### Missing:
- Documents persistence for student is granted, but not the "pip install"
- RestApi to manage students (only local script)

### Sorry for my low drawing performances!
![scheme](https://github.com/raikoug/jupyterhub-dockerspawner-LVM-ManagementScript/blob/main/jhub2.png?raw=true)


## Let's Begin
### Steps
1. Environment Setup
	a. Prerequisites
	b. Python
	c. LVM
	d. StartupServices
1. JupyterHub + DockerSpawner
	a. Installation
	b. Startup Services
1. User Management


#### 1 - Environment Setup
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
# We will use altinstall, and it's absolutely recommended to not overwrite system default python3!!!!
make altinstall
```
###### 1.c - LVM
There 2 cases: 
1. You already use logical volumes
2. You don't.

I will help follow second hypothesis since most of the times VPS doesn't come with this type of configurations.

Steps are simple:
- Create a big zero file
- Use it to mount our filesystem
- Create our logical volume environment

This solution is really efficient with SSD (often used with VPS!)
```
# Note: BS is the length and count, the times you make the length.
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
We won't create any user volume now; we want it to be managed automatically!
And here we go without startup service, in case of restart!

###### 1.d - StartupServices
We need our volumes loaded if the system reboot, we don't want to create new user volumes, we want to retrieve them for user data persistence!
Thh startup script will be Appended every time a new user will be created.

I will user `mount-jupy-user-volumes.service` as my service name.
I tried to use names I would remember later, but you can change all of them.
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
As you can see, we have 2 scripts: `mount_dd_and_volumes` and `umount_dd_and_volumes`
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
Make it starts at boot!
```
chmod 744 /etc/systemd/mount_dd_and_volumes
chmod 744 /etc/systemd/umount_dd_and_volumes
chmod 664 /etc/systemd/system/mount-jupy-user-volumes.service
systemctl daemon-reload
systemctl enable mount-jupy-user-volumes.service
```

We are ready to install JupyterHub and DockerSpawner

#### 2.a - JupyterHub + DockerSpawner
There are really few commands here:
```
# I expect python3.8 to be my alt install!
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
Don't warry about node warnings

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
    
    # NOT TESTED YET
    echo "umount $USER_DIRECTORY" >> /etc/systemd/umount_dd_and_volumes
    echo "" >> /etc/systemd/umount_dd_and_volumes

fi

exit 0
```
I'm sorry, and still, don't know how "USER_NOT_NAME" is chosen... I made this procedure in 2 different system and in the first one all volumes needed to be chowned to "raikoug" to be used by dockers, and the next one with another username "userpy" I had previously there.. I never used them in the procedures, I just use root (I'm a bad guy..)
The procedure I use to discover this is a first launch with a random username.
chmod 777 the user volume
Run jupyterhub for the user, and create a file.
I then discover his attributes. At least this is a one-time procedure, because from that moment on you know that "user:group" will be used for all the users!
With this you are ready to test and use the above workaround!
In userlist there is a user (in my example raikoug) with admin permission
- Start jupyer hub:
	`/opt/jupyterhub/bin/jupyterhub -f /opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py`
- Go to http://ip:8000
- Login
- An error will occur, we already know why ;)
- scripts should have create the LVM raikoug and mounted it on `/opt/jupyterhub/user_volume/raikoug`
```
chmod -R 777 /opt/jupyterhub/user_volume/raikoug
```
- retry login to jupyterhub (we needed first login with error to run the user volumes script)
- it Works!
- Create a file save, stop you server, logout, kill jupyterhub (ctrl+c under the process you started before)
- Go check in /opt/jupyterhub/user_volume/raikoug with
```
ls -la /opt/jupyterhub/user_volume/raikoug/
```
- Get the username it belongs, and chmod back it to 655
- Change the `bootstrap_user_dir.sh` script replacing USER_NOT_NAME

#### 2.b - Startup Services
Yes, another startup service
File: `/opt/jupyterhub/etc/systemd/jupyterhub.service` (create folder beforehand)
```
[Unit]
Description=JupyterHub
After=syslog.target network.target

[Service]
User=root
Environment="PATH=/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/opt/jupyterhub/bin"
ExecStart=/opt/jupyterhub/bin/jupyterhub -f /opt/jupyterhub/etc/jupyterhub/jupyterhub_config.py

[Install]
WantedBy=multi-user.target
```
Then:
```
sudo ln -s /opt/jupyterhub/etc/systemd/jupyterhub.service /etc/systemd/system/jupyterhub.service
systemctl daemon-reload
systemctl enable jupyterhub.service
systemctl start jupyterhub.service
systemctl status jupyterhub.service
```

Now you system is ready, we need some automation to create new user.

#### User Management
To create a new user the steps are:
- adduser to system
- add user to jupyterhub
- communicate username-password to students.

We will a python script to manage all these things, and will use email to notify students.
The script will take a CSV as argument.
You need to log in jupyter hub as Admin and take the token.
I won't explain you should modify my script to not have token hard coded into it, but you should!

the script!
```python
import requests
import argparse
import os
import sys
from passgen import passgen
import crypt
from myUtils import Mailer # you will find this soon in the project
from jinja2 import Environment, FileSystemLoader
from random import shuffle
import pwd

parser = argparse.ArgumentParser(description='Gestione utenti per jupyterhub')

parser.add_argument('-a', '--add',
                     metavar='add',
                     type=str,
                     help='Path to csv file')

args = parser.parse_args()

input_path = args.add

if input_path:
    if not os.path.exists(input_path):
        print(f'File doesn't exists: {input_path}')
        sys.exit()
    
    lista = open(input_path, 'r').read()
    # i'm barbaric in my csv... not quotes.. i Know.. not the best..
    if "'" in lista or '"' in lista:
        print(f"CSV file is unsupported, check the template:\n")
	# I have a template to tell how I like them...
        print(open('/opt/jupyterhub/etc/jupyterhub/csv.template', 'r').read())
        sys.exit(1)

    lista = lista.split("\n")[1::]
    # I accept that each user could have more than 1 male separated with ";"
    lista = [{'studente':el.split(',')[0], 'mail':el.split(',')[1]} for el in lista if el]
    mails = []
    allusers = []
    api_user_list = []
    
    for el in lista:
        userlist = [u.pw_name for u in pwd.getpwall()]
	
	# This could be seen as crazy... I take only alpha char of students
	# Then i shuffle them and create the username...
	# had not a better idea for duplicate "name surnames"
        protouser = el['studente']
        protouser = [b.lower() for b in protouser if b.isalpha()]
        while True:
            shuffle(protouser)
            username = "".join(protouser)
	    # check if username generated is not duplicated
            if username not in userlist:
                break
	
        print(f"Utente risulatante {username}")
	
        # Unix user creation
        password = passgen(50)
	# too long?
        encPass = crypt.crypt(password,"22")
	# encryption for useradd command on unix
        os.system("useradd -p "+encPass+f" {username}")

        ## user will be added as last thing to jupyterhub with a single api
        ## now MAILS
        file_loader = FileSystemLoader('templates')
        env = Environment(loader=file_loader)
	
	# I use a template to create html body of the mail
        template = env.get_template('base_send_password.html')
        output = template.render(username = username, password = password)

        mails = el['mail'].split(";")
        for email in mails:
            print(f"Creazione ed invio mail a {email}")
            mail = Mailer(rcpt = email, html = output)
            mail.mail_send()
	
	# DEBUG PURPOSE ONLY, this fill will store username password
        with open('utenze', 'a') as outfile:
            outfile.write(f"{username}:{password}\n")

    ## api to add users
    token = "YOUR_TOKEN"
    api_url = 'http://127.0.0.1:8000/hub/api'
    # body with list of users
    body = {"usernames": api_user_list,
            "admin": False
            }
    r = requests.post(api_url + '/users', headers={'Authorization': f"token {token}"}, json=body)
    if r.ok:
        print("DONE!!")
    else:
        print("Some error occurred")
    
```
In myUtils there is a mailer class, you can make your own or watch mine (which I modified from one passed to me by MarcoB!!!)

Noe you can call the script, giving a csv as argument.

### Next Steps
- Improve overall code
- Making a install.sh file with some magic



