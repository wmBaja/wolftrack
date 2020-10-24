import * as firebase from 'firebase/app';
import 'firebase/auth';
import 'firebase/firestore';

import firebaseConfig from './firebaseconfig.js';
firebase.initializeApp(firebaseConfig);

// the rate at which documents are uploaded
const UPLOAD_INTERVAL = 3000;
// the name of the collection to upload data to
const DATA_COLLECTION_ID = 'z';

export default class FirebaseClient {
  constructor() {
    this.firebase = firebase;
    this.db = firebase.firestore();
    this.user = null;
    firebase.auth().onAuthStateChanged(this._onAuthStateChanged.bind(this));

    // the currently buffered data points awaiting upload
    this.dataPoints = [];
    // the time that the first data point (currently awaiting upload) came in
    this.docTime = null;


    this.uploadIntervalId = setInterval(this._upload.bind(this), UPLOAD_INTERVAL);
  }

///////// AUTHENTICATION ///////////
  /**
   * A callback for monitoring for changes to auth state.
   * @param {object} user all of the currently signed-in user's information
   */
  _onAuthStateChanged(user) {
    if (user) {
      // get all the infos
      this.user = user;
    } else {
      // user just signed out
      this.user = null;
    }
  }

  /**
   * Returns whether or not a user is currently signed in.
   * @return whether or not a user is currently signed in
   */
  isSignedIn() {
    return this.user !== null;
  }

  /**
   * Signs a user in with the given email and password
   * @param {string} email the user's email
   * @param {string} password the user's password
   * @return true if the user was successfully signed in
   * @throws an error if the user was not successfully signed in
   */
  async signIn(email, password) {
    try {
      await firebase.auth().signInWithEmailAndPassword(email, password);
      return true;
    } catch (error) {
      console.log(error);
      throw error;
    }
  }

  /**
   * Signs out the currently signed in user.
   * @return true if the user is successfully signed out
   */
  async signOut() {
    await firebase.auth().signOut();
    return true;
  }
///////// AUTHENTICATION //////////


///////// FIRESTORE OPERATIONS ////////
  async _upload() {
    console.log('Attempting upload...');
    if (!this.isSignedIn()) {
      console.log('Upload aborted. No user is signed in.');
      return;
    }
    const doc = this._buildDocument();
    if (!doc) {
      console.log('Upload aborted. There is no data to upload.');
      return;
    }
    const success = await this._uploadNewDocument(doc);
    console.log(success ? 'Upload successful.' : 'Upload failed.');
  }

  /**
   * Builds a new document from the current data points and doc time.
   * Resets the data points and doc time after they have been used to
   * create the document.
   * @return a new document ready for upload
   */
  _buildDocument() {
    if (this.dataPoints.length < 1) {
      return null;
    }
    const timestamp = firebase.firestore.Timestamp.fromMillis(this.docTime);

    // transform the array of data points into Firestore blob form
    const blobs = this.dataPoints.map((dataPoint) => {
      return firebase.firestore.Blob.fromUint8Array(dataPoint);
    });

    const doc = {
      t: timestamp,
      d: blobs,
    };

    // reset dataPoints and docTime
    this.dataPoints = [];
    this.docTime = null;

    return doc;
  }

  /**
   * Uploads the given document to the data collection on Firestore.
   * @param {object} doc the document to upload
   */
  async _uploadNewDocument(doc) {
    if (!doc) {
      return false;
    }
    const collectionRef = this.db.collection(DATA_COLLECTION_ID);
    try {
      await collectionRef.add(doc);
      return true;
    } catch (error) {
      console.log('Error while uploading document: ', error);
      // TODO add this document to a list of failed uploads
      // this.failedUploads.push(doc);
      // we can periodically be running a function that batch writes
      // failed uploads; the max number of failed uploads should be constrained
      return false;
    }
  }

  /**
   * Adds a new data point to the internal list of data points awaiting upload.
   * @param {object} data data in the format that the DataDecoder produces
   */
  addNewDataPoint(data) {
    return;
    const sensorDataView = data.rawData;
    if (sensorDataView.byteLength !== 16) {
      console.log('Non-protocol number of bytes in data array: ' + data.rawData.byteLength);
      console.log('The data point will not be added.');
      return;
    }
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

    // add the data point to the dataPoints array as a Uint8Array
    this.dataPoints.push(new Uint8Array(dataPointBuffer));
    // if this is the first data point for this document
    if (this.dataPoints.length === 1) {
      this.docTime = Date.now();
    }
  }
}
