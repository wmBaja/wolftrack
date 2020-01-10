import React from 'react';

import './Dashboard.css';

function formatFuelPerc(origFuelPerc) {
  let fuelPerc = origFuelPerc;
  if (fuelPerc < 0) {
    fuelPerc = 0;
  }
  fuelPerc = (fuelPerc * 100).toPrecision(2);
  return fuelPerc;
}

function Dashboard({ data }) {
  const { fuel, drivetrain } = data;

  const formattedPercentage = formatFuelPerc(fuel.remainingEMAPercentage);
  const formattedSpeed = drivetrain.speedMPH.toPrecision(2);

  return (
    <div className="Dashboard">
      <div className="Fuel">
        <div>
          <div className="Dashboard-data-num">{formattedPercentage}</div>
          <div className="Dashboard-data-unit">% Fuel</div>
        </div>
      </div>
      <div className="Speed">
      <div>
          <div className="Dashboard-data-num">{formattedSpeed}</div>
          <div className="Dashboard-data-unit">MPH</div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
