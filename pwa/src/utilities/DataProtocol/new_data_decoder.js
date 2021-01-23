const BIT_MASKS = [
  0b11111111, 0b01111111, 0b00111111, 0b00011111,
  0b00001111, 0b00000111, 0b00000011, 0b00000001
];

function extractValues(byteArray, packetDefinition) {
  const values = [];

  let bitOffset = 0;
  for (let {valueName, bitLength} of packetDefinition) {
    let value = 0;

    // extract the bits for this value from the byte array
    let bitsLeftToExtract = bitLength;
    let curByteIdx = Math.floor(bitOffset / 8);
    let nextBitInCurByteToExtractIdx = bitOffset % 8;
    while (bitsLeftToExtract > 0) {
      const numBitsToExtractFromCurByte = Math.min(8 - nextBitInCurByteToExtractIdx, bitsLeftToExtract);
      // pull the needed bits out of the current byte
      const curByte = byteArray[curByteIdx];
      let extractedBits = curByte & BIT_MASKS[nextBitInCurByteToExtractIdx];
      // shift out any extra bits that weren't needed on the least significant side
      extractedBits = extractedBits >>> (8 - (nextBitInCurByteToExtractIdx + numBitsToExtractFromCurByte));
      // shift the value left to fit the new bits
      value = value << numBitsToExtractFromCurByte;
      // OR in the new bits
      value = value | extractedBits;
      // decrement the bits left to extract
      bitsLeftToExtract -= numBitsToExtractFromCurByte;
      // then go to the next byte
      curByteIdx++;
      nextBitInCurByteToExtractIdx = 0;
    }

    values.push({valueName, value}); // add the value to the list of values
    bitOffset += bitLength; // update the bit offset into the byte array
  }
  return values;
}


// const PACKET_DEFINITION = [
//   {valueName: 'engine_rpm', bitLength: 13},
//   {valueName: 'cvt_sec_rpm', bitLength: 13},
//   {valueName: 'front_brake_pressure', bitLength: 11},
//   {valueName: 'rear_brake_pressure', bitLength: 11},
// ];

// const view = new DataView(new ArrayBuffer(20));
// // engine RPM:           1000001101000 (4200)
// // cvt RPM:              0111110100000 (4000)
// // front brake pressure: 11011100101 (1765)
// // rear brake pressure:  01011011110 (734)
// view.setUint8(0, 0b10000011); // 0-7 MSB: engine RPM
// view.setUint8(1, 0b01000100); // 0-4 MSB: engine RPM
//                               // 5-7 MSB: cvt RPM
// view.setUint8(2, 0b00011010); // 0-7 MSB: cvt RPM
// view.setUint8(3, 0b11110111); // 0-1 MSB: cvt RPM
//                               // 2-7 MSB: front brake pressure
// view.setUint8(4, 0b00101010); // 0-4 MSB: front brake pressure
//                               // 5-7 MSB: rear brake pressure
// view.setUint8(5, 0b11011110); // 0-7 MSB: rear brake pressure
const PACKET_DEFINITION = [
  {valueName: 'valueA', bitLength: 10},
  {valueName: 'valueB', bitLength: 4},
  {valueName: 'valueC', bitLength: 10},
];

const view = new DataView(new ArrayBuffer(20));
// valueA: 1000101101 (557)
// valueB: 0111 (7)
// valueC: 1101110010 (882)
view.setUint8(0, 0b10001011); // 0-7 MSB: valueA
view.setUint8(1, 0b01011111); // 0-1 MSB: valueA
                              // 2-5 MSB: valueB
                              // 6-7 MSB: valueC
view.setUint8(2, 0b01110010); // 0-7 MSB: valueC

const byteArray = new Uint8Array(view.buffer);
console.log(byteArray);

const extractedValues = extractValues(byteArray, PACKET_DEFINITION);

for (value of extractedValues) {
  console.log(value);
}
