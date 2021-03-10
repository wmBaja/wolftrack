#include <Arduino.h>

#include "StrainGauge_HX711.h"
#include "../../config.h"

StrainGauge_HX711::StrainGauge_HX711(uint8_t dataPin, uint8_t clockPin, int calibrationFactor):
  gauge(),
  gaugeReading(0),
  dataPin(dataPin),
  clockPin(clockPin),
  calibrationFactor(calibrationFactor),
  nextReadTime(0)
{
  gauge.begin(this->dataPin, this->clockPin);
  gauge.set_scale(this->calibrationFactor);
  gauge.tare();
}

void StrainGauge_HX711::loop() {
#if GENERATE_RANDOM_VALUES
  this->gaugeReading = random(1024);
#else
  unsigned long curTime = millis();

  if (curTime > this->nextReadTime) {
    float reading = gauge.get_units();

    this->gaugeReading = reading;

    // calculate the next read time
    this->nextReadTime = curTime + READ_INTERVAL;
  }
#endif
}

int StrainGauge_HX711::getValue() {
  return this->gaugeReading;
}
