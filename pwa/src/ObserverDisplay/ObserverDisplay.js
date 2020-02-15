import React,{useState} from 'react';
import { DEFAULT_DATA } from '../BLEClient/DEFAULT_DATA';
import Graph from "./Graph/Graph.js"

function ObserverDisplay() {
  //const [data, setData] = useState(DEFAULT_DATA);

  return (
    <div className='ObserverDisplay'>
      <Graph/>
    </div>
  );
}

export default ObserverDisplay;
