#!/bin/bash
# file: afterStartup.sh
#
# This script will be executed in background after Witty Pi 3 gets initialized.
# If you want to run your commands after boot, you can place them here.
HOME=/home/pi
echo "$(date)" >> ~/boot.txt
PATH=/home/pi/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/local/games:/usr/games

STORAGE=VERBATIM

while ! ls /media/pi | grep $STORAGE > /dev/null;
do
	sleep 1
done

python3 /home/pi/internet_connection.py &
bash /media/pi/*/gottbat/process.sh &
bash /media/pi/*/gottbat/record.sh &

# sleep 5
# export TERM=linux
# sudo minicom -D /dev/ttyUSB2 -S ~/lte.script >> ~/lte_log.txt 2>&1