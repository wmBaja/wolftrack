#include "DataPacket.h"

DataPacket::DataPacket() {
  this->bits = std::bitset<MAX_BITS_IN_PACKET>{0};
  this->numBitsUsed = 0;
  this->byteArray = {};
}

/**
 * Adds the rightmost numBitsNeeded bits of the given value to the data packet.
 * @param value the value to add
 * @param numBitsNeeded the number of rightmost bits of value to add to the
 *    data packet
 */
void DataPacket::addValue(unsigned int value, size_t numBitsNeeded) {
  if (this->numBitsUsed + numBitsNeeded > MAX_BITS_IN_PACKET) {
    throw; // should not happen as long as clients don't add too many bits
  }

  // get the rightmost numBitsNeeded bits of the value
  std::bitset<numBitsNeeded> valueAsBits (value);
  // make room for the new value's bits by shifting the packet's current bits left
  this->bits = this->bits << numBitsNeeded;
  // OR in the new value's bits
  this->bits = this->bits | valueAsBits;

  this->numBitsUsed += numBitsNeeded;
}

uint8_t* DataPacket::toByteArray(size_t* arraySize) {
  // figure out the number of bytes used in the packet (AKA the array size)
  size_t numFullBytesUsed = this->numBitsUsed / BITS_IN_BYTE;
  size_t numExtraBitsUsed = this->numBitsUsed % BITS_IN_BYTE;
  size_t numBytesUsed = numFullBytesUsed;
  if (numExtraBitsUsed > 0) {
    numBytesUsed += 1;
  }
  // calculate the number of bits needed to fill out the last byte
  size_t numPaddingBitsNeeded = BITS_IN_BYTE - numExtraBitsUsed;

  // shift the packet's bits left by the number of padding bits needed
  this->bits = this->bits << numPaddingBitsNeeded;

  // place the bits into the byte array
  for (int i = 0; i < numBytesUsed; i++) {
    // get the i-th byte from the left
    this->byteArray[i] = (uint8_t) this->bits >> ((numBytesUsed - i - 1) * BITS_IN_BYTE);
  }

  *arraySize = numBytesUsed;
  return &this->byteArray;
}
