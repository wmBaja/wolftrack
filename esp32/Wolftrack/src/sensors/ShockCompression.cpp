#include <Arduino.h>

#include "ShockCompression.h"
#include "../../config.h"

ShockCompression::ShockCompression():
  shockCompression(0)
{}

void ShockCompression::loop() {
#if _GENERATE_RANDOM_VALUES
  this->shockCompression = random(1024);
#else
  // TODO need to implement
  this->shockCompression = random(1024);
#endif
}

int ShockCompression::getValue() {
  return this->shockCompression;
}
