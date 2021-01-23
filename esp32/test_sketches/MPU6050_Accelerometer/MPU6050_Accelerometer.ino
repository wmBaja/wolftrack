// Basic demo for accelerometer readings from Adafruit MPU6050

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>
#include <Wire.h>

// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between updates (in ms)
#define UPDATE_INTERVAL 10

Adafruit_MPU6050 mpu;

unsigned long nextUpdateTime;

void setup(void) {
  Serial.begin(BAUD_RATE);
  nextUpdateTime = millis() + UPDATE_INTERVAL;

  Serial.println("Adafruit MPU6050 test!");

  // Try to initialize!
  if (!mpu.begin()) {
    Serial.println("Failed to find MPU6050 chip");
    while (1) {
      delay(10);
    }
  }
  Serial.println("MPU6050 Found!");

  mpu.setAccelerometerRange(MPU6050_RANGE_8_G);
  mpu.setGyroRange(MPU6050_RANGE_500_DEG);
  mpu.setFilterBandwidth(MPU6050_BAND_260_HZ);

  delay(100);
}

void loop() {
  unsigned long curTime = millis();
  if (curTime > nextUpdateTime) {

    /* Get new sensor events with the readings */
    sensors_event_t a, g, temp;
    mpu.getEvent(&a, &g, &temp);
  
    /* Print out the values */
    Serial.print("Acceleration X: ");
    Serial.print(a.acceleration.x);
    Serial.print(", Y: ");
    Serial.print(a.acceleration.y);
    Serial.print(", Z: ");
    Serial.print(a.acceleration.z);
    Serial.println(" m/s^2");
  
//    Serial.print("Rotation X: ");
//    Serial.print(g.gyro.x);
//    Serial.print(", Y: ");
//    Serial.print(g.gyro.y);
//    Serial.print(", Z: ");
//    Serial.print(g.gyro.z);
//    Serial.println(" rad/s");
  
    Serial.println("");
    
    nextUpdateTime = curTime + UPDATE_INTERVAL;
  }
}
