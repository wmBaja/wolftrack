import React from 'react';

import './PureInfoDisplay.css';

function formatFuelPerc(origFuelPerc) {
  let fuelPerc = origFuelPerc;
  if (fuelPerc < 0) {
    fuelPerc = 0;
  }
  fuelPerc = (fuelPerc * 100).toPrecision(2);
  return fuelPerc;
}

function PureInfoDisplay({ data }) {
  const { fuel, drivetrain } = data;

  const formattedPercentage = formatFuelPerc(fuel.remainingEMAPercentage);
  const formattedSpeed = drivetrain.speedMPH.toPrecision(2);

  return (
    <div className='PureInfoDisplay'>
      <div className='Fuel'>
        <div>
          <div className='PureInfoDisplay-data-num'>{formattedPercentage}</div>
          <div className='PureInfoDisplay-data-unit'>% Fuel</div>
        </div>
      </div>
      <div className='Speed'>
      <div>
          <div className='PureInfoDisplay-data-num'>{formattedSpeed}</div>
          <div className='PureInfoDisplay-data-unit'>MPH</div>
        </div>
      </div>
    </div>
  );
}

export default PureInfoDisplay;
