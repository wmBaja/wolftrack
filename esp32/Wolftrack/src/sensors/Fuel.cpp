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

Fuel::Fuel():
  fuel(0)
{}

void Fuel::loop() {
#if GENERATE_RANDOM_VALUES
  this->fuel = random(100);
#else
  // TODO need to implement
  int voltageValue = 0;

  int distFromCenterValue = std::abs(voltageValue - NEUTRAL_MAGNETISM_VALUE);

  double remainingLiters = (distFromCenterValue / 513) * MAX_FUEL_CAPACITY;
  this->fuel = remainingLiters / MAX_FUEL_CAPACITY;
#endif
}

int Fuel::getValue() {
  return this->fuel;
}
