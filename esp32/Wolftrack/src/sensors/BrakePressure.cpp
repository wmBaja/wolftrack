#include <Arduino.h>

#include "BrakePressure.h"
#include "../../config.h"
#include "../utils.h"

BrakePressure::BrakePressure(MCP3008* adc, uint8_t adcChannel):
  adc(adc),
  adcChannel(adcChannel),
  brakePressure(0),
  nextReadTime(0)
{}

void BrakePressure::loop() {
#if GENERATE_RANDOM_VALUES
  this->brakePressure = random(2000);
#else
  unsigned long curTime = millis();

  if (curTime > this->nextReadTime) {
    uint32_t analogValue = this->adc->analogRead(this->adcChannel);
    this->brakePressure = utils::mapRangeToRange(0, 1024, 0, 2000, analogValue);
    // calculate the next read time
    this->nextReadTime = curTime + READ_INTERVAL;
  }
#endif
}

int BrakePressure::getValue() {
  return this->brakePressure;
}

int BrakePressure::getDataBits() {
  return BRAKE_PRESSURE_DATA_BITS;
}
