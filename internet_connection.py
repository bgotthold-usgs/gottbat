import RPi.GPIO as GPIO
import time
import urllib.request

LED_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(LED_PIN, GPIO.OUT)

MAXTIMEOUT=300
timeout= 5
GPIO.output(LED_PIN,GPIO.LOW)


try:
    while True:
        try:
            urllib.request.urlopen('http://example.com')        
            GPIO.output(LED_PIN,GPIO.HIGH)
            timeout=min(MAXTIMEOUT,timeout * 2)
        except Exception as e:
            timeout = 5
            GPIO.output(LED_PIN,GPIO.LOW)
        finally:
            time.sleep(timeout)
except:
    GPIO.cleanup()
