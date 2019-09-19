import React from 'react';

import './Dashboard.css';

function Dashboard({ data }) {
  const { fuelData, gpsData } = data;

  const formattedPercentage = (fuelData.remainingPercentage * 100).toPrecision(2);
  const formattedSpeed = (gpsData.speed).toPrecision(2);

  return (
    <div className="Dashboard">
      <div className="Fuel">
        <div>
          <div class="Dashboard-data-num">{formattedPercentage}</div>
          <div class="Dashboard-data-unit">% Fuel</div>
        </div>
      </div>
      <div className="Speed">
      <div>
          <div class="Dashboard-data-num">{formattedSpeed}</div>
          <div class="Dashboard-data-unit">MPH</div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
