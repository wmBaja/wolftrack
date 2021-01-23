import React, { useState, useEffect } from 'react';

import './App.css';
import settingsImg from './assets/settings.svg';

import DriverDisplay from './components/DriverDisplay/DriverDisplay.js';
import ObserverDisplay from './components/ObserverDisplay/ObserverDisplay.js';

import Settings from './components/Settings/Settings.js';

import SettingsContext from './utilities/Settings/SettingsContext.js';
import { DEFAULT_SETTINGS } from './utilities/Settings/DEFAULT_SETTINGS.js';

import BLEClientContext from './utilities/BLEClient/BLEClientContext.js';
import BLEClient from './utilities/BLEClient/BLEClient.js';

import FirebaseClientContext from './utilities/FirebaseClient/FirebaseClientContext.js';
import FirebaseClient from './utilities/FirebaseClient/FirebaseClient.js';

import Button from 'muicss/lib/react/button';

function App() {
  // functional state
  const [settings, setSettings] = useState(DEFAULT_SETTINGS);
  const [bleClient] = useState(new BLEClient());
  const [firebaseClient] = useState(new FirebaseClient());

  // UI state
  const [showSettings, setShowSettings] = useState(false);
  const [currentDisplay, setCurrentDisplay] = useState('driverDisplay');

  function onData(data) {
    firebaseClient.addNewDataPoint(data);
  }

  // register/unregister the FirebaseClient with the BLEClient
  useEffect(() => {
    bleClient.register(onData);
    return () => {
      bleClient.unregister(onData);
    };
  // eslint-disable-next-line
  }, []);

  function toggleSettingsPage() {
    console.log(showSettings ? 'Exiting settings' : 'Going to settings');
    setShowSettings(!showSettings);
  }

  let mainDisplay = <DriverDisplay />;
  if (currentDisplay === 'observerDisplay') {
    mainDisplay = <ObserverDisplay />;
  }

  let toRender = (
    <div>
      <Button size='small' variant='fab' color='primary' className='App-settings-btn' onClick={toggleSettingsPage}>
        <img src={settingsImg} alt='settings' className='App-settings-btn-icon' />
      </Button>
      {mainDisplay}
    </div>
  );

  if (showSettings) {
    toRender = (
      <div>
        <Button size='small' variant='fab' color='primary' className='App-settings-btn' onClick={toggleSettingsPage}>
          X
        </Button>
        <Settings currentDisplay={currentDisplay} setCurrentDisplay={setCurrentDisplay} toggleSettingsPage={toggleSettingsPage}/>
      </div>
    );
  }

  return (
    <SettingsContext.Provider value={[settings, setSettings]}>
      <BLEClientContext.Provider value={bleClient}>
        <FirebaseClientContext.Provider value={firebaseClient}>
          <div className='App'>
            {toRender}
          </div>
        </FirebaseClientContext.Provider>
      </BLEClientContext.Provider>
    </SettingsContext.Provider>
  );
}

export default App;
