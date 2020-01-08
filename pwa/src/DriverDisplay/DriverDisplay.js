import React, { useState, useContext } from 'react';

import './DriverDisplay.css';
import Dashboard from './Dashboard.js';
import BLEClientContext from '../BLEClient/BLEClientContext.js';

const initialData = {
  fuelData: {
    remainingPercentage: 0,
    remainingLiters: 0,
    remainingLitersEMA: 0,
  },
  gpsData: {
    latitude: 0,
    longitude: 0,
    speed: 0,
    trackAngle: 0,
  },
};

function DriverDisplay() {
  const [data, setData] = useState(initialData);
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  function onData(data) {
    console.log('Received data.');
    console.log(data);
    setData(data);
  }

  async function connectToVehicle(simulate) {
    const success = await bleClient.connect(onData, simulate);
    if (success) {
      setBleConnected(true);
    }
  }

  return (
    <div className="DriverDisplay">
      {bleConnected ?
      <Dashboard data={data} /> :
      <div>
        <button onClick={() => connectToVehicle(false)}>Connect to vehicle</button>
        <button onClick={() => connectToVehicle(true)}>Simulate connection</button>
      </div>}
    </div>
  );
}

export default DriverDisplay;
