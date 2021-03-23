import { Button, Checkbox } from 'muicss/react';
import React from 'react';
import {useState}  from 'react';
import SensorProfile from "../../utilities/DataProtocol/Profile"
export default class SensorProfileModule extends React.Component {
  constructor(props) {
    super(props)
    this.setRender = this.setRender.bind(this);
    this.profile = new SensorProfile();

    this.state = {showList: false, sensors: this.profile.sensors}

  }
  setRender(shouldRender) {
    this.setState({showList: shouldRender})
    
  }
  submitData(){
    this.setState({showList: false})
    console.log("Data submitted")
  }
  render(){
    let divStyle = {
      width: "300px", margin:"auto", border: "dotted red 3px"
    }
    let checkStyle = {
      display: "flex", width: "200px", margin:"10px"
    }
    const render = this.state.showList;
    let list;
    if(render){
      list = <div style = {divStyle}>
        
        <ul>
        {
          this.state.sensors.map((sensor) => {
            return (<Checkbox style={checkStyle} value = {sensor.valueName} label = {sensor.valueName} key = {sensor.valueName} />
          )})
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
  
  

  