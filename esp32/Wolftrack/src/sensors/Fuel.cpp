#include <Arduino.h>

#include "Fuel.h"
#include "../../config.h"

Fuel::Fuel():
  fuel(0)
{}

void Fuel::loop() {
#if GENERATE_RANDOM_VALUES
  this->fuel = random(100);
#else
  // TODO need to implement
  this->fuel = random(100);
#endif
}

int Fuel::getValue() {
  return this->fuel;
}
