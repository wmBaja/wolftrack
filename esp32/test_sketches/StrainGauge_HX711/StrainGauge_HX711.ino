#include "HX711.h"

#define calibration_factor 10

// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between updates (in ms)
#define UPDATE_INTERVAL 50

#define HX711_DATA 4
#define HX711_CLK 2

unsigned long nextUpdateTime;
HX711 gauge;

void setup() {
  Serial.begin(BAUD_RATE);

  Serial.println("Starting...");

  gauge.begin(HX711_DATA, HX711_CLK);
  gauge.set_scale(calibration_factor); //This value is obtained by using the SparkFun_HX711_Calibration sketch
  gauge.tare(); //Assuming there is no weight on the scale at start up, reset the scale to 0
}

void loop() {
  unsigned long curTime = millis();
  if (curTime > nextUpdateTime) {
    Serial.println(gauge.get_units(), 1); // .get_units() returns a float

    nextUpdateTime = curTime + UPDATE_INTERVAL;
  }
}
