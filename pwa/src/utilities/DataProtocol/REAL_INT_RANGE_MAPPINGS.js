const GRAVITY_MS2 = 9.80665;

const ACCEL_REAL_START = -8 * GRAVITY_MS2;
const ACCEL_REAL_END = 8 * GRAVITY_MS2;
const ACCEL_INT_START = 0;
const ACCEL_INT_END = 2048;
const ACCEL_INT_REAL_RATIO = (ACCEL_INT_END - ACCEL_INT_START) / (ACCEL_REAL_END - ACCEL_REAL_START);
const ACCEL_REAL_INT_RATIO = (ACCEL_REAL_END - ACCEL_REAL_START) / (ACCEL_INT_END - ACCEL_INT_START);

export { ACCEL_REAL_START, ACCEL_REAL_END, ACCEL_INT_START, ACCEL_INT_END, ACCEL_REAL_INT_RATIO }