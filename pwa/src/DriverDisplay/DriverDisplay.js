import React, { useState, useEffect } from 'react';

import './DriverDisplay.css';
import { onHwData } from '../api.js';
import Dashboard from './Dashboard.js';

const initialState = {
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
  const [data, setData] = useState(initialState);

  useEffect(
    () => {
      const unsubscribe = onHwData((data) => {
        if (data.type === 'fuel_data') {
          console.log('Updating fuel data', data.value);
          setData(prevState => ({ ...prevState, fuelData: data.value }));
        } else if (data.type === 'gps_data') {
          console.log('Updating GPS data', data.value);
          setData(prevState => ({ ...prevState, gpsData: data.value }));
        }
      });
      return unsubscribe; // call unsubscribe when unmounting
    },
    [], // only run on mount and unmount
  );

  return (
    <div className="DriverDisplay">
      <Dashboard data={data} />
    </div>
  );
}

export default DriverDisplay;
