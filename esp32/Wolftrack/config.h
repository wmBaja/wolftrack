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
// acceleration of gravity in m/s^2 
#define GRAVITY_MS2 9.80665


//////////////////////////////////////////////////////// Bluetooth Low Energy ///////////////
// BLE device name
#define BLE_DEVICE_NAME "NCSU Wolftrack"
// BLE service UUID
#define SERVICE_UUID "12345678-1234-5678-1234-56789abcdef0"
// BLE characteristic UUID
#define CHARACTERISTIC_UUID "12345678-1234-5678-1234-56789abcdef1"
// amount of time between data notifications over BLE (in ms)
#define TRANSMISSION_INTERVAL 1000


//////////////////////////////////////////////////////// SD Card ///////////////
// File that keeps track of the order in which data files are created
#define ORDER_FILE "/order.txt"
// amount of time between data points on SD card
#define SD_WRITE_INTERVAL 10


//////////////////////////////////////////////////////// Default Sensor Profile //////////////
// Define the default sensor profile here, valid sensors include:
// "accelerometer"
// "front_brake"
// "rear_brake"
// "fuel"
// "engine_rpm"
// "cvt_sec_rpm"
// "cvt_temp"
// "front_left_shock"
// "front_right_shock"
#define DEFAULT_SENSOR_GROUP {"accelerometer", "front_brake", "cvt_temp"}


//////////////////////////////////////////////////////// Sensor Class getValue Status ////////
// Generic - single getValue function
#define GENERIC_VALUE 0
// Accelerometer - has getXAccel, getYAccel, getZAccel
#define IS_ACCELEROMETER 1

//////////////////////////////////////////////////////// ESP32 Pin Definitions ///////////////
/////////////////////////// Hardware defined SPI protocol pins ///////////////
// Hardware defined SPI Master Out Slave In (MOSI)
#define HW_SPI_MOSI 23
// Hardware defined SPI Master In Slave Out (MISO)
#define HW_SPI_MISO 19
// Hardware defined SPI Clock (SCLK)
#define HW_SPI_SCLK 18
// Hardware defined SPI Chip Select (CS)
#define HW_SPI_CS 5

/////////////////////////// Secondary, software defined SPI protocol pins ///////////////
// Software defined SPI Master Out Slave In (MOSI)
#define SW_SPI_MOSI 25
// Software defined SPI Master In Slave Out (MISO)
#define SW_SPI_MISO 33
// Software defined SPI Clock (SCLK)
#define SW_SPI_SCLK 32

/////////////////////////// I2C protocol pins ///////////////
// I2C Serial Data Line (SDA)
#define I2C_SDA 21
// I2C Serial Clock Line (SCL)
#define I2C_SCL 22

/////////////////////////// SD card reader pins ///////////////
/* The SD card reader uses the hardware defined SPI pins
because the SD library doesn't let you specify MOSI, MISO, SCLK
pins; only a different CS pin. NOTE: No other SPI devices should
use the hardware defined SPI pins because SD card readers
typically do not play well with other SPI devices.*/
// SD Card SPI MOSI
#define SD_CARD_SPI_MOSI HW_SPI_MOSI
// SD Card SPI MISO
#define SD_CARD_SPI_MISO HW_SPI_MISO
// SD Card SPI SCLK
#define SD_CARD_SPI_SCLK HW_SPI_SCLK
// SD Card SPI Chip Select
#define SD_CARD_SPI_CS HW_SPI_CS

/////////////////////////// MCP3008 pins ///////////////
/* The MCP3008 has to use a second, software defined set
of SPI pins because the SD card reader does not play well
with other SPI devices even though it should.  It's safe
to connect other SPI devices along with the MCP3008. */
// MCP3008 SPI MOSI
#define MCP3008_SPI_MOSI SW_SPI_MOSI
// MCP3008 SPI MISO
#define MCP3008_SPI_MISO SW_SPI_MISO
// MCP3008 SPI SCLK
#define MCP3008_SPI_SCLK SW_SPI_SCLK
// MCP3008 SPI Chip Select
#define MCP3008_SPI_CS 26

/////////////////////////// MPU6050 pins ///////////////
// MPU6050 I2C SDA
#define MPU6050_I2C_SDA I2C_SDA
// MPU6050 I2C SCL
#define MPU6050_I2C_SCL I2C_SCL

/////////////////////////// Misc. digital pins ///////////////
// Engine RPM Signal
#define ENGINE_RPM_PIN 16
// CVT Secondary RPM Signal
#define CVT_SEC_RPM_PIN 2
// CVT Temperature One Wire Bus
#define CVT_TEMP_PIN 4
// IR Lap Timer Signal
#define IR_LAP_TIMER_PIN 15
// Stop Operation Button
#define STOP_OP_PIN 17

//////////////////////////////////////////////////////// MCP3008 Channel Definitions ///////////////
// Fuel Hall-Effect Sensor Output
#define FUEL_HALL_EFFECT_CHANNEL 0
// Front Brakes Transducer Output
#define FRONT_BRAKE_PRESSURE_CHANNEL 1
// Rear Brakes Transducer Output
#define REAR_BRAKE_PRESSURE_CHANNEL 2
// Front Left Shock Linear Potentiometer Output
#define FL_SHOCK_COMPRESSION_CHANNEL 3
// Front Right Shock Linear Potentiometer Output
#define FR_SHOCK_COMPRESSION_CHANNEL 4


//////////////////////////////////////////////////////// Data Protocol ///////////////
/////////////////////////// Bits needed for each data type ///////////////
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
// the number of bits needed to represent accelerometer data
#define ACCELERATION_DATA_BITS 11
// the number of bits needed to represent shock compression data
#define SHOCK_COMPRESSION_DATA_BITS 10

/////////////////////////// Values needed for mapping from real value ranges to integer value ranges ///////////////
#define ACCEL_REAL_START -8 * GRAVITY_MS2
#define ACCEL_REAL_END 8 * GRAVITY_MS2
#define ACCEL_INT_START 0
#define ACCEL_INT_END 2048
#define ACCEL_INT_REAL_RATIO (ACCEL_INT_END - ACCEL_INT_START) / (ACCEL_REAL_END - ACCEL_REAL_START)


#endif
