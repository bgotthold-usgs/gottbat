#!bin/bash

sleep 10

while ! ls /media/pi | grep verbatim > /dev/null;
do
	sleep 1
done

while ls /media/pi | grep verbatim > /dev/null; 
do
	hour=$(date +%H)
	echo $hour
	arecord -d 5 -f S16 -r 250000 -t wav --use-strftime /media/pi/verbatim/wav.temp -c 1
	sleep 1
	mv /media/pi/verbatim/wav.temp /media/pi/verbatim/$(date +%s).wav
done
