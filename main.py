#!/usr/bin/env python

import paho.mqtt.client as mqtt
from time import sleep

SERVER_IP = 'localhost'

ALTITUDE = 211
USE_APPARENT = False
BUS = 0
SAMPLES = 1 

def apparent_temperature(temp,humidity):
    if humidity is None:
        return temp
    ''' http://www.engineeringtoolbox.com/water-vapor-saturation-pressure-air-d_689.html '''
    T = float(temp)+273.15
    e = 2.71828
    pw = e**(77.345+0.0057*T-7235/T) / T**8.2
    ''' Steadman, R.G., 1984: A universal scale of apparent temperature. '''
    at = -1.3 + 0.92*float(temp) + 2.2*(float(humidity)/100)*(pw/1000)
    return round(at,3)

def read_temp():
  temp = 0
  hum = 0
  try:
    import sht21
    sht = sht21.SHT21(BUS)
    for i in range(SAMPLES):
      temp += sht.read_temperature()
      hum += sht.read_humidity()
#      if(i < SAMPLES):
#        delay(5s)
    
    temp /= SAMPLES
    hum /= SAMPLES
  except Exception:
    pass
  return (temp,hum)

def read_press(read_temp=False):
  temp = 0
  press = 0
  try:
    import Adafruit_BMP.BMP085 as BMP085
    pres_sensor = BMP085.BMP085(busnum=BUS, mode=BMP085.BMP085_HIGHRES)
    
    if read_temp:
      for i in range(SAMPLES):
        temp += pres_sensor.read_temperature()
      temp /= SAMPLES
    
    for i in range(SAMPLES):
      press += pres_sensor.read_pressure()
   
    press = float(press)
    press /= SAMPLES
    press /= 100  # convert Pa to hPa
  except Exception:
    pass

  return (press,temp)

def pressure_to_sealevel(press,temp,altitude):
    try:
      a = 0.0065 * float(altitude)
    except TypeError:
      return press
    b = a / (float(temp) + a + 273.15)
    p = press / (1 - b)**(5.257)

    return p

def get_data():
    (temperature, humidity) = read_temp();
    (pressure,t) = read_press(True);
    pressure = pressure_to_sealevel(pressure,t,ALTITUDE);
    apparent = round(apparent_temperature(temperature,humidity),1)
    temperature = round(temperature,1)
    humidity = round(humidity,1)
    pressure = round(pressure,1)
    if USE_APPARENT: current = apparent
    else: current = temperature 
    print "H:"+str(humidity), "P:"+str(pressure), "T:"+str(temperature), "A:"+str(apparent), "C:"+str(current)

    return [{'topic':"room/1/temp_real", 'payload':str(temperature), 'retain':True},
            {'topic':"room/1/temp_feel", 'payload':str(apparent), 'retain':True},
            {'topic':"room/1/humidity", 'payload':str(humidity), 'retain':True},
            {'topic':"room/1/pressure", 'payload':str(pressure), 'retain':True},
            {'topic':"room/1/temp_current", 'payload':str(current), 'retain':True}]

def check(client):
    msgs = get_data()
    for data in msgs:
        client.publish(**data) 

def on_connect(client, userdata, flags, rc):
    client.subscribe("room/1/use_apparent")

def on_message(client, userdata, msg):
    if(msg.topic == 'room/1/use_apparent'):
        global USE_APPARENT
        USE_APPARENT = bool(int(msg.payload))

if __name__ == '__main__':
    client = mqtt.Client('Room 1')
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(SERVER_IP, 1883, 60)
    client.loop_start()
    while True:
        check(client)
        sleep(60)