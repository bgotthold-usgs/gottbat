#!bin/bash

STORAGE=VERBATIM

cd "$(dirname "$0")"

echo "$(date)" >> /media/pi/$STORAGE/log.txt
pwd >> /media/pi/$STORAGE/log.txt
which python3 >> /media/pi/$STORAGE/log.txt
pip3 freeze >> /media/pi/$STORAGE/log.txt

GRTS=$(cat ../settings.txt | grep GRTS | cut -d "=" -f 2)
DETECTOR=$(cat ../settings.txt | grep DETECTOR | cut -d "=" -f 2)

python3 /media/pi/$STORAGE/gottbat/nabat_ml_cli.py -p /media/pi/$STORAGE -g $GRTS -u $DETECTOR  >> /media/pi/$STORAGE/log.txt 2>&1
