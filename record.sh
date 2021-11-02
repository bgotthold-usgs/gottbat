#!bin/bash

sleep 15

STORAGE=VERBATIM
MINAMP=0.10

while ! ls /media/pi | grep $STORAGE > /dev/null;
do
	sleep 1
done

while true 
do
	hour=$(date +%H)
	arecord -d 5 -f S16 -r 250000 -t wav --device hw:2,0 --use-strftime /media/pi/$STORAGE/wav.temp -c 1
	sleep 1
	amp=$(sox -t .wav /media/pi/VERBATIM/wav.temp -n stat 2>&1 | grep "Maximum amplitude:" | cut -d ":" -f 2 | bc)
	if (( $(echo "$amp > $MINAMP" | bc -l) )); then
		mv /media/pi/$STORAGE/wav.temp /media/pi/$STORAGE/$(date +%s).wav
	fi
done
