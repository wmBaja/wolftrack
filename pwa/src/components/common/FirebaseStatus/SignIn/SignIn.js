import React, { useState } from 'react';

import Form from 'muicss/lib/react/form';
import Input from 'muicss/lib/react/input';
import Button from 'muicss/lib/react/button';

import './SignIn.css';

function SignIn(props) {
  const { onSignIn } = props;

  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  function onEmailChange(event) {
    setEmail(event.target.value);
  }

  function onPasswordChange(event) {
    setPassword(event.target.value);
  }

  async function signIn(email, password) {
    setLoading(true);
    try {
      await onSignIn(email, password);
    } catch (error) {
      setEmail('');
      setPassword('');
      setLoading(false);
    }
    // NOTE: It's assumed that this component will be unmounted if the sign-in process
    // is successful so the following call will cause a memory leak warning.
    // setLoading(false);
  }

  return (
    <Form>
      <Input label='Email' type='email' value={email} onChange={onEmailChange} />
      <Input label='Password' type='password' value={password} onChange={onPasswordChange} />
      <Button variant='raised' onClick={() => signIn(email, password)} disabled={loading}>
        {!loading ? 'Sign In' : '...'}
      </Button>
    </Form>
  );
}

export default SignIn;
