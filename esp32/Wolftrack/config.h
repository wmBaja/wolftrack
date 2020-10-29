#ifndef _CONFIG_H
#define _CONFIG_H

/**
 * This file is intended to serve as an easy way to change the way that
 * the microcontroller code behaves.
 */

//////////////////////////////////////////////////////// Testing Electronics System ///////////////
// whether or not to enable performance profiling
#define ENABLE_PERFORMANCE_PROFILING 1
// whether or not to generate random values for sensor readings
#define GENERATE_RANDOM_VALUES 1
// whether or not the electronics system is being tested
#define TESTING (ENABLE_PERFORMANCE_PROFILING || GENERATE_RANDOM_VALUES)
// the baud rate for the serial connection
#define BAUD_RATE 115200

//////////////////////////////////////////////////////// Physical Constants ///////////////
// number of milliseconds in a second
#define MILLIS_IN_SEC 1000
// number of seconds in a minute
#define SECS_IN_MIN 60
// number of microseconds in a minute
#define MICROS_IN_MIN 60000000

//////////////////////////////////////////////////////// Bluetooth Low Energy ///////////////
// BLE device name
#define BLE_DEVICE_NAME "NCSU Wolftrack"
// BLE service UUID
#define SERVICE_UUID "12345678-1234-5678-1234-56789abcdef0"
// BLE characteristic UUID
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"
// amount of time between data notifications over BLE (in ms)
#define TRANSMISSION_INTERVAL 1000

//////////////////////////////////////////////////////// ESP32 Pin Definitions ///////////////
// SPI Master Out Slave In (MOSI)
#define SPI_MOSI 23
// SPI Master In Slave Out (MISO)
#define SPI_MISO 19
// SPI Clock (SCLK)
#define SPI_SCLK 18

// SD Card SPI MOSI
#define SD_CARD_SPI_MOSI SPI_MOSI
// SD Card SPI MISO
#define SD_CARD_SPI_MISO SPI_MISO
// SD Card SPI SCLK
#define SD_CARD_SPI_SCLK SPI_SCLK
// SD Card SPI Chip Select
#define SD_CARD_SPI_CS 5

// MCP3008 SPI MOSI
#define MCP3008_SPI_MOSI SPI_MOSI
// MCP3008 SPI MISO
#define MCP3008_SPI_MISO SPI_MISO
// MCP3008 SPI SCLK
#define MCP3008_SPI_SCLK SPI_SCLK
// MCP3008 SPI Chip Select
#define MCP3008_SPI_CS 17

// I2C Serial Data Line (SDA)
#define I2C_SDA 21
// I2C Serial Clock Line (SCL)
#define I2C_SCL 22

// MPU6050 I2C SDA
#define MPU6050_I2C_SDA I2C_SDA
// MPU6050 I2C SCL
#define MPU6050_I2C_SCL I2C_SCL

// Engine RPM Signal
#define ENGINE_RPM_PIN 0
// CVT Secondary RPM Signal
#define CVT_SEC_RPM_PIN 2
// CVT Temperature One Wire Bus
#define CVT_TEMP_PIN 4
// IR Lap Timer Signal
#define IR_LAP_TIMER_PIN 15

//////////////////////////////////////////////////////// MCP3008 Channel Definitions ///////////////
// Fuel Hall-Effect Sensor Output
#define FUEL_HALL_EFFECT_CHANNEL 0
// Front Brakes Transducer Output
#define FRONT_BRAKE_PRESSURE_CHANNEL 1
// Rear Brakes Transducer Output
#define REAR_BRAKE_PRESSURE_CHANNEL 2
// Shock 1 Linear Potentiometer Output
#define SHOCK_1_COMPRESSION_CHANNEL 3
// Shock 2 Linear Potentiometer Output
#define SHOCK_2_COMPRESSION_CHANNEL 4

//////////////////////////////////////////////////////// Data Protocol ///////////////
// the number of bits needed to represent fuel data
#define FUEL_DATA_BITS 7
// the number of bits needed to represent engine RPM data
#define ENGINE_RPM_DATA_BITS 13
// the number of bits needed to represent CVT secondary RPM data
#define CVT_SEC_DATA_BITS 13
// the number of bits needed to represent CVT temperature data
#define CVT_TEMP_DATA_BITS 8
// the number of bits needed to represent brake pressure data
#define BRAKE_PRESSURE_DATA_BITS 11
// the number of bits needed to represent lap timer data
#define IR_LAP_TIMER_DATA_BITS 1

#endif
