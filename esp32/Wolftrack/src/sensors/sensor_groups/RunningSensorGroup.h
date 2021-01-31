#ifndef _RUNNING_SENSOR_GROUP_H
#define _RUNNING_SENSOR_GROUP_H

#include <MCP3XXX.h>

#include "../Accelerometer.h"
#include "../BrakePressure.h"
#include "../CVTSecRPM.h"
#include "../EngineRPM.h"
#include "../Fuel.h"
#include "../Sensor.h"
#include "../ShockCompression.h"
#include "SensorGroup.h"

/** The maximum number of sensors that can be running */
#define MAX_SENSORS 6

/**
 * This class represents the sensors that are currently running on the Baja rig
 * There is a default array of sensors that can be ran, or a custom array can
 * be configured
 * @author Phil Burney
 */
class RunningSensorGroup : public SensorGroup {
    /** ADC that is to be used */
    MCP3008 adc;
    /** The array that represents the group of sensors that is running */
    Sensor sensorArray[MAX_SENSORS];

  public:
    /**
     * Constructor method for RunningSensorGroup class. Starts the adc.
     *
     */
    RunningSensorGroup();
    /**
     * Starts the loop sequences of the sensors that are in the current sensorArray().
     *
     */
    void loop();
    /**
     * Builds the data packet that is to be used to read sensors
     */
    void buildDataPacket(DataPacket *);
    /**
     * This method initalizes a default array of sensors. These sensors are 
     * hard-coded by the programmer and cannot be changed without changing and
     * recompiling the code.
     */
    void initDefaultSensorArray();
    /**
     * This method initalizes a custom array of sensors.  A custom array is passed in
     * through the sensor array, and the contents of that array are copied and overwrite
     * the contents of the current sensorArray().  The size of the array is passed in through
     * the integer.  If the array is larger than the MAX_SENSORS constant, then an exception
     * is thrown.  
     */
    void initCustomSensorArray(Sensor *, int)
};

#endif