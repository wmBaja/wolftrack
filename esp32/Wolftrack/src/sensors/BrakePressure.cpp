#include <Arduino.h>

#include "BrakePressure.h"
#include "../../config.h"

BrakePressure::BrakePressure():
  brakePressure(0)
{}

void BrakePressure::loop() {
#if GENERATE_RANDOM_VALUES
  this->brakePressure = random(1024);
#else
  // TODO need to implement
  this->brakePressure = random(1024);
#endif
}

int BrakePressure::getValue() {
  return this->brakePressure;
}
