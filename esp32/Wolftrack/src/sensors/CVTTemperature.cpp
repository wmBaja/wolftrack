#include <Arduino.h>

#include "CVTTemperature.h"
#include "../../config.h"

CVTTemperature::CVTTemperature():
  cvtTemp(0),
  oneWire(CVT_TEMP_PIN),
  sensors(&oneWire),
  nextReadTime(0)
{
	sensors.begin();
}

void CVTTemperature::loop() {
#if GENERATE_RANDOM_VALUES
  this->cvtTemp = random(255);
#else
  unsigned long curTime = millis();

  if (curTime > this->nextReadTime) {
    sensors.requestTemperatures();
    float temperatureF = sensors.getTempFByIndex(0);
    this->cvtTemp = (int) temperatureF;

    // calculate the next read time
    this->nextReadTime = curTime + READ_INTERVAL;
  }

#endif
}

int CVTTemperature::getValue() {
  return this->cvtTemp;
}

int CVTTemperature::getMoreValues() {
	return GENERIC_VALUE;
}

int CVTTemperature::getDataBits() {
	return CVT_TEMP_DATA_BITS;
}

void  CVTTemperature::printType() {
	Serial.println("\tCVT Temperature");
}
