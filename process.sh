#!bin/bash


STORAGE=VERBATIM

cd "$(dirname "$0")"

echo "$(date)" >> /media/pi/$STORAGE/log.txt
pwd >> /media/pi/$STORAGE/log.txt
which python3 >> /media/pi/$STORAGE/log.txt
pip3 freeze >> /media/pi/$STORAGE/log.txt
python3 /media/pi/$STORAGE/gottbat/nabat_ml_cli.py -p /media/pi/$STORAGE -g 77474 -u a524c686-1a68-11ec-bb96-06e6624076b1  >> /media/pi/$STORAGE/log.txt 2>&1
