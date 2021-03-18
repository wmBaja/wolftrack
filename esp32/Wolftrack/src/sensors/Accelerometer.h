#ifndef _ACCELEROMETER_H
#define _ACCELEROMETER_H

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#include "Sensor.h"

// amount of time between sensor reads
#define READ_INTERVAL 10

class Accelerometer: public Sensor {
    Adafruit_MPU6050 mpu;
    // the most recently calculated accelerations in integer form
    int xAccel;
    int yAccel;
    int zAccel;
    // the time at which to read a new value from the sensor
    unsigned long nextReadTime;
  public:
    Accelerometer();
    void loop();
    int getValue();
	int getMoreValues();
	int getDataBits();
    int getXAccel();
    int getYAccel();
    int getZAccel();
};

#endif
