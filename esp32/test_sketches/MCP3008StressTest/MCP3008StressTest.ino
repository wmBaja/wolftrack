#include <MCP3XXX.h>

MCP3008 adc;

// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between updates (in ms)
#define UPDATE_INTERVAL 10

// SPI Master Out Slave In (MOSI)
#define SPI_MOSI 23
// SPI Master In Slave Out (MISO)
#define SPI_MISO 19
// SPI Clock (SCLK)
#define SPI_SCLK 18
// MCP3008 SPI Chip Select
#define MCP3008_SPI_CS 17

unsigned long nextUpdateTime;

void setup() {
  Serial.begin(BAUD_RATE);
  nextUpdateTime = millis() + UPDATE_INTERVAL;
  // Hardware SPI (specify CS, use any available digital)
  // this should work, but I think the SPI.h library doesn't have the correct pins assigned for our ESP32
  // adc.begin(MCP3008_SPI_CS);

  // Software SPI (specify all, use any available digital pins)
  // (cs, mosi, miso, sck);
  adc.begin(MCP3008_SPI_CS, SPI_MOSI, SPI_MISO, SPI_SCLK);
}

void loop() {
  unsigned long curTime = millis();
  if (curTime > nextUpdateTime) {
    uint32_t values[8];

    // read all of the channels as fast as possible
    for (int i = 0; i < 8; i++) {
      values[i] = adc.analogRead(i);
    }

    // print out the values you got for them
    for (int i = 0; i < 8; i++) {
      Serial.print(values[i]);
      Serial.print(" | ");
    }
    Serial.println();

    nextUpdateTime = curTime + UPDATE_INTERVAL;
  }
}
