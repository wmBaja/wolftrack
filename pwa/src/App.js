import React, { useState } from 'react';

import './App.css';
import settings from './img/settings.svg';

import DriverDisplay from './DriverDisplay/DriverDisplay.js';
import BLEClientContext from './BLEClient/BLEClientContext.js';
import BLEClient from './BLEClient/BLEClient.js';

import Button from 'muicss/lib/react/button';

function App() {
  const [showSettings, setShowSettings] = useState(false);
  const [bleClient] = useState(new BLEClient());

  function toggleSettingsPage() {
    console.log(showSettings ? 'Exiting settings' : 'Going to settings');
    setShowSettings(!showSettings);
  }

  let toRender = (
    <div>
      <Button size='small' variant='fab' color='primary' className='App-settings-btn' onClick={toggleSettingsPage}>
        <img src={settings} alt='settings' className='App-settings-btn-icon' />
      </Button>
      <DriverDisplay />
    </div>
  );

  if (showSettings) {
    toRender = (
      <div>
        <Button size='small' variant='fab' color='primary' className='App-settings-btn' onClick={toggleSettingsPage}>
          X
        </Button>
        Settings
      </div>
    );
  }

  return (
    <BLEClientContext.Provider value={bleClient}>
      <div className='App'>
        {toRender}
      </div>
    </BLEClientContext.Provider>
  );
}

export default App;
