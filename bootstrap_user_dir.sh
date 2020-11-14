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
