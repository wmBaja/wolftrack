import React, { useState, useContext, useEffect } from 'react';
import Option from 'muicss/lib/react/option';
import Select from 'muicss/lib/react/select';
import Button from 'muicss/lib/react/button';

import './Settings.css';

import DriverDisplaySettings from './DriverDisplaySettings/DriverDisplaySettings.js';
import BLEClientContext from '../BLEClient/BLEClientContext.js';

import FirebaseClientContext from '../FirebaseClient/FirebaseClientContext.js';

function Settings(props) {
  const { currentDisplay, setCurrentDisplay, toggleSettingsPage } = props;

  // BLE state
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  // Firebase state
  const firebaseClient = useContext(FirebaseClientContext);
  const [signedIn, setSignedIn] = useState(firebaseClient.isSignedIn());

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

  function onFbAuthChange(user) {
    setSignedIn(user ? true : false);
  }

  // register/unregister the onFbAuthChange callback with firebase
  useEffect(() => {
    const unsub = firebaseClient.firebase.auth().onAuthStateChanged(onFbAuthChange);
    return unsub;
  });

  return (
    <div className='Settings'>
      <h1>Settings</h1>

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
        {
          signedIn ?
          <div>
            <Button variant='raised' onClick={firebaseClient.signOut}>
              Sign out
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
