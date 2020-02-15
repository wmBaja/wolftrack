import React from 'react';
import { DEFAULT_DATA } from '../BLEClient/DEFAULT_DATA';

function ObserverDisplay() {
  const [data, setData] = useState(DEFAULT_DATA);

  return (
    <div className='ObserverDisplay'>
    </div>
  );
}

export default ObserverDisplay;
