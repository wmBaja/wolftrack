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
function mapRangeToRangeWithRatio(inStart, outStart, ratio, input) {
  return outStart + ratio * (input - inStart);
}

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
function mapRangeToRange(inStart, inEnd, outStart, outEnd, input) {
  const inputRange = inEnd - inStart;
  const outputRange = outEnd - outStart;
  const ratio = outputRange / inputRange;
  return mapRangeToRangeWithRatio(inStart, outStart, ratio, input);
  // return outStart + (outputRange / inputRange) * (input - inStart);
}

export { mapRangeToRange, mapRangeToRangeWithRatio };
