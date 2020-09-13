#include <Arduino.h>

#include "CVTTemperature.h"
#include "../../config.h"

CVTTemperature::CVTTemperature() {
  this->cvtTemp = 0;
}

void CVTTemperature::loop() {
  this->cvtTemp = random(1024);
}

int CVTTemperature::getValue() {
  return this->cvtTemp;
}
