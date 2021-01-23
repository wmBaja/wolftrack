#ifndef _UTILS_H
#define _UTILS_H

namespace utils {
  /**
   * Maps an input value from a certain range of values to an output value in a
   * different range of values. This function is more efficient than mapRangeToRange
   * because it eliminates the division between the output and input ranges if you
   * already know the ratio between the ranges that you're mapping between.
   * @param inStart the starting value of the input range
   * @param outStart the starting value of the output range
   * @param ratio the ratio between the output and input ranges (output range / input range)
   * @param input the input value
   * @return the output value
   */
  double mapRangeToRangeWithRatio(double inStart, double outStart, double ratio, double input);

  /**
   * Maps an input value from a certain range of values to an output value in a
   * different range of values.
   * @param inStart the starting value of the input range
   * @param inEnd the ending value of the input range
   * @param outStart the starting value of the output range
   * @param outEnd the ending value of the output range
   * @param input the input value
   * @return the output value
   */
  double mapRangeToRange(double inStart, double inEnd, double outStart, double outEnd, double input);
}


#endif
