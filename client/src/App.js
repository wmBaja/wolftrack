import React, { Component, useState } from 'react';
import ReactMapGL from 'react-map-gl';
import { fromJS } from 'immutable';

import './App.css';
import './mapbox-gl.css';

import mapStyle from './mapbox-style/style.json';
import testGeo from './mapbox-style/test.geojson';

import { sendMsg, onHwData } from './api.js';

const dataLayer = fromJS({
  id: 'data',
  source: 'testData',
  type: 'fill',
  interactive: true,
  layout: {},
  paint: {
    'fill-color': "hsla(131, 86%, 55%, 0.6)",
    'fill-outline-color': "hsl(164, 89%, 59%)"
  }
});

function App() {
  const [fuelPerc, setFuelPerc] = useState(0);
  onHwData((data) => {
    if (data.type === 'fuel_data') {
      console.log('updating fuel perc', data.value.remainingPercentage);
      setFuelPerc(data.value.remainingPercentage);
    }
  });

  return (
    <div className="App">
      <header className="App-header">
        <h1>Henlo</h1>
        <button onClick={sendMsg}>Send a message</button>
        {/* <Map /> */}
        <div className="Speed">
          {fuelPerc}
        </div>
      </header>
    </div>
  );
}

class Map extends Component {
  state = {
    mapStyle: fromJS(mapStyle),
    viewport: {
      width: '100vw',
      height: '100vh',
      latitude: 35.7898,
      longitude: -78.6993,
      zoom: 18
    }
  };

  componentDidMount() {
    this._loadData(testGeo);
  }

  _loadData = data => {
    const mapStyle = this.state.mapStyle
      // Add geojson source to map
      .setIn(['sources', 'testData'], fromJS({type: 'geojson', data}))
      // Add point layer to map
      .set('layers', this.state.mapStyle.get('layers').push(dataLayer));

    this.setState({data, mapStyle});
  };

  render() {
    return (
      <ReactMapGL
        {...this.state.viewport}
        onViewportChange={(viewport) => this.setState({viewport})}
        mapStyle={this.state.mapStyle}
      />
    );
  }
}

export default App;
