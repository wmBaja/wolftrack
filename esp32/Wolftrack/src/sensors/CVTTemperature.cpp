#include <Arduino.h>

#include "CVTTemperature.h"
#include "../../config.h"

CVTTemperature::CVTTemperature():
  cvtTemp(0)
{}

void CVTTemperature::loop() {
#if GENERATE_RANDOM_VALUES
  this->cvtTemp = random(255);
#else
  // TODO need to implement
  this->cvtTemp = random(255);
#endif
}

int CVTTemperature::getValue() {
  return this->cvtTemp;
}
