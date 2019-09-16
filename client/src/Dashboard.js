import React from 'react';

import './Dashboard.css';
import { sendMsg } from './api.js';

function Dashboard({ data }) {
  const { fuelData } = data;

  const formattedPercentage = (fuelData.remainingPercentage * 100).toPrecision(2);
  const formattedSpeed = (34.56783).toPrecision(2);

  return (
    <div className="Dashboard">
      {/* <div> */}
        <button onClick={sendMsg} className="Message">Send a message</button>
      {/* </div> */}
      <div className="Fuel">
        {formattedPercentage}
      </div>
      <div className="Speed">
        {formattedSpeed}
      </div>
    </div>
  );
}

export default Dashboard;
