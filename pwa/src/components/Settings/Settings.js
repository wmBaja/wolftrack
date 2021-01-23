import React, { useState, useContext } from 'react';
import Option from 'muicss/lib/react/option';
import Select from 'muicss/lib/react/select';
import Button from 'muicss/lib/react/button';

import './Settings.css';

import DriverDisplaySettings from './DriverDisplaySettings/DriverDisplaySettings.js';
import BLEClientContext from '../../utilities/BLEClient/BLEClientContext.js';

import FirebaseStatus from '../common/FirebaseStatus/FirebaseStatus.js';

function Settings(props) {
  const { currentDisplay, setCurrentDisplay, toggleSettingsPage } = props;

  // BLE state
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  async function disconnectFromVehicle() {
    console.log('Disconnecting from vehicle...');
    await bleClient.disconnect();
    setBleConnected(bleClient.connected);
  }

  function switchDisplays() {
    console.log('Switching displays...');
    if (currentDisplay === 'driverDisplay') {
      setCurrentDisplay('observerDisplay');
    } else {
      setCurrentDisplay('driverDisplay');
    }
    toggleSettingsPage();
  }

  return (
    <div className='Settings'>
      <h1>Settings</h1>

      <FirebaseStatus />

      <div className='Settings-control-btns'>
        {
          bleConnected ?
          <div>
            <Button variant='raised' className='Settings-disconnect-vehicle-btn' onClick={disconnectFromVehicle}>
              Disconnect from vehicle
            </Button>
            <br/>
          </div> : ''
        }
        <Button variant='raised' className='Settings-disconnect-vehicle-btn' onClick={switchDisplays}>
          {currentDisplay === 'driverDisplay' ?
          'Switch to Observer Display' :
          'Switch to Driver Display'}
        </Button>
      </div>


      <DriverDisplaySettings />

      <h2>Observer Display Settings</h2>
      <form>
        <Select name='base' label='Base Display'>
          <Option value='blah' label='BLAH' />
        </Select>
      </form>
    </div>
  );
}

export default Settings;
