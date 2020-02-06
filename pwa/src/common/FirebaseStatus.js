import React, { useState, useContext, useEffect } from 'react';

import Panel from 'muicss/lib/react/panel';
import Button from 'muicss/lib/react/button';

import SignIn from './SignIn.js';

import FirebaseClientContext from '../FirebaseClient/FirebaseClientContext.js';

import './FirebaseStatus.css';

const SIGNED_IN_PROMPT = 'You are signed in. Data will be uploaded to the database.';
const SIGNED_OUT_PROMPT = 'You are not signed in. Data will NOT be uploaded to the database.';

function FirebaseStatus() {
  // Firebase state
  const firebaseClient = useContext(FirebaseClientContext);
  const [signedIn, setSignedIn] = useState(firebaseClient.isSignedIn());

  // UI state
  const [error, setError] = useState('');

  function onFbAuthChange(user) {
    const isUser = user ? true : false;
    setSignedIn(isUser);
    if (isUser) {
      setError('');
    }
  }

  // register/unregister the onFbAuthChange callback with firebase
  useEffect(() => {
    const unsub = firebaseClient.firebase.auth().onAuthStateChanged(onFbAuthChange);
    return unsub;
  });

  async function signIn(email, password) {
    try {
      const result = await firebaseClient.signIn(email, password);
      setSignedIn(result);
      return true;
    } catch (error) {
      setError(error.message);
      throw error;
    }
  }

  let prompt = SIGNED_IN_PROMPT;
  if (!signedIn) {
    prompt = SIGNED_OUT_PROMPT;
  }

  return (
    <Panel className='FirebaseStatus'>
      <div className='mui--text-title FirebaseStatus-title'>Database Status</div>
      {error ? <p className='FirebaseStatus-error-text'>{error}</p> : ''}
      <p>{prompt}</p>
      {
        signedIn ?
        <Button variant='raised' onClick={firebaseClient.signOut}>
          Sign out
        </Button> :
        <SignIn prompt={prompt} onSignIn={signIn} />
      }
    </Panel>
  );
}

export default FirebaseStatus;
