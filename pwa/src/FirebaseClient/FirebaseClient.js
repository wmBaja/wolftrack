import * as firebase from 'firebase/app';
import 'firebase/auth';
import 'firebase/firestore';

import firebaseConfig from './firebaseconfig.js';
firebase.initializeApp(firebaseConfig);

// the rate at which documents are uploaded
const UPLOAD_INTERVAL = 3000;
// the approximate time between data points
const DATA_POINT_INTERVAL = 200;
// the name of the collection to upload data to
const DATA_COLLECTION_ID = 'd';

export default class FirebaseClient {
  constructor() {
    this.firebase = firebase;
    this.db = firebase.firestore();
    this.user = null;
    firebase.auth().onAuthStateChanged(this._onAuthStateChanged.bind(this));

    // the currently buffered data points awaiting upload
    this.dataPoints = [];
  }

  _onAuthStateChanged(user) {
    if (user) {
      // get all the infos
      this.user = user;
    } else {
      // user just signed out
      this.user = null;
    }
  }

  isSignedIn() {
    return this.user !== null;
  }

  async signIn(email, password) {
    try {
      await firebase.auth().signInWithEmailAndPassword(email, password);
      return true;
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  async signOut() {
    await firebase.auth().signOut();
    return true;
  }

  buildDocument() {
    const timestamp = firebase.firestore.Timestamp.fromMillis(this.docTime);

    // build the array of data points into Firestore blob form
    const blobs = this.dataPoints.map((dataPoint) => {
      return firebase.firestore.Blob.fromUint8Array(dataPoint);
    });

    const doc = {
      t: timestamp,
      d: blobs,
    };

    // delete dataPoints and docTime
    this.dataPoints = [];
    this.docTime = null;

    return doc;
  }

  async _uploadNewDocument() {
    // build the document from the collected data points
    const doc = this.buildDocument();

    const collectionRef = this.db.collection(DATA_COLLECTION_ID);
    try {
      await collectionRef.add(doc);
      return true;
    } catch (error) {
      console.log('Error while uploading document: ', error);
      return false;
    }
  }

  addNewDataPoint(data) {
    if (data.rawData.byteLength !== 16) {
      console.log('Non-protocol number of bytes in data array: ' + data.rawData.byteLength);
      console.log('Undefined behavior expected...');
    }
    const sensorDataView = data.rawData;
    const geoCoordinate = {lat: 35.789799, lon: -78.699365}; // TODO once geolocation is implemented, change this to be the actual geo coordinate

    // construct the data point's array buffer
    const dataPointBuffer = new ArrayBuffer(32);
    const dataPointDataView = new DataView(dataPointBuffer);

    // transfer sensor data to data point buffer 4 bytes at a time
    for (let i = 0; i < sensorDataView.byteLength; i += 4) {
      dataPointDataView.setUint32(i, sensorDataView.getUint32(i));
    }

    // place geo coordinate in the last 16 bytes
    dataPointDataView.setFloat64(16, geoCoordinate.lat);
    dataPointDataView.setFloat64(24, geoCoordinate.lon);

    this.dataPoints.push(new Uint8Array(dataPointBuffer));
    if (!this.docTime) {
      this.docTime = Date.now();
    }
  }
}
