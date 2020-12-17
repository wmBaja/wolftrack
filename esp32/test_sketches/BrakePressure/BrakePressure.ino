#include <MCP3XXX.h>

MCP3008 adc;

// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between updates (in ms)
#define UPDATE_INTERVAL 10

// SPI Master Out Slave In (MOSI)
#define MCP3008_SPI_MOSI 25
// SPI Master In Slave Out (MISO)
#define MCP3008_SPI_MISO 33
// SPI Clock (SCLK)
#define MCP3008_SPI_SCLK 32
// MCP3008 SPI Chip Select
#define MCP3008_SPI_CS 26

// Front Brakes Transducer Output
#define FRONT_BRAKE_PRESSURE_CHANNEL 1

unsigned long nextUpdateTime;

void setup() {
  Serial.begin(BAUD_RATE);
  nextUpdateTime = millis() + UPDATE_INTERVAL;
  // Hardware SPI (specify CS, use any available digital)
  // this should work, but I think the SPI.h library doesn't have the correct pins assigned for our ESP32
  // adc.begin(MCP3008_SPI_CS);

  // Software SPI (specify all, use any available digital pins)
  // (cs, mosi, miso, sck);
  adc.begin(MCP3008_SPI_CS, MCP3008_SPI_MOSI, MCP3008_SPI_MISO, MCP3008_SPI_SCLK);
}

void loop() {
  unsigned long curTime = millis();
  if (curTime > nextUpdateTime) {
    uint32_t sensorValue = adc.analogRead(FRONT_BRAKE_PRESSURE_CHANNEL);
    double psi = (sensorValue / 1023.0) * 2000; // range: 0 - 2000

    Serial.print(sensorValue);
    Serial.print(" | ");
    Serial.println(psi);

    nextUpdateTime = curTime + UPDATE_INTERVAL;
  }
}
