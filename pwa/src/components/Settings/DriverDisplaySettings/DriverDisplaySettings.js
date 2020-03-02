import React, { useContext } from 'react';
import Option from 'muicss/lib/react/option';
import Select from 'muicss/lib/react/select';
import Checkbox from 'muicss/lib/react/checkbox';

// import './DriverDisplaySettings.css';

import SettingsContext from '../../../utilities/Settings/SettingsContext.js';
import { POSSIBLE_SETTINGS } from '../../../utilities/Settings/DEFAULT_SETTINGS.js';

function DriverDisplaySettings() {
  const [settings, setSettings] = useContext(SettingsContext);
  const selectedDriverBaseDisplay = settings.driverDisplay.base;

  function onBaseChange(ev) {
    const newValue = ev.target.value;
    setSettings(settings =>
      ({
        ...settings, // copy in the rest of the settings
        driverDisplay: {
          ...settings.driverDisplay, // copy in the rest of the driverDisplay settings
          base: newValue, // change the actual value that is changing
        }
      })
    );
  }

  function onDisplayedValuesChange(val, ev) {
    const checked = ev.target.checked;
    const copy = { ...settings };
    const displayedValues = copy.driverDisplay[copy.driverDisplay.base].displayedValues;
    if (checked) {
      // add the value to the displayed values
      displayedValues.push(val);
    } else {
      // remove the value from the displayed values
      const idx = displayedValues.indexOf(val);
      if (idx !== -1) {
        displayedValues.splice(idx, 1);
      }
    }

    setSettings(copy);
  }

  return (
    <div className='DriverDisplaySettings'>
      <h2>Driver Display Settings</h2>
      <form>
        <Select name='base' label='Base Display' value={selectedDriverBaseDisplay} onChange={onBaseChange}>
          {
            POSSIBLE_SETTINGS.driverDisplay.base.map((val) => <Option value={val} label={val} key={val} />)
          }
        </Select>
        <h3>{selectedDriverBaseDisplay} Settings</h3>
        <h4>Displayed Values</h4>
        {
          POSSIBLE_SETTINGS.driverDisplay[selectedDriverBaseDisplay].displayedValues.map((val) => {
            const checked = settings.driverDisplay[selectedDriverBaseDisplay].displayedValues.includes(val);
            return <Checkbox
              label={val}
              key={val}
              checked={checked}
              onChange={onDisplayedValuesChange.bind(null, val)}
            />;
          })
        }
      </form>
    </div>
  );
}

export default DriverDisplaySettings;
