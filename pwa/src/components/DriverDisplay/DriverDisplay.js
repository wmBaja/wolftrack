import React, { useState, useContext, useEffect } from 'react';
import Button from 'muicss/lib/react/button';

import './DriverDisplay.css';
import PureInfoDisplay from './PureInfoDisplay/PureInfoDisplay.js';
import BLEClientContext from '../../utilities/BLEClient/BLEClientContext.js';
import { DEFAULT_DATA } from '../../utilities/DataProtocol/DEFAULT_DATA.js';

import FirebaseStatus from '../common/FirebaseStatus/FirebaseStatus.js';

import DataDecoder from '../../utilities/DataProtocol/DataDecoder.js';
import { saveAs } from 'file-saver';
import streamSaver from 'streamsaver';

function DriverDisplay() {
  const [data, setData] = useState(DEFAULT_DATA);

  // BLE state
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  function onData(data) {
    setData(data);
  }

  // register/unregister the onData callback with the BLEClient
  useEffect(() => {
    bleClient.register(onData);
    return () => {
      bleClient.unregister(onData);
    };
  });

  async function connectToVehicle(simulate) {
    const success = await bleClient.connect(simulate);
    if (success) {
      setBleConnected(true);
    }
  }

  async function convertFile(e) {
    const file = e.target.files[0];
    // create the name for the output file
    const outputFilename = file.name.substring(0, file.name.length - 10) + '.csv';
    const reader = new FileReader();
    reader.readAsArrayBuffer(file);

    const textEncoder = new TextEncoder();

    const fileStream = streamSaver.createWriteStream(outputFilename);
    const writer = fileStream.getWriter();

    const csvHeader = 'x_acceleration_ms2,y_acceleration_ms2,z_acceleration_ms2,shock_compression_in,front_brake_pressure_psi\n';
    // const outputFileContents = [csvHeader];
    writer.write(textEncoder.encode(csvHeader));

    reader.onload = () => {
      const buffer = reader.result;
      const bufferObj = {buffer: buffer};
      const curData = {};
      const progressTriggerPointInterval = buffer.byteLength / 10;
      for (let i = 0; i < buffer.byteLength; i += 7) {
        const decodedData = DataDecoder.decodeData(bufferObj, curData, i, 7);
        const xAccel = decodedData.acceleration.xAccelms2.toPrecision(5);
        const yAccel = decodedData.acceleration.yAccelms2.toPrecision(5);
        const zAccel = decodedData.acceleration.zAccelms2.toPrecision(5);
        const shock = decodedData.suspension.shock1actuationInches.toPrecision(5);
        const brake = decodedData.brakes.frontBrakePressurePsi.toPrecision(4);

        writer.write(textEncoder.encode([xAccel, yAccel, zAccel, shock, brake].join(',') + '\n'));
        // outputFileContents.push([xAccel, yAccel, zAccel, shock, brake].join(','), '\n');

        // if at a trigger point, report on progress
        if (i % progressTriggerPointInterval === 0) {
          console.log(`${i} / ${buffer.byteLength} bytes processed...`);
        }
      }


      writer.close();
      // const outputBlob = new Blob(outputFileContents, {type: 'text/csv;charset=utf-8'});
      // saveAs(outputBlob, outputFilename);
    };
    reader.onerror = () => {
      console.log(reader.error);
    };
  }

  return (
    <div className='DriverDisplay'>
      {bleConnected ?
      <PureInfoDisplay data={data} /> :
      <div className='DriverDisplay-statuses'>
        <h1>Driver Display</h1>
        <FirebaseStatus />
        <Button variant='raised' className='DriverDisplay-connect-btn' onClick={() => connectToVehicle(false)}>
          Connect to vehicle
        </Button>
        <br/>
        <Button variant='raised' className='DriverDisplay-simulate-btn' onClick={() => connectToVehicle(true)}>
          Simulate connection
        </Button>
        
        <h2>Data File Conversion</h2>
        <p>You can choose a .wolftrack data file to convert to CSV by using the file picker below.</p>
        <input type="file" onChange={convertFile} accept=".wolftrack" />
      </div>}
    </div>
  );
}

export default DriverDisplay;
