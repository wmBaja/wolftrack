import * as firebase from 'firebase/app';

import 'firebase/auth';

export default class FirebaseClient {
  constructor() {
    this.firebase = firebase;
    this.user = null;
    firebase.auth().onAuthStateChanged(this.onAuthStateChanged);
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
