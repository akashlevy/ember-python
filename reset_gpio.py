# Import GPIO library
import RPi.GPIO as GPIO

# Pin mappings
USE_MMCM_PIN = 1
RRAM_BUSY_PIN = 7
MCLK_PAUSE_PIN = 25

# Reset to 0 by default
GPIO.setmode(GPIO.BCM)
GPIO.setup(MCLK_PAUSE_PIN, GPIO.OUT)
GPIO.setup(USE_MMCM_PIN, GPIO.OUT)
GPIO.output(MCLK_PAUSE_PIN, 0)
GPIO.output(USE_MMCM_PIN, 0)
