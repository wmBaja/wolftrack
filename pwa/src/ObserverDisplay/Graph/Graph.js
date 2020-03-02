import Dygraph from 'dygraphs';
import React from 'react';

class Graph extends React.Component {
  constructor(props) {
    super(props);
    this.data = props.data;
    this.options = props.options;
  }

  render() {
    return <div ref="chart"></div>;
  }

  componentDidMount() {
    new Dygraph(this.refs.chart, this.data, this.options);
  }

}

export default Graph;