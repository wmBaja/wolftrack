# Arduino
Everything in this folder is related to the code that runs on the Arduino on the Baja vehicle.

## Arduino Profiling
An easy way to find out how fast your Arduino (or other microcontroller) loop runs is to add some simple profiling code.
Add the following code outside of and before the loop (global variables):
```
// REMOVE: ONLY FOR PROFILING
bool profilingDone = false;
unsigned long loopCount = 0;
```
And add the following code at the end of the loop (but still inside of it):
```
// REMOVE: ONLY FOR PROFILING
loopCount++;
unsigned long timePassed = micros();
if (timePassed > 5000000 && !profilingDone) {
  Serial.println("\nTime passed (microseconds): ");
  Serial.print(timePassed);
  Serial.println("\nLoop count: ");
  Serial.print(loopCount);
  Serial.println("\nLoops per second: ");
  Serial.println(loopCount / (timePassed / 1000000));
  profilingDone = true;
}
```
The code above uses a profiling period of 5 seconds (5 million microseconds).  You can change that time to anything you want.
