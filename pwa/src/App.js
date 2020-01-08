import React from 'react';

import './App.css';
import DriverDisplay from './DriverDisplay/DriverDisplay.js';
import BLEClientContext from './BLEClient/BLEClientContext.js';
import BLEClient from './BLEClient/BLEClient.js';

function App() {
  return (
    <BLEClientContext.Provider value={new BLEClient()}>
      <div className='App'>
        <DriverDisplay />
      </div>
    </BLEClientContext.Provider>
  );
}

export default App;
