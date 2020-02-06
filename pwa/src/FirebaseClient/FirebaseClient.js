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
}
