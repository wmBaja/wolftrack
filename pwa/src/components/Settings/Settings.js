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

  var profile = new SensorProfile();

  

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

  let handleChange = (e, sensor) =>{
    let isChecked = e.target.checked
    sensor.running = isChecked
    
  }
  
  let divStyle = {
    width: "300px", border: "dotted red 3px"
  }
  let checkStyle = {
    display: "flex", width: "200px", margin:"10px"
  }

  let checkBoxList = profile.sensors.map((sensor) => {
    return (<Checkbox style={checkStyle} value = {sensor.running} label = {sensor.valueName} key = {sensor.valueName} onChange = {e => handleChange(e, sensor)}/>
  )});

  let submitData = () =>{
    let b = new ArrayBuffer(20);
    var longInt32View = new Uint32Array(b);
    let int32 = 0b0;
    var includeExport = [];
    profile.sensors.forEach(sensor => {

      if(sensor.running){
        
        int32+=0b1;
        includeExport.push(sensor);

      }
      int32 = int32<<1;


    });
    console.log(includeExport);
    
    bleClient.setSensorProfile(includeExport);
    //bleClient.writeData(bitString);
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
      <div style = {divStyle}>
        <h2 style = {checkStyle}>Sensor Profile Configuration</h2>
        {checkBoxList}
        <Button variant='raised' onClick={() => submitData()}>Add Sensors</Button>
      </div>

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
