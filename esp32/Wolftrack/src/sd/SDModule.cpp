#include <Arduino.h>
#include <SPI.h>
#include "SD.h"

#include <string.h>

#include "SDModule.h"
#include "../../config.h"

SDModule::SDModule() {
  this->cardConnected = false;
  this->bufferSize = 0;

  Serial.println("Initializing SD card...");
  if (SD.begin(SD_CARD_SPI_CS)) {
    this->cardConnected = true;
  }

  // generate a random name for the data file
  long fileNum = random(9999999);
  sprintf(this->curDataFileName, "/%d.wolftrack", fileNum);

  // add the file name to the list of names in the order file
  this->addCurDataFileNameToOrderFile();
}

void SDModule::addCurDataFileNameToOrderFile() {
  File file = SD.open(ORDER_FILE, FILE_APPEND);
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }
  if (!file.println(this->curDataFileName)) {
    Serial.println("Write failed");
  }
  file.close();
}

void SDModule::write(DataPacket* dataPacket) {
  // copy the data to the buffer and increment the size 
  uint8_t arr[MAX_BYTES_IN_PACKET];
  size_t size = dataPacket->toByteArray(arr);
  memcpy(this->buffer + this->bufferSize, arr, size);
  this->bufferSize += size;

  if (this->bufferSize > (MAX_WRITE_BUFFER_SIZE - MAX_BYTES_IN_PACKET)) {
    // write the buffer to the data file
    File file = SD.open(this->curDataFileName, FILE_APPEND);
    if (!file) {
      Serial.println("Failed to open file for writing");
      return;
    }
    file.write(this->buffer, this->bufferSize);
    file.close();

    // reset buffer size
    this->bufferSize = 0;
  }
}

bool SDModule::isCardConnected() {
  return this->cardConnected;
}

