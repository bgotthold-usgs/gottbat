#!bin/bash

cd "$(dirname "$0")"

sleep 10

while ! ls /media/pi | grep verbatim > /dev/null;
do
	sleep 1
done

echo "$(date)" >> /media/pi/verbatim/log.txt
python3 /home/pi/NABat/gottbat/nabat_ml_cli.py -p /media/pi/verbatim -g 77474 -u df3048a2-fa0e-11eb-9528-02fb14f25dd5  >> /media/pi/verbatim/log.txt 2>&1