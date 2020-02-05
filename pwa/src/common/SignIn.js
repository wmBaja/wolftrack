import React, { useState } from 'react';

import Panel from 'muicss/lib/react/panel';
import Input from 'muicss/lib/react/input';
import Button from 'muicss/lib/react/button';

import './SignIn.css';

function SignIn(props) {
  const { prompt, onSignIn } = props;

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  function onEmailChange(event) {
    setEmail(event.target.value);
  }

  function onPasswordChange(event) {
    setPassword(event.target.value);
  }

  return (
    <Panel className='SignIn-panel'>
      <p>{prompt}</p>
      <Input label='Email' type='email' value={email} onChange={onEmailChange} />
      <Input label='Password' type='password' value={password} onChange={onPasswordChange} />
      <Button variant='raised' onClick={() => onSignIn(email, password)}>
        Sign In
      </Button>
    </Panel>
  );
}

export default SignIn;
