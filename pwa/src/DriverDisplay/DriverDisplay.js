import React, { useState, useContext, useEffect } from 'react';
import Button from 'muicss/lib/react/button';

import './DriverDisplay.css';
import PureInfoDisplay from './PureInfoDisplay/PureInfoDisplay.js';
import BLEClientContext from '../BLEClient/BLEClientContext.js';
import { DEFAULT_DATA } from '../BLEClient/DEFAULT_DATA.js';

import FirebaseClientContext from '../Firebase/FirebaseClientContext.js';

import SignIn from '../common/SignIn.js';

const DEFAULT_SIGN_IN_PROMPT = 'You are not signed in. Data will NOT be uploaded to the database.';

function DriverDisplay() {
  const [data, setData] = useState(DEFAULT_DATA);

  // BLE state
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  // Firebase state
  const firebaseClient = useContext(FirebaseClientContext);
  const [signedIn, setSignedIn] = useState(firebaseClient.isSignedIn());

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

  function onFbAuthChange(user) {
    setSignedIn(user ? true : false);
  }

  // register/unregister the onFbAuthChange callback with firebase
  useEffect(() => {
    const unsub = firebaseClient.firebase.auth().onAuthStateChanged(onFbAuthChange);
    return unsub;
  });

  async function signIn(email, password) {
    try {
      const result = await firebaseClient.signIn(email, password);
      setSignedIn(result);
      return true;
    } catch (error) {
      throw error;
    }
  }

  const fbSignInBox = (
    !signedIn ?
    <SignIn prompt={DEFAULT_SIGN_IN_PROMPT} onSignIn={signIn} /> :
    <p>You are signed in. Data will be uploaded to the database.</p>
  );

  return (
    <div className='DriverDisplay'>
      {bleConnected ?
      <PureInfoDisplay data={data} /> :
      <div>
        <h1>Driver Display</h1>
        {fbSignInBox}
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
