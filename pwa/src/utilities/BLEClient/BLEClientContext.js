import React from 'react';

const BLEClientContext = React.createContext({});

export default BLEClientContext;
// const BLEClientProvider = (props) => {
//   const [state, setState] = useState({});
//   return (
//     <BLEClientContext.Provider value={[state, setState]}>
//       {props.children}
//     </BLEClientContext.Provider>
//   );
// };

// export { BLEClientContext, BLEClientProvider };
