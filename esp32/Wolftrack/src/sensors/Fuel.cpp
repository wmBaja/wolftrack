#include <Arduino.h>
#include <cmath>

#include "Fuel.h"
#include "../../config.h"


// constants for fuel calculations
#define MAX_FUEL_CAPACITY 3.45
#define MAX_DETECTABLE_FUEL_CAPACITY 1.6
#define NEUTRAL_MAGNETISM_VALUE 512
#define LOWEST_MAGNETISM_VALUE 16
#define HIGHEST_MAGNETISM_VALUE 623

Fuel::Fuel(MCP3008* adc, uint8_t adcChannel):
  adc(adc),
  adcChannel(adcChannel),
  fuel(0),
  nextReadTime(0)
{}

void Fuel::loop() {
#if GENERATE_RANDOM_VALUES
  this->fuel = random(100);
#else
  unsigned long curTime = millis();

  if (curTime > this->nextReadTime) {
    // TODO implement fuel calculation
    uint32_t analogValue = this->adc->analogRead(this->adcChannel);
    // int distFromCenterValue = std::abs(voltageValue - NEUTRAL_MAGNETISM_VALUE);
    // double remainingLiters = (distFromCenterValue / 513) * MAX_FUEL_CAPACITY;
    // this->fuel = remainingLiters / MAX_FUEL_CAPACITY;
    this->fuel = (analogValue / 1023.0) * 100;

    // calculate the next read time
    this->nextReadTime = curTime + READ_INTERVAL;
  }

#endif
}

int Fuel::getValue() {
  return this->fuel;
}

int Fuel::getMoreValues() {
	return GENERIC_VALUE;
}

int Fuel::getDataBits() {
	return FUEL_DATA_BITS;
}

void Fuel::printType() {
	Serial.println("Fuel");
}
