#include <Arduino.h>

#include "Fuel.h"
#include "../../config.h"

Fuel::Fuel() {
  this->fuel = 0;
}

void Fuel::loop() {
  this->fuel = random(1024);
}

int Fuel::getValue() {
  return this->fuel;
}
