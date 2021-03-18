#include <Arduino.h>
#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

#include "Accelerometer.h"
#include "../../config.h"
#include "../utils.h"

Accelerometer::Accelerometer():
  mpu(),
  xAccel(0),
  yAccel(0),
  zAccel(0),
  nextReadTime(0)
{
  mpu.begin();
  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_260_HZ);
}

void Accelerometer::loop() {
#if GENERATE_RANDOM_VALUES
  this->xAccel = random(2048);
  this->yAccel = random(2048);
  this->zAccel = random(2048);
#else
  unsigned long curTime = millis();

  if (curTime > this->nextReadTime) {
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);

    // get the accel values in m/s^2
    float xAccelms2 = a.acceleration.x;
    float yAccelms2 = a.acceleration.y;
    float zAccelms2 = a.acceleration.z;

    // map the accels to the int value range
    this->xAccel = utils::mapRangeToRangeWithRatio(ACCEL_REAL_START, ACCEL_INT_START, ACCEL_INT_REAL_RATIO, xAccelms2);
    this->yAccel = utils::mapRangeToRangeWithRatio(ACCEL_REAL_START, ACCEL_INT_START, ACCEL_INT_REAL_RATIO, yAccelms2);
    this->zAccel = utils::mapRangeToRangeWithRatio(ACCEL_REAL_START, ACCEL_INT_START, ACCEL_INT_REAL_RATIO, zAccelms2);

    // calculate the next read time
    this->nextReadTime = curTime + READ_INTERVAL;
  }
#endif
}

int Accelerometer::getValue() {
  // NOTE: this should not be used; use getXAccel, getYAccel, and getZAccel
  return 0;
}

// Return non-zero value when alternate getValue functions should be used
int Accelerometer::getMoreValues() {
	return IS_ACCELEROMETER;
}

int Accelerometer::getDataBits() {
	return ACCELERATION_DATA_BITS;
}

int Accelerometer::getXAccel() {
  return this->xAccel;
}

int Accelerometer::getYAccel() {
  return this->yAccel;
}

int Accelerometer::getZAccel() {
  return this->zAccel;
}
