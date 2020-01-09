import React, { useState, useContext, useEffect } from 'react';
import Button from 'muicss/lib/react/button';

import './DriverDisplay.css';
import Dashboard from './Dashboard.js';
import BLEClientContext from '../BLEClient/BLEClientContext.js';
import { DEFAULT_DATA } from '../BLEClient/DEFAULT_DATA';

function DriverDisplay() {
  const [data, setData] = useState(DEFAULT_DATA);
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  function onData(data) {
    // console.log('Received data.');
    // console.log(data);
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

  return (
    <div className='DriverDisplay'>
      {bleConnected ?
      <Dashboard data={data} /> :
      <div>
        <h1>Driver Display</h1>
        <Button variant='raised' className='DriverDisplay-connect-btn' onClick={() => connectToVehicle(false)}>
          Connect to vehicle
        </Button>
        <br/>
        <Button variant='raised' className='DriverDisplay-simulate-btn' onClick={() => connectToVehicle(true)}>
          Simulate connection
        </Button>
      </div>}
    </div>
  );
}

export default DriverDisplay;
