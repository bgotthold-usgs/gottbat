#!bin/bash

sleep 15

STORAGE=VERBATIM

while ! ls /media/pi | grep $STORAGE > /dev/null;
do
	sleep 1
done

while true 
do
	hour=$(date +%H)
	arecord -d 5 -f S16 -r 250000 -t wav --device hw:2,0 --use-strftime /media/pi/$STORAGE/wav.temp -c 1
	sleep 1
	mv /media/pi/$STORAGE/wav.temp /media/pi/$STORAGE/$(date +%s).wav
done
