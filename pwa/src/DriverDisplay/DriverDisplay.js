import React, { useState, useContext, useEffect } from 'react';
import Button from 'muicss/lib/react/button';

import './DriverDisplay.css';
import PureInfoDisplay from './PureInfoDisplay/PureInfoDisplay.js';
import BLEClientContext from '../BLEClient/BLEClientContext.js';
import { DEFAULT_DATA } from '../BLEClient/DEFAULT_DATA.js';

import FirebaseStatus from '../common/FirebaseStatus.js';

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

  return (
    <div className='DriverDisplay'>
      {bleConnected ?
      <PureInfoDisplay data={data} /> :
      <div>
        <h1>Driver Display</h1>
        <FirebaseStatus />
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
