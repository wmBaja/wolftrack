import React, { useContext } from 'react';

import SettingsContext from '../../../utilities/Settings/SettingsContext.js';

import './PureInfoDisplay.css';

function formatFuelPerc(origFuelPerc) {
  let fuelPerc = origFuelPerc;
  if (fuelPerc < 0) {
    fuelPerc = 0;
  }
  fuelPerc = (fuelPerc * 100).toPrecision(2);
  return fuelPerc;
}

function getValueAndUnitFor(typeOfValue, data) {
  switch(typeOfValue) {
    case 'PERCENT_FUEL':
      return [formatFuelPerc(data.fuel.remainingEMAPercentage), '% Fuel'];
    case 'LITERS_FUEL':
      return [data.fuel.remainingEMALiters.toPrecision(2), 'L Fuel'];
    case 'SPEED':
      return [data.drivetrain.speedMPH.toPrecision(2), 'MPH'];
    case 'ENGINE_RPM':
      return [data.drivetrain.engineRPM, 'Eng RPM'];
    case 'SEC_RPM':
      return [data.drivetrain.secRPM, 'Sec RPM'];
    case 'CVT_RATIO':
      return [data.drivetrain.cvtRatio.toPrecision(2), 'CVT Ratio'];
    case 'CVT_TEMPERATURE':
      return [data.drivetrain.cvtTemperatureCelsius, 'Temp C'];
    case 'ACCELERATION':
      return [0, 'G'];
    case 'SHOCK_ACTUATION_1':
      return [data.suspension.shock1actuationInches.toPrecision(2), 'S1 in'];
    case 'SHOCK_ACTUATION_2':
      return [data.suspension.shock2actuationInches.toPrecision(2), 'S2 in'];
    case 'FRONT_BRAKE_PRESSURE':
      return [data.brakes.frontBrakePressurePsi, 'FB psi'];
    case 'REAR_BRAKE_PRESSURE':
      return [data.brakes.rearBrakePressurePsi, 'RB psi'];
    default:
      return ['ERROR', 'ERROR'];
  }
}

function PureInfoDisplay({ data }) {
  const [settings] = useContext(SettingsContext);

  const numValuesToDisplay = settings.driverDisplay['PURE_INFO'].displayedValues.length;

  const valueDisplays = settings.driverDisplay['PURE_INFO'].displayedValues.map((typeOfValue) => {
    const [value, unit] = getValueAndUnitFor(typeOfValue, data);
    return (
      <div className={typeOfValue} key={typeOfValue}>
        <div>
          <div className='PureInfoDisplay-data-num'>{value}</div>
          <div className='PureInfoDisplay-data-unit'>{unit}</div>
        </div>
      </div>
    );
  });

  // const formattedPercentage = formatFuelPerc(fuel.remainingEMAPercentage);
  // const formattedSpeed = drivetrain.speedMPH.toPrecision(2);

  return (
    <div className={'PureInfoDisplay values-' + numValuesToDisplay}>
      {valueDisplays}
      {/* <div className='Fuel'>
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
      </div> */}
    </div>
  );
}

export default PureInfoDisplay;
