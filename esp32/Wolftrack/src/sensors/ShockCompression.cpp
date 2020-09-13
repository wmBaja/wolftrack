#include <Arduino.h>

#include "ShockCompression.h"
#include "../../config.h"

ShockCompression::ShockCompression() {
  this->shockCompression = 0;
}

void ShockCompression::loop() {
  this->shockCompression = random(1024);
}

int ShockCompression::getValue() {
  return this->shockCompression;
}
