import React, { useState, useContext, useEffect } from 'react';
import Button from 'muicss/lib/react/button';

import './DriverDisplay.css';
import PureInfoDisplay from './PureInfoDisplay/PureInfoDisplay.js';
import SensorProfile from "../../utilities/DataProtocol/Profile"
import BLEClientContext from '../../utilities/BLEClient/BLEClientContext.js';
import { DEFAULT_DATA } from '../../utilities/DataProtocol/DEFAULT_DATA.js';
import { Checkbox } from 'muicss/react';
import FirebaseStatus from '../common/FirebaseStatus/FirebaseStatus.js';

function DriverDisplay() {
  const [data, setData] = useState(DEFAULT_DATA);
  var displayProfileList = false;
  // BLE state
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);
  const state = {showList: false, profile: new SensorProfile()}


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

  let updateCheckBox = (sensor) => {
    sensor.running = !sensor.running
  }
  
  let divStyle = {
    width: "300px", margin:"auto", border: "dotted red 3px"
  }
  let checkStyle = {
    display: "flex", width: "200px", margin:"10px"
  }
  let checkBoxList = state.profile.sensors.map((sensor) => {
    return (<Checkbox style={checkStyle} value = {sensor.valueName} label = {sensor.valueName} key = {sensor.valueName} onClick={() => updateCheckBox(sensor)}/>
  )});

  let submitData = () =>{
    let bitString = 0b0;
    state.profile.sensors.forEach(sensor => {
      if(sensor.running){
        bitString += 0b1
      }
      bitString *= 0b10
      bitString <<= 0;
      sensor.running = false;
    });
    
    console.log(bitString);
    bleClient.writeData(bitString);
  }

  
  return (
    <div className='DriverDisplay'>
      {bleConnected ?
      <PureInfoDisplay data={data} /> :
      <div className='DriverDisplay-statuses'>
        <h1>Driver Display</h1>
        <FirebaseStatus />
        <Button variant='raised' className='DriverDisplay-connect-btn' onClick={() => connectToVehicle(false)}>
          Connect to vehicle
        </Button>
        <br/>
        <Button variant='raised' className='DriverDisplay-simulate-btn' onClick={() => connectToVehicle(true)}>
          Simulate connection
        </Button>
        <Button variant='raised' onClick={() => submitData()}>Add Sensors</Button>
        <br/>
        {checkBoxList}

       
        
  
        
      </div>}
    </div>
  );
}

export default DriverDisplay;
