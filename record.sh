#!bin/bash

STORAGE=VERBATIM
MINAMP=0.10

# Exports pin to userspace
echo "18" > /sys/class/gpio/export                  

# Sets pin 18 as an output
echo "out" > /sys/class/gpio/gpio18/direction


while true 
do
	# Sets pin 18 to low
	echo "0" > /sys/class/gpio/gpio18/value

	hour=$(date +%H)
	arecord -d 5 -f S16 -r 250000 -t wav --device plughw:2,0 --use-strftime /media/pi/$STORAGE/wav.temp -c 1
	amp=$(sox -t .wav /media/pi/VERBATIM/wav.temp -n stat 2>&1 | grep "Maximum amplitude:" | cut -d ":" -f 2 | bc)
	if (( $(echo "$amp > $MINAMP" | bc -l) )); then
		# Sets pin 18 to high
		echo "1" > /sys/class/gpio/gpio18/value

		mv /media/pi/$STORAGE/wav.temp /media/pi/$STORAGE/$(date +%s).wav
		sleep 0.5
	fi
done
