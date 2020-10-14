#include "DataPacket.h"

DataPacket::DataPacket() {
  this->bits = std::bitset<MAX_BITS_IN_PACKET>{0};
  this->numBitsUsed = 0;
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

  // make room for the new value's bits by shifting the packet's current bits left
  this->bits = this->bits << numBitsNeeded;

  // iterate through the value's bits while setting them in the packet's bits
  unsigned int mask = 0x1;
  for (int i = 0; i < numBitsNeeded; i++) {
    bool bit = value & mask;
    this->bits[i] = bit;
    mask <<= 1; // shift the mask 1 bit to the left
  }

  this->numBitsUsed += numBitsNeeded;
}

/**
 * Returns the n-th byte from the right in the given bitset.
 * @param bits the bitset to get the n-th byte from
 * @param n the index of the byte (from the right) in the bitset you want to get
 * @return the n-th byte from the right in the given bitset
 */
uint8_t getNthByteFromRight(std::bitset<MAX_BITS_IN_PACKET> bits, size_t n) {
  uint8_t nthByteFromRight = 0;
  for (int i = 0; i < BITS_IN_BYTE; i++) {
    nthByteFromRight <<= 1; // shift left one bit
    nthByteFromRight |= bits[n * BITS_IN_BYTE + i]; // set the rightmost bit to the appropriate bit in the bitset
  }
  return nthByteFromRight;
}

/**
 * NOTE: This method destroys the internal bitset used to maintain a
 * DataPacket's state. Do NOT use the DataPacket after this method is
 * called.
 */
size_t DataPacket::toByteArray(uint8_t* arr) {
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
    /* transfer the i-th byte (from the right) in the bitset to the i-th byte
    (from the right) in the byte array */
    arr[numBytesUsed - i - 1] = getNthByteFromRight(this->bits, i);
  }

  return numBytesUsed;
}
