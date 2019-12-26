import React, { useState, useEffect } from 'react';

import './DriverDisplay.css';
import Dashboard from './Dashboard.js';
import BLEClient from './BLEClient/BLEClient.js';

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
  const [bleClient] = useState(new BLEClient());
  const [bleConnected, setBleConnected] = useState(false);

  useEffect(
    () => {
      // const unsubscribe = onHwData((data) => {
      //   if (data.type === 'fuel_data') {
      //     console.log('Updating fuel data', data.value);
      //     setData(prevState => ({ ...prevState, fuelData: data.value }));
      //   } else if (data.type === 'gps_data') {
      //     console.log('Updating GPS data', data.value);
      //     setData(prevState => ({ ...prevState, gpsData: data.value }));
      //   }
      // });
      return bleClient.disconnect; // disconnect the client when unmounting
    },
    [], // only run on mount and unmount
  );

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
