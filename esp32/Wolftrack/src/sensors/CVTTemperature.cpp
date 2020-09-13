#include <Arduino.h>

#include "CVTTemperature.h"
#include "../../config.h"

CVTTemperature::CVTTemperature() {
  this->cvtTemp = 0;
}

void CVTTemperature::loop() {
#if _GENERATE_RANDOM_VALUES
  this->cvtTemp = random(1024);
#else
  // TODO need to implement
  this->cvtTemp = random(1024);
#endif
}

int CVTTemperature::getValue() {
  return this->cvtTemp;
}
