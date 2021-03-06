#ifndef _DATA_PACKET_H
#define _DATA_PACKET_H

#include <Arduino.h>
#include <stdlib.h>
#include <stdbool.h>
#include <bitset>

#define MAX_BYTES_IN_PACKET 20
#define BITS_IN_BYTE 8
#define MAX_BITS_IN_PACKET MAX_BYTES_IN_PACKET * BITS_IN_BYTE

class DataPacket {
    // the data as a set of bits
    std::bitset<MAX_BITS_IN_PACKET> bits;
    // the number of bits 
    size_t numBitsUsed;
  public:
    DataPacket();
    void addValue(unsigned int, size_t);
    size_t toByteArray(uint8_t*);
};

#endif
