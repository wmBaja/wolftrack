#include <SPI.h>
#include "SD.h"

File data;

// the baud rate for the serial connection
#define BAUD_RATE 115200

// SD Card SPI Chip Select
#define SD_CARD_SPI_CS 5

void setup() {
  Serial.begin(BAUD_RATE);

  Serial.println("Initializing SD card...");
  if (!SD.begin(SD_CARD_SPI_CS)) {
    Serial.println("ERROR - SD card initialization failed!");
    return;    // init failed
  }

  SD.remove("/data.txt");

  appendFile(SD, "/data.txt", "henlo big boi\n");
  readFile(SD, "/data.txt");

  testFileIO(SD, "/data.txt");
}

// Write to the SD card
void appendFile(fs::FS &fs, const char * path, const char * message) {
  File file = fs.open(path, FILE_APPEND);
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }
  if (file.print(message)) {
    Serial.printf("Wrote to file %s\n", path);
  } else {
    Serial.println("Write failed");
  }
  file.close();
}

void readFile(fs::FS &fs, const char * path){
  File file = fs.open(path);
  if(!file){
    Serial.println("Failed to open file for reading");
    return;
  }
  
  Serial.printf("Read from file %s: ", path);
  while(file.available()){
    Serial.write(file.read());
  }
  file.close();
}

void testFileIO(fs::FS &fs, const char * path) {
  File file = fs.open(path);
  static uint8_t buf[512];
  size_t len = 0;
  uint32_t start = millis();
  uint32_t end = start;
  if (file) {
    len = file.size();
    size_t flen = len;
    start = millis();
    while (len) {
      size_t toRead = len;
      if (toRead > 512) {
        toRead = 512;
      }
      file.read(buf, toRead);
      len -= toRead;
    }
    end = millis() - start;
    Serial.printf("%u bytes read for %u ms\n", flen, end);
    file.close();
  } else {
    Serial.println("Failed to open file for reading");
  }

  file = fs.open(path, FILE_WRITE);
  if (!file) {
    Serial.println("Failed to open file for writing");
    return;
  }

  size_t i;
  start = millis();
  for (i = 0; i < 10; i++) {
    file.write(buf, 512);
  }
  end = millis() - start;
  Serial.printf("%u bytes written for %u ms\n", 10 * 512, end);
  file.close();
}

void loop() {}
