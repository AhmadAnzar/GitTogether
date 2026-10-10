import { useEffect, useRef, useState } from 'react';
import * as api from '../api.js';
import { CloseIcon } from './Icons.jsx';

/** Log in / sign up. `mode` is 'login' or 'register'; `reason` explains why we're asking. */
export default function AuthModal({ mode: initialMode, reason, onAuthed, onClose }) {
  const [mode, setMode] = useState(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const emailField = useRef(null);
  const registering = mode === 'register';

  useEffect(() => {
    emailField.current?.focus();
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const user = registering ? await api.register(email, password) : await api.login(email, password);
      onAuthed(user);
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const switchMode = () => {
    setMode(registering ? 'login' : 'register');
    setError('');
  };

  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <form className="sheet sheet-narrow" onSubmit={submit} aria-labelledby="auth-title">
        <div className="sheet-head">
          <div>
            <p className="eyebrow">{registering ? 'git init' : 'git checkout'}</p>
            <h2 id="auth-title">{registering ? 'Create your account' : 'Welcome back'}</h2>
          </div>
          <button type="button" className="icon-btn" onClick={onClose} aria-label="Close"><CloseIcon /></button>
        </div>

        <div className="sheet-body">
          {reason && <p className="auth-reason">{reason}</p>}
          <label className="field">
            <span>Email</span>
            <input
              ref={emailField}
              type="email"
              autoComplete="email"
              required
              maxLength={254}
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@university.edu"
            />
          </label>
          <label className="field">
            <span>Password {registering && <em>at least 8 characters</em>}</span>
            <input
              type="password"
              autoComplete={registering ? 'new-password' : 'current-password'}
              required
              minLength={8}
              maxLength={128}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && <p className="form-error" role="alert">{error}</p>}
        </div>

        <div className="sheet-foot sheet-foot-split">
          <button type="button" className="btn-text" onClick={switchMode}>
            {registering ? 'I already have an account' : 'Create an account'}
          </button>
          <button type="submit" className="btn-primary" disabled={busy}>
            {busy ? 'One moment…' : registering ? 'Sign up' : 'Log in'}
          </button>
        </div>
      </form>
    </div>
  );
}
