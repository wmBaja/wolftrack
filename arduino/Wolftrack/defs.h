// number of milliseconds in a second
#define MILLIS_IN_SEC 1000
// number of seconds in a minute
#define SECS_IN_MIN 60
// number of microseconds in a minute
#define MICROS_IN_MIN 60000000
// the baud rate for the serial connection
#define BAUD_RATE 115200
// amount of time between transmissions to RPi (in ms)
#define TRANSMISSION_INTERVAL 250
// the size of the data packet sent to the RPi
#define DATA_PACKET_SIZE 18

// pin for engine rpm reading
#define ENGINE_RPM_PIN 2
// pin for reading CVT rpm
#define CVT_SEC_RPM_PIN 3

// pin for hall effect fuel gauge reading
#define FUEL_HALL_EFFECT_PIN A0
// pin for reading CVT temperature
#define CVT_TEMP_PIN A1
// pin for reading brake 1 pressure
#define BRAKE_PRESSURE_1_PIN A2
// pin for reading brake 2 pressure
#define BRAKE_PRESSURE_2_PIN A3
// pin for reading shock 1 actuation
#define SHOCK_ACTUATION_1_PIN A4
// pin for reading shock 2 actuation
#define SHOCK_ACTUATION_2_PIN A5

// current time in milliseconds
extern unsigned long curTime;
// the time at which the next data packet should be sent to the RPi
extern unsigned long nextTransmissionTime;
