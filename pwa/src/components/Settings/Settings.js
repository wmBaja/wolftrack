import React, { useState, useContext } from 'react';
import Option from 'muicss/lib/react/option';
import Select from 'muicss/lib/react/select';
import Button from 'muicss/lib/react/button';
import { Checkbox } from 'muicss/react';

import './Settings.css';

import DriverDisplaySettings from './DriverDisplaySettings/DriverDisplaySettings.js';
import BLEClientContext from '../../utilities/BLEClient/BLEClientContext.js';

import FirebaseStatus from '../common/FirebaseStatus/FirebaseStatus.js';

import SensorProfile from "../../utilities/DataProtocol/Profile"

function Settings(props) {
  const { currentDisplay, setCurrentDisplay, toggleSettingsPage } = props;

  const state = {showList: false, profile: new SensorProfile()}
  // BLE state
  const bleClient = useContext(BLEClientContext);
  const [bleConnected, setBleConnected] = useState(bleClient.connected);

  async function disconnectFromVehicle() {
    console.log('Disconnecting from vehicle...');
    await bleClient.disconnect();
    setBleConnected(bleClient.connected);
  }

  function switchDisplays() {
    console.log('Switching displays...');
    if (currentDisplay === 'driverDisplay') {
      setCurrentDisplay('observerDisplay');
    } else {
      setCurrentDisplay('driverDisplay');
    }
    toggleSettingsPage();
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
    <div className='Settings'>
      <h1>Settings</h1>

      <FirebaseStatus />

      <div className='Settings-control-btns'>
        {
          bleConnected ?
          <div>
            <Button variant='raised' className='Settings-disconnect-vehicle-btn' onClick={disconnectFromVehicle}>
              Disconnect from vehicle
            </Button>
            <br/>
          </div> : ''
        }
        <Button variant='raised' className='Settings-disconnect-vehicle-btn' onClick={switchDisplays}>
          {currentDisplay === 'driverDisplay' ?
          'Switch to Observer Display' :
          'Switch to Driver Display'}
        </Button>
      </div>
        {checkBoxList}
        <Button variant='raised' onClick={() => submitData()}>Add Sensors</Button>

      <DriverDisplaySettings />

      <h2>Observer Display Settings</h2>
      <form>
        <Select name='base' label='Base Display'>
          <Option value='blah' label='BLAH' />
        </Select>
      </form>
    </div>
  );
}

export default Settings;
