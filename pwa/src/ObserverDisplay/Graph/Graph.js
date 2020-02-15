import Dygraph from 'dygraphs';
import React from 'react';

class Graph extends React.Component {


    render() {
      return <div ref="chart"></div>;
    }

  componentDidMount() {
    //const messages = [0, 2, 4, 6, 8];

    var data = [
      [1,10],
      [2,20],
      [3,50],
      [4,70]
    ] ;
    /*messages.forEach((response) => {
      data += response[0] + ',' + response[1] + "\n";
    });*/

    new Dygraph(this.refs.chart, data, {
      drawPoints: true,
      showRoller: true,
      labels: ['X', 'A'],
    });
  }

}

export default Graph;