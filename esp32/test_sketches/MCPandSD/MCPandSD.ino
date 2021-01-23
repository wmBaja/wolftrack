#include <SPI.h>
#include "SD.h"
#include <MCP3XXX.h>

MCP3008 adc;

// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between updates (in ms)
#define UPDATE_INTERVAL 1000

// SPI Master Out Slave In (MOSI)
#define SD_CARD_SPI_MOSI 23
// SPI Master In Slave Out (MISO)
#define SD_CARD_SPI_MISO 19
// SPI Clock (SCLK)
#define SD_CARD_SPI_SCLK 18
// SD Card SPI Chip Select
#define SD_CARD_SPI_CS 5


// SPI Master Out Slave In (MOSI)
#define MCP3008_SPI_MOSI 25
// SPI Master In Slave Out (MISO)
#define MCP3008_SPI_MISO 33
// SPI Clock (SCLK)
#define MCP3008_SPI_SCLK 32
// MCP3008 SPI Chip Select
#define MCP3008_SPI_CS 26


unsigned long nextUpdateTime;

void setup() {
  Serial.begin(BAUD_RATE);
  nextUpdateTime = millis() + UPDATE_INTERVAL;

  Serial.println("Initializing SD card...");
  if (!SD.begin(SD_CARD_SPI_CS)) {
    Serial.println("ERROR - SD card initialization failed!");
    return;    // init failed
  }

  adc.begin(MCP3008_SPI_CS, MCP3008_SPI_MOSI, MCP3008_SPI_MISO, MCP3008_SPI_SCLK);
}

// Write to the SD card
void writeFile(fs::FS &fs, const char * path, const char * message) {
  Serial.printf("Writing file: %s\n", path);
  File file = fs.open(path, FILE_WRITE);
  if(!file) {
    Serial.println("Failed to open file for writing");
    return;
  }
  if(file.print(message)) {
    Serial.println("File written");
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

void loop() {
  unsigned long curTime = millis();
  if (curTime > nextUpdateTime) {
    uint32_t values[8];

    // read all of the channels as fast as possible
    for (int i = 0; i < 8; i++) {
      values[i] = adc.analogRead(i);
    }

    File file = SD.open("/data.txt", FILE_APPEND);
    if(file) {
      for (int i = 0; i < 8; i++) {
        file.print(values[i]);
        if (i != 7) file.print(",");
      }
      file.println();
    } else {
      Serial.println("Failed to open file for writing");
    }
    file.close();

    readFile(SD, "/data.txt");

    nextUpdateTime = curTime + UPDATE_INTERVAL;
  }
}
