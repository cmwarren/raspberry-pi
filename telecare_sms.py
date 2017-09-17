import sys
import time
import os
import RPi.GPIO as GPIO
import urllib

sms_apikey = 'NXqJDwuUIkQ-wEQRo0cSbXyQKoQdmVZTb96zUxXz1r'
mobile_number = raw_input("Enter a mobile number to receive SMS:")
SMS_THRESHOLD = 30  # Number of timesteps with activity detected before SMS sent
SMS_RESEND_DELAY = 240  # Number of timesteps to wait before sending another SMS

GPIO.setmode(GPIO.BCM)
DEBUG = 0

# read SPI data from MCP3008 chip, 8 possible adc's (0 thru 7)
def readadc(adcnum, clockpin, mosipin, misopin, cspin):
    if ((adcnum > 7) or (adcnum < 0)):
        return -1
    GPIO.output(cspin, True)

    GPIO.output(clockpin, False)  # start clock low
    GPIO.output(cspin, False)     # bring CS low

    commandout = adcnum
    commandout |= 0x18  # start bit + single-ended bit
    commandout <<= 3    # we only need to send 5 bits here
    for i in range(5):
        if (commandout & 0x80):
            GPIO.output(mosipin, True)
        else:
            GPIO.output(mosipin, False)
        commandout <<= 1
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)

    adcout = 0
    # read in one empty bit, one null bit and 10 ADC bits
    for i in range(12):
        GPIO.output(clockpin, True)
        GPIO.output(clockpin, False)
        adcout <<= 1
        if (GPIO.input(misopin)):
            adcout |= 0x1

    GPIO.output(cspin, True)
    
    adcout >>= 1       # first bit is 'null' so drop it
    return adcout


def send_sms(apikey, numbers, sender, message):
    data = urllib.urlencode({'apikey': apikey, 'numbers': numbers,
                                   'message': message, 'sender': sender})
    data = data.encode('utf-8')
    url = "https://api.txtlocal.com/send/?"
    f = urllib.urlopen(url, data)
    fr = f.read()
    return (fr)

# change these as desired - they're the pins connected from the
# SPI port on the ADC to the Cobbler
SPICLK = 18
SPIMISO = 23
SPIMOSI = 24
SPICS = 25
PIR = 17
LED = 2

# set up the SPI interface pins
GPIO.setup(SPIMOSI, GPIO.OUT)
GPIO.setup(SPIMISO, GPIO.IN)
GPIO.setup(SPICLK, GPIO.OUT)
GPIO.setup(SPICS, GPIO.OUT)
GPIO.setup(PIR, GPIO.IN)
GPIO.setup(LED, GPIO.OUT)

# 10k trim pot connected to adc #0
potentiometer_adc = 0;

last_read = 0       # this keeps track of the last potentiometer value
tolerance = 5       # to keep from being jittery we'll only change
                    # volume when the pot has moved more than 5 'counts'

pressure = False
movement = False
reading_count = 0
last_sms_count = 0

while True:
    try:
        # we'll assume that the pot didn't move
        trim_pot_changed = False
        
        # read the analog pin
        trim_pot = readadc(potentiometer_adc, SPICLK, SPIMOSI, SPIMISO, SPICS)
        # how much has it changed since the last read?
        pot_adjust = abs(trim_pot - last_read)

        if DEBUG:
            print "trim_pot:", trim_pot
            print "pot_adjust:", pot_adjust
            print "last_read", last_read

        if pot_adjust > tolerance:
            trim_pot_changed = True

        if DEBUG:
            print "trim_pot_changed", trim_pot_changed

        if trim_pot_changed:
            set_volume = trim_pot / 10.24           # convert 10bit adc0 (0-1024) trim pot read into 0-100 volume level
            set_volume = round(set_volume)          # round out decimal value
            set_volume = int(set_volume)            # cast volume as integer

            if set_volume > 5:
                print "Pressure detected"
                pressure = True
            else:
                print "No pressure"
                pressure = False

            if DEBUG:
                print 'Volume = {volume}%' .format(volume = set_volume)
            set_vol_cmd = 'sudo amixer cset numid=1 -- {volume}% > /dev/null' .format(volume = set_volume)
            os.system(set_vol_cmd)  # set volume

            if DEBUG:
                print "set_volume", set_volume
                print "tri_pot_changed", set_volume

            # save the potentiometer reading for the next loop
            last_read = trim_pot
            
        i = GPIO.input(PIR)
        if i == 0:                 #When output from motion sensor is LOW
            if movement:
                print "No movement"
            movement = False
        elif i == 1:               #When output from motion sensor is HIGH
            print "Movement detected"
            movement = True
            
        if pressure or movement:
            GPIO.output(LED, 1)  #Turn ON LED
            reading_count += 1  # Track activity to decide when to send SMS
        else:
            GPIO.output(LED, 0)  #Turn OFF LED


        # Send SMS
        if reading_count > SMS_THRESHOLD and last_sms_count == 0:
            if mobile_number:
                resp = send_sms(sms_apikey, mobile_number,
                                'Telecare', 'Billy got up')
                print ("SMS sent: " + resp)
            last_sms_count += 1

        # Wait for a number of timesteps before sending any more texts
        if last_sms_count > SMS_RESEND_DELAY:
            last_sms_count = 0
            reading_count = 0
        
        # hang out and do nothing for a half second
        time.sleep(0.5)
    except KeyboardInterrupt:
        print "Stopping..."
        break
    
GPIO.cleanup()