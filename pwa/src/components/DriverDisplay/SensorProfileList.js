import { Button, Checkbox } from 'muicss/react';
import React from 'react';
import {useState}  from 'react';
import SensorProfile from "../../utilities/DataProtocol/Profile"
export default class SensorProfileModule extends React.Component {
  constructor(props) {
    super(props)
    this.setRender = this.setRender.bind(this);

    this.state = {showList: false, profile: new SensorProfile()}

    this.checkBoxList = null; 

  }
  setRender(shouldRender) {
    this.setState({showList: shouldRender})
    
  }
  /**
   * Method outputs binary string.  The highest order bit indicates inclusion of the first sensor of the array,
   * second highest order bit indicates inclusion of the second sensor of the array, and so on.  
   */
  submitData(){
    this.setState({showList: false})
    let bitString = 0b0;
    this.state.profile.sensors.forEach(sensor => {
      if(sensor.running){
        bitString += 0b1
      }
      bitString *= 0b10
      bitString <<= 0;
      sensor.running = false;
    });
    
    console.log(bitString);
  }
  
  render(){
    let updateCheckBox = (sensor) => {
      sensor.running = !sensor.running
    }
    
    let divStyle = {
      width: "300px", margin:"auto", border: "dotted red 3px"
    }
    let checkStyle = {
      display: "flex", width: "200px", margin:"10px"
    }

    this.checkBoxList = this.state.profile.sensors.map((sensor) => {
      return (<Checkbox style={checkStyle} value = {sensor.valueName} label = {sensor.valueName} key = {sensor.valueName} onClick={() => updateCheckBox(sensor)}/>
    )});

    const render = this.state.showList;
    let list;
    if(render){
      list = <div style = {divStyle}>
        
        <ul>
        {
          this.checkBoxList
        }
        </ul>
      <Button variant='raised' onClick={() => this.submitData()}>
          Submit
        </Button>
        </div>
    } else {
      list = null;
    }
  
      return (        
        <div id='sensorlist'>
          <Button variant='raised' className='DriverDisplay-setting-btn' onClick = {() => this.setRender(true)}>
          Create Sensor Profile
        </Button>
        {list}
       
        </div>   
    );
  
    }
  }
  
  

  