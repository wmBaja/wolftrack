#include <Arduino.h>

#include "BrakePressure.h"
#include "../../config.h"

BrakePressure::BrakePressure() {
  this->brakePressure = 0;
}

void BrakePressure::loop() {
  this->brakePressure = random(1024);
}

int BrakePressure::getValue() {
  return this->brakePressure;
}
