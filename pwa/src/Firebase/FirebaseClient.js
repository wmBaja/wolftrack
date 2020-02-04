import * as firebase from 'firebase/app';
import 'firebase/auth';

import firebaseConfig from './firebaseconfig.js';
firebase.initializeApp(firebaseConfig);

export default class FirebaseClient {
  constructor() {
    this.firebase = firebase;
    this.user = null;
    firebase.auth().onAuthStateChanged(this._onAuthStateChanged.bind(this));
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

  async signIn(email, password) {
    const result = await firebase.auth().signInWithEmailAndPassword(email, password);
    return true;
  }

  async signOut() {
    const result = firebase.auth().signOut();
    return true;
  }
}
