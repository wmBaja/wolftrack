#include <Arduino.h>

#include "Fuel.h"
#include "../../config.h"

Fuel::Fuel() {
  this->fuel = 0;
}

void Fuel::loop() {
#if _GENERATE_RANDOM_VALUES
  this->fuel = random(1024);
#else
  // TODO need to implement
  this->fuel = random(1024);
#endif
}

int Fuel::getValue() {
  return this->fuel;
}
